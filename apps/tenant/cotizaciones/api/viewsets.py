"""
ViewSets para Cotizaciones v2.62.0 - SINTEL FSD
"""
import logging

from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response

from apps.config.api.pagination import StandardResultsSetPagination
from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.api.permissions import IsTenantAdminOrReadOnly, IsTenantMember
from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.api.utils import resolve_tenant_empresa

from ..models import Cotizacion, Producto, Servicio, CotizacionItem
from ..services import (
    CotizacionServiceMixin,
    ProductoServiceMixin,
    ServicioServiceMixin,
    CotizacionItemServiceMixin,
    CotizacionPDFExportService,
)
from ..services.selectors import CotizacionSelector
from .serializers import (
    CotizacionItemSerializer,
    CotizacionListSerializer,
    CotizacionSerializer,
    ProductoSerializer,
    ServicioSerializer,
)

logger = logging.getLogger(__name__)


class ProductoViewSet(SintelDSVMixin, ProductoServiceMixin, BaseTenantViewSet):
    serializer_class = ProductoSerializer
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    queryset = Producto.objects.none()

    def get_queryset(self):
        if self.action == 'list':
            return self.get_qs_list()
        return self.get_qs_detail()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = self.service_crear_producto(serializer)
        return Response(self.get_serializer(instance).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        partial = kwargs.get('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated = self.service_actualizar_producto(instance, serializer)
        return Response(self.get_serializer(updated).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ServicioViewSet(SintelDSVMixin, ServicioServiceMixin, BaseTenantViewSet):
    serializer_class = ServicioSerializer
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    queryset = Servicio.objects.none()

    def get_queryset(self):
        if self.action == 'list':
            return self.get_qs_list()
        return self.get_qs_detail()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = self.service_crear_servicio(serializer)
        return Response(self.get_serializer(instance).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        partial = kwargs.get('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated = self.service_actualizar_servicio(instance, serializer)
        return Response(self.get_serializer(updated).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CotizacionViewSet(SintelDSVMixin, CotizacionServiceMixin, BaseTenantViewSet):
    lookup_field = 'uuid'
    queryset = Cotizacion.objects.none()
    serializer_class = CotizacionSerializer
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    renderer_classes = [JSONRenderer]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        if self.action == 'list':
            return self.get_qs_list()
        return self.get_qs_detail()

    def get_serializer_class(self):
        if self.action == 'list':
            return CotizacionListSerializer
        return CotizacionSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = self.service_crear_cotizacion(serializer)
        return Response(self.get_serializer(instance).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        partial = kwargs.get('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated = self.service_actualizar_cotizacion(instance, serializer)
        return Response(self.get_serializer(updated).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='exportar-pdf')
    def exportar_pdf(self, request, **kwargs):
        instance = self.get_object()
        empresa = resolve_tenant_empresa(request, self)
        pdf_content = CotizacionPDFExportService.generar_pdf_publico(instance, empresa, request)
        if not pdf_content:
            return Response({"error": "Error generando PDF"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        filename = f'Cotizacion_{instance.codigo_unico or instance.numero_cotizacion}.pdf'
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer],
            url_path='render-offcanvas/crear')
    def render_offcanvas_crear(self, request):
        empresa = resolve_tenant_empresa(request, self)
        context = {
            'cotizacion': None,
            'clientes': CotizacionSelector.get_clientes_activos(empresa.id) if empresa else [],
            'configuraciones': CotizacionSelector.get_configuraciones_activas(empresa.id) if empresa else [],
        }
        return Response(context, template_name='tenant/cotizaciones/editor_cotizacion.html')

    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer],
            url_path='render-offcanvas/editar')
    def render_offcanvas_editar(self, request, **kwargs):
        empresa = resolve_tenant_empresa(request, self)
        cotizacion = self.get_object()
        context = {
            'cotizacion': cotizacion,
            'clientes': CotizacionSelector.get_clientes_activos(empresa.id) if empresa else [],
            'configuraciones': CotizacionSelector.get_configuraciones_activas(empresa.id) if empresa else [],
        }
        return Response(context, template_name='tenant/cotizaciones/editor_cotizacion.html')

    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer],
            url_path='render-offcanvas/detalle')
    def render_offcanvas_detalle(self, request, **kwargs):
        cotizacion = self.get_object()
        return Response({'cotizacion': cotizacion}, template_name='tenant/cotizaciones/offcanvas_detalle_cotizacion.html')

    @action(detail=True, methods=['post'], url_path='recalcular')
    def recalcular(self, request, **kwargs):
        from ..services.business_service import CotizacionService
        instance = self.get_object()
        CotizacionService.calcular_totales(instance.id)
        instance.refresh_from_db()
        return Response(self.get_serializer(instance).data)


class CotizacionItemViewSet(SintelDSVMixin, CotizacionItemServiceMixin, BaseTenantViewSet):
    serializer_class = CotizacionItemSerializer
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    queryset = CotizacionItem.objects.none()

    def get_queryset(self):
        if self.action == 'list':
            return self.get_qs_list()
        return self.get_qs_detail()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = self.service_crear_item(serializer)
        return Response(self.get_serializer(instance).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        partial = kwargs.get('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated = self.service_actualizar_item(instance, serializer)
        return Response(self.get_serializer(updated).data, status=status.HTTP_200_OK)

    def destroy(self, _request, *args, **kwargs):
        instance = self.get_object()
        self.business_service_class.eliminar_item(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
