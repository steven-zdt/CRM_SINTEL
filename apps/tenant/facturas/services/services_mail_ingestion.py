"""
Servicio de orquestación de ingesta de facturas desde correo.

# WARNING: FASE 4/5: Service Layer paralelo a apps/tenant/facturas/services.py
- Expone funcionalidad de ingesta por correo para otras capas
- NO duplica lógica UBL (permanece en services.py)
- Cero signals: toda la lógica es explícita
- SSoT: Consume configuraciones desde apps.tenant.empresa (mailbox_provider)
- Procesamiento incremental: Usa UIDs IMAP para evitar reprocesar correos
- Validación de NIT: Aplica validación de pertenencia al tenant antes de persistir

# WARNING: IMPORTS LAZY: Importa Celery tasks solo cuando se necesitan (evita ciclos).
"""
from __future__ import annotations

import logging
from typing import Any

from django.db import connection
from django.utils import timezone

from apps.tenant.facturas.inbox_state import get_or_create_inbox_state, update_inbox_state
from apps.tenant.facturas.models import MailIngestionRun

logger = logging.getLogger(__name__)


def enqueue_mail_ingestion(
    *,
    config_id: int,
    limit_messages: int = 50,
    started_by=None,
) -> MailIngestionRun:
    """
    Encola la tarea de ingesta de correo para facturas XML.
    
    Crea un registro MailIngestionRun en estado PENDING y encola la tarea Celery.
    
    # WARNING: MULTI-TENANT: Usa connection.schema_name para obtener el esquema actual.
    # WARNING: SSoT: Consume configuraciones desde apps.tenant.empresa.services.mailbox_provider.
    # WARNING: SSoT: La lógica UBL y persistencia de facturas está en services.py.
    # WARNING: NATURALEZA: No se especifica; se determina automáticamente desde el XML UBL.
    
    Args:
        config_id: ID de MailInboxConfig de empresa (debe estar activa)
        limit_messages: Número máximo de mensajes a procesar (default: 50)
        started_by: Usuario que inició la ingesta (opcional)
        
    Returns:
        MailIngestionRun creado con task_id asignado
        
    Raises:
        MailInboxConfig.DoesNotExist: Si la config no existe o no está activa
    """
    # # WARNING: SEGURIDAD: NO leer mailbox_config aquí (evita exposición en logs)
    # La tarea leerá la configuración desde BD dentro de schema_context
    
    # Crear registro de ejecución en estado PENDING
    # Naturaleza se determina automáticamente desde el XML
    run = MailIngestionRun.objects.create(
        started_by=started_by,
        task_id="PENDING",
        naturaleza="VENTA",  # Valor por defecto, se actualiza según el XML procesado
        status="PENDING",
        counts={"processed": 0, "xml_detected": 0, "imported": 0, "duplicates": 0, "errors": 0},
    )
    
    # Obtener esquema del tenant actual
    tenant_schema = connection.schema_name
    
    # # WARNING: IMPORT LAZY: Importar Celery task solo cuando se necesita (evita ciclos)
    from apps.services.maildigester.tasks import fetch_and_process_billing_mail
    
    # # WARNING: SEGURIDAD: Encolar tarea Celery SIN credenciales en payload
    # Solo enviar config_id; la tarea leerá la configuración desde BD dentro de schema_context
    async_res = fetch_and_process_billing_mail.apply_async(
        kwargs={
            "tenant_schema": tenant_schema,
            "config_id": config_id,  # Solo ID, NO credenciales
            "limit_messages": limit_messages,
        },
        queue="high_priority",  # Cola de alta prioridad según CELERY_TASK_ROUTES
    )
    
    # Actualizar con task_id real
    run.task_id = async_res.id
    run.status = "PENDING"
    run.save(update_fields=["task_id", "status"])
    
    return run


