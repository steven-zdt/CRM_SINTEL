"""
ViewSets para Configuración de Cotizaciones v2.60.

# WARNING: v2.60: CRUD completo de perfiles de configuración.
Permite gestionar múltiples perfiles por empresa.
# WARNING: Error Boundary Pattern: Todos los errores retornan JSON nativo (sin template_name).
"""
import logging

from django.db import IntegrityError
from rest_framework import permissions, serializers, status
from rest_framework.decorators import action
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from apps.config.api.pagination import StandardResultsSetPagination
from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.api.permissions import IsTenantMember

from .models import ConfiguracionCotizacion
from .serializers import (
    ConfiguracionCotizacionDetailSerializer,
    ConfiguracionCotizacionListSerializer,
)

logger = logging.getLogger(__name__)


class ConfiguracionCotizacionViewSet(BaseTenantViewSet):
    """
    ViewSet para Perfiles de Configuración de Cotizaciones v2.60.
    
    # WARNING: Tabulator Factory v2.40:
    - Endpoint: GET /api/v1/cotizaciones/configuracion/ con StandardResultsSetPagination
    - CRUD completo de perfiles de configuración
    - Múltiples perfiles por empresa permitidos
    
    # WARNING: IMPORTANTE: Usa 'id' como lookup_field porque ConfiguracionCotizacion no tiene UUID
    """
    # # WARNING: CRÍTICO: DRF necesita un queryset definido para generar las rutas del router
    # Usamos .none() como base porque el filtrado real se hace en get_queryset()
    queryset = ConfiguracionCotizacion.objects.none()
    lookup_field = 'id'  # ConfiguracionCotizacion usa ID, no UUID
    lookup_url_kwarg = 'id'
    serializer_class = ConfiguracionCotizacionDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]
    renderer_classes = [JSONRenderer]
    pagination_class = StandardResultsSetPagination

    def _resolve_empresa(self, request):
        empresa = getattr(request, 'empresa', None)
        if empresa:
            return empresa

        tenant = getattr(request, 'tenant', None)
        empresa = getattr(tenant, 'empresa', None)
        if empresa:
            return empresa

        from apps.tenant.empresa.models import Empresa
        return Empresa.objects.only('id').first()

    def get_queryset(self):
        """
        Filtrado por empresa del tenant actual (singleton).
        
        # WARNING: SSoT v2.60: La empresa se obtiene del tenant, no del usuario.
        """
        empresa = self._resolve_empresa(self.request)
        if not empresa:
            return ConfiguracionCotizacion.objects.none()
        
        queryset = ConfiguracionCotizacion.objects.filter(empresa=empresa)
        
        # # WARNING: Filtro: Solo plantillas activas
        solo_activos = self.request.query_params.get('solo_activos', None)
        if solo_activos == 'true':
            queryset = queryset.filter(es_activo=True)
        
        # # WARNING: Tabulator Factory: Soporte para búsqueda
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                nombre_configuracion__icontains=search
            )
        
        return queryset.order_by('-es_activo', 'nombre_configuracion')

    def get_serializer_class(self):
        """Diferenciación entre List (Ligero) y Detail (Completo)."""
        if self.action == 'list':
            return ConfiguracionCotizacionListSerializer
        return ConfiguracionCotizacionDetailSerializer

    def create(self, request, *args, **kwargs):
        """
        # WARNING: v2.60: Sobrescribir create para aplicar Error Boundary Pattern.
        
        # WARNING: Error Boundary Pattern: Todos los errores retornan JSON nativo (sin template_name).
        """
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # # WARNING: SSoT v2.60: Validación de empresa antes de crear
            from rest_framework.exceptions import ValidationError

            empresa = self._resolve_empresa(request)
            if not empresa:
                raise ValidationError({
                    "detail": "No se encontró la empresa del tenant. Por favor, configure la empresa primero."
                })
            
            # # WARNING: SSoT: El serializer ya tiene 'empresa' en read_only_fields
            # pero aseguramos que se inyecte desde el tenant
            instance = serializer.save(empresa=empresa)
            logger.info(f"Perfil de configuración creado: {instance.nombre_configuracion} (Empresa: {empresa.id})")
            
            output_serializer = self.get_serializer(instance)
            headers = self.get_success_headers(output_serializer.data)
            return Response(output_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        
        except serializers.ValidationError as e:
            logger.error(f"[ConfiguracionCotizacionViewSet] Error de validación en create: {str(e)}", exc_info=True)
            error_detail = e.detail if hasattr(e, 'detail') else str(e)
            # # WARNING: Error Boundary: Siempre devolver estructura {"error": "...", "detail": "..."}
            if isinstance(error_detail, dict):
                # Si el dict ya tiene "error" y "detail", usarlo; si no, envolverlo
                if "error" in error_detail and "detail" in error_detail:
                    return Response(error_detail, status=status.HTTP_400_BAD_REQUEST)
                # Si es un dict de errores de campo, convertirlo a formato estándar
                return Response(
                    {"error": "Error de validación", "detail": error_detail},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                {"error": "Error de validación", "detail": str(error_detail)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except IntegrityError as e:
            logger.error(f"[ConfiguracionCotizacionViewSet] Error de integridad en create: {str(e)}", exc_info=True)
            # Verificar si es un error de unicidad
            if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
                return Response(
                    {
                        "error": "Ya existe una configuración con estos datos. Por favor, verifique la información.",
                        "detail": str(e),
                        "code": "duplicate_configuracion"
                    },
                    status=status.HTTP_409_CONFLICT
                )
            return Response(
                {"error": "Error de integridad de datos", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except Exception as e:
            logger.error(f"[ConfiguracionCotizacionViewSet] Error inesperado en create: {str(e)}", exc_info=True)
            return Response(
                {"error": "Ocurrió un error inesperado al crear la configuración.", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_create(self, serializer):
        """
        # WARNING: SSoT v2.60: Este método ya no se usa porque sobrescribimos create().
        Se mantiene para compatibilidad pero no hace nada.
        """
        pass

    @action(detail=True, methods=['post'], url_path='activar')
    def activar(self, request, pk=None):
        """
        POST /api/v1/cotizaciones/configuracion/{id}/activar/
        
        # WARNING: v2.60: MÚLTIPLES PERFILES ACTIVOS PERMITIDOS
        Marca un perfil como activo sin desactivar los demás.
        
        # WARNING: Error Boundary Pattern: Todos los errores retornan JSON nativo (sin template_name).
        """
        try:
            perfil = self.get_object()
            perfil.es_activo = True
            perfil.save()
            
            logger.info(f"Perfil de configuración activado: {perfil.nombre_configuracion} (ID: {perfil.id})")
            
            serializer = self.get_serializer(perfil)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except serializers.ValidationError as e:
            logger.error(f"[ConfiguracionCotizacionViewSet] Error de validación en activar: {str(e)}", exc_info=True)
            error_detail = e.detail if hasattr(e, 'detail') else str(e)
            # # WARNING: Error Boundary: Siempre devolver estructura {"error": "...", "detail": "..."}
            if isinstance(error_detail, dict):
                # Si el dict ya tiene "error" y "detail", usarlo; si no, envolverlo
                if "error" in error_detail and "detail" in error_detail:
                    return Response(error_detail, status=status.HTTP_400_BAD_REQUEST)
                # Si es un dict de errores de campo, convertirlo a formato estándar
                return Response(
                    {"error": "Error de validación", "detail": error_detail},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                {"error": "Error de validación", "detail": str(error_detail)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except Exception as e:
            logger.error(f"[ConfiguracionCotizacionViewSet] Error inesperado en activar: {str(e)}", exc_info=True)
            return Response(
                {"error": "Ocurrió un error inesperado al activar la configuración.", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
