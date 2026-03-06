"""
Tareas Celery para procesamiento asíncrono de documentos (tenant-aware).

⚠️ PRINCIPIOS:
- Tenant-aware: Usa schema_context para aislamiento por esquema
- Agnóstico: Retorna DTO serializable (sin acoplar a modelos de negocio)
- Soporta múltiples formatos: XML, PDF, XLS/XLSX, CSV, TXT
- Nombre canónico (dotted path) para evitar "unregistered task"

⚠️ v2.36: Migrado desde apps/services/xml_ingest/tasks.py
"""
from celery import shared_task
from celery.result import AsyncResult
import base64
import time
import logging
from typing import Dict, Any, Tuple, Optional
from django_tenants.utils import schema_context
from django.conf import settings
from django.db import connection

from apps.services.document_ingest.ingest_service import ingest_document

log_task = logging.getLogger("apps.services.document_ingest")

def _safe_len(v):
    """Helper para obtener longitud segura."""
    try:
        return len(v) if v else 0
    except (TypeError, AttributeError):
        return 0

@shared_task(name="apps.services.document_ingest.tasks.document_ingest_task")
def document_ingest_task(schema_name: str, file_b64: str, filename: Optional[str] = None) -> Dict[str, Any]:
    """
    Tarea tenant-aware: abre schema_context(schema_name) antes de cualquier acceso.
    Nombre canónico (dotted path) para evitar 'unregistered task'.
    
    ⚠️ v2.36: Migrado desde xml_ingest_task para usar pipeline universal.
    ⚠️ NORMALIZACIÓN: Logging estructurado con inicio, duración y resultado.
    
    Args:
        schema_name: Nombre del esquema del tenant (ej: "tenant1", "cliente_acme")
        file_b64: Archivo codificado en base64
        filename: Nombre del archivo (opcional, para detección de tipo)
        
    Returns:
        Dict serializable con estructura del pipeline universal: {"persisted": bool, "dto": {...}, "id": int, ...}
    """
    t0 = time.monotonic()
    size_b64 = _safe_len(file_b64)
    
    try:
        with schema_context(schema_name):
            log_task.info(
                "document_ingest_task start",
                extra={"schema_name": schema_name, "size_b64": size_b64, "upload_filename": filename}
            )
            
            file_bytes = base64.b64decode(file_b64.encode("utf-8"))
            result, status_code = ingest_document(
                content=file_bytes,
                filename=filename,
                preview=False,
                async_mode=False
            )
            
            # El pipeline universal retorna {"persisted": bool, "dto": {...}, "id": int, ...}
            # Mantenemos este formato para consistencia
            
            dt = time.monotonic() - t0
            log_task.info(
                "document_ingest_task done",
                extra={
                    "schema_name": schema_name,
                    "elapsed_s": round(dt, 3),
                    "persisted": result.get("persisted", False),
                    "status_code": status_code
                }
            )
            return result
    except Exception as e:
        dt = time.monotonic() - t0
        log_task.exception(
            "document_ingest_task error",
            extra={
                "schema_name": schema_name,
                "elapsed_s": round(dt, 3)
            }
        )
        raise


def get_task_status(task_id: str, request=None) -> Tuple[Dict[str, Any], int]:
    """
    Devuelve un JSON apto para UI:
      - state: PENDING | STARTED | SUCCESS | FAILURE | UNKNOWN
      - result: payload si SUCCESS
      - error_code/message/hint cuando hay problemas
    Nunca levanta excepción; siempre retorna (payload, 200).
    
    ⚠️ v2.36: Migrado desde apps/services/xml_ingest/service.py
    ⚠️ NORMALIZACIÓN: Acepta request opcional para extraer contexto (request_id, schema_name).
    
    Args:
        task_id: ID de la tarea Celery
        request: Request opcional para contexto de logging
        
    Returns:
        Tuple (payload, status_code) donde payload tiene estructura:
        {
            "state": "PENDING" | "STARTED" | "SUCCESS" | "FAILURE" | "UNKNOWN",
            "result": {...} si SUCCESS,
            "error_code": str si FAILURE,
            "message": str si hay error,
            "hint": str opcional
        }
    """
    # ⚠️ NORMALIZACIÓN: Extraer contexto de logging
    schema = "-"
    rid = "-"
    if request:
        if hasattr(request, 'tenant') and request.tenant:
            schema = getattr(request.tenant, 'schema_name', '-')
        rid = getattr(request, 'META', {}).get('REQUEST_ID', '-')
    else:
        # Intentar obtener desde connection si está disponible
        schema = getattr(connection, "schema_name", "-")
        rid = getattr(settings, 'REQUEST_ID', '-')
    
    try:
        task = AsyncResult(task_id)
        state = task.state or "PENDING"
        
        payload = {
            "state": state,
        }
        
        if state == "SUCCESS":
            payload["result"] = task.result
        elif state == "FAILURE":
            payload["error_code"] = "task_failed"
            payload["message"] = str(task.info) if task.info else "Tarea falló"
            payload["hint"] = "Revisar logs del worker para más detalles"
        elif state in ("PENDING", "STARTED"):
            payload["message"] = f"Tarea en estado: {state}"
        else:
            payload["state"] = "UNKNOWN"
            payload["message"] = f"Estado desconocido: {state}"
        
        log_task.info(
            "task_status_queried",
            extra={
                "request_id": rid,
                "schema_name": schema,
                "task_id": task_id,
                "state": state
            }
        )
        
        return payload, 200
    except Exception as e:
        log_task.exception(
            "task_status_error",
            extra={
                "request_id": rid,
                "schema_name": schema,
                "task_id": task_id
            }
        )
        return {
            "state": "UNKNOWN",
            "error_code": "query_error",
            "message": f"Error al consultar estado de tarea: {str(e)}"
        }, 200