def persist_run_result(
    *,
    tenant_schema: str,
    task_id: str,
    result: dict[str, Any],
    status_label: str
) -> None:
    """
    Persiste el resultado de una ejecución de ingesta en MailIngestionRun.
    
    # WARNING: CERO SIGNALS: Esta función se invoca explícitamente desde la tarea Celery.
    # WARNING: MULTI-TENANT: Debe ejecutarse dentro de schema_context del tenant correcto.
    
    Args:
        tenant_schema: Nombre del esquema del tenant (para logging)
        task_id: ID de la tarea Celery
        result: Dict con resultado de la ejecución (MailDigesterResult)
        status_label: Estado final (SUCCESS|FAILURE)
    """
    try:
        run = MailIngestionRun.objects.get(task_id=task_id)
    except MailIngestionRun.DoesNotExist:
        # Si no existe el run, no hacer nada (puede ser una ejecución manual sin tracking)
        return
    
    run.status = status_label
    run.finished_at = timezone.now()
    run.counts = {
        "xml_detected": result.get("xml_detected", 0),
        "imported": result.get("imported", 0),
        "duplicates": result.get("duplicates", 0),
        "errors": result.get("errors", 0),
    }
    run.summary = {"details": result.get("details", [])}
    run.save(update_fields=["status", "finished_at", "counts", "summary"])


