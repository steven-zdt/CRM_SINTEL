"""
Core API Views para Empresa (Mailbox CRUD).

⚠️ v2.30: Core API como orquestador único de la UI privada.
- GET /api/v1/core/empresa/mailbox/configs/ → Lista paginada
- POST /api/v1/core/empresa/mailbox/configs/ → Crea configuración
- PATCH /api/v1/core/empresa/mailbox/configs/{id}/ → Actualiza configuración
- DELETE /api/v1/core/empresa/mailbox/configs/{id}/ → Elimina configuración

⚠️ POLÍTICA:
- SessionAuthentication + CSRF (UI privada)
- IsAuthenticated + IsTenantAdmin (solo ADMIN puede gestionar configs)
- JSON-only global (sin BrowsableAPIRenderer)
- Usa Core Service Adapter (apps/tenant/core/services/empresa_adapter)
"""
import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from apps.tenant.empresa.permissions import IsTenantAdmin

logger = logging.getLogger(__name__)


class CoreEmpresaMailboxConfigsListCreateAPIView(APIView):
    """
    GET: Lista configuraciones de buzones de correo (paginado)
    POST: Crea una configuración
    
    ⚠️ PERMISOS: IsTenantAdmin (solo ADMIN puede gestionar configs)
    ⚠️ SEGURIDAD: password es write_only (no se expone en respuestas)
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsTenantAdmin]
    
    def get(self, request, *args, **kwargs):
        """
        GET /api/v1/core/empresa/mailbox/configs/
        
        Lista configuraciones de buzones de correo (paginado).
        Query params: page, page_size
        """
        try:
            from apps.tenant.core.services.empresa_adapter import core_mailbox_list
            
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            result = core_mailbox_list(page=page, page_size=page_size)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(
                "CoreEmpresaMailboxConfigsListCreateAPIView GET: error=%s",
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al listar configuraciones."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request, *args, **kwargs):
        """
        POST /api/v1/core/empresa/mailbox/configs/
        
        Crea una configuración de buzón de correo.
        """
        try:
            from apps.tenant.core.services.empresa_adapter import core_mailbox_create
            
            data = request.data.copy()
            result = core_mailbox_create(data)
            return Response(result, status=status.HTTP_201_CREATED)
        except ValueError as e:
            # Errores de validación del Service Layer
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(
                "CoreEmpresaMailboxConfigsListCreateAPIView POST: error=%s",
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al crear la configuración."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CoreEmpresaMailboxConfigRetrieveUpdateDestroyAPIView(APIView):
    """
    GET: Obtiene una configuración (sin password)
    PATCH: Actualiza una configuración
    DELETE: Elimina una configuración
    
    ⚠️ PERMISOS: IsTenantAdmin (solo ADMIN puede gestionar configs)
    ⚠️ SEGURIDAD: password es write_only (no se expone en respuestas)
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsTenantAdmin]
    
    def get(self, request, config_id, *args, **kwargs):
        """
        GET /api/v1/core/empresa/mailbox/configs/{id}/
        
        Obtiene una configuración (sin password).
        """
        try:
            from apps.tenant.core.services.empresa_adapter import core_mailbox_list
            
            # Obtener la configuración específica desde la lista
            result = core_mailbox_list(page=1, page_size=1000)  # Obtener todas para buscar
            config = next((c for c in result['results'] if c['id'] == config_id), None)
            
            if not config:
                return Response(
                    {"detail": "Configuración no encontrada."},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response(config, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(
                "CoreEmpresaMailboxConfigRetrieveUpdateDestroyAPIView GET: error=%s",
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al obtener la configuración."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def patch(self, request, config_id, *args, **kwargs):
        """
        PATCH /api/v1/core/empresa/mailbox/configs/{id}/
        
        Actualiza una configuración de buzón de correo.
        """
        try:
            from apps.tenant.core.services.empresa_adapter import core_mailbox_update
            
            data = request.data.copy()
            result = core_mailbox_update(config_id, data)
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            # Errores de validación del Service Layer
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(
                "CoreEmpresaMailboxConfigRetrieveUpdateDestroyAPIView PATCH: error=%s",
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al actualizar la configuración."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, config_id, *args, **kwargs):
        """
        DELETE /api/v1/core/empresa/mailbox/configs/{id}/
        
        Elimina una configuración de buzón de correo.
        """
        try:
            from apps.tenant.core.services.empresa_adapter import core_mailbox_delete
            
            core_mailbox_delete(config_id)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(
                "CoreEmpresaMailboxConfigRetrieveUpdateDestroyAPIView DELETE: error=%s",
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al eliminar la configuración."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
