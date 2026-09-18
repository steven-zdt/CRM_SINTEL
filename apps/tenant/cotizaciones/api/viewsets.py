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
from apps.tenant.core.services.organizational_context import OrganizationalContextMixin

from ..models import Cotizacion, Producto, Servicio, CotizacionItem
from ..services import (
    CotizacionServiceMixin,
    ProductoServiceMixin,
    ServicioServiceMixin,
    CotizacionItemServiceMixin,
    CotizacionPDFExportService,
)
from ..services.selectors import CotizacionSelector
from ..services.business_service import CotizacionService
from .serializers import (
    CotizacionItemSerializer,
    CotizacionListSerializer,
    CotizacionSerializer,
    ProductoSerializer,
    ServicioSerializer,
)

logger = logging.getLogger(__name__)


class ProductoViewSet(OrganizationalContextMixin, SintelDSVMixin, ProductoServiceMixin, BaseTenantViewSet):
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
        try:
            instance = self.service_crear_producto(serializer)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(instance).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        partial = kwargs.get('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        try:
            updated = self.service_actualizar_producto(instance, serializer)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(updated).data)

    def destroy(self, request, *args, **kwargs):
        """DELETE via Service Layer (antes bypaseaba a business/crud service --
        hallazgo real, auditoria REL Cotizaciones FASE 5, 2026-08-26)."""
        instance = self.get_object()
        self.service_eliminar_producto(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer],
            url_path='render-offcanvas/editar')
    def render_offcanvas_editar(self, request, **kwargs):
        """El backend ya soportaba PATCH; el boton 'Editar' de la grilla era
        un stub (console.log, sin efecto) porque nunca existio esta vista ni
        su template de edicion -- hallazgo real, auditoria de modernizacion
        Cotizaciones, 2026-08-27. Reutiliza el mismo template de creacion
        (Regla Absoluta #1: no crear un segundo formulario)."""
        instance = self.get_object()
        return Response({'instance': instance}, template_name='tenant/cotizaciones/offcanvas_crear_producto.html')


class ServicioViewSet(OrganizationalContextMixin, SintelDSVMixin, ServicioServiceMixin, BaseTenantViewSet):
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
        """DELETE via Service Layer (antes bypaseaba a business/crud service --
        hallazgo real, auditoria REL Cotizaciones FASE 5, 2026-08-26)."""
        instance = self.get_object()
        self.service_eliminar_servicio(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer],
            url_path='render-offcanvas/editar')
    def render_offcanvas_editar(self, request, **kwargs):
        """Ver ProductoViewSet.render_offcanvas_editar -- mismo hallazgo y
        mismo fix (boton 'Editar' era un stub sin vista de edicion)."""
        instance = self.get_object()
        return Response({'instance': instance}, template_name='tenant/cotizaciones/offcanvas_crear_servicio.html')


