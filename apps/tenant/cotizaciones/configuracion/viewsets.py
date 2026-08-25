"""
ViewSets para Configuracion de Cotizaciones v2.62.0 - SINTEL FSD
"""
import logging

from django.db import IntegrityError
from rest_framework import permissions, serializers, status
from rest_framework.decorators import action
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from apps.config.api.pagination import StandardResultsSetPagination
from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.api.permissions import IsTenantMember

from .models import ConfiguracionCotizacion
from .serializers import (
    ConfiguracionCotizacionDetailSerializer,
    ConfiguracionCotizacionListSerializer,
)
from .services import ConfiguracionServiceMixin

logger = logging.getLogger(__name__)


class ConfiguracionCotizacionViewSet(SintelDSVMixin, ConfiguracionServiceMixin, BaseTenantViewSet):
    """
    ViewSet para Perfiles de Configuracion de Cotizaciones v2.62.0.
    """
    # # WARNING: CRITICO: DRF necesita un queryset definido para generar las rutas del router
    # Usamos .none() como base porque el filtrado real se hace en get_queryset()
    queryset = ConfiguracionCotizacion.objects.none()
    serializer_class = ConfiguracionCotizacionDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]
    renderer_classes = [JSONRenderer]
    pagination_class = StandardResultsSetPagination


    def get_queryset(self):
        """Filtrado por empresa del tenant actual (Zero Waste)."""
        queryset = self.get_qs_list()
        
        solo_activos = self.request.query_params.get('solo_activos', None)
        if solo_activos == 'true':
            queryset = queryset.filter(es_activo=True)
        
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(nombre_configuracion__icontains=search)
        
        return queryset.order_by('-es_activo', 'nombre_configuracion')

    def get_serializer_class(self):
        """Diferenciacion entre List (Ligero) y Detail (Completo)."""
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
            
            instance = self.service_crear_configuracion(serializer)
            logger.info(f"Perfil de configuracion creado: {instance.nombre_configuracion}")
            
            output_serializer = self.get_serializer(instance)
            headers = self.get_success_headers(output_serializer.data)
            return Response(output_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        
        except serializers.ValidationError as e:
            logger.error(f"[ConfiguracionCotizacionViewSet] Error de validacion en create: {str(e)}", exc_info=True)
            error_detail = e.detail if hasattr(e, 'detail') else str(e)
            # # WARNING: Error Boundary: Siempre devolver estructura {"error": "...", "detail": "..."}
            if isinstance(error_detail, dict):
                # Si el dict ya tiene "error" y "detail", usarlo; si no, envolverlo
                if "error" in error_detail and "detail" in error_detail:
                    return Response(error_detail, status=status.HTTP_400_BAD_REQUEST)
                # Si es un dict de errores de campo, convertirlo a formato estandar
                return Response(
                    {"error": "Error de validacion", "detail": error_detail},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                {"error": "Error de validacion", "detail": str(error_detail)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except IntegrityError as e:
            logger.error(f"[ConfiguracionCotizacionViewSet] Error de integridad en create: {str(e)}", exc_info=True)
            # Verificar si es un error de unicidad
            if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
                return Response(
                    {
                        "error": "Ya existe una configuracion con estos datos. Por favor, verifique la informacion.",
                        "detail": str(e),
                        "code": "duplicate_configuracion"
                    },
                    status=status.HTTP_409_CONFLICT
                )
            return Response(
                {"error": "Error de integridad de datos", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
            return Response(
                {"error": "Ocurrio un error inesperado al crear la configuracion.", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, *args, **kwargs):
        """Actualizacion de configuracion via Service Layer."""
        try:
            partial = kwargs.get('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            
            updated_instance = self.service_actualizar_configuracion(instance, serializer)
            logger.info(f"Perfil de configuracion actualizado: {updated_instance.nombre_configuracion}")
            
            return Response(self.get_serializer(updated_instance).data)
            
        except Exception as e:
            logger.error(f"[ConfiguracionCotizacionViewSet] Error en update: {str(e)}", exc_info=True)
            return Response(
                {"error": "Error al actualizar configuracion", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


    @action(detail=True, methods=['post'], url_path='activar')
    def activar(self, request, pk=None):
        """
        POST /api/v1/cotizaciones/configuracion/{id}/activar/
        
        # WARNING: v2.60: MULTIPLES PERFILES ACTIVOS PERMITIDOS
        Marca un perfil como activo sin desactivar los demas.
        
        # WARNING: Error Boundary Pattern: Todos los errores retornan JSON nativo (sin template_name).
        """
        try:
            perfil = self.get_object()
            perfil.es_activo = True
            perfil.save()
            
            logger.info(f"Perfil de configuracion activado: {perfil.nombre_configuracion} (ID: {perfil.id})")
            
            serializer = self.get_serializer(perfil)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except serializers.ValidationError as e:
            logger.error(f"[ConfiguracionCotizacionViewSet] Error de validacion en activar: {str(e)}", exc_info=True)
            error_detail = e.detail if hasattr(e, 'detail') else str(e)
            # # WARNING: Error Boundary: Siempre devolver estructura {"error": "...", "detail": "..."}
            if isinstance(error_detail, dict):
                # Si el dict ya tiene "error" y "detail", usarlo; si no, envolverlo
                if "error" in error_detail and "detail" in error_detail:
                    return Response(error_detail, status=status.HTTP_400_BAD_REQUEST)
                # Si es un dict de errores de campo, convertirlo a formato estandar
                return Response(
                    {"error": "Error de validacion", "detail": error_detail},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                {"error": "Error de validacion", "detail": str(error_detail)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except Exception as e:
            logger.error(f"[ConfiguracionCotizacionViewSet] Error inesperado en activar: {str(e)}", exc_info=True)
            return Response(
                {"error": "Ocurrio un error inesperado al activar la configuracion.", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
