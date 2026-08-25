"""
Tareas Celery para ingesta asíncrona de correo -> Document Intake Service.

WARNING: FASE 2: Tareas asíncronas multi-tenant friendly con Celery.
WARNING: MAIL-16: este módulo YA NO importa ningún dominio consumidor
(Facturas/Compras/...) directamente. Solo conoce ReceivedDocument /
DocumentDispatcher (apps.services.document_intake) -- genérico, transversal.
Cada dominio se auto-registra como consumidor desde su propio
AppConfig.ready() (ver apps/tenant/facturas/apps.py,
apps/tenant/compras/apps.py). Agregar un nuevo dominio consumidor nunca
requiere modificar este archivo.

Principios:
- Multi-tenant por esquemas: Usa schema_context para aislamiento
- SSoT: No duplica lógica de parsing (document_ingest) ni de persistencia
  de dominio (delegada al DocumentHandler registrado para cada tipo)
- Idempotencia: Delegada al handler de dominio (ej. CUFE en Facturas)
- Reintentos: Configurados con backoff solo para errores transitorios (red/IO)
- Cancelación cooperativa: Lee estado CANCEL_REQUESTED desde BD (no usa self.is_aborted())
- Logging estructurado: Logger dedicado 'maildigester' para trazabilidad (sin secretos)
"""
from __future__ import annotations

import logging
from typing import Any, TypedDict

from celery import shared_task
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, ProgrammingError, transaction
from django.utils import timezone
from django_tenants.utils import schema_context

from apps.services.document_intake import DocumentSource, ProcessingStatus, ReceivedDocument
from apps.services.document_intake.dispatcher import dispatcher

# WARNING: IMPORT LAZY: Importar funciones de estado desde módulo puro (evita ciclos)
# Estas funciones se importan dentro de la función cuando se necesitan

logger = logging.getLogger("maildigester")


def _should_abort(tenant_schema: str, task_id: str) -> bool:
    """
    Verifica si la tarea debe abortar (cancelación cooperativa).
    
    Lee el estado CANCEL_REQUESTED desde BD dentro de schema_context.
    
    Args:
        tenant_schema: Nombre del esquema del tenant
        task_id: ID de la tarea Celery
        
    Returns:
        True si el run está en CANCEL_REQUESTED, False en caso contrario
    """
    from apps.tenant.facturas.models import MailIngestionRun
    
    try:
        with schema_context(tenant_schema):
            run = MailIngestionRun.objects.only("status").get(task_id=task_id)
            return run.status == "CANCEL_REQUESTED"
    except MailIngestionRun.DoesNotExist:
        return False
    except Exception:
        # Si hay error al leer BD, no abortar (evitar fallos en cascada)
        logger.warning("maildigester.abort_check_error", extra={"task_id": task_id})
        return False


def _update_run(tenant_schema: str, task_id: str, **fields):
    """
    Actualiza un MailIngestionRun de forma atómica.
    
    Usa select_for_update para evitar condiciones de carrera.
    
    Args:
        tenant_schema: Nombre del esquema del tenant
        task_id: ID de la tarea Celery
        **fields: Campos a actualizar (status, counts, finished_at, summary, etc.)
        
    Returns:
        MailIngestionRun actualizado o None si no existe
    """
    from apps.tenant.facturas.models import MailIngestionRun
    
    try:
        with schema_context(tenant_schema), transaction.atomic():
            run = (
                MailIngestionRun.objects
                .select_for_update()
                .get(task_id=task_id)
            )
            for k, v in fields.items():
                setattr(run, k, v)
            run.save()
            return run
    except MailIngestionRun.DoesNotExist:
        logger.warning("maildigester.update_run_not_found", extra={"task_id": task_id})
        return None
    except Exception as e:
        # No romper la tarea si falla la persistencia
        logger.warning("maildigester.update_run_error", extra={"task_id": task_id, "error": str(e)})
        return None