def preview_mail_ingestion(
    *,
    config_id: int,
    limit_messages: int = 50,
) -> dict[str, Any]:
    """
    Pre-visualiza facturas desde correo sin persistirlas (solo metadatos).
    
    # WARNING: FUNCIÓN DE PRE-VISUALIZACIÓN: Extrae metadatos de facturas encontradas pero NO las persiste.
    # WARNING: PROCESAMIENTO INCREMENTAL: Usa MailInboxState para obtener last_seen_uid.
    # WARNING: FILTRO DE ADJUNTOS: Busca específicamente archivos .zip o .xml.
    # WARNING: DESCOMPRESIÓN: Si es ZIP, lo descomprime en memoria para buscar el archivo UBL interno.
    # WARNING: SIN PERSISTENCIA: Solo extrae metadatos (Emisor, Fecha, Valor) para mostrar al usuario.
    
    Flujo:
    1. Consulta MailInboxState para obtener last_seen_uid (procesamiento incremental)
    2. Llama al pipeline del maildigester para extraer XMLs
    3. Filtra adjuntos .zip o .xml (ya lo hace el pipeline internamente)
    4. Si es ZIP, lo descomprime en memoria (ya lo hace el pipeline internamente)
    5. Parsea cada XML para extraer metadatos (sin persistir)
    6. Retorna lista de facturas pendientes para que el usuario seleccione
    
    Args:
        config_id: ID de MailInboxConfig de empresa (debe estar activa)
        limit_messages: Número máximo de mensajes a procesar (default: 50)
        
    Returns:
        Dict con lista de facturas pendientes:
        {
            "ok": bool,
            "processed": int,
            "xml_detected": int,
            "pending_invoices": List[Dict],  # Lista de facturas pendientes con metadatos
            "details": List[Dict],  # Detalles de cada factura encontrada
        }
        
    Raises:
        ValueError: Si la configuración no existe o no está activa
    """
    from apps.services.maildigester import pipeline
    from apps.services.maildigester.schemas import MailboxConfigDTO
    from apps.tenant.empresa.services import get_mailbox_config
    
    # 1. Consulta de Estado: Obtener last_seen_uid para procesamiento incremental
    try:
        inbox_state = get_or_create_inbox_state(config_id)
        start_uid = inbox_state.last_seen_uid  # None = histórico completo, int = incremental
        logger.info(f"[preview_mail_ingestion] Estado del buzón obtenido: last_seen_uid={start_uid}")
    except ValueError as e:
        logger.error(f"[preview_mail_ingestion] Error obteniendo estado del buzón: {e}")
        raise
    
    # 2. Obtener configuración del buzón (SSoT)
    # # WARNING: VALIDACIÓN DE SEGURIDAD: get_mailbox_config ya valida que pertenezca al tenant
    try:
        mailbox_config_dict = get_mailbox_config(config_id)
        if not mailbox_config_dict:
            logger.error(f"[preview_mail_ingestion] Configuración {config_id} no encontrada o no activa")
            return {
                "ok": False,
                "error": "config_not_found",
                "message": f"La configuración de buzón (ID: {config_id}) no existe o no está activa para este tenant.",
                "processed": 0,
                "xml_detected": 0,
                "pending_invoices": [],
                "details_list": []
            }
        
        # WARNING: BUGFIX (hallado durante FASE 12): MailboxConfigDTO es un TypedDict -- llamarlo
        # como constructor solo devuelve un dict plano, nunca un objeto con atributos. El acceso
        # mailbox_config.host de mas abajo crasheaba SIEMPRE (AttributeError), exactamente igual
        # que tasks.py ya usa el dict directamente sin envolverlo.
        mailbox_config: MailboxConfigDTO = mailbox_config_dict
        logger.debug(f"[preview_mail_ingestion] Configuración del buzón obtenida: {mailbox_config.get('host')}")

        # WARNING: SSoT (FASE 12 Document Intake): resolver la MISMA empresa que usara la
        # persistencia real (MailInboxConfig.empresa), no una config global independiente --
        # antes se usaba get_empresa_emisor_data(), una fuente distinta que podia divergir.
        from apps.tenant.empresa.models import MailInboxConfig as _MailInboxConfig
        empresa_nit_tenant = (
            _MailInboxConfig.objects.only("empresa__nit")
            .select_related("empresa")
            .get(id=config_id)
            .empresa.nit
        )
    except ValueError as e:
        # ValueError indica que la configuración no existe o no está activa
        logger.error(f"[preview_mail_ingestion] Error obteniendo configuración del buzón: {e}", exc_info=True)
        return {
            "ok": False,
            "error": "config_not_found",
            "message": str(e),
            "processed": 0,
            "xml_detected": 0,
            "pending_invoices": [],
            "details_list": []
        }
    except Exception as e:
        logger.error(f"[preview_mail_ingestion] Error inesperado obteniendo configuración del buzón: {e}", exc_info=True)
        return {
            "ok": False,
            "error": "config_error",
            "message": f"Error al obtener configuración del buzón: {str(e)}",
            "processed": 0,
            "xml_detected": 0,
            "pending_invoices": [],
            "details_list": []
        }
    
    # 3. Llamada al Digester: Procesar correos y extraer XMLs (SIN PERSISTIR)
    # # WARNING: El pipeline ya filtra adjuntos .zip o .xml y descomprime ZIPs en memoria
    try:
        if start_uid is not None:
            # Procesamiento incremental: usar función que acepta start_uid
            from apps.services.maildigester.pipeline import collect_invoice_xml_from_mailbox_by_uid
            invoice_xmls, last_uid = collect_invoice_xml_from_mailbox_by_uid(
                mailbox_config,
                start_uid=start_uid,
                batch_size=limit_messages,
                naturaleza=None  # Se determina automáticamente desde XML
            )
        else:
            # Primera ejecución: procesar histórico completo
            invoice_xmls = pipeline.collect_invoice_xml_from_mailbox(
                mailbox_config,
                limit_messages=limit_messages,
                naturaleza=None  # Se determina automáticamente desde XML
            )
            last_uid = None
        
        logger.info(f"[preview_mail_ingestion] XMLs detectados: {len(invoice_xmls)}")
    except Exception as e:
        # # WARNING: IMPORT LAZY: Importar excepciones del maildigester solo cuando se necesitan
        from apps.services.maildigester.exceptions import MailboxConnectionError
        
        # # WARNING: CAPTURA ESPECÍFICA: Detectar MailboxConnectionError del maildigester
        if isinstance(e, MailboxConnectionError):
            logger.error(f"[preview_mail_ingestion] Error de conexión al buzón: {e}", exc_info=True)
            
            # Analizar el mensaje de error para determinar el tipo específico
            error_str = str(e).lower()
            
            # Detectar si es Gmail
            is_gmail = 'gmail' in error_str or '@gmail.com' in error_str or 'imap.gmail.com' in error_str
            # Detectar si es Outlook
            is_outlook = 'outlook' in error_str or '@outlook.com' in error_str or '@hotmail.com' in error_str or 'office365' in error_str
            
            # Determinar tipo de error
            if any(keyword in error_str for keyword in ['authentication', 'login', 'credential', 'unauthorized']):
                error_type = "authentication_error"
                error_message = "Error de autenticación con el servidor de correo"
                
                if is_gmail:
                    troubleshooting = (
                        "# WARNING: GMAIL: Para usar Gmail, necesitas una 'App Password' (Contraseña de Aplicación) de 16 dígitos. "
                        "No puedes usar tu contraseña normal. "
                        "Pasos: 1) Ve a tu cuenta de Google → Seguridad → Verificación en 2 pasos → Contraseñas de aplicaciones. "
                        "2) Genera una nueva contraseña de aplicación para 'Correo' y 'Otro (personalizado)'. "
                        "3) Usa esa contraseña de 16 dígitos en lugar de tu contraseña normal. "
                        "4) Asegúrate de que IMAP esté habilitado en Configuración → Reenvío y correo POP/IMAP."
                    )
                elif is_outlook:
                    troubleshooting = (
                        "# WARNING: OUTLOOK/Office365: Asegúrate de usar tu contraseña de cuenta Microsoft o una contraseña de aplicación. "
                        "Si tienes autenticación en 2 pasos activada, necesitas generar una contraseña de aplicación. "
                        "Pasos: 1) Ve a account.microsoft.com → Seguridad → Opciones de seguridad adicionales. "
                        "2) Genera una nueva contraseña de aplicación. "
                        "3) Asegúrate de que IMAP esté habilitado en la configuración de tu cuenta."
                    )
                else:
                    troubleshooting = (
                        "# WARNING: ERROR DE AUTENTICACIÓN: Verifica que las credenciales sean correctas. "
                        "Si tienes autenticación en 2 pasos activada, necesitas usar una contraseña de aplicación. "
                        "Asegúrate de que IMAP esté habilitado en la configuración de tu cuenta de correo."
                    )
            else:
                # Error de conexión general
                error_type = "connection_error"
                error_message = "Error de conexión con el servidor de correo"
                troubleshooting = (
                    "# WARNING: ERROR DE CONEXIÓN: Verifica que: "
                    "1) El servidor IMAP y el puerto sean correctos (Gmail: imap.gmail.com:993, Outlook: outlook.office365.com:993). "
                    "2) Tu conexión a Internet esté activa. "
                    "3) El firewall no esté bloqueando la conexión. "
                    "4) IMAP esté habilitado en la configuración de tu cuenta de correo."
                )
            
            return {
                "ok": False,
                "error": error_type,
                "message": error_message,
                "details": str(e),
                "troubleshooting": troubleshooting,
                "processed": 0,
                "xml_detected": 0,
                "pending_invoices": [],
                "details_list": []
            }
        
        # # WARNING: FALLBACK: Si no es MailboxConnectionError, aplicar detección genérica de errores
        logger.error(f"[preview_mail_ingestion] Error procesando correos (genérico): {e}", exc_info=True)
        
        # Detectar errores de autenticación comunes
        error_str = str(e).lower()
        error_message = str(e)
        error_type = "mailbox_error"
        troubleshooting = None
        
        if any(keyword in error_str for keyword in ['authentication failed', 'login failed', 'invalid credentials', 
                                                     'bad credentials', 'authentication error', 'unauthorized']):
            error_type = "authentication_error"
            error_message = "Error de autenticación con el servidor de correo"
            
            # Detectar si es Gmail
            if 'gmail' in error_str or '@gmail.com' in error_str or 'imap.gmail.com' in error_str:
                troubleshooting = (
                    "# WARNING: GMAIL: Para usar Gmail, necesitas una 'App Password' (Contraseña de Aplicación) de 16 dígitos. "
                    "No puedes usar tu contraseña normal. "
                    "Pasos: 1) Ve a tu cuenta de Google → Seguridad → Verificación en 2 pasos → Contraseñas de aplicaciones. "
                    "2) Genera una nueva contraseña de aplicación para 'Correo' y 'Otro (personalizado)'. "
                    "3) Usa esa contraseña de 16 dígitos en lugar de tu contraseña normal. "
                    "4) Asegúrate de que IMAP esté habilitado en Configuración → Reenvío y correo POP/IMAP."
                )
            elif 'outlook' in error_str or '@outlook.com' in error_str or '@hotmail.com' in error_str or 'office365' in error_str:
                troubleshooting = (
                    "# WARNING: OUTLOOK/Office365: Asegúrate de usar tu contraseña de cuenta Microsoft o una contraseña de aplicación. "
                    "Si tienes autenticación en 2 pasos activada, necesitas generar una contraseña de aplicación. "
                    "Pasos: 1) Ve a account.microsoft.com → Seguridad → Opciones de seguridad adicionales. "
                    "2) Genera una nueva contraseña de aplicación. "
                    "3) Asegúrate de que IMAP esté habilitado en la configuración de tu cuenta."
                )
            else:
                troubleshooting = (
                    "# WARNING: ERROR DE AUTENTICACIÓN: Verifica que las credenciales sean correctas. "
                    "Si tienes autenticación en 2 pasos activada, necesitas usar una contraseña de aplicación. "
                    "Asegúrate de que IMAP esté habilitado en la configuración de tu cuenta de correo."
                )
        
        # Detectar errores de conexión IMAP
        elif any(keyword in error_str for keyword in ['imap', 'connection refused', 'connection timeout', 
                                                       'could not connect', 'network is unreachable']):
            error_type = "connection_error"
            error_message = "Error de conexión con el servidor de correo"
            troubleshooting = (
                "# WARNING: ERROR DE CONEXIÓN: Verifica que: "
                "1) El servidor IMAP y el puerto sean correctos (Gmail: imap.gmail.com:993, Outlook: outlook.office365.com:993). "
                "2) Tu conexión a Internet esté activa. "
                "3) El firewall no esté bloqueando la conexión. "
                "4) IMAP esté habilitado en la configuración de tu cuenta de correo."
            )
        
        return {
            "ok": False,
            "error": error_type,
            "message": error_message,
            "details": str(e),
            "troubleshooting": troubleshooting,  # # WARNING: Mensaje de ayuda específico
            "processed": 0,
            "xml_detected": 0,
            "pending_invoices": [],
            "details_list": []
        }
    
    # 4. Extraer metadatos de cada XML (SIN PERSISTIR)
    pending_invoices = []
    details = []
    
    for xml_item in invoice_xmls:
        xml_text = xml_item.get("xml_text", "")
        source_email_id = xml_item.get("source_email_id", "unknown")
        source_filename = xml_item.get("source_filename", "unknown")
        
        try:
            # # WARNING: PASO 4.1: Parsear XML para extraer solo metadatos (sin persistir)
            # Usar el pipeline universal de document_ingest si está disponible, o parser UBL legacy
            try:
                from apps.services.document_ingest.ingest_service import ingest_document
                HAS_DOCUMENT_INGEST = True
            except ImportError:
                HAS_DOCUMENT_INGEST = False
                ingest_document = None
            
            if HAS_DOCUMENT_INGEST and ingest_document:
                # WARNING: BUGFIX (hallado durante FASE 12): ingest_document() no acepta
                # file_type= (el kwarg real es mime_type=) y retorna una tupla (result,
                # status_code), no un dict suelto -- esto hacia que TODA llamada real cayera
                # al except de abajo, devolviendo pending_invoices=[] con ok=True (falso
                # "sin facturas" en vez de un error real).
                xml_bytes = xml_text.encode('utf-8')
                result, _ingest_status = ingest_document(
                    xml_bytes,
                    filename=source_filename,
                    mime_type="application/xml",
                    kind_hint="xml",
                    preview=True,
                    async_mode=False,
                )
                if result and result.get("dto"):
                    dto = result.get("dto")
                else:
                    raise ValueError("No se pudo extraer DTO del XML usando document_ingest")
            else:
                # WARNING: [PERF-C3] Fallback: usar parser UBL legacy en modo persist=False.
                # Este bloque es solo de PREVISUALIZACION (PASO 4.1: "extraer solo metadatos,
                # sin persistir") -- debe recibir el dict de datos parseados, no una Factura ya
                # creada. Con persist=True (comportamiento anterior por defecto) esta previsualizacion
                # habria creado una Factura real en cada llamada, antes de que el usuario confirmara
                # la importacion.
                from apps.tenant.facturas.utils.ubl_parser import importar_factura_desde_ubl
                factura_data = importar_factura_desde_ubl(xml_text, persist=False)

                # Convertir a formato DTO canónico
                dto = {
                    "numero": factura_data.get("numero"),
                    "fecha_emision": factura_data.get("fecha_emision"),
                    "prefijo": factura_data.get("prefijo"),
                    "consecutivo": factura_data.get("consecutivo", 0),
                    "emisor": {
                        "nit": factura_data.get("emisor_nit"),
                        "razon_social": factura_data.get("emisor_razon_social"),
                    },
                    "receptor": {
                        "nit": factura_data.get("receptor_nit"),
                        "razon_social": factura_data.get("receptor_razon_social"),
                    },
                    "totales": {
                        "subtotal": str(factura_data.get("subtotal", "0.00")),
                        "impuestos": str(factura_data.get("impuestos", "0.00")),
                        "total": str(factura_data.get("total", "0.00")),
                        "moneda": factura_data.get("moneda", "COP"),
                    },
                    "identificadores": {
                        "cufe": factura_data.get("cufe"),
                        "uuid": factura_data.get("cufe"),
                    },
                    "metadata": {
                        "context": "mail_ingestion",  # # WARNING: CASCADING SECURITY: Marcar contexto de correo
                        "file_type": "xml",
                        "source": "mailbox"
                    }
                }
            
            # # WARNING: PASO 4.2: Extraer solo metadatos para mostrar al usuario
            emisor = dto.get("emisor", {})
            receptor = dto.get("receptor", {})
            totales = dto.get("totales", {})
            identificadores = dto.get("identificadores", {})
            
            # # WARNING: PASO 4.3: VALIDACIÓN DE NIT + naturaleza -- SSoT (FASE 12 Document Intake)
            # Antes esta funcion reimplementaba su propia comparacion emisor/receptor == empresa
            # (duplicando la regla de negocio VENTA/COMPRA). Ahora consulta el mismo servicio que
            # usa la persistencia real (FacturaBusinessService), garantizando que preview y
            # persistencia siempre den la misma naturaleza para el mismo documento.
            # FACTURAS-UI-CRONO-01 FASE 2/3: el guard de pertenencia usaba
            # normalize_document_number (concatena el DV) mientras que
            # guardar_desde_dto() usa same_nit()/clean_nit() (descarta el DV
            # con guion) -- podian divergir para NIT con DV separado por
            # guion. Alineado a same_nit(), la misma funcion que usa la
            # persistencia real, para que preview nunca contradiga lo que
            # pasara al guardar.
            from apps.tenant.facturas.services.business_service import FacturaBusinessService, same_nit

            belongs_to_tenant = None  # None = no validado, True = pertenece, False = no pertenece
            validation_message = None

            try:
                emisor_nit_raw = emisor.get("nit")
                receptor_nit_raw = receptor.get("nit")
                nit_tenant = FacturaBusinessService.normalize_document_number(empresa_nit_tenant)
                emisor_nit = FacturaBusinessService.normalize_document_number(emisor_nit_raw)
                receptor_nit = FacturaBusinessService.normalize_document_number(receptor_nit_raw)

                if not empresa_nit_tenant:
                    belongs_to_tenant = None
                    validation_message = "No se pudo validar (empresa no configurada)"
                elif not same_nit(emisor_nit_raw, empresa_nit_tenant) and not same_nit(receptor_nit_raw, empresa_nit_tenant):
                    # Mismo guard que FacturaBusinessService.guardar_desde_dto(): si ni el
                    # emisor ni el receptor coinciden con la empresa, el documento seria
                    # rechazado en persistencia -- reflejarlo aqui identicamente.
                    belongs_to_tenant = False
                    validation_message = (
                        f"No pertenece a la empresa (Emisor NIT: {emisor_nit}, "
                        f"Receptor NIT: {receptor_nit} != Tenant NIT: {nit_tenant})"
                    )
                else:
                    naturaleza = FacturaBusinessService._resolver_naturaleza(
                        emisor_nit_raw, receptor_nit_raw, empresa_nit_tenant
                    )
                    belongs_to_tenant = True
                    if naturaleza == "VENTA":
                        validation_message = "VENTA (emitida por esta empresa)"
                    elif naturaleza == "COMPRA":
                        validation_message = "COMPRA (recibida por esta empresa)"
                    else:
                        # FACTURAS-UI-CRONO-01: caso ambiguo (ej. emisor Y
                        # receptor son la propia empresa) -- nunca inventar
                        # VENTA/COMPRA, mismo criterio que guardar_desde_dto().
                        validation_message = "Revisar (naturaleza ambigua -- ver FACTURAS_NATURALEZA_RULE.md)"
            except Exception as e:
                logger.warning(f"[preview_mail_ingestion] Error validando NIT: {e}")
                belongs_to_tenant = None
                validation_message = f"Error en validación: {str(e)}"
            
            # Construir metadatos para mostrar
            metadata = {
                "numero": dto.get("numero"),
                "fecha_emision": dto.get("fecha_emision"),
                "emisor_nit": emisor.get("nit"),
                "emisor_razon_social": emisor.get("razon_social"),
                "receptor_nit": receptor.get("nit"),
                "receptor_razon_social": receptor.get("razon_social"),
                "subtotal": totales.get("subtotal", "0.00"),
                "impuestos": totales.get("impuestos", "0.00"),
                "total": totales.get("total", "0.00"),
                "moneda": totales.get("moneda", "COP"),
                "cufe": identificadores.get("cufe") or identificadores.get("uuid"),
                "source_email_id": source_email_id,
                "source_filename": source_filename,
                # # WARNING: FILTRO CONTABLE: Información de validación para mostrar al usuario
                "belongs_to_tenant": belongs_to_tenant,  # True/False/None
                "validation_message": validation_message,  # Mensaje descriptivo
            }
            
            # # WARNING: CRÍTICO: Incluir el XML completo y el DTO para poder persistirlo después
            # El frontend enviará estos datos al endpoint create-from-dto/
            pending_invoice = {
                **metadata,
                "xml_text": xml_text,  # XML completo para persistir
                "dto": dto,  # DTO completo para persistir
                "file_bytes_b64": None,  # Se codificará en base64 si es necesario
            }
            
            # Codificar XML en base64 para enviarlo al frontend
            import base64
            xml_bytes = xml_text.encode('utf-8')
            pending_invoice["file_bytes_b64"] = base64.b64encode(xml_bytes).decode('utf-8')
            
            pending_invoices.append(pending_invoice)
            
            details.append({
                "source_email_id": source_email_id,
                "source_filename": source_filename,
                "numero": metadata.get("numero"),
                "emisor": metadata.get("emisor_razon_social"),
                "total": metadata.get("total"),
                "status": "pending"
            })
                
        except Exception as e:
            logger.error(f"[preview_mail_ingestion] Error extrayendo metadatos de {source_filename}: {e}", exc_info=True)
            details.append({
                "source_email_id": source_email_id,
                "source_filename": source_filename,
                "status": "error",
                "error": str(e)
            })
    
    # 5. Retornar resultado (SIN actualizar estado del buzón - eso se hace al persistir)
    # # WARNING: ZERO WASTE: Incluir last_uid_processed para actualizar estado después de procesar
    result = {
        "ok": True,
        "processed": len(invoice_xmls),
        "xml_detected": len(invoice_xmls),
        "pending_invoices": pending_invoices,  # [OK] Lista de facturas pendientes con metadatos y XML
        "details": details,
        "last_uid_processed": last_uid,  # # WARNING: Último UID procesado para actualizar estado
        "config_id": config_id,  # # WARNING: ID de configuración para actualizar estado
    }
    
    logger.info(f"[preview_mail_ingestion] Pre-visualización completada: {len(pending_invoices)} facturas pendientes, last_uid={last_uid}")
    return result
