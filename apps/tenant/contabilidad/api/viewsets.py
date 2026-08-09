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
import calendar
import logging
import traceback
from datetime import date
from decimal import Decimal

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
from apps.tenant.core.services.organizational_context import OrganizationalContextMixin

logger = logging.getLogger(__name__)

def _decimal_from_value(value):
    """Convierte valores del timeline a Decimal sin propagar None/string vacio."""
    if value in (None, ''):
        return Decimal('0')
    return Decimal(str(value))


def _date_from_timeline(value):
    """Extrae YYYY-MM-DD del timeline como date para templates/serializers."""
    raw = str(value or '')[:10]
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None

from apps.config.api.pagination import StandardResultsSetPagination
from apps.tenant.contabilidad.api.serializers import (
    AsientoContableDetailSerializer,
    AsientoContableListSerializer,
    AsistenteIAInputSerializer,
    CatalogoMaestroNIIFDetailSerializer,
    CatalogoMaestroNIIFListSerializer,
    ConfiguracionRetencionesDetailSerializer,
    ConfiguracionRetencionesListSerializer,
    ContabilizarManualInputSerializer,
    CuentaContableDetailSerializer,
    CuentaContableListSerializer,
    DocumentoPendienteSerializer,
    MovimientoContableDetailSerializer,
    MovimientoContableListSerializer,
    PeriodoContableDetailSerializer,
    PeriodoContableListSerializer,
    LineaPlantillaSerializer,
    PlantillaContableDetailSerializer,
    PlantillaContableListSerializer,
    RetencionDetailSerializer,
    RetencionListSerializer,
    TipoComprobanteDetailSerializer,
    TipoComprobanteListSerializer,
    ReporteFinancieroInputSerializer,
    BalancePruebaOutputSerializer,
    EstadoResultadosOutputSerializer,
    LibroDiarioSerializer,
)
from apps.tenant.contabilidad.models import (
    AsientoContable,
    CatalogoMaestroNIIF,
    ConfiguracionRetenciones,
    CuentaContable,
    LineaPlantilla,
    MovimientoContable,
    PeriodoContable,
    PlantillaContable,
    ReglaContable,
    Retencion,
    TipoComprobante,
)
from apps.tenant.contabilidad.services.selectors import (
    AsientoContableSelector,
    CuentaContableSelector,
    PeriodoContableSelector,
    PlantillaContableSelector,
    TipoComprobanteSelector,
    get_asiento_by_identifier,
    get_cuenta_by_identifier,
    get_periodo_by_identifier,
    qs_facturas_pendientes,
    qs_gastos_pendientes,
    qs_nominas_pendientes,
    qs_inventario_movimientos_recientes_pendientes,
    get_documento_pendiente,
    balance_prueba_selector,
    estado_resultados_selector,
    filtrar_cuentas_por_app_origen,
    get_libro_diario_periodo,
    qs_periodos_disponibles,
)
from apps.tenant.contabilidad.services.business_service import ContabilidadBusinessService
from apps.tenant.contabilidad.services.retenciones_service import RetencionesService
from apps.tenant.contabilidad.integracion.dtos import LineaManual, ComprobanteManualDTO


class ContabilidadServiceMixin(SintelServiceMixin):
    """Bridge layer that decouples viewsets from direct business logic calls."""
    service_class = ContabilidadBusinessService
    mutation_lookup_fields = ("id", "uuid")

    def get_mutation_queryset(self, model_class, *extra_fields):
        fields = list(self.mutation_lookup_fields)
        fields.extend(extra_fields)
        return model_class.objects.only(*fields)


