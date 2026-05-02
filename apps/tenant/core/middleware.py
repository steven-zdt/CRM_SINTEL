"""
SintelExceptionMiddleware - Sistema de Manejo de Errores Centralizado v2.40

# WARNING: ARQUITECTURA v2.40:
- Captura todas las excepciones no manejadas
- Loguea errores incluyendo request.tenant actual
- Para peticiones /api/, devuelve JsonResponse estandarizado
- Para otras peticiones, delega al handler estándar de Django

# WARNING: REGISTRO: Debe estar DESPUÉS de TenantMainMiddleware para tener contexto del esquema
"""

import logging
import traceback

from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class SintelExceptionMiddleware(MiddlewareMixin):
    """
    Middleware de excepciones centralizado para SINTEL v2.40.
    
    Captura todas las excepciones no manejadas y:
    1. Loguea el error con contexto del tenant
    2. Para peticiones /api/, devuelve JsonResponse estandarizado
    3. Para otras peticiones, delega al handler estándar de Django
    """
    
    def process_exception(self, request, exception):
        """
        Procesa excepciones no manejadas.
        
        Args:
            request: HttpRequest de Django
            exception: Excepción no manejada
            
        Returns:
            JsonResponse si la petición es /api/, None para delegar al handler estándar
        """
        # Obtener información del tenant actual
        tenant_info = "public"
        if hasattr(request, 'tenant') and request.tenant:
            tenant_info = f"{request.tenant.schema_name} (id: {request.tenant.id})"
        
        # Obtener información del usuario
        user_info = "anonymous"
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_info = f"{request.user.username} (id: {request.user.id})"
        
        # Loguear el error con contexto completo
        error_traceback = traceback.format_exc()
        logger.error(
            f"[SintelExceptionMiddleware] Excepción no manejada\n"
            f"Tenant: {tenant_info}\n"
            f"Usuario: {user_info}\n"
            f"Path: {request.path}\n"
            f"Method: {request.method}\n"
            f"Excepción: {type(exception).__name__}: {str(exception)}\n"
            f"Traceback:\n{error_traceback}"
        )
        
        # Si la petición es a /api/, devolver JsonResponse estandarizado
        if request.path.startswith('/api/'):
            # Determinar código de error según el tipo de excepción
            status_code = 500
            error_code = "INTERNAL_SERVER_ERROR"
            message = "Error interno del servidor"
            detail = None
            
            # Mapear excepciones comunes a códigos HTTP
            if hasattr(exception, 'status_code'):
                status_code = exception.status_code
            elif hasattr(exception, 'status'):
                status_code = exception.status
            
            # Mapear códigos de estado a mensajes y códigos de error
            if status_code == 400:
                error_code = "BAD_REQUEST"
                message = "Solicitud inválida"
            elif status_code == 401:
                error_code = "UNAUTHORIZED"
                message = "No autorizado"
            elif status_code == 403:
                error_code = "FORBIDDEN"
                message = "Acceso denegado"
            elif status_code == 404:
                error_code = "NOT_FOUND"
                message = "Recurso no encontrado"
            elif status_code == 409:
                error_code = "CONFLICT"
                message = "Conflicto en la solicitud"
            elif status_code == 422:
                error_code = "VALIDATION_ERROR"
                message = "Error de validación"
            
            # Extraer mensaje de la excepción si está disponible
            if hasattr(exception, 'detail'):
                if isinstance(exception.detail, str):
                    message = exception.detail
                elif isinstance(exception.detail, dict):
                    # Si detail es un dict, intentar extraer 'message' o 'detail'
                    message = exception.detail.get('message') or exception.detail.get('detail') or message
            elif hasattr(exception, 'message'):
                message = str(exception.message)
            elif str(exception):
                message = str(exception)
            
            # Incluir detail solo en DEBUG
            if settings.DEBUG:
                detail = error_traceback
            
            # Construir respuesta JSON estandarizada
            response_data = {
                "status": status_code,
                "message": message,
                "code": error_code,
            }
            
            if detail:
                response_data["detail"] = detail
            
            return JsonResponse(response_data, status=status_code)
        
        # Para peticiones no-API, delegar al handler estándar de Django
        return None
