"""
ViewSets DRF para gastos (JSON-only).

v2.62.0: ARQUITECTURA ESTABILIZADA.
- Documento Soporte y Resolucion DIAN con flexibilidad operativa.
- Deprecacion formal de endpoints legacy (410 Gone).
- Integracion con TabulatorFactory y UIManager.
"""
import logging
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, render
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response

from apps.config.api.pagination import StandardResultsSetPagination
from apps.tenant.api.permissions import IsTenantAdminOrReadOnly, IsTenantMember
from apps.tenant.gastos.models import DocumentoSoporte, ResolucionDIAN
from apps.tenant.gastos.services import (
    GastoServiceMixin,
    ResolucionServiceMixin,
    GastoBusinessService,
    ResolucionBusinessService,
)
from apps.tenant.gastos.services.selectors import DocumentoSelector

from .serializers import (
    GastoSerializer,
    GastoDetailSerializer,
    ResolucionDIANCreateSerializer,
    ResolucionDIANDetailSerializer,
    ResolucionDIANListSerializer,
    ResolucionDIANNestedSerializer,
)

from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.core.services.organizational_context import OrganizationalContextMixin

logger = logging.getLogger(__name__)

class GastoViewSet(OrganizationalContextMixin, GastoServiceMixin, SintelDSVMixin, BaseTenantViewSet):
    """
    ViewSet para gastos (v2.62.0).

    Fase 9 (OCF): OrganizationalContextMixin adoptado de forma aditiva.
    Caso de PARIDAD (no divergencia), igual que compras/bancos/contabilidad:
    esta app ya hereda SintelDSVMixin y usa get_empresa_id() directamente -
    la misma SSoT que OrganizationalContext.resolve() duplica (Fase 2).
    get_queryset() no se migra: get_qs_list()/get_qs_detail() usan el
    selector con sus propios .only() que context.filter() generico no
    replica.
    """
    queryset = DocumentoSoporte.objects.none()
    serializer_class = GastoDetailSerializer
    service_class = GastoBusinessService
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']
    
    pagination_class = StandardResultsSetPagination
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    renderer_classes = [JSONRenderer]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["categoria_contable", "proveedor__numero_documento"]
    search_fields = ["descripcion", "proveedor__razon_social", "consecutivo"]
    ordering_fields = ["fecha", "total", "created_at"]
    ordering = ["-fecha", "-created_at"]

    def get_queryset(self):
        """SSoT: Delegar al mixin que usa get_empresa_id() validado."""
        if not hasattr(self, 'action') or self.action is None:
            return DocumentoSoporte.objects.none()

        if self.action == "list":
            return self.get_qs_list()

        return self.get_qs_detail()

    def get_serializer_class(self):
        if self.action == "list":
            return GastoSerializer
        return GastoDetailSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        try:
            context['empresa_id'] = self.get_empresa_id()
        except Exception:
            context['empresa_id'] = None
        return context
    
    def create(self, request, *args, **kwargs):
        """Crea un nuevo Gasto via Service Layer."""
        try:
            empresa = self._get_empresa()
            if not empresa:
                return Response(
                    {"error": "empresa_no_configurada", "message": "No se pudo determinar la empresa activa."},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # WARNING: [SEC-M6] Solo nombres de campo, no valores (datos de proveedor/monto).
            _campos = list(request.data.keys()) if hasattr(request.data, 'keys') else type(request.data).__name__
            logger.info(f"[GastoViewSet:create] Campos recibidos: {_campos}")
            
            success, result, status_code = self.service_crear_gasto(request.data.copy(), empresa)
            if not success:
                logger.warning(f"[GastoViewSet:create] Fallo creacion: {result}")
                return Response(result, status=status_code)
                
            serializer = self.get_serializer(result)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error en GastoViewSet.create: {e}", exc_info=True)
            return Response({"error": "error_interno", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, *args, **kwargs):
        """Elimina un gasto fisicamente."""
        try:
            if not settings.DEBUG:
                # En produccion, el gasto debe estar anulado primero
                instance = self.get_object()
                if not instance.anulado:
                    return Response(
                        {"detail": "El gasto debe estar anulado antes de eliminar."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            instance = self.get_object()
            success, result, status_code = self.service_class.eliminar_gasto(
                instance.id,
                empresa_id=self.get_empresa_id()
            )
            return Response(result, status=status_code)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=True, methods=["post"], url_path="anular")
    def anular(self, request, uuid=None):
        """Anula un gasto (DocumentoSoporte) v2.62.0."""
        try:
            gasto = self.get_object()
            motivo = request.data.get('motivo')
            if not motivo:
                return Response({"detail": "Debe especificar un motivo de anulacion."}, status=status.HTTP_400_BAD_REQUEST)
            
            usuario_perfil = getattr(request.user, 'tenant_profile', None)
            if not usuario_perfil:
                return Response({"detail": "Perfil operativo no encontrado."}, status=status.HTTP_403_FORBIDDEN)
            
            success, result, status_code = self.service_anular_gasto(gasto, motivo, usuario_perfil)
            return Response(result, status=status_code)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """Obtiene resumen financiero neto."""
        try:
            summary_data = self.service_get_summary()
            return Response(summary_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # --- Acciones de Renderizado (UI/HTMX) ---

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/crear')
    def render_offcanvas_crear(self, request):
        """Renderiza offcanvas para crear."""
        import datetime
        empresa_id = self.get_empresa_id()

        resolucion_activa = ResolucionDIAN.objects.filter(empresa_id=empresa_id, vigente=True).first()

        doc_soporte_siguiente = ''
        fecha_default = datetime.date.today().isoformat()
        if resolucion_activa:
            preview = DocumentoSelector.get_siguiente_numero_preview(resolucion_activa)
            doc_soporte_siguiente = preview['formateado']
            if resolucion_activa.fecha_inicio and resolucion_activa.fecha_inicio > datetime.date.today():
                fecha_default = resolucion_activa.fecha_inicio.isoformat()

        context = {
            'offcanvas_id': 'offcanvas-gasto-crear',
            'mode': 'create',
            'resolucion_activa': resolucion_activa,
            'doc_soporte_siguiente': doc_soporte_siguiente,
            'fecha_default': fecha_default,
        }
        return Response(context, template_name='tenant/gastos/offcanvas_crear_gasto.html')

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/editar')
    def render_offcanvas_editar(self, request):
        """Renderiza offcanvas para editar."""
        uuid_val = request.query_params.get('uuid') or request.query_params.get('id')
        empresa_id = self.get_empresa_id()
        if not uuid_val:
            return Response({"error": "ID requerido"}, status=status.HTTP_400_BAD_REQUEST)

        # [OSF Fase F13] Antes solo filtraba por empresa_id (bypaseaba
        # get_queryset()/get_qs_detail()) - mismo gap que F11 encontro y
        # corrigio en Facturas: un perfil alcance=SEDE podia editar por UUID
        # directo un DocumentoSoporte de otra sede.
        instance = get_object_or_404(self._get_documento_scope_qs(empresa_id), uuid=uuid_val)

        # Pull Model (ADR-001 / §28): retenciones viven en tabla Retencion, no en campos deprecated
        retenciones_fracciones = {}
        try:
            from apps.tenant.contabilidad.services.retenciones_service import RetencionesService
            _zero_keys = {'0.00', '0', '0.0'}
            _choices_map = {}
            for fraction_str, _ in (DocumentoSoporte.RETEFUENTE_CHOICES + DocumentoSoporte.RETEICA_CHOICES):
                if fraction_str not in _zero_keys:
                    pct_norm = (Decimal(fraction_str) * Decimal('100')).normalize()
                    _choices_map[pct_norm] = fraction_str
            for r in RetencionesService.listar_retenciones_por_documento(
                documento_origen_app='gastos',
                documento_origen_modelo='DocumentoSoporte',
                documento_origen_id=instance.id,
                empresa_id=empresa_id,
            ):
                if r.tipo in ('RETEFUENTE', 'RETEICA', 'RETEIVA'):
                    pct_norm = Decimal(str(r.porcentaje)).normalize()
                    retenciones_fracciones[r.tipo] = _choices_map.get(pct_norm, '0.00')
        except Exception as e:
            logger.warning(
                "[GastoViewSet:render_offcanvas_editar] No se pudieron cargar retenciones "
                "para documento id=%s: %s", instance.id, e,
            )

        context = {
            'instance': instance,
            'offcanvas_id': 'offcanvas-gasto-editar',
            'mode': 'edit',
            'retenciones_fracciones': retenciones_fracciones,
        }
        return Response(context, template_name='tenant/gastos/offcanvas_editar_gasto.html')

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/detalle')
    def render_offcanvas_detalle(self, request):
        """Renderiza offcanvas de detalle."""
        uuid_val = request.query_params.get('uuid') or request.query_params.get('id')
        empresa_id = self.get_empresa_id()
        if not uuid_val:
            return Response({"error": "ID requerido"}, status=status.HTTP_400_BAD_REQUEST)

        # [OSF Fase F13] ver nota de render_offcanvas_editar - mismo gap.
        instance = get_object_or_404(self._get_documento_scope_qs(empresa_id), uuid=uuid_val)
        return Response({'instance': instance, 'offcanvas_id': 'offcanvas-gasto-detalle'}, template_name='tenant/gastos/offcanvas_detalle_gasto.html')

    def _get_documento_scope_qs(self, empresa_id):
        """[OSF Fase F13] QuerySet de DocumentoSoporte con OrganizationalScope
        aplicado (NULL-safe, mismo criterio que get_qs_detail()) - reusado por
        las acciones render-offcanvas que resuelven su propio objeto sin pasar
        por get_queryset()/get_object()."""
        from apps.tenant.core.services.organizational_scope import (
            OrganizationalScope,
            OrganizationalScopeError,
        )
        try:
            sede_ids = OrganizationalScope.resolve(self.request).sede_ids
        except OrganizationalScopeError:
            sede_ids = None
        return DocumentoSelector.get_detail(empresa_id, sede_ids=sede_ids)

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/resolucion')
    def render_offcanvas_resolucion(self, request):
        """Renderiza offcanvas de resolucion DIAN."""
        uuid_val = request.query_params.get('uuid') or request.query_params.get('id')
        empresa_id = self.get_empresa_id()
        context = {'offcanvas_id': 'offcanvas-resolucion-editor'}

        if uuid_val:
            instance = get_object_or_404(ResolucionDIAN, uuid=uuid_val, empresa_id=empresa_id)
            context['instance'] = instance
            context['mode'] = 'edit'
        else:
            context['mode'] = 'create'

        return Response(context, template_name='tenant/gastos/offcanvas_resolucion.html')



class ResolucionDIANViewSet(OrganizationalContextMixin, ResolucionServiceMixin, SintelDSVMixin, BaseTenantViewSet):
    """
    ViewSet para Resoluciones DIAN (v2.62.0).
    """
    queryset = ResolucionDIAN.objects.none()
    serializer_class = ResolucionDIANDetailSerializer
    service_class = ResolucionBusinessService
    pagination_class = StandardResultsSetPagination
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']
    
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    renderer_classes = [JSONRenderer]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['numero_resolucion', 'prefijo']
    ordering_fields = ['fecha_resolucion', 'vigente', 'created_at']
    ordering = ['-vigente', '-fecha_resolucion']

    def get_queryset(self):
        if not hasattr(self, 'action') or self.action is None:
            return ResolucionDIAN.objects.none()
        if self.action == "list":
            return self.get_qs_list()
        return self.get_qs_detail()

    def get_serializer_class(self):
        if self.action == "list":
            return ResolucionDIANListSerializer
        if self.action == "create":
            return ResolucionDIANCreateSerializer
        return ResolucionDIANDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            resultado = self.service_crear_resolucion(serializer)
            return Response(ResolucionDIANDetailSerializer(resultado).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=True, methods=["post"], url_path="desactivar")
    def desactivar(self, request, uuid=None):
        try:
            resolucion = self.get_object()
            resultado = self.service_desactivar_resolucion(resolucion)
            return Response(self.get_serializer(resultado).data, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=False, methods=["get"], url_path="activa")
    def activa(self, request):
        try:
            resolucion = self.service_obtener_vigente()
            if not resolucion:
                return Response({"error": "No hay resolucion vigente."}, status=status.HTTP_404_NOT_FOUND)
            return Response(ResolucionDIANNestedSerializer(resolucion).data, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)