class CuentaContableViewSet(OrganizationalContextMixin, SintelDSVMixin, ContabilidadServiceMixin, BaseTenantViewSet):
    """
    ViewSet para CuentaContable.
    [ARCHITECTURE v3.5]
    - DSV: Validación inyectiva de empresa_id.
    - SSoT: Selectors para lectura, Business Service para escritura.

    Fase 9 (OCF): OrganizationalContextMixin adoptado de forma aditiva en
    los 10 ViewSets de esta app. Caso de PARIDAD (no divergencia): toda la
    app ya hereda SintelDSVMixin y usa self.get_empresa_id() directamente -
    la misma SSoT que OrganizationalContext.resolve() duplica (Fase 2).
    get_queryset() no se migra de todos modos: cada Selector de esta app
    tiene su propio .only()/select_related que context.filter() generico
    no replica.
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
            qs = CuentaContableSelector.get_qs_list(self.get_empresa_id()).order_by('codigo')

            # Filtro por app de origen (restringe a prefijos PUC relevantes)
            app_origen = self.request.query_params.get('app_origen', '').strip()
            if app_origen:
                qs = filtrar_cuentas_por_app_origen(qs, app_origen)

            # Filtro por prefijo de código (ej. codigo_prefix=15 para activos, 51 para gastos)
            codigo_prefix = self.request.query_params.get('codigo_prefix', '').strip()
            if codigo_prefix:
                qs = qs.filter(codigo__startswith=codigo_prefix)

            # solo_auxiliares=true → solo nivel 6 (unico nivel que recibe movimientos contables)
            solo_auxiliares = self.request.query_params.get('solo_auxiliares', '').lower() == 'true'
            if solo_auxiliares:
                qs = qs.filter(nivel=6)

            # Soporte lookup por UUID para resolucion de nombre desde apps externas (§18 HTTP pull)
            uuid_param = self.request.query_params.get('uuid', '').strip()
            if uuid_param:
                qs = qs.filter(uuid=uuid_param)

            return qs
        elif self.action in ["retrieve", "render_offcanvas_detalle", "render_offcanvas_editar"]:
            return CuentaContableSelector.get_qs_detail()
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

    @action(detail=False, methods=['post'], url_path='sincronizar')
    def sincronizar(self, request):
        """
        POST /api/v1/contabilidad/cuentas-contables/sincronizar/
        Crea en CuentaContable todas las entradas del CatalogoMaestroNIIF
        que aun no existen para la empresa. Idempotente.
        Requiere que el catalogo este poblado (make poblar-catalogo).
        """
        try:
            empresa_id = self.get_empresa_id()
            resultado = self.service.sincronizar_cuentas_plan(empresa_id)
            return Response(resultado, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=False, methods=['get'], url_path='cuentas-proveedor')
    def cuentas_proveedor(self, request):
        """
        Retorna cuentas filtradas para proveedores (gastos/pasivos).
        """
        try:
            qs = CuentaContableSelector.get_qs_list(self.get_empresa_id()).order_by('codigo')
            qs = filtrar_cuentas_por_app_origen(qs, 'gastos')
            serializer = CuentaContableListSerializer(qs, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error en cuentas_proveedor: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





class AsientoContableViewSet(OrganizationalContextMixin, SintelDSVMixin, ContabilidadServiceMixin, BaseTenantViewSet):
    """
    ViewSet para AsientoContable.
    
    WARNING: v2.40: ENFORCED MODE - POST/PATCH/PUT/DELETE solo para STAFF/ADMIN.
    WARNING: v2.37: Usa AsientoContableSelector.get_qs_list() y AsientoContableSelector.get_qs_detail() del service.
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
        QuerySet optimizado usando AsientoContableSelector.get_qs_list() y AsientoContableSelector.get_qs_detail() del service.
        
        WARNING: v2.37: Alineado con Service Layer Pattern.
        """
        if self.action == "list":
            return AsientoContableSelector.get_qs_list(self.get_empresa_id()).order_by('-fecha', '-numero')
        elif self.action == "retrieve":
            return AsientoContableSelector.get_qs_detail(self.get_empresa_id())
        else:
            return self.get_mutation_queryset(AsientoContable, 'numero', 'estado', 'fecha').filter(empresa_id=self.get_empresa_id())
    
    def retrieve(self, request, *args, **kwargs):
        """Soporte para IDs numéricos y UUIDs."""
        try:
            asiento_identifier = kwargs.get('uuid') or kwargs.get('pk')
            asiento = get_asiento_by_identifier(asiento_identifier, empresa_id=self.get_empresa_id())
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
            
            asiento = AsientoContableSelector.get_qs_detail(empresa_id).get(id=resultado['id'])
            serializer = AsientoContableDetailSerializer(asiento, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return self.handle_service_error(e)

    def update(self, request, *args, **kwargs):
        try:
            asiento_identifier = kwargs.get('uuid') or kwargs.get('pk')
            asiento = get_asiento_by_identifier(asiento_identifier, empresa_id=self.get_empresa_id())
            resultado = self.service.actualizar_asiento(asiento.id, request.data)
            asiento = AsientoContableSelector.get_qs_detail(self.get_empresa_id()).get(id=resultado['id'])
            serializer = AsientoContableDetailSerializer(asiento, context={'request': request})
            return Response(serializer.data)
        except Exception as e:
            return self.handle_service_error(e)

    def destroy(self, request, *args, **kwargs):
        identifier = str(kwargs.get('uuid') or kwargs.get('pk') or '')
        if not identifier:
            return Response({'error': 'missing_id', 'message': 'UUID requerido'}, status=status.HTTP_400_BAD_REQUEST)
        empresa_id = self.get_empresa_id()
        deleted, _ = AsientoContable.objects.filter(uuid=identifier, empresa_id=empresa_id).delete()
        if not deleted:
            # Fallback: intentar por PK entero
            try:
                deleted, _ = AsientoContable.objects.filter(pk=int(identifier), empresa_id=empresa_id).delete()
            except (ValueError, TypeError):
                pass
        if not deleted:
            return Response({'error': 'not_found', 'message': f'Asiento {identifier} no existe'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='aprobar')
    def aprobar(self, request, **kwargs):
        try:
            asiento_identifier = kwargs.get('uuid') or kwargs.get('pk')
            asiento = get_asiento_by_identifier(asiento_identifier, empresa_id=self.get_empresa_id())
            self.service.aprobar_asiento(asiento.id)
            asiento = AsientoContableSelector.get_qs_detail(self.get_empresa_id()).get(id=asiento.id)
            serializer = AsientoContableDetailSerializer(asiento, context={'request': request})
            return Response(serializer.data)
        except Exception as e:
            return self.handle_service_error(e)

    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='reporte')
    def reporte_page(self, request):
        """
        Endpoint HTMX/UI para cargar la página de reportes financieros.
        
        WARNING: v3.5: Feature-Sliced UI - Template dedicado
        """
        return Response({}, template_name='tenant/contabilidad/reporte_page.html')

    @action(
        methods=["GET"],
        detail=False,
        url_path="reporte-balance-prueba",
        permission_classes=[IsTenantMember],
    )
    def balance_prueba(self, request):
        """
        Retorna el Balance de Prueba (Saldos y Movimientos) para un periodo.
        GET /api/v1/contabilidad/asientos-contables/reporte-balance-prueba/?fecha_inicio=...&fecha_fin=...
        """
        serializer = ReporteFinancieroInputSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        empresa_id = self.get_empresa_id()
        
        # Invocación al selector
        resultado = balance_prueba_selector(
            empresa_id=empresa_id,
            fecha_inicio=data['fecha_inicio'],
            fecha_fin=data['fecha_fin']
        )
        
        # Serialización de salida
        output = BalancePruebaOutputSerializer(resultado, many=True)
        return Response(output.data, status=status.HTTP_200_OK)

    @action(
        methods=["GET"],
        detail=False,
        url_path="reporte-estado-resultados",
        permission_classes=[IsTenantMember],
    )
    def estado_resultados(self, request):
        """
        Retorna el Estado de Resultados (P&G) para un periodo.
        GET /api/v1/contabilidad/asientos-contables/reporte-estado-resultados/?fecha_inicio=...&fecha_fin=...
        """
        serializer = ReporteFinancieroInputSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        empresa_id = self.get_empresa_id()
        
        # Invocación al selector
        resultado = estado_resultados_selector(
            empresa_id=empresa_id,
            fecha_inicio=data['fecha_inicio'],
            fecha_fin=data['fecha_fin']
        )
        
        # Serialización de salida
        output = EstadoResultadosOutputSerializer(resultado)
        return Response(output.data, status=status.HTTP_200_OK)

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
    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/editar')
    def render_offcanvas_editar(self, request, uuid=None):
        """HTMX: Carga offcanvas de edición."""
        try:
            asiento = AsientoContableSelector.get_qs_detail(
                empresa_id=self.get_empresa_id()
            ).filter(uuid=uuid).first()
            
            if not asiento:
                return Response({'error': 'Asiento no encontrado'}, status=404)
                
            serializer = AsientoContableDetailSerializer(asiento, context={'request': request})
            return Response({'asiento': serializer.data}, template_name='tenant/contabilidad/partials/asiento_offcanvas_editar.html')
        except Exception as e:
            logger.error(f"Error en render_offcanvas_editar: {e}")
            return Response({'error': str(e)}, template_name='tenant/contabilidad/partials/asiento_offcanvas_editar.html', status=500)

    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/detalle')
    def render_offcanvas_detalle(self, request, uuid=None):
        """HTMX: Carga offcanvas de detalle."""
        try:
            asiento = AsientoContableSelector.get_qs_detail(
                empresa_id=self.get_empresa_id()
            ).filter(uuid=uuid).first()
            
            if not asiento:
                return Response({'error': 'Asiento no encontrado'}, status=404)
                
            serializer = AsientoContableDetailSerializer(asiento, context={'request': request})
            return Response({'asiento': serializer.data}, template_name='tenant/contabilidad/partials/asiento_offcanvas_detalle.html')
        except Exception as e:
            logger.error(f"Error en render_offcanvas_detalle: {e}")
            return Response({'error': str(e)}, template_name='tenant/contabilidad/partials/asiento_offcanvas_detalle.html', status=500)


class MovimientoContableViewSet(OrganizationalContextMixin, SintelDSVMixin, ContabilidadServiceMixin, BaseTenantViewSet):
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


class CatalogoMaestroNIIFViewSet(OrganizationalContextMixin, SintelDSVMixin, ContabilidadServiceMixin, BaseTenantViewSet):
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
        return CatalogoMaestroNIIF.objects.only(
            'id', 'codigo', 'nombre', 'nivel', 'naturaleza', 'activa'
        ).prefetch_related('cuentas_vinculadas').order_by('codigo')
    
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


class PeriodoContableViewSet(OrganizationalContextMixin, SintelDSVMixin, ContabilidadServiceMixin, BaseTenantViewSet):
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
        empresa_id = self.get_empresa_id()
        if self.action == "list":
            return PeriodoContableSelector.get_qs_list(empresa_id).order_by('-periodo')
        elif self.action == "retrieve":
            return PeriodoContableSelector.get_qs_detail(empresa_id)
        return self.get_mutation_queryset(PeriodoContable, 'periodo', 'estado')

    def create(self, request, *args, **kwargs):
        try:
            resultado = self.service.crear_periodo(self.get_empresa_id(), request.data)
            periodo = PeriodoContableSelector.get_qs_detail().get(id=resultado['id'])
            serializer = PeriodoContableDetailSerializer(periodo, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return self.handle_service_error(e)

    def update(self, request, *args, **kwargs):
        try:
            periodo_identifier = kwargs.get('uuid') or kwargs.get('pk')
            periodo = get_periodo_by_identifier(periodo_identifier)
            resultado = self.service.actualizar_periodo(periodo.id, request.data)
            periodo = PeriodoContableSelector.get_qs_detail().get(id=resultado['id'])
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

    @action(detail=True, methods=['post'], url_path='cerrar')
    def cerrar(self, request, **kwargs):
        """POST /periodos-contables/{uuid}/cerrar/ — Cierra un periodo ABIERTO."""
        try:
            periodo_identifier = kwargs.get('uuid') or kwargs.get('pk')
            periodo = get_periodo_by_identifier(periodo_identifier)
            resultado = self.service.cerrar_periodo(periodo.id, request.data)
            periodo_obj = PeriodoContableSelector.get_qs_detail().get(id=resultado['id'])
            serializer = PeriodoContableDetailSerializer(periodo_obj, context={'request': request})
            return Response(serializer.data)
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


class TipoComprobanteViewSet(OrganizationalContextMixin, SintelDSVMixin, ContabilidadServiceMixin, BaseTenantViewSet):
    """
    ViewSet para TipoComprobante.
    Permite configurar plantillas de comprobantes (CC, RC, NC, etc.) con prefijos y consecutivos.
    """
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['activa', 'codigo']
    search_fields = ['codigo', 'nombre', 'prefijo']
    ordering_fields = ['codigo', 'nombre', 'prefijo', 'consecutivo_actual']
    ordering = ['codigo']

    def get_serializer_class(self):
        if self.action == "retrieve":
            return TipoComprobanteDetailSerializer
        return TipoComprobanteListSerializer

    def get_queryset(self):
        empresa_id = self.get_empresa_id()
        if self.action == "list":
            return TipoComprobanteSelector.get_qs_list(empresa_id).order_by('codigo')
        return TipoComprobanteSelector.get_qs_detail(empresa_id).order_by('codigo')

    def create(self, request, *args, **kwargs):
        try:
            empresa_id = self.get_empresa_id()
            payload = request.data.copy()
            payload['empresa_id'] = empresa_id
            
            # TODO: Mover a Business Service si hay lógica compleja
            comprobante = TipoComprobante.objects.create(**payload)
            
            serializer = TipoComprobanteDetailSerializer(comprobante, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return self.handle_service_error(e)

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        except Exception as e:
            return self.handle_service_error(e)


class DocumentosPendientesViewSet(OrganizationalContextMixin, SintelDSVMixin, ContabilidadServiceMixin, BaseTenantViewSet):
    """
    Documentos pendientes de contabilizar + endpoint de asignacion manual On-Demand.

    GET  /api/v1/contabilidad/pendientes/                      -> lista unificada
    GET  /api/v1/contabilidad/pendientes/render-offcanvas/     -> offcanvas HTMX
    POST /api/v1/contabilidad/pendientes/contabilizar-manual/  -> genera asiento
    """
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    pagination_class = None
    http_method_names = ['get', 'post', 'head', 'options']

    def get_serializer_class(self):
        return DocumentoPendienteSerializer

    def get_queryset(self):
        return AsientoContable.objects.none()

    def list(self, request, *args, **kwargs):
        # DSV: Aislamiento por empresa
        if hasattr(self, 'get_empresa_id'):
            empresa_id = self.get_empresa_id()
        else:
            # Fallback direct access if mixin lookup fails
            empresa_id = request.user.tenant_profile.empresa_id if hasattr(request.user, 'tenant_profile') else None
        
        if not empresa_id:
             return Response({"error": "No se encontró configuración de empresa."}, status=400)
             
        resultado = []

        for f in qs_facturas_pendientes(empresa_id):
            es_venta = getattr(f, 'naturaleza', '') == 'VENTA'
            fecha = f.fecha_emision
            if hasattr(fecha, 'date'):
                fecha = fecha.date()
            resultado.append({
                'tipo_doc': 'FACTURA',
                'app_label': 'facturas',
                'modelo': 'Factura',
                'documento_id': f.id,
                'numero': f.numero,
                'fecha': str(fecha),
                'tercero_nit': f.receptor_nit if es_venta else f.emisor_nit,
                'tercero_nombre': f.receptor_razon_social if es_venta else f.emisor_razon_social,
                'subtotal': str(f.subtotal),
                'impuestos': str(f.impuestos),
                'total': str(f.total),
                'estado': f.estado,
            })

        for g in qs_gastos_pendientes(empresa_id):
            resultado.append({
                'tipo_doc': 'GASTO',
                'app_label': 'gastos',
                'modelo': 'DocumentoSoporte',
                'documento_id': g.id,
                'numero': g.numero_documento,
                'fecha': str(g.fecha),
                'tercero_nit': g.proveedor.numero_documento,
                'tercero_nombre': g.proveedor.razon_social,
                'subtotal': str(g.subtotal),
                'impuestos': str(g.total_retefuente + g.total_reteica),
                'total': str(g.total),
                'estado': 'ACTIVO',
            })

        for n in qs_nominas_pendientes(empresa_id):
            resultado.append({
                'tipo_doc': 'NOMINA',
                'app_label': 'empleados',
                'modelo': 'Devengo',
                'documento_id': n.id,
                'numero': f"{n.periodo_mes}",
                'fecha': str(n.fecha_pago),
                'tercero_nit': n.empleado.numero_documento,
                'tercero_nombre': f"{n.empleado.primer_nombre} {n.empleado.primer_apellido}",
                'subtotal': str(n.neto_pagar),
                'impuestos': "0.00",
                'total': str(n.neto_pagar),
                'estado': 'ACTIVO',
            })

        for item in qs_inventario_movimientos_recientes_pendientes(empresa_id):
            cantidad = _decimal_from_value(item.get('cantidad'))
            valor = _decimal_from_value(item.get('valor_costo'))
            total = (cantidad * valor).quantize(Decimal('0.01'))
            fecha = _date_from_timeline(item.get('fecha'))
            resultado.append({
                'tipo_doc': 'INVENTARIO',
                'app_label': 'inventario',
                'modelo': item.get('modelo_origen'),
                'documento_id': item.get('documento_id'),
                'numero': item.get('referencia') or item.get('uuid'),
                'fecha': str(fecha) if fecha else '',
                'tercero_nit': 'N/A',
                'tercero_nombre': item.get('item_nombre') or item.get('modulo_origen') or 'Movimiento de inventario',
                'subtotal': str(total),
                'impuestos': "0.00",
                'total': str(total),
                'estado': item.get('tipo_accion_display') or 'ACTIVO',
            })

        return Response(resultado, status=status.HTTP_200_OK)


    @action(
        detail=False, methods=['get'],
        renderer_classes=[TemplateHTMLRenderer],
        url_path='render-offcanvas',
    )
    def render_offcanvas_contabilizar(self, request):
        app_label = request.query_params.get('app', '')
        modelo = request.query_params.get('modelo', '')
        documento_id_str = request.query_params.get('id', '')

        if not all([app_label, modelo, documento_id_str]):
            return Response(
                {'error': 'Parametros app, modelo e id son requeridos.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            documento_id = int(documento_id_str)
        except ValueError:
            return Response({'error': 'id debe ser entero.'}, status=status.HTTP_400_BAD_REQUEST)

        empresa_id = self.get_empresa_id()
        doc = get_documento_pendiente(app_label, modelo, documento_id, empresa_id)
        if not doc:
            return Response(
                {'error': 'Documento no encontrado o ya contabilizado.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        _cero = Decimal('0.00')
        if app_label == 'facturas':
            es_venta = getattr(doc, 'naturaleza', '') == 'VENTA'
            fecha = doc.fecha_emision
            if hasattr(fecha, 'date'):
                fecha = fecha.date()
            _retefuente = Decimal(str(getattr(doc, 'retefuente', _cero) or _cero))
            _reteica    = Decimal(str(getattr(doc, 'reteica', _cero) or _cero))
            _impuestos  = Decimal(str(doc.impuestos))
            _iva        = max(_cero, _impuestos - _retefuente - _reteica)
            ctx = {
                'app_label': app_label, 'modelo': modelo, 'documento_id': documento_id,
                'numero': doc.numero, 'fecha': fecha,
                'subtotal': doc.subtotal, 'impuestos': _impuestos, 'total': doc.total,
                'iva_generado': _iva, 'retefuente': _retefuente,
                'reteica': _reteica, 'reteiva': _cero,
                'tercero_nit': doc.receptor_nit if es_venta else doc.emisor_nit,
                'tercero_nombre': doc.receptor_razon_social if es_venta else doc.emisor_razon_social,
            }
        elif app_label == 'empleados':
            ctx = {
                'app_label': app_label, 'modelo': modelo, 'documento_id': documento_id,
                'numero': doc.periodo_mes, 'fecha': doc.fecha_pago,
                'subtotal': doc.neto_pagar,
                'impuestos': _cero, 'iva_generado': _cero,
                'retefuente': _cero, 'reteica': _cero, 'reteiva': _cero,
                'total': doc.neto_pagar,
                'tercero_nit': doc.empleado.numero_documento,
                'tercero_nombre': f"{doc.empleado.primer_nombre} {doc.empleado.primer_apellido}",
            }
        elif app_label == 'inventario':
            cantidad = _decimal_from_value(doc.get('cantidad'))
            valor = _decimal_from_value(doc.get('valor_costo'))
            total = (cantidad * valor).quantize(Decimal('0.01'))
            fecha = _date_from_timeline(doc.get('fecha'))
            ctx = {
                'app_label': app_label, 'modelo': modelo, 'documento_id': documento_id,
                'numero': doc.get('referencia') or doc.get('uuid'), 'fecha': fecha,
                'subtotal': total,
                'impuestos': _cero, 'iva_generado': _cero,
                'retefuente': _cero, 'reteica': _cero, 'reteiva': _cero,
                'total': total,
                'tercero_nit': 'N/A',
                'tercero_nombre': doc.get('item_nombre') or doc.get('modulo_origen') or 'Movimiento de inventario',
            }
        else:
            # Pull Model v3.7.1 (ADR-001): retefuente/reteica ya no son campos
            # directos del documento -- se leen desde Contabilidad.Retencion via
            # las properties total_retefuente/total_reteica (ver DocumentoSoporte).
            _retefuente = Decimal(str(doc.total_retefuente or _cero))
            _reteica    = Decimal(str(doc.total_reteica or _cero))
            ctx = {
                'app_label': app_label, 'modelo': modelo, 'documento_id': documento_id,
                'numero': doc.numero_documento, 'fecha': doc.fecha,
                'subtotal': doc.subtotal,
                'impuestos': _retefuente + _reteica,
                'iva_generado': _cero, 'retefuente': _retefuente,
                'reteica': _reteica, 'reteiva': _cero,
                'total': doc.total,
                'tercero_nit': doc.proveedor.numero_documento,
                'tercero_nombre': doc.proveedor.razon_social,
            }

        # Obtener tipos de comprobante activos v3.6
        ctx['tipos_comprobante'] = TipoComprobante.objects.filter(
            empresa_id=empresa_id, activa=True
        ).only('id', 'codigo', 'nombre', 'prefijo', 'consecutivo_actual')

        # Obtener periodos contables abiertos utilizables para contabilización v3.8
        ctx['periodos_disponibles'] = qs_periodos_disponibles(empresa_id)


        # Obtener sugerencias de cuentas basadas en reglas v3.6
        if app_label == 'facturas':
            tipo_tx = 'VENTA_FACTURA'
        elif app_label == 'empleados':
            tipo_tx = 'NOMINA_LIQUIDACION'
        elif app_label == 'inventario':
            if modelo == 'HistorialServicio':
                tipo_tx = 'VENTA_FACTURA'
            else:
                tipo_accion = str(doc.get('tipo_accion', ''))
                tipo_tx = 'COMPRA_INVENTARIO' if tipo_accion.startswith('ENTRADA') else 'SALIDA_INVENTARIO_VENTA'
        else:
            tipo_tx = 'COMPRA_GASTO'

        reglas = ReglaContable.objects.filter(
            empresa_id=empresa_id,
            tipo_transaccion=tipo_tx,
            activo=True
        ).only('concepto', 'cuenta_codigo')
        
        sugerencias = []
        for r in reglas:
            cuenta = CuentaContable.objects.filter(empresa_id=empresa_id, codigo=r.cuenta_codigo).only('nombre').first()
            sugerencias.append({
                'concepto': r.concepto,
                'cuenta_codigo': r.cuenta_codigo,
                'cuenta_nombre': cuenta.nombre if cuenta else 'Cuenta no encontrada'
            })
        ctx['sugerencias_puc'] = sugerencias

        # ── Auto-Inferencia de Plantilla (Motor Fase 3 v3.17.0) ──────────────────
        # Mapeo tipo_tx (TipoTransaccion.value) -> tipo_motor (VENTA/COMPRA/GASTO/NOMINA)
        _TIPO_A_MOTOR = {
            'VENTA_FACTURA': 'VENTA', 'VENTA_NOTA_CREDITO': 'VENTA',
            'VENTA_NOTA_DEBITO': 'VENTA', 'SALIDA_INVENTARIO_VENTA': 'VENTA',
            'RECAUDO_CLIENTE': 'VENTA',
            'COMPRA_GASTO': 'COMPRA', 'COMPRA_NOTA_CREDITO': 'COMPRA',
            'COMPRA_INVENTARIO': 'COMPRA', 'ACTIVO_FIJO_COMPRA': 'COMPRA',
            'PAGO_PROVEEDOR': 'COMPRA',
            'INVENTARIO_COSTO_VENTA': 'GASTO', 'BAJA_INVENTARIO': 'GASTO',
            'AJUSTE_INVENTARIO': 'GASTO',
            'NOMINA_LIQUIDACION': 'NOMINA', 'NOMINA_PROVISION': 'NOMINA',
            'NOMINA_PAGO': 'NOMINA', 'NOMINA_RETIRO': 'NOMINA',
        }
        tipo_motor = _TIPO_A_MOTOR.get(tipo_tx, '')
        ctx['requiere_revision_plantilla'] = False
        ctx['plantilla_sugerida_uuid'] = ''

        if tipo_motor:
            plantilla_activa = PlantillaContableSelector.obtener_motor_plantilla(
                empresa_id, tipo_motor
            )
            if not plantilla_activa:
                try:
                    plantilla_sugerida = self.service.inferir_y_crear_plantilla_desde_documento(
                        empresa_id=empresa_id,
                        app_label=app_label,
                        modelo=modelo,
                        documento_id=documento_id,
                    )
                    ctx['requiere_revision_plantilla'] = True
                    ctx['plantilla_sugerida_uuid'] = str(plantilla_sugerida.uuid)
                    logger.info(
                        '[render_offcanvas] Plantilla borrador %s generada para %s/%s/%s',
                        plantilla_sugerida.uuid, app_label, modelo, documento_id,
                    )
                except Exception as exc_inf:
                    # Fallo suave: el usuario puede seguir contabilizando manualmente
                    logger.warning(
                        '[render_offcanvas] No se pudo inferir plantilla para %s/%s/%s: %s',
                        app_label, modelo, documento_id, exc_inf,
                    )

        return Response(
            ctx,
            template_name='tenant/contabilidad/partials/pendiente_offcanvas_contabilizar.html',
        )

    @action(detail=False, methods=['post'], url_path='contabilizar-manual')
    def contabilizar_manual(self, request):
        serializer = ContabilizarManualInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        empresa_id = self.get_empresa_id()

        try:
            dto = ComprobanteManualDTO(
                empresa_id=empresa_id,
                fecha=data['fecha'],
                descripcion=data['descripcion'],
                app_label=data['app_label'],
                modelo=data['modelo'],
                documento_id=data['documento_id'],
                documento_numero=data['documento_numero'],
                tipo_comprobante_id=data['tipo_comprobante_id'],
                periodo_uuid=str(data['periodo_uuid']),
                lineas=[
                    LineaManual(
                        cuenta_codigo=l['cuenta_codigo'],
                        debe=Decimal(str(l.get('debe', 0))),
                        haber=Decimal(str(l.get('haber', 0))),
                        descripcion=l.get('descripcion', ''),
                        tercero_nit=l.get('tercero_nit', ''),
                        tercero_razon_social=l.get('tercero_razon_social', ''),
                    )
                    for l in data['lineas']
                ],
            )
            resultado = self.service.contabilizar_documento_manual(empresa_id, dto)
            return Response(resultado, status=status.HTTP_201_CREATED)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=False, methods=['post'], url_path='asistente-ia')
    def asistente_ia(self, request):
        """
        POST /api/v1/contabilidad/pendientes/asistente-ia/

        Recibe datos del documento pendiente y devuelve lineas de asiento
        sugeridas por el modelo Claude (Anthropic API).
        El frontend inyecta las lineas en el offcanvas; el contador revisa y confirma.
        """
        serializer = AsistenteIAInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        empresa_id = self.get_empresa_id()

        ctx = {
            'numero': data.get('numero', ''),
            'subtotal': data['subtotal'],
            'impuestos': data['impuestos'],
            'total': data['total'],
            'tercero_nit': data.get('tercero_nit', ''),
            'tercero_nombre': data.get('tercero_nombre', ''),
        }

        try:
            lineas = self.service.sugerir_lineas_asiento_ia(
                empresa_id=empresa_id,
                app_label=data['app_label'],
                ctx=ctx,
            )
            return Response({'lineas': lineas}, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)


class ConfiguracionRetencionesViewSet(OrganizationalContextMixin, SintelDSVMixin, BaseTenantViewSet):
    """
    ViewSet para ConfiguracionRetenciones (v3.7.1).
    Gestiona configuración de tasas de retención por tercero.
    """
    queryset = ConfiguracionRetenciones.objects.none()
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['tipo_tercero', 'tipo_retencion', 'naturaleza', 'activa']
    search_fields = ['nit_tercero', 'tipo_tercero']
    ordering_fields = ['tipo_tercero', 'nit_tercero', 'tipo_retencion']
    ordering = ['tipo_tercero', 'nit_tercero']
    # WARNING: [ARQ-A1] lookup_field='uuid' se hereda de BaseTenantViewSet — no
    # redeclarar con 'id' (exponia la PK entera en la URL, AGENTS.md §25.1).

    def get_queryset(self):
        """Retorna queryset optimizado para ConfiguracionRetenciones."""
        return ConfiguracionRetenciones.objects.select_related('cuenta_retencion').only(
            'id', 'uuid', 'tipo_tercero', 'nit_tercero', 'tipo_retencion',
            'porcentaje_por_defecto', 'activa', 'naturaleza', 'created_at',
            'cuenta_retencion__uuid', 'cuenta_retencion__codigo', 'cuenta_retencion__nombre'
        )

    def get_serializer_class(self):
        """Selecciona serializer según acción."""
        if self.action == 'retrieve':
            return ConfiguracionRetencionesDetailSerializer
        return ConfiguracionRetencionesListSerializer

    def perform_create(self, serializer):
        """Asigna automáticamente la empresa del tenant al crear."""
        empresa_id = self.get_empresa_id()
        serializer.save(empresa_id=empresa_id)


class RetencionViewSet(OrganizationalContextMixin, SintelDSVMixin, BaseTenantViewSet):
    """
    ViewSet para Retencion (v3.7.1).
    Gestiona registros de retenciones aplicadas a documentos.

    Pull Model: Las retenciones se vinculan a documentos en otras apps
    vía (documento_origen_app, documento_origen_modelo, documento_origen_id).
    """
    queryset = Retencion.objects.none()
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = [
        'tipo', 'naturaleza', 'reversada', 'documento_origen_app', 'documento_origen_modelo'
    ]
    search_fields = ['uuid', 'documento_origen_app', 'documento_origen_modelo']
    ordering_fields = ['tipo', 'monto', 'created_at']
    ordering = ['-created_at']
    lookup_field = 'uuid'

    def get_queryset(self):
        """Retorna queryset optimizado para Retencion."""
        return Retencion.objects.select_related(
            'configuracion', 'asiento_contable'
        ).only(
            'id', 'uuid', 'tipo', 'porcentaje', 'base', 'monto', 'naturaleza',
            'documento_origen_app', 'documento_origen_modelo', 'documento_origen_id',
            'reversada', 'created_at',
            'configuracion__id', 'configuracion__tipo_tercero',
            'asiento_contable__uuid', 'asiento_contable__numero'
        )

    def get_serializer_class(self):
        """Selecciona serializer según acción."""
        if self.action == 'retrieve':
            return RetencionDetailSerializer
        return RetencionListSerializer

    def perform_create(self, serializer):
        """Asigna automáticamente la empresa del tenant al crear."""
        empresa_id = self.get_empresa_id()
        serializer.save(empresa_id=empresa_id)

    @action(detail=False, methods=['get'], url_path='obtener-por-tercero')
    def obtener_por_tercero(self, request):
        """
        GET /api/v1/contabilidad/retenciones/obtener-por-tercero/?nit=&tipo_tercero=&naturaleza=

        Obtiene configuración de retenciones para un tercero específico.
        Soporta fallback a defaults si no existe configuración específica.

        Query params:
        - nit: NIT del tercero (normalizado)
        - tipo_tercero: CLIENTE, PROVEEDOR, EMPLEADO
        - naturaleza: VENTA, COMPRA (default: VENTA)

        Returns:
            {
                'aplica_retefuente': bool,
                'retefuente_porcentaje': Decimal,
                'aplica_reteica': bool,
                'reteica_porcentaje': Decimal,
                'aplica_reteiva': bool,
                'reteiva_porcentaje': Decimal,
            }
        """
        nit = request.query_params.get('nit')
        tipo_tercero = request.query_params.get('tipo_tercero', 'CLIENTE')
        naturaleza = request.query_params.get('naturaleza', 'VENTA')

        if not nit:
            return Response(
                {'error': 'missing_nit', 'message': 'Parámetro nit es obligatorio'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            empresa_id = self.get_empresa_id()
            retenciones = RetencionesService.obtener_retenciones_desde_tercero(
                nit=nit,
                tipo_tercero=tipo_tercero,
                naturaleza=naturaleza,
                empresa_id=empresa_id,
            )

            # Convertir Decimal a string para JSON
            result = {
                k: str(v) if isinstance(v, Decimal) else v
                for k, v in retenciones.items()
            }

            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception('Error obteniendo retenciones')
            return Response(
                {'error': 'internal_error', 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='obtener-por-documento')
    def obtener_por_documento(self, request):
        """
        GET /api/v1/contabilidad/retenciones/obtener-por-documento/?app=&modelo=&id=

        Obtiene todas las retenciones de un documento específico.

        Query params:
        - app: documento_origen_app (ej: facturas)
        - modelo: documento_origen_modelo (ej: Factura, ItemFactura)
        - id: documento_origen_id (ID del documento)

        Returns:
            [
                {uuid, tipo, porcentaje, monto, ...},
                ...
            ]
        """
        app = request.query_params.get('app')
        modelo = request.query_params.get('modelo')
        doc_id = request.query_params.get('id')

        if not all([app, modelo, doc_id]):
            return Response(
                {'error': 'missing_params', 'message': 'Parámetros app, modelo, id son obligatorios'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            empresa_id = self.get_empresa_id()
            retenciones = RetencionesService.listar_retenciones_por_documento(
                documento_origen_app=app,
                documento_origen_modelo=modelo,
                documento_origen_id=int(doc_id),
                empresa_id=empresa_id,
            )

            serializer = RetencionListSerializer(retenciones, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception('Error listando retenciones')
            return Response(
                {'error': 'internal_error', 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LibroDiarioViewSet(OrganizationalContextMixin, SintelDSVMixin, ContabilidadServiceMixin, viewsets.ViewSet):
    """
    Libro Diario Contable — Vista Unificada Raw + Procesado (Normatividad PYMES Colombia).

    Código de Comercio Art. 48: Registro cronológico de todas las transacciones.
    Devuelve documentos pendientes + contabilizados con cuentas PUC resueltas.

    GET /api/v1/contabilidad/libro-diario/?periodo=2026-05
    GET /api/v1/contabilidad/libro-diario/?fecha_inicio=2026-05-01&fecha_fin=2026-05-31
    """
    permission_classes = [IsTenantMember]

    def list(self, request, *args, **kwargs):
        empresa_id = self.get_empresa_id()
        periodo_param = request.query_params.get('periodo', '').strip()
        fecha_inicio_str = request.query_params.get('fecha_inicio', '').strip()
        fecha_fin_str = request.query_params.get('fecha_fin', '').strip()

        fecha_inicio = fecha_fin = None

        if periodo_param:
            try:
                año, mes = map(int, periodo_param.split('-'))
                fecha_inicio = date(año, mes, 1)
                fecha_fin = date(año, mes, calendar.monthrange(año, mes)[1])
            except (ValueError, IndexError):
                return Response(
                    {'detail': 'Formato de periodo invalido. Use YYYY-MM.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        elif fecha_inicio_str and fecha_fin_str:
            try:
                fecha_inicio = date.fromisoformat(fecha_inicio_str)
                fecha_fin = date.fromisoformat(fecha_fin_str)
            except ValueError:
                return Response(
                    {'detail': 'Formato de fecha invalido. Use YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            hoy = date.today()
            fecha_inicio = date(hoy.year, hoy.month, 1)
            fecha_fin = hoy

        resultado = get_libro_diario_periodo(empresa_id, fecha_inicio, fecha_fin)
        serializer = LibroDiarioSerializer(resultado)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PlantillaContableViewSet(OrganizationalContextMixin, SintelDSVMixin, ContabilidadServiceMixin, BaseTenantViewSet):
    """
    ViewSet para PlantillaContable + LineaPlantilla (Motor Fase 3 v3.16.2).

    GET  /api/v1/contabilidad/plantillas-contables/              -> listado
    GET  /api/v1/contabilidad/plantillas-contables/{uuid}/       -> detalle con lineas
    GET  /api/v1/contabilidad/plantillas-contables/render-offcanvas/crear/
    GET  /api/v1/contabilidad/plantillas-contables/{uuid}/render-offcanvas/editar/
    GET  /api/v1/contabilidad/plantillas-contables/{uuid}/render-offcanvas/detalle/
    POST /api/v1/contabilidad/plantillas-contables/              -> crear plantilla
    PATCH /api/v1/contabilidad/plantillas-contables/{uuid}/      -> actualizar plantilla
    DELETE /api/v1/contabilidad/plantillas-contables/{uuid}/     -> eliminar plantilla
    POST /api/v1/contabilidad/plantillas-contables/{uuid}/lineas/   -> agregar linea
    DELETE /api/v1/contabilidad/plantillas-contables/{uuid}/lineas/{linea_id}/ -> eliminar linea
    """
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['tipo_transaccion', 'activo']
    search_fields = ['nombre', 'tipo_transaccion']
    ordering_fields = ['tipo_transaccion', 'nombre', 'activo', 'created_at']
    ordering = ['-activo', 'tipo_transaccion']

    def get_serializer_class(self):
        if self.action in ('retrieve', 'render_offcanvas_editar', 'render_offcanvas_detalle'):
            return PlantillaContableDetailSerializer
        return PlantillaContableListSerializer

    def get_queryset(self):
        empresa_id = self.get_empresa_id()
        if self.action == 'list':
            return PlantillaContableSelector.get_qs_list(empresa_id)
        return PlantillaContableSelector.get_qs_detail(empresa_id)

    def create(self, request, *args, **kwargs):
        empresa_id = self.get_empresa_id()
        data = request.data.copy()
        try:
            plantilla = PlantillaContable.objects.create(
                empresa_id=empresa_id,
                nombre=data.get('nombre') or None,
                tipo_transaccion=data.get('tipo_transaccion') or None,
                activo=data.get('activo', True),
            )
            serializer = PlantillaContableDetailSerializer(plantilla)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return self.handle_service_error(e)

    def partial_update(self, request, *args, **kwargs):
        empresa_id = self.get_empresa_id()
        plantilla = self.get_object()
        data = request.data
        try:
            if 'nombre' in data:
                plantilla.nombre = data['nombre'] or None
            if 'tipo_transaccion' in data:
                plantilla.tipo_transaccion = data['tipo_transaccion'] or None
            if 'activo' in data:
                plantilla.activo = data['activo']
            plantilla.save()
            serializer = PlantillaContableDetailSerializer(plantilla)
            return Response(serializer.data)
        except Exception as e:
            return self.handle_service_error(e)

    def destroy(self, request, *args, **kwargs):
        plantilla = self.get_object()
        try:
            plantilla.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=True, methods=['post'], url_path='lineas')
    def agregar_linea(self, request, **kwargs):
        """POST /plantillas-contables/{uuid}/lineas/ — agrega una LineaPlantilla."""
        empresa_id = self.get_empresa_id()
        plantilla = self.get_object()
        data = request.data
        cuenta_id = data.get('cuenta_contable')
        if not cuenta_id:
            return Response({'detail': 'cuenta_contable es obligatorio'}, status=400)
        try:
            linea = LineaPlantilla.objects.create(
                empresa_id=empresa_id,
                plantilla=plantilla,
                cuenta_contable_id=cuenta_id,
                naturaleza=data.get('naturaleza', 'DEBE'),
                origen_valor=data.get('origen_valor', 'SALDO_BASE'),
                porcentaje_aplicar=Decimal(str(data.get('porcentaje_aplicar', '100.00'))),
                orden=int(data.get('orden', 1)),
                descripcion=data.get('descripcion', ''),
            )
            return Response(LineaPlantillaSerializer(linea).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=True, methods=['delete'], url_path=r'lineas/(?P<linea_id>\d+)')
    def eliminar_linea(self, request, linea_id=None, **kwargs):
        """DELETE /plantillas-contables/{uuid}/lineas/{id}/ — elimina una LineaPlantilla."""
        plantilla = self.get_object()
        try:
            linea = LineaPlantilla.objects.get(id=linea_id, plantilla=plantilla)
            linea.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except LineaPlantilla.DoesNotExist:
            return Response({'detail': 'Linea no encontrada'}, status=404)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer],
            url_path='render-offcanvas/crear')
    def render_offcanvas_crear(self, request):
        """HTMX: Carga offcanvas de creacion de PlantillaContable."""
        return Response({}, template_name='tenant/contabilidad/partials/plantilla_offcanvas_form.html')

    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer],
            url_path='render-offcanvas/editar')
    def render_offcanvas_editar(self, request, **kwargs):
        """HTMX: Carga offcanvas de edicion."""
        try:
            plantilla = self.get_object()
            serializer = PlantillaContableDetailSerializer(plantilla)
            return Response(
                {'plantilla': serializer.data},
                template_name='tenant/contabilidad/partials/plantilla_offcanvas_form.html',
            )
        except Exception as e:
            logger.error('PlantillaContableViewSet.render_offcanvas_editar: %s', e)
            return Response({'error': str(e)}, status=500)

    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer],
            url_path='render-offcanvas/detalle')
    def render_offcanvas_detalle(self, request, **kwargs):
        """HTMX: Carga offcanvas de detalle."""
        try:
            plantilla = self.get_object()
            serializer = PlantillaContableDetailSerializer(plantilla)
            return Response(
                {'plantilla': serializer.data},
                template_name='tenant/contabilidad/partials/plantilla_offcanvas_detalle.html',
            )
        except Exception as e:
            logger.error('PlantillaContableViewSet.render_offcanvas_detalle: %s', e)
            return Response({'error': str(e)}, status=500)


# Lista de ViewSets para registro automático en el router
VIEWSETS = [
    (r'cuentas-contables', CuentaContableViewSet, 'cuenta-contable'),
    (r'asientos-contables', AsientoContableViewSet, 'asiento-contable'),
    (r'movimientos-contables', MovimientoContableViewSet, 'movimiento-contable'),
    (r'periodos-contables', PeriodoContableViewSet, 'periodo-contable'),
    (r'catalogo-niif', CatalogoMaestroNIIFViewSet, 'catalogo-niif'),
    (r'tipos-comprobante', TipoComprobanteViewSet, 'tipo-comprobante'),
    (r'pendientes', DocumentosPendientesViewSet, 'pendientes'),
    (r'retenciones', RetencionViewSet, 'retencion'),
    (r'configuraciones-retenciones', ConfiguracionRetencionesViewSet, 'configuracion-retencion'),
    (r'libro-diario', LibroDiarioViewSet, 'libro-diario'),
]
