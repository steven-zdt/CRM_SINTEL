"""
ViewSets para la app contabilidad.

WARNING: v2.60: ENFORCED MODE implementado.
POST/PATCH/PUT/DELETE solo para STAFF/ADMIN; no-staff recibe 405.
WARNING: v2.60: Alineado con Service Layer Pattern.
WARNING: IMPORTANTE: 
- django-tenants maneja automáticamente el aislamiento por esquema
- NO es necesario filtrar manualmente por tenant_id

Referencia: https://www.django-rest-framework.org/api-guide/viewsets/
"""
import logging
import traceback

from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response

from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.api.mixins import SintelDSVMixin, SintelServiceMixin
from apps.tenant.api.permissions import IsTenantMember, IsTenantAdminOrReadOnly

logger = logging.getLogger(__name__)

from apps.config.api.pagination import StandardResultsSetPagination
from apps.tenant.contabilidad.api.serializers import (
    AsientoContableDetailSerializer,
    AsientoContableListSerializer,
    CatalogoMaestroNIIFDetailSerializer,
    CatalogoMaestroNIIFListSerializer,
    CuentaContableDetailSerializer,
    CuentaContableListSerializer,
    MovimientoContableDetailSerializer,
    MovimientoContableListSerializer,
    PeriodoContableDetailSerializer,
    PeriodoContableListSerializer,
)
from apps.tenant.contabilidad.models import (
    AsientoContable,
    CatalogoMaestroNIIF,
    CuentaContable,
    MovimientoContable,
    PeriodoContable,
)
from apps.tenant.contabilidad.services.selectors import (
    qs_asiento_detail,
    qs_asiento_list,
    qs_cuenta_detail,
    qs_cuenta_list,
    qs_periodo_detail,
    qs_periodo_list,
    get_asiento_by_identifier,
    get_cuenta_by_identifier,
    get_periodo_by_identifier,
)
from apps.tenant.contabilidad.services.business_service import ContabilidadBusinessService


class ContabilidadServiceMixin(SintelServiceMixin):
    """Bridge layer that decouples viewsets from direct business logic calls."""
    service_class = ContabilidadBusinessService
    mutation_lookup_fields = ("id", "uuid")

    def get_mutation_queryset(self, model_class, *extra_fields):
        fields = list(self.mutation_lookup_fields)
        fields.extend(extra_fields)
        return model_class.objects.only(*fields)


