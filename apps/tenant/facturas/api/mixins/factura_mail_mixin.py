import logging

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.tenant.facturas.inbox_state import update_inbox_state

# Logger normalizado para facturas
log_up = logging.getLogger("facturas")

# Claves estándar de LogRecord que NO se pueden pisar
_RESERVED = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename", "module",
    "exc_info", "exc_text", "stack_info", "lineno", "funcName", "created", "msecs",
    "relativeCreated", "thread", "threadName", "processName", "process", "asctime",
    "message"
}

def safe_extra(d: dict) -> dict:
    """
    Devuelve un nuevo dict sin colisión con LogRecord; renombra claves reservadas añadiendo sufijo '_x'.
    """
    if not d:
        return {}
    out = {}
    for k, v in d.items():
        out[k + "_x" if k in _RESERVED else k] = v
    return out


class FacturaMailMixin:
    """
    Mixin especializado para la gestión y actualización del estado del buzón IMAP / correo entrante.
    """

    @action(detail=False, methods=['post'], url_path='update-inbox-state')
    def update_inbox_state(self, request: Request) -> Response:
        """
        Actualiza el estado del buzón IMAP después de procesar facturas.
        
        # WARNING: ZERO WASTE: Actualiza last_seen_uid para evitar reprocesar correos ya vistos.
        # WARNING: Este endpoint se llama después de que el usuario procesa facturas desde el modal.
        
        POST /api/v1/facturas/update-inbox-state/
        
        Body (JSON):
        {
            "config_id": int,  # ID de MailInboxConfig
            "last_uid": int,   # Último UID procesado
            "messages_processed": int  # Número de mensajes procesados
        }
        
        Returns:
            - 200 OK: Estado actualizado
            - 400 Bad Request: Faltan parámetros
            - 404 Not Found: Configuración no encontrada
        """
        config_id = request.data.get('config_id')
        last_uid = request.data.get('last_uid')
        messages_processed = request.data.get('messages_processed', 0)
        
        if not config_id:
            return Response(
                {"error": "missing_config_id", "message": "Falta 'config_id' en el cuerpo."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if last_uid is None:
            return Response(
                {"error": "missing_last_uid", "message": "Falta 'last_uid' en el cuerpo."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Actualizar estado del buzón
            update_inbox_state(config_id, last_uid, messages_processed)
            
            log_up.info("update_inbox_state", extra=safe_extra({
                "config_id": config_id,
                "last_uid": last_uid,
                "messages_processed": messages_processed,
            }))
            
            return Response({
                "ok": True,
                "message": "Estado del buzón actualizado correctamente",
                "config_id": config_id,
                "last_uid": last_uid,
                "messages_processed": messages_processed,
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {"error": "config_not_found", "message": str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            log_up.error("update_inbox_state_error", extra=safe_extra({
                "config_id": config_id,
                "error": str(e),
            }), exc_info=True)
            return Response(
                {"error": "update_failed", "message": f"Error al actualizar estado: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