class CotizacionViewSet(OrganizationalContextMixin, SintelDSVMixin, CotizacionServiceMixin, BaseTenantViewSet):
    """Fase 9 (OCF): OrganizationalContextMixin adoptado de forma aditiva.
    Hallazgo propio de esta app: get_queryset() usa la SSoT (SintelDSVMixin,
    igual que OrganizationalContext.resolve()) pero exportar_pdf()/
    render_offcanvas_crear()/render_offcanvas_editar() usan
    resolve_tenant_empresa() (el mecanismo mas permisivo, sin exigir
    TenantProfile) - una inconsistencia interna real de esta ViewSet, no
    documentada hasta ahora. Ninguna de las dos rutas se migro."""

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

    def destroy(self, request, *args, **kwargs):
        """DELETE via Service Layer -- antes usaba el destroy() por defecto
        de DRF (hard-delete directo, sin ningun chequeo de trazabilidad).
        Bloqueado si la cotizacion ya fue vinculada a una Factura (ver
        CotizacionService.eliminar_cotizacion) -- hallazgo real, auditoria
        REL Cotizaciones FASE 5, 2026-08-26."""
        instance = self.get_object()
        self.service_eliminar_cotizacion(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'], url_path='exportar-pdf')
    def exportar_pdf(self, request, **kwargs):
        """Descarga el PDF sin importar el estado (nunca cambia el estado --
        mismo criterio que siempre tuvo este endpoint). Para la transicion
        BORRADOR->ENVIADA gated por PDF, usar POST .../generar-pdf/."""
        instance = self.get_object()
        empresa = resolve_tenant_empresa(request, self)
        pdf_content = CotizacionPDFExportService.generar_pdf_publico(instance, empresa, request)
        if not pdf_content:
            return Response({"error": "Error generando PDF"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        filename = f'Cotizacion_{instance.codigo_unico or instance.numero_cotizacion}.pdf'
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=['post'], url_path='generar-pdf')
    def generar_pdf(self, request, **kwargs):
        """COTIZACIONES-02 Fase 04: BORRADOR -> genera PDF -> exito: ENVIADA
        / error: permanece BORRADOR. Si la cotizacion ya no esta en
        BORRADOR, genera el PDF igual (compatibilidad con exportar-pdf) pero
        no toca el estado. Devuelve el PDF como adjunto (mismo
        Content-Disposition que exportar-pdf) para no romper consumidores
        que ya esperan descargar el archivo en la misma llamada."""
        instance = self.get_object()
        empresa = resolve_tenant_empresa(request, self)
        usuario = getattr(request.user, "tenant_profile", None)
        cotizacion, pdf_content = CotizacionService.generar_pdf_y_enviar(instance, empresa, usuario=usuario)
        filename = f'Cotizacion_{cotizacion.codigo_unico or cotizacion.numero_cotizacion}.pdf'
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['X-Cotizacion-Estado'] = cotizacion.estado
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
        instance = self.get_object()
        CotizacionService.calcular_totales(instance.id, instance.empresa_id)
        instance.refresh_from_db()
        return Response(self.get_serializer(instance).data)

    # ------------------------------------------------------------------
    # Maquina de estados (COTIZACIONES-01, extendida en COTIZACIONES-02
    # Fase 05) -- accion de dominio explicita, nunca PATCH generico al
    # campo 'estado'. BORRADOR->ENVIADA ya no es una transicion manual --
    # solo ocurre gated por PDF exitoso en generar_pdf() arriba.
    # ------------------------------------------------------------------
    def _cambiar_estado_action(self, nuevo_estado, request):
        # CotizacionService.cambiar_estado() lanza rest_framework.exceptions
        # .ValidationError -- DRF la captura automaticamente y responde 400
        # con el detalle estructurado, igual que create()/update() de esta
        # misma vista (no envuelven sus propias llamadas al service).
        instance = self.get_object()
        usuario = getattr(request.user, "tenant_profile", None)
        motivo = request.data.get("motivo", "") if hasattr(request, "data") else ""
        cotizacion = CotizacionService.cambiar_estado(instance, nuevo_estado, usuario=usuario, motivo=motivo)
        return Response(self.get_serializer(cotizacion).data)

    @action(detail=True, methods=['post'], url_path='volver-a-borrador')
    def volver_a_borrador(self, request, **kwargs):
        return self._cambiar_estado_action(Cotizacion.Estado.BORRADOR, request)

    @action(detail=True, methods=['post'], url_path='aprobar')
    def aprobar(self, request, **kwargs):
        return self._cambiar_estado_action(Cotizacion.Estado.APROBADA, request)

    @action(detail=True, methods=['post'], url_path='rechazar')
    def rechazar(self, request, **kwargs):
        return self._cambiar_estado_action(Cotizacion.Estado.RECHAZADA, request)

    @action(detail=True, methods=['post'], url_path='archivar')
    def archivar(self, request, **kwargs):
        return self._cambiar_estado_action(Cotizacion.Estado.ARCHIVADA, request)

    @action(detail=True, methods=['get'], url_path='historial')
    def historial(self, request, **kwargs):
        """COTIZACIONES-02 Fase 03: lectura del historial append-only."""
        instance = self.get_object()
        filas = instance.historial_estados.select_related("usuario__user").all()
        payload = [
            {
                "estado_anterior": h.estado_anterior,
                "estado_nuevo": h.estado_nuevo,
                "usuario": str(h.usuario.user) if h.usuario_id else None,
                "motivo": h.motivo,
                "created_at": h.created_at.isoformat(),
            }
            for h in filas
        ]
        return Response(payload)

    @action(detail=True, methods=['post'], url_path='convertir-a-venta')
    def convertir_a_venta(self, request, **kwargs):
        """Solo desde APROBADA (mandato §6). Idempotente (§14): un segundo
        POST devuelve la misma Venta ya creada, con 200 (no 201). Import
        diferido de Venta (apps externas siempre dentro del metodo, mismo
        criterio que eliminar_cotizacion() con Factura)."""
        from apps.tenant.ventas.models import Venta

        instance = self.get_object()
        ya_existia = Venta.objects.filter(
            cotizacion_uuid=instance.uuid, empresa_id=instance.empresa_id,
        ).exists()
        venta = CotizacionService.convertir_a_venta(instance)
        payload = {
            "uuid": str(venta.uuid),
            "estado": venta.estado,
            "cliente_id": venta.cliente_id,
            "subtotal": str(venta.subtotal),
            "impuestos": str(venta.impuestos),
            "total_neto": str(venta.total_neto),
            "cotizacion_uuid": str(venta.cotizacion_uuid),
        }
        return Response(payload, status=status.HTTP_200_OK if ya_existia else status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='facturar-venta')
    def facturar_venta(self, request, **kwargs):
        """COTIZACIONES-02 Fase 07: Venta (ya creada via convertir-a-venta)
        -> Factura VENTA, reutilizando VentaBusinessService.
        procesar_y_facturar_venta(). Idempotente por herencia (COMERCIAL-04):
        un segundo POST devuelve la misma Venta/Factura, 200 en vez de 201."""
        instance = self.get_object()
        sede_id = request.data.get("sede_id") if hasattr(request, "data") else None
        venta, status_code = CotizacionService.facturar_venta_de_cotizacion(instance, sede_id=sede_id)
        payload = {
            "uuid": str(venta.uuid),
            "estado": venta.estado,
            "factura_uuid": str(venta.factura_asociada.uuid) if venta.factura_asociada_id else None,
            "cotizacion_uuid": str(venta.cotizacion_uuid),
        }
        return Response(payload, status=status_code)

    @action(detail=True, methods=['post'], url_path='convertir-a-proyecto')
    def convertir_a_proyecto(self, request, **kwargs):
        """COTIZACIONES-02 Fase 11: items SERVICIO de una cotizacion APROBADA
        -> Proyecto (reutiliza orchestrate_create_proyecto ya existente).
        Idempotente por codigo derivado -- ver CotizacionService.
        convertir_a_proyecto()."""
        instance = self.get_object()
        proyecto = CotizacionService.convertir_a_proyecto(instance)
        payload = {
            "uuid": str(proyecto.uuid),
            "codigo": proyecto.codigo,
            "nombre": proyecto.nombre,
            "valor_contrato_proyectado": str(proyecto.valor_contrato_proyectado),
        }
        return Response(payload, status=status.HTTP_200_OK)


class CotizacionItemViewSet(OrganizationalContextMixin, SintelDSVMixin, CotizacionItemServiceMixin, BaseTenantViewSet):
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
