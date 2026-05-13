"""
ViewSet para Proyectos v3.5 - Alineado con Tabulator Factory y FSD

WARNING: SINTEL v3.5: API-First & Zero-Coupling
- DSV Pattern: Inyección de servicios vía ProyectoServiceMixin
- Zero Trust: Aislamiento estricto por empresa_id
- Performance: Queries optimizadas (Zero Waste) vía Selectors
"""
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.response import Response

from apps.tenant.api.permissions import IsTenantAdminOrReadOnly, IsTenantMember
from apps.tenant.empresa.models import Empresa
from .serializers import ProyectoDetailSerializer, ProyectoListSerializer
from .mixins import ProyectoServiceMixin
from ..models import Proyecto

class StandardResultsSetPagination(PageNumberPagination):
    """
    Paginación estándar SaaS para Tabulator.
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class ProyectoViewSet(
    ProyectoServiceMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    """
    ViewSet para Proyectos v3.5.
    Delegación absoluta al Service Layer modularizado.
    """
    queryset = Proyecto.objects.none()
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ProyectoListSerializer
        return ProyectoDetailSerializer
    
    def get_empresa(self):
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            raise APIException(detail='No se encontró la empresa (SSoT) configurada en este tenant.')
        return empresa
    
    def get_queryset(self):
        """Usa el selector optimizado con Zero Trust."""
        empresa = self.get_empresa()
        search = self.request.query_params.get('search', None)
        return self.proyecto_selector(empresa_id=empresa.id, search=search)
    
    def get_object(self):
        """Usa el selector de detalle optimizado."""
        empresa = self.get_empresa()
        obj = self.proyecto_detail_selector(empresa_id=empresa.id, pk=self.kwargs['pk'])
        if not obj:
            raise NotFound("Proyecto no encontrado o no pertenece a este tenant.")
        return obj
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data,
            'next': None,
            'previous': None
        }, status=status.HTTP_200_OK)
    
    def create(self, request, *args, **kwargs):
        import logging
        logger = logging.getLogger(__name__)
        
        empresa = self.get_empresa()
        serializer = self.get_serializer(data=request.data)
        
        # ⚠️ Logging para debug de validación
        if not serializer.is_valid():
            logger.error(f"[ProyectoViewSet] Validación fallida: {serializer.errors}")
            logger.error(f"[ProyectoViewSet] Datos recibidos: {request.data}")
            return Response(
                {'detail': 'Datos inválidos', 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Orquestación vía Business Service
        try:
            proyecto = self.proyecto_business_service.orchestrate_create_proyecto(
                empresa, 
                serializer.validated_data
            )
        except ValidationError as e:
            logger.error(f"[ProyectoViewSet] Error de negocio: {e.detail}")
            return Response(
                {'detail': 'Error de validación de negocio', 'errors': e.detail},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        response_serializer = ProyectoDetailSerializer(proyecto)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        proyecto = self.get_object()
        serializer = self.get_serializer(proyecto, data=request.data)
        serializer.is_valid(raise_exception=True)
        
        proyecto = self.proyecto_business_service.orchestrate_update_proyecto(
            proyecto, 
            serializer.validated_data
        )
        
        response_serializer = ProyectoDetailSerializer(proyecto)
        return Response(response_serializer.data)
    
    def partial_update(self, request, *args, **kwargs):
        proyecto = self.get_object()
        serializer = self.get_serializer(proyecto, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        proyecto = self.proyecto_business_service.orchestrate_update_proyecto(
            proyecto, 
            serializer.validated_data
        )
        
        response_serializer = ProyectoDetailSerializer(proyecto)
        return Response(response_serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        proyecto = self.get_object()
        self.proyecto_crud_service.delete_proyecto(proyecto)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'], url_path='avanzar-fase')
    def avanzar_fase(self, request, pk=None):
        """
        POST /api/v1/proyectos/{id}/avanzar-fase/
        """
        proyecto = self.get_object()
        nueva_fase = request.data.get('fase')
        responsable_id = request.data.get('responsable_id', None)
        responsable_nombre = request.data.get('responsable_nombre', None)
        
        if not nueva_fase:
            return Response({'detail': 'El campo "fase" es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            self.proyecto_business_service.cambiar_fase_proyecto(
                proyecto, nueva_fase, responsable_id, responsable_nombre
            )
            # calcular_indicadores_financieros guarda internamente via crud_service
            self.proyecto_business_service.calcular_indicadores_financieros(proyecto)
            
            response_serializer = ProyectoDetailSerializer(proyecto)
            return Response(response_serializer.data)
            
        except ValidationError as e:
            return Response({'detail': str(e.detail) if hasattr(e, 'detail') else str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='gestor-offcanvas')
    def gestor_offcanvas(self, request):
        """
        [FSD v3.5] Devuelve el HTML del formulario local de la app Proyectos.
        """
        empresa = self.get_empresa()
        proyecto = None
        id_instancia = request.query_params.get('id')
        
        if id_instancia:
            proyecto = get_object_or_404(self.get_queryset(), id=id_instancia)
        
        clientes = []
        try:
            from apps.tenant.clientes.models import Cliente
            clientes = Cliente.objects.filter(empresa_id=empresa.id, activo=True).only(
                'id', 'razon_social', 'numero_documento'
            ).order_by('razon_social')[:100]
        except ImportError:
            pass
        
        empleados = []
        try:
            from apps.tenant.empleados.services.selectors import EmpleadoSelector
            empleados = EmpleadoSelector.get_list(empresa_id=empresa.id).only(
                'id', 'primer_nombre', 'primer_apellido', 'segundo_nombre', 'segundo_apellido'
            )[:100]
        except ImportError:
            pass
            
        proveedores = []
        try:
            from apps.tenant.proveedores.models import Proveedor
            proveedores = Proveedor.objects.filter(empresa_id=empresa.id, activo=True).only(
                'id', 'razon_social', 'numero_documento'
            ).order_by('razon_social')[:100]
        except ImportError:
            pass
            
        context = {
            'proyecto': proyecto,
            'clientes': clientes,
            'empleados': empleados,
            'proveedores': proveedores,
            'tipos_servicio': Proyecto.TIPO_SERVICIO,
            'fases': Proyecto.FASES,
            'estados_tarea': Proyecto.ESTADO_TAREA,
        }
        
        # [v3.5] Ruta local FSD
        return Response(context, template_name='tenant/proyectos/offcanvas_form.html')