def _clasificar_excepcion(exc: Exception) -> str:
    """
    Clasifica una excepcion de procesamiento de un documento (FASE 3).

    Nunca debe usarse para decidir SI se loggea -- solo COMO se loggea y
    se cuenta. Un error de "programming" o "security" siempre se loggea
    con logger.error + exc_info=True (nunca silenciado bajo un warning
    generico), el resto con logger.warning + exc_info=True.
    """
    if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
        return "transient"
    if isinstance(exc, PermissionError):
        return "security"
    if isinstance(exc, (ImportError, AttributeError, ProgrammingError, NameError, TypeError)):
        return "programming"
    if isinstance(exc, IntegrityError):
        return "domain"
    if isinstance(exc, (DjangoValidationError, ValueError, KeyError)):
        return "validation"
    return "unknown"


class MailDigesterResult(TypedDict, total=False):
    """
    DTO de resultado de la tarea de ingesta de correo.
    
    Ejemplo:
        result = {
            "tenant_schema": "tenant_acme",
            "naturaleza": "VENTA",
            "processed_messages": 10,
            "attachments_found": 15,
            "archives_expanded": 3,
            "xml_detected": 12,
            "imported": 10,
            "duplicates": 2,
            "errors": 0,
            "details": [
                {"status": "imported", "numero": "FAC-123"},
                {"status": "duplicate", "message": "La factura con número 'FAC-124' ya existe."}
            ]
        }
    """
    tenant_schema: str
    naturaleza: str
    processed_messages: int
    attachments_found: int
    archives_expanded: int
    xml_detected: int
    imported: int
    duplicates: int
    errors: int
    details: list[dict[str, Any]]  # lista de eventos/resumen por archivo


def _build_result(tenant_schema: str, naturaleza: str) -> MailDigesterResult:
    """
    Construye un resultado inicial vacío.
    
    Args:
        tenant_schema: Nombre del esquema del tenant
        naturaleza: Naturaleza de las facturas (VENTA|COMPRA)
        
    Returns:
        MailDigesterResult inicializado con contadores en cero
    """
    return {
        "tenant_schema": tenant_schema,
        "naturaleza": naturaleza,
        "processed_messages": 0,
        "attachments_found": 0,
        "archives_expanded": 0,
        "xml_detected": 0,
        "imported": 0,
        "duplicates": 0,
        "errors": 0,
        "details": [],
    }