class CuentaContableViewSet(SintelDSVMixin, ContabilidadServiceMixin, BaseTenantViewSet):
    """
    ViewSet para CuentaContable.
    [ARCHITECTURE v3.5]
    - DSV: Validación inyectiva de empresa_id.
    - SSoT: Selectors para lectura, Business Service para escritura.
    """
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['tipo', 'activa', 'cuenta_padre']
    search_fields = ['codigo', 'nombre', 'descripcion']
    ordering_fields = ['codigo', 'nombre', 'tipo']
    ordering = ['codigo']
    
    def get_serializer_class(self):
        if self.action in ["retrieve", "render_offcanvas_editar", "render_offcanvas_detalle"]:
            return CuentaContableDetailSerializer
        return CuentaContableListSerializer
    
    def get_queryset(self):
        if self.action == "list":
            return qs_cuenta_list().order_by('codigo')
        elif self.action in ["retrieve", "render_offcanvas_detalle", "render_offcanvas_editar"]:
            return qs_cuenta_detail()
        return self.get_mutation_queryset(CuentaContable)
    
    def create(self, request, *args, **kwargs):
        try:
            empresa_id = self.get_empresa_id()
            payload = request.data.copy()
            # Inyección DSV
            payload['empresa_id'] = empresa_id
            
            # TODO: v3.5: business_service.crear_cuenta aún no existe, 
            # se usa crud_service directo por ahora o se añade al business
            resultado = self.service.crud.crear_cuenta(empresa_id, payload)
            
            cuenta = CuentaContable.objects.get(id=resultado.id)
            serializer = CuentaContableDetailSerializer(cuenta, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return self.handle_service_error(e)
    
    def update(self, request, *args, **kwargs):
        try:
            cuenta_id = kwargs.get('pk') or self.get_object().id
            payload = request.data.copy()
            
            resultado = self.service.crud.actualizar_cuenta(cuenta_id, payload)
            
            cuenta = CuentaContable.objects.get(id=resultado.id)
            serializer = CuentaContableDetailSerializer(cuenta, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)

    def destroy(self, request, *args, **kwargs):
        try:
            cuenta_identifier = kwargs.get('uuid') or kwargs.get('pk')
            cuenta = get_cuenta_by_identifier(cuenta_identifier)
            self.service.eliminar_cuenta(cuenta.id)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/crear')
    def render_offcanvas_crear(self, request):
        """
        Endpoint HTMX RESTful para cargar offcanvas de creación de cuentas contables.
        
        WARNING: v2.60: Feature-Sliced Architecture - Template dedicado para creación
        - GET /api/v1/contabilidad/cuentas-contables/render-offcanvas/crear/ → Modo creación
        
        Returns:
            Template HTML: tenant/contabilidad/partials/cuenta_offcanvas_form.html
        """
        context = {'cuenta': None}
        return Response(context, template_name='tenant/contabilidad/partials/cuenta_offcanvas_form.html')
    
    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/editar')
    def render_offcanvas_editar(self, request, **kwargs):
        """HTMX: Carga offcanvas de edición."""
        try:
            cuenta_identifier = kwargs.get('uuid') or kwargs.get('pk')
            cuenta = get_cuenta_by_identifier(cuenta_identifier)
            serializer = self.get_serializer(cuenta)
            return Response({'cuenta': serializer.data}, template_name='tenant/contabilidad/partials/cuenta_offcanvas_form.html')
        except Exception as e:
            logger.error(f"Error en render_offcanvas_editar: {e}")
            return Response({"detail": [str(e)]}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/detalle')
    def render_offcanvas_detalle(self, request, **kwargs):
        """HTMX: Carga offcanvas de detalle."""
        try:
            cuenta_identifier = kwargs.get('uuid') or kwargs.get('pk')
            cuenta = get_cuenta_by_identifier(cuenta_identifier)
            serializer = self.get_serializer(cuenta)
            return Response({'cuenta': serializer.data}, template_name='tenant/contabilidad/partials/cuenta_offcanvas_detalle.html')
        except Exception as e:
            logger.error(f"Error en render_offcanvas_detalle: {e}")
            return Response({'error': str(e)}, template_name='tenant/contabilidad/partials/cuenta_offcanvas_detalle.html', status=500)

    @action(detail=False, methods=['get'], renderer_classes=[JSONRenderer], url_path='cuentas_gasto')
    def cuentas_gasto(self, request):
        """Lista cuentas marcadas como GASTO."""
        try:
            resultados = self.service.obtener_cuentas_gasto(self.get_empresa_id())
            return Response(resultados, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=False, methods=['get'], url_path='cuentas-proveedor')
    def cuentas_proveedor(self, request):
        """
        WARNING: v2.61.8: Retorna listado de cuentas Clase 2 (Pasivos) compatibles con proveedores.
        Utilizado por el Offcanvas de Proveedores para el mapeo NIIF.
        """
        empresa = self.get_empresa()
        
        # Filtro: Clase 2 (Pasivos) y Nivel 6 (Subcuenta)
        # WARNING: PERFORMANCE BIBLE: Solo traer campos necesarios
        from apps.tenant.contabilidad.models import CuentaContable
        cuentas = list(CuentaContable.objects.filter(
            empresa=empresa,
            codigo__startswith='2',
            nivel=6,
            activa=True
        ).only('codigo', 'nombre').values('codigo', 'nombre'))
        
        return Response(cuentas)



class AsientoContableViewSet(SintelDSVMixin, ContabilidadServiceMixin, BaseTenantViewSet):
    """
    ViewSet para AsientoContable.
    
    WARNING: v2.40: ENFORCED MODE - POST/PATCH/PUT/DELETE solo para STAFF/ADMIN.
    WARNING: v2.37: Usa qs_asiento_list() y qs_asiento_detail() del service.
    WARNING: OPTIMIZACIÓN: NO usa .all(), usa only() para reducir SELECT.
    """
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['estado', 'fecha']
    search_fields = ['numero', 'descripcion']
    ordering_fields = ['fecha', 'numero', 'total_debe', 'total_haber', 'created_at']
    ordering = ['-fecha', '-numero']
    
    def get_serializer_class(self):
        """Selecciona el serializer según la acción."""
        if self.action == "retrieve":
            return AsientoContableDetailSerializer
        return AsientoContableListSerializer
    
    def get_queryset(self):
        """
        QuerySet optimizado usando qs_asiento_list() y qs_asiento_detail() del service.
        
        WARNING: v2.37: Alineado con Service Layer Pattern.
        """
        if self.action == "list":
            return qs_asiento_list().order_by('-fecha', '-numero')
        elif self.action == "retrieve":
            return qs_asiento_detail()
        else:
            return self.get_mutation_queryset(AsientoContable, 'numero', 'estado', 'fecha')
    
    def retrieve(self, request, *args, **kwargs):
        """Soporte para IDs numéricos y UUIDs."""
        try:
            asiento_identifier = kwargs.get('uuid') or kwargs.get('pk')
            asiento = get_asiento_by_identifier(asiento_identifier)
            serializer = self.get_serializer(asiento)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error en retrieve: {e}")
            return Response({"detail": [str(e)]}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def create(self, request, *args, **kwargs):
        try:
            empresa_id = self.get_empresa_id()
            payload = request.data.copy()
            payload['empresa_id'] = empresa_id
            
            resultado = self.service.crear_asiento(empresa_id, payload)
            
            asiento = qs_asiento_detail().get(id=resultado['id'])
            serializer = AsientoContableDetailSerializer(asiento, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return self.handle_service_error(e)

    def update(self, request, *args, **kwargs):
        try:
            asiento_identifier = kwargs.get('uuid') or kwargs.get('pk')
            asiento = get_asiento_by_identifier(asiento_identifier)
            resultado = self.service.actualizar_asiento(asiento.id, request.data)
            asiento = qs_asiento_detail().get(id=resultado['id'])
            serializer = AsientoContableDetailSerializer(asiento, context={'request': request})
            return Response(serializer.data)
        except Exception as e:
            return self.handle_service_error(e)

    def destroy(self, request, *args, **kwargs):
        try:
            asiento_identifier = kwargs.get('uuid') or kwargs.get('pk')
            asiento = get_asiento_by_identifier(asiento_identifier)
            self.service.eliminar_asiento(asiento.id)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=True, methods=['post'], url_path='aprobar')
    def aprobar(self, request, **kwargs):
        try:
            asiento_identifier = kwargs.get('uuid') or kwargs.get('pk')
            asiento = get_asiento_by_identifier(asiento_identifier)
            self.service.aprobar_asiento(asiento.id)
            asiento = qs_asiento_detail().get(id=asiento.id)
            serializer = AsientoContableDetailSerializer(asiento, context={'request': request})
            return Response(serializer.data)
        except Exception as e:
            return self.handle_service_error(e)

    
    @action(detail=False, methods=['get'], url_path='balance-prueba')
    def balance_prueba(self, request):
        try:
            empresa_id = self.get_empresa_id()
            fecha_desde = request.query_params.get('fecha_desde')
            fecha_hasta = request.query_params.get('fecha_hasta')
            
            balance = self.service.obtener_balance_prueba(
                empresa_id=empresa_id,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta
            )
            return Response(balance, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/crear')
    def render_offcanvas_crear(self, request):
        """
        Endpoint HTMX RESTful para cargar offcanvas de creación de asientos contables.
        
        WARNING: v2.60: Feature-Sliced Architecture - Template dedicado para creación
        - GET /api/v1/contabilidad/asientos-contables/render-offcanvas/crear/ → Modo creación
        
        Returns:
            Template HTML: tenant/contabilidad/partials/asiento_offcanvas_form.html
        """
        context = {'asiento': None}
        return Response(context, template_name='tenant/contabilidad/partials/asiento_offcanvas_form.html')
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/cargar-desde-documentos')
    def render_offcanvas_cargar_desde_documentos(self, request):
        """
        Endpoint HTMX RESTful para cargar offcanvas de selección de documentos.
        
        WARNING: v2.60 Fase 3: Asistente de Selección - Lista Facturas y Gastos sin asiento
        
        Returns:
            Template HTML: tenant/contabilidad/partials/asiento_offcanvas_cargar_desde_docs.html
        """
        context = {}
        return Response(context, template_name='tenant/contabilidad/partials/asiento_offcanvas_cargar_desde_docs.html')
    
    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/editar')
    def render_offcanvas_editar(self, request, **kwargs):
        """HTMX: Carga offcanvas de edición."""
        try:
            asiento_identifier = kwargs.get('uuid') or kwargs.get('pk')
            asiento = get_asiento_by_identifier(asiento_identifier)
            serializer = AsientoContableDetailSerializer(asiento, context={'request': request})
            return Response({'asiento': serializer.data}, template_name='tenant/contabilidad/partials/asiento_offcanvas_editar.html')
        except Exception as e:
            logger.error(f"Error en render_offcanvas_editar: {e}")
            return Response({"detail": [str(e)]}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], url_path='documentos-sin-asiento')
    def documentos_sin_asiento(self, request):
        try:
            tipo = request.query_params.get('tipo', '').lower()
            resultado = self.service.listar_documentos_sin_asiento(tipo)
            return Response(resultado, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)
    
    @action(detail=False, methods=['post'], url_path='crear-desde-documentos')
    def crear_desde_documentos(self, request):
        try:
            facturas_ids = request.data.get('facturas', [])
            gastos_ids = request.data.get('gastos', [])
            
            if not facturas_ids and not gastos_ids:
                return Response(
                    {"error": "At least one factura_id or gasto_id is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            resultado = self.service.materializar_documentos(facturas_ids, gastos_ids)
            return Response(resultado, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/detalle')
    def render_offcanvas_detalle(self, request):
        """HTMX: Carga offcanvas de detalle."""
        try:
            asiento_id = request.query_params.get('id')
            asiento = get_asiento_by_identifier(asiento_id)
            serializer = AsientoContableDetailSerializer(asiento, context={'request': request})
            return Response({'asiento': serializer.data}, template_name='tenant/contabilidad/partials/asiento_offcanvas_detalle.html')
        except Exception as e:
            logger.error(f"Error en render_offcanvas_detalle: {e}")
            return Response({'error': str(e)}, template_name='tenant/contabilidad/partials/asiento_offcanvas_detalle.html', status=500)


class MovimientoContableViewSet(SintelDSVMixin, ContabilidadServiceMixin, BaseTenantViewSet):
    """
    ViewSet para MovimientoContable.
    [ARCHITECTURE v3.5]
    """
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['asiento', 'cuenta']
    search_fields = ['descripcion', 'cuenta__nombre']
    ordering_fields = ['asiento', 'orden', 'debe', 'haber']
    ordering = ['asiento', 'orden']
    
    def get_serializer_class(self):
        if self.action == "retrieve":
            return MovimientoContableDetailSerializer
        return MovimientoContableListSerializer
    
    def get_queryset(self):
        # Campos mínimos para LIST (Zero Waste)
        list_fields = ('id', 'asiento', 'cuenta', 'orden', 'debe', 'haber', 'descripcion')
        return MovimientoContable.objects.only(*list_fields).select_related('cuenta').order_by('asiento', 'orden')

    def create(self, request, *args, **kwargs):
        try:
            empresa_id = self.get_empresa_id()
            payload = request.data.copy()
            payload['empresa_id'] = empresa_id
            
            resultado = self.service.crud.crear_movimiento(empresa_id, payload)
            
            serializer = MovimientoContableDetailSerializer(resultado, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return self.handle_service_error(e)

    def update(self, request, *args, **kwargs):
        try:
            mov_id = kwargs.get('pk') or self.get_object().id
            payload = request.data.copy()
            
            resultado = self.service.crud.actualizar_movimiento(mov_id, payload)
            
            serializer = MovimientoContableDetailSerializer(resultado, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)

    def destroy(self, request, *args, **kwargs):
        try:
            mov_id = kwargs.get('pk') or self.get_object().id
            self.service.crud.eliminar_movimiento(mov_id)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return self.handle_service_error(e)


class CatalogoMaestroNIIFViewSet(SintelDSVMixin, ContabilidadServiceMixin, BaseTenantViewSet):
    """
    ViewSet para CatalogoMaestroNIIF (Catálogo oficial NIIF Colombia).
    [ARCHITECTURE v3.5]
    """
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['nivel', 'naturaleza', 'activa']
    search_fields = ['codigo', 'nombre']
    ordering_fields = ['codigo', 'nombre', 'nivel']
    ordering = ['codigo']
    
    def get_serializer_class(self):
        if self.action == "retrieve":
            return CatalogoMaestroNIIFDetailSerializer
        return CatalogoMaestroNIIFListSerializer
    
    def get_queryset(self):
        if self.action in ["list", "buscar_por_tipo"]:
            return CatalogoMaestroNIIF.objects.only(
                'id', 'codigo', 'nombre', 'nivel', 'naturaleza', 'activa'
            ).order_by('codigo')
        return CatalogoMaestroNIIF.objects.prefetch_related('cuentas_vinculadas')
    
    def create(self, request, *args, **kwargs):
        try:
            codigo = request.data.get('codigo')
            if not codigo:
                return Response({'error': 'Codigo is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            resultado = self.service.materializar_catalogo_niif(codigo)
            
            serializer = CatalogoMaestroNIIFDetailSerializer(resultado, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=False, methods=['get'], url_path='buscar-por-tipo')
    def buscar_por_tipo(self, request):
        try:
            tipo = request.query_params.get('tipo', None)
            search = request.query_params.get('search', '').strip()
            nivel = request.query_params.get('nivel', None)
            
            if not tipo:
                return Response({'error': 'El parámetro "tipo" es requerido'}, status=status.HTTP_400_BAD_REQUEST)
            
            resultados = self.service.buscar_catalogo_niif_por_tipo(
                tipo=tipo,
                search=search,
                nivel=nivel
            )
            
            return Response(resultados, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)


class PeriodoContableViewSet(SintelDSVMixin, ContabilidadServiceMixin, BaseTenantViewSet):
    """
    ViewSet para PeriodoContable.
    [ARCHITECTURE v3.5]
    """
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['estado', 'periodo']
    search_fields = ['periodo', 'observaciones']
    ordering_fields = ['periodo', 'fecha_inicio', 'fecha_fin', 'created_at']
    ordering = ['-periodo']
    
    def get_serializer_class(self):
        if self.action in ["retrieve", "render_offcanvas_editar", "render_offcanvas_detalle"]:
            return PeriodoContableDetailSerializer
        return PeriodoContableListSerializer
    
    def get_queryset(self):
        if self.action == "list":
            return qs_periodo_list().order_by('-periodo')
        elif self.action == "retrieve":
            return qs_periodo_detail()
        return self.get_mutation_queryset(PeriodoContable, 'periodo', 'estado')

    def create(self, request, *args, **kwargs):
        try:
            resultado = self.service.crear_periodo(self.get_empresa_id(), request.data)
            periodo = qs_periodo_detail().get(id=resultado['id'])
            serializer = PeriodoContableDetailSerializer(periodo, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return self.handle_service_error(e)

    def update(self, request, *args, **kwargs):
        try:
            periodo_identifier = kwargs.get('uuid') or kwargs.get('pk')
            periodo = get_periodo_by_identifier(periodo_identifier)
            resultado = self.service.actualizar_periodo(periodo.id, request.data)
            periodo = qs_periodo_detail().get(id=resultado['id'])
            serializer = PeriodoContableDetailSerializer(periodo, context={'request': request})
            return Response(serializer.data)
        except Exception as e:
            return self.handle_service_error(e)

    def destroy(self, request, *args, **kwargs):
        try:
            periodo_identifier = kwargs.get('uuid') or kwargs.get('pk')
            periodo = get_periodo_by_identifier(periodo_identifier)
            self.service.eliminar_periodo(periodo.id)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/crear')
    def render_offcanvas_crear(self, request):
        """HTMX: Carga offcanvas de creación."""
        return Response({}, template_name='tenant/contabilidad/partials/periodo_offcanvas_form.html')

    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/editar')
    def render_offcanvas_editar(self, request, **kwargs):
        """HTMX: Carga offcanvas de edición."""
        try:
            periodo_identifier = kwargs.get('uuid') or kwargs.get('pk')
            periodo = get_periodo_by_identifier(periodo_identifier)
            serializer = self.get_serializer(periodo)
            return Response({'periodo': serializer.data}, template_name='tenant/contabilidad/partials/periodo_offcanvas_form.html')
        except Exception as e:
            logger.error(f"Error en render_offcanvas_editar: {e}")
            return Response({"detail": [str(e)]}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/detalle')
    def render_offcanvas_detalle(self, request, **kwargs):
        """HTMX: Carga offcanvas de detalle."""
        try:
            periodo_identifier = kwargs.get('uuid') or kwargs.get('pk')
            periodo = get_periodo_by_identifier(periodo_identifier)
            serializer = self.get_serializer(periodo)
            return Response({'periodo': serializer.data}, template_name='tenant/contabilidad/partials/periodo_offcanvas_detalle.html')
        except Exception as e:
            logger.error(f"Error en render_offcanvas_detalle: {e}")
            return Response({"detail": [str(e)]}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Lista de ViewSets para registro automático en el router
VIEWSETS = [
    (r'cuentas-contables', CuentaContableViewSet, 'cuenta-contable'),
    (r'asientos-contables', AsientoContableViewSet, 'asiento-contable'),
    (r'movimientos-contables', MovimientoContableViewSet, 'movimiento-contable'),
    (r'periodos-contables', PeriodoContableViewSet, 'periodo-contable'),  # WARNING: v2.61
    (r'catalogo-niif', CatalogoMaestroNIIFViewSet, 'catalogo-niif'),
]