@shared_task(
    bind=True,
    name="apps.services.maildigester.tasks.fetch_and_process_billing_mail",  # FQN para registro explícito
    # Solo transitorios: red/IO/timeouts. EXCLUIR AttributeError u otros program errors.
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def fetch_and_process_billing_mail(
    self,
    tenant_schema: str,
    config_id: int,
    limit_messages: int = 50,
    naturaleza: str | None = None
):
    """
    Procesa correo → XML UBL → Facturas (histórico completo + incremental por UIDs).
    
    Cancelación cooperativa leyendo BD (CANCEL_REQUESTED).
    Procesamiento por UIDs IMAP para evitar reprocesar correos ya examinados.
    """
    task_id = self.request.id
    logger.info("maildigester.start", extra={"tenant_schema": tenant_schema, "task_id": task_id, "config_id": config_id})
    
    try:
        # 1) RUNNING
        _update_run(tenant_schema, task_id, status="RUNNING")
        
        # 2) Abort cooperativo (inicio)
        if _should_abort(tenant_schema, task_id):
            _update_run(tenant_schema, task_id, status="CANCELED", finished_at=timezone.now())
            return {"ok": False, "canceled": True}
        
        # 3) Resolver config desde BD (sin credenciales en payload)
        from apps.services.maildigester import pipeline
        from apps.tenant.empresa.services import get_mailbox_config

        with schema_context(tenant_schema):
            mailbox_config = get_mailbox_config(config_id)

            # 3b) Resolver empresa_id del tenant (nunca se infiere desde el DTO)
            from apps.tenant.empresa.models import MailInboxConfig
            empresa_id = MailInboxConfig.objects.only("empresa_id").get(id=config_id).empresa_id

            # 3c) MAIL-17: resolver run_id una sola vez para el detalle por documento
            from apps.tenant.facturas.models import DocumentProcessing, MailIngestionRun
            run_id = MailIngestionRun.objects.only("id").get(task_id=task_id).id

            # 4) Obtener estado del buzón (último UID procesado)
            # WARNING: IMPORT LAZY: Importar desde módulo puro (evita ciclos)
            from apps.tenant.facturas.inbox_state import get_or_create_inbox_state
            
            inbox_state = get_or_create_inbox_state(config_id)
            start_uid = inbox_state.last_seen_uid  # None = histórico completo, int = incremental
            
            mode = "histórico completo" if start_uid is None else f"incremental (desde UID {start_uid + 1})"
            logger.info(
                "maildigester.mode",
                extra={
                    "tenant_schema": tenant_schema,
                    "config_id": config_id,
                    "mode": mode,
                    "task_id": task_id,
                }
            )
            
            # 5) Procesar por lotes (UIDs)
            counts = {"processed": 0, "xml_detected": 0, "imported": 0, "duplicates": 0, "errors": 0}
            batch_size = limit_messages  # Usar limit_messages como tamaño de lote
            current_uid = start_uid
            total_messages_processed = 0
            
            # Procesar en lotes hasta que no haya más mensajes o se cancele
            while True:
                # Abort cooperativo antes de cada lote
                if _should_abort(tenant_schema, task_id):
                    # Actualizar estado con el último UID procesado antes de cancelar
                    if current_uid is not None:
                        # WARNING: IMPORT LAZY: Importar desde módulo puro (evita ciclos)
                        from apps.tenant.facturas.inbox_state import update_inbox_state
                        update_inbox_state(config_id, current_uid, total_messages_processed)
                    _update_run(tenant_schema, task_id, status="CANCELED", counts=counts, finished_at=timezone.now())
                    return {"ok": False, "canceled": True, "counts": counts}
                
                # Obtener lote de mensajes por UID
                xml_items, last_uid = pipeline.collect_invoice_xml_from_mailbox_by_uid(
                    mailbox_config,
                    start_uid=current_uid,
                    batch_size=batch_size,
                    naturaleza=naturaleza,
                    should_abort=lambda: _should_abort(tenant_schema, task_id)
                )
                
                # Si no hay mensajes nuevos, terminar
                if not xml_items:
                    if last_uid is None or last_uid == current_uid:
                        # No hay más mensajes para procesar
                        break
                
                # Procesar XMLs del lote
                batch_messages = 0
                for item in xml_items:
                    # Abort cooperativo durante el loop
                    if _should_abort(tenant_schema, task_id):
                        if current_uid is not None:
                            # WARNING: IMPORT LAZY: Importar desde módulo puro (evita ciclos)
                            from apps.tenant.facturas.inbox_state import update_inbox_state
                            update_inbox_state(config_id, current_uid, total_messages_processed)
                        _update_run(tenant_schema, task_id, status="CANCELED", counts=counts, finished_at=timezone.now())
                        return {"ok": False, "canceled": True, "counts": counts}
                    
                    counts["processed"] += 1
                    batch_messages += 1
                    
                    try:
                        # WARNING: v2.37: Usar pipeline universal SOLO para parsear/validar (NO persiste)
                        from apps.services.document_ingest.ingest_service import ingest_document
                        
                        # Convertir XML texto a bytes
                        xml_bytes = item["xml_text"].encode("utf-8") if isinstance(item["xml_text"], str) else item["xml_text"]
                        source_filename = item.get("source_filename", "ubl.xml")
                        
                        # Llamar al pipeline universal (SOLO parsing, preview=True para obtener DTO)
                        parsed, status_code = ingest_document(
                            content=xml_bytes,
                            filename=source_filename,
                            mime_type="application/xml",
                            kind_hint="xml",
                            preview=True,  # Siempre preview - document_ingest NO persiste
                            async_mode=False
                        )

                        # Verificar si hubo error en el parsing
                        if status_code != 200 or parsed.get("error"):
                            counts["errors"] += 1
                            error_msg = parsed.get("message", "Error al parsear XML")
                            logger.warning(
                                "maildigester.parse_error",
                                extra={
                                    "tenant_schema": tenant_schema,
                                    "task_id": task_id,
                                    "source_filename": source_filename,
                                    "error": parsed.get("error", "unknown"),
                                    # WARNING: BUGFIX MAIL-17: "message" es un atributo reservado de
                                    # logging.LogRecord -- usarlo como key de extra={} lanza
                                    # KeyError("Attempt to overwrite 'message' in LogRecord") SIEMPRE
                                    # que este codepath se ejecuta, enmascarando el parse_error real
                                    # bajo un error de logging distinto. Bug preexistente, hallado al
                                    # verificar MAIL-17 con un documento invalido real.
                                    "error_detail": error_msg,
                                }
                            )
                            DocumentProcessing.objects.create(
                                empresa_id=empresa_id, run_id=run_id,
                                source="EMAIL", filename=source_filename,
                                status="INVALID", error_message=error_msg,
                            )
                            continue

                        # Obtener DTO del resultado
                        dto = parsed.get("dto", {})
                        if not dto:
                            counts["errors"] += 1
                            logger.warning(
                                "maildigester.empty_dto",
                                extra={
                                    "tenant_schema": tenant_schema,
                                    "task_id": task_id,
                                    "source_filename": source_filename,
                                }
                            )
                            DocumentProcessing.objects.create(
                                empresa_id=empresa_id, run_id=run_id,
                                source="EMAIL", filename=source_filename,
                                status="INVALID", error_message="empty_dto",
                            )
                            continue
                        
                        # WARNING: MAIL-16: dispatch generico -- este modulo ya NO conoce
                        # Facturas. El dto ya parseado viaja en metadata para que el handler
                        # no tenga que volver a parsear el mismo XML (ver InvoiceHandler).
                        # FacturaBusinessService.guardar_desde_dto() sigue siendo el SSoT real
                        # de persistencia (FASE 1); solo cambio COMO se le llama, no que se
                        # llama a el.
                        doc_type = dto.get("type") or dto.get("document_type") or ""
                        document = ReceivedDocument(
                            tenant_schema=tenant_schema,
                            source=DocumentSource.EMAIL,
                            content=xml_bytes,
                            filename=source_filename,
                            mime_type="application/xml",
                            document_type=doc_type,
                            message_id=item.get("source_email_id"),
                            metadata={"empresa_id": empresa_id, "dto": dto},
                        )
                        result = dispatcher.dispatch(document)

                        # MAIL-17: fila de detalle por documento, siempre (SUCCESS incluido) --
                        # sin esto no se puede responder "que paso con este XML especifico"
                        # sin parsear MailIngestionRun.summary como texto libre.
                        DocumentProcessing.objects.create(
                            empresa_id=empresa_id,
                            run_id=run_id,
                            document_id=document.document_id,
                            source=document.source,
                            filename=document.filename,
                            document_type=doc_type,
                            handler=result.handler,
                            domain=result.domain,
                            status=result.status,
                            numero=result.metadata.get("numero"),
                            error_message="; ".join(result.errors) if result.errors else None,
                        )

                        if result.status == ProcessingStatus.SUCCESS:
                            counts["imported"] += 1
                            logger.info(
                                "maildigester.imported",
                                extra={
                                    "tenant_schema": tenant_schema,
                                    "task_id": task_id,
                                    "handler": result.handler,
                                    "numero": result.metadata.get("numero"),
                                    "cufe": result.metadata.get("cufe"),
                                }
                            )
                        elif result.status == ProcessingStatus.DUPLICATE:
                            # Idempotencia real (por CUFE/CUDE o por numero) -- documento ya existia
                            counts["duplicates"] += 1
                            logger.info(
                                "maildigester.duplicate",
                                extra={
                                    "tenant_schema": tenant_schema,
                                    "task_id": task_id,
                                    "handler": result.handler,
                                    "numero": result.metadata.get("numero"),
                                }
                            )
                        else:
                            # INVALID / FAILED / REQUIRES_REVIEW / PARTIAL -- ninguno es exito
                            # (FASE 2: nunca SUCCESS falso). El dispatcher ya clasifico/loggeo
                            # con exc_info=True cualquier excepcion real del handler.
                            counts["errors"] += 1
                            logger.warning(
                                "maildigester.import_error",
                                extra={
                                    "tenant_schema": tenant_schema,
                                    "task_id": task_id,
                                    "status": result.status,
                                    "handler": result.handler,
                                    "domain": result.domain,
                                    "errors": result.errors,
                                }
                            )
                    
                    except Exception as e:
                        # FASE 3: clasificar tambien los errores de la etapa de parsing (previa a persistencia)
                        error_type = _clasificar_excepcion(e)
                        counts["errors"] += 1
                        log_fn = logger.error if error_type in ("programming", "security") else logger.warning
                        log_fn(
                            "maildigester.process_error",
                            exc_info=True,
                            extra={
                                "tenant_schema": tenant_schema,
                                "task_id": task_id,
                                "source_filename": item.get("source_filename", "unknown"),
                                "error_type": error_type,
                                "error": str(e),
                            }
                        )
                        DocumentProcessing.objects.create(
                            empresa_id=empresa_id, run_id=run_id,
                            source="EMAIL", filename=item.get("source_filename", "unknown"),
                            status="FAILED", error_message=str(e),
                        )

                counts["xml_detected"] += len(xml_items)
                total_messages_processed += batch_messages
                
                # Actualizar estado después de cada lote
                if last_uid is not None and last_uid != current_uid:
                    # WARNING: IMPORT LAZY: Importar desde módulo puro (evita ciclos)
                    from apps.tenant.facturas.inbox_state import update_inbox_state
                    update_inbox_state(config_id, last_uid, batch_messages)
                    current_uid = last_uid
                elif last_uid is None:
                    # No hay más mensajes (primera ejecución sin mensajes o inbox vacío)
                    break
                
                # Si el lote está incompleto (menos de batch_size), no hay más mensajes
                if batch_messages < batch_size:
                    break
            
            # 6) Estado final segun resultados REALES (FASE 2 -- nunca SUCCESS falso)
            imported = counts["imported"]
            duplicates = counts["duplicates"]
            errors = counts["errors"]
            if errors == 0:
                final_status = "SUCCESS"
            elif imported > 0 or duplicates > 0:
                final_status = "PARTIAL_SUCCESS"
            else:
                final_status = "FAILED"

            _update_run(tenant_schema, task_id, status=final_status, counts=counts, finished_at=timezone.now())
            logger.info(
                "maildigester.end",
                extra={
                    "tenant_schema": tenant_schema,
                    "task_id": task_id,
                    "counts": counts,
                    "status": final_status,
                    "last_uid": current_uid,
                    "mode": mode,
                }
            )
            return {"ok": final_status != "FAILED", "status": final_status, "counts": counts, "last_uid": current_uid}
    
    except Exception as e:
        logger.error("maildigester.task_failure", exc_info=True, extra={"tenant_schema": tenant_schema, "task_id": task_id})
        # 6) FAILED (no reintentar AttributeError; el decorador ya no autoretry para AttributeError)
        try:
            _update_run(tenant_schema, task_id, status="FAILED", finished_at=timezone.now(), summary={"error": str(e)})
        except Exception:
            # Evitar fallar al persistir error (p.ej., tabla no existe): log minimal
            logger.warning("maildigester.persist_error", extra={"task_id": task_id})
        # Lanza de nuevo para que Celery aplique reintentos solo si entra en autoretry_for (transitorios)
        raise
