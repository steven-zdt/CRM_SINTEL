import datetime
import logging

from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response

from apps.config.api.pagination import StandardResultsSetPagination
from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.api.permissions import IsTenantAdminOrReadOnly, IsTenantMember
from apps.tenant.core.services.organizational_context import OrganizationalContextMixin
from apps.tenant.ventas.api.serializers import (
    ResolucionFacturacionSerializer,
    VentaDetailSerializer,
    VentaListSerializer,
)
from apps.tenant.ventas.models import ResolucionFacturacion, Venta
from apps.tenant.ventas.services.api_mixins import (
    ResolucionFacturacionServiceMixin,
    VentaServiceMixin,
)

logger = logging.getLogger(__name__)


class VentaViewSet(OrganizationalContextMixin, VentaServiceMixin, BaseTenantViewSet):
    """Fase 9 (OCF): OrganizationalContextMixin adoptado de forma aditiva.
    get_queryset()/get_object() no migrados - _get_empresa_id_seguro()
    (BaseServiceMixin) cae al singleton Empresa.objects.only('id').first()
    sin exigir TenantProfile (VentaServiceMixin no hereda SintelDSVMixin),
    mismo patron de riesgo ya documentado en empresa (Fase 9 app 1/14)."""

    queryset = Venta.objects.none()
    serializer_class = VentaDetailSerializer
    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    renderer_classes = [JSONRenderer]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["observaciones", "numero_factura"]
    ordering_fields = ["fecha_emision", "total_neto", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        if not hasattr(self, "action") or self.action is None:
            return Venta.objects.none()
        if self.action == "list":
            return self.get_qs_list()
        return self.get_qs_detail()

    def get_serializer_class(self):
        if self.action == "list":
            return VentaListSerializer
        return VentaDetailSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        try:
            ctx["empresa_id"] = self.get_empresa_id()
        except Exception:
            ctx["empresa_id"] = None
        return ctx

    def get_object(self):
        uuid_val = self.kwargs.get(self.lookup_url_kwarg)
        empresa_id = self._get_empresa_id_seguro()
        obj = Venta.objects.filter(uuid=uuid_val, empresa_id=empresa_id).first()
        if not obj:
            from rest_framework.exceptions import NotFound
            raise NotFound("Venta no encontrada en su organizacion.")
        self.check_object_permissions(self.request, obj)
        return obj

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(self, request, *args, **kwargs):
        empresa = self._get_empresa()
        if not empresa:
            return Response(
                {"detail": "No se pudo determinar la empresa activa."},
                status=status.HTTP_403_FORBIDDEN,
            )
        payload = request.data if isinstance(request.data, dict) else dict(request.data)
        ok, result, status_code = self.service_crear_borrador(empresa, payload)
        if not ok:
            return Response(result, status=status_code)
        out = VentaDetailSerializer(result, context=self.get_serializer_context())
        return Response(out.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        venta = self.get_object()
        empresa_id = self._get_empresa_id_seguro()
        ok, result, status_code = self.service_anular_venta(str(venta.uuid), empresa_id)
        if not ok:
            return Response(result, status=status_code)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ------------------------------------------------------------------
    # Acciones de estado
    # ------------------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="procesar-facturar")
    def procesar_facturar(self, request, uuid=None):
        empresa = self._get_empresa()
        if not empresa:
            return Response(
                {"detail": "No se pudo determinar la empresa activa."},
                status=status.HTTP_403_FORBIDDEN,
            )
        venta = self.get_object()
        payload = request.data if isinstance(request.data, dict) else dict(request.data)
        payload["cliente"] = str(venta.cliente.uuid) if not payload.get("cliente") else payload["cliente"]
        payload["fecha_emision"] = payload.get("fecha_emision") or str(venta.fecha_emision)
        payload.setdefault("fecha_vencimiento", str(venta.fecha_vencimiento) if venta.fecha_vencimiento else None)
        payload.setdefault("observaciones", venta.observaciones or "")

        if not payload.get("items"):
            payload["items"] = [
                {
                    "descripcion": item.descripcion,
                    "cantidad": str(item.cantidad),
                    "precio_unitario": str(item.precio_unitario),
                    "porcentaje_iva": str(item.porcentaje_iva),
                    "producto_id": str(item.producto.uuid) if item.producto_id else None,
                    "servicio_id": str(item.servicio.uuid) if item.servicio_id else None,
                }
                for item in venta.items.select_related("producto", "servicio").all()
            ]

        # [COMERCIAL-04] venta_existente=venta: promueve esta misma fila en
        # vez de crear una hermana nueva; si ya estaba FACTURADA_DIAN, el
        # service devuelve status_code=200 (idempotente, no re-procesa).
        ok, result, status_code = self.service_procesar_y_facturar(
            empresa, payload, venta_existente=venta,
        )
        if not ok:
            return Response(result, status=status_code)
        out = VentaDetailSerializer(result, context=self.get_serializer_context())
        return Response(out.data, status=status_code)

    @action(detail=True, methods=["post"], url_path="anular")
    def anular(self, request, uuid=None):
        venta = self.get_object()
        empresa_id = self._get_empresa_id_seguro()
        ok, result, status_code = self.service_anular_venta(str(venta.uuid), empresa_id)
        if not ok:
            return Response(result, status=status_code)
        out = VentaDetailSerializer(result, context=self.get_serializer_context())
        return Response(out.data, status=status.HTTP_200_OK)

    # ------------------------------------------------------------------
    # HTMX offcanvas renders
    # ------------------------------------------------------------------

    @action(
        detail=False,
        methods=["get"],
        renderer_classes=[TemplateHTMLRenderer],
        url_path="render-offcanvas/crear",
    )
    def render_offcanvas_crear(self, request):
        from apps.tenant.clientes.models import Cliente
        from apps.tenant.ventas.services.selectors import ResolucionFacturacionSelector

        empresa_id = self._get_empresa_id_seguro()
        clientes_qs = (
            Cliente.objects.filter(empresa_id=empresa_id, activo=True)
            .only("id", "uuid", "razon_social", "numero_documento")
            .order_by("razon_social")
        )
        resoluciones_qs = ResolucionFacturacionSelector.get_vigentes(empresa_id)

        return Response(
            {
                "clientes": clientes_qs,
                "resoluciones": resoluciones_qs,
                "fecha_default": datetime.date.today().isoformat(),
            },
            template_name="tenant/ventas/offcanvas_crear_venta.html",
        )

    @action(
        detail=False,
        methods=["get"],
        renderer_classes=[TemplateHTMLRenderer],
        url_path="render-offcanvas/detalle",
    )
    def render_offcanvas_detalle(self, request):
        venta_uuid = request.query_params.get("uuid")
        empresa_id = self._get_empresa_id_seguro()
        venta = (
            Venta.objects.filter(uuid=venta_uuid, empresa_id=empresa_id)
            .select_related("cliente", "proyecto", "factura_asociada", "resolucion")
            .prefetch_related("items", "items__producto", "items__servicio")
            .first()
        )
        return Response(
            {"venta": venta},
            template_name="tenant/ventas/offcanvas_detalle_venta.html",
        )


class ResolucionFacturacionViewSet(OrganizationalContextMixin, ResolucionFacturacionServiceMixin, BaseTenantViewSet):
    queryset = ResolucionFacturacion.objects.none()
    serializer_class = ResolucionFacturacionSerializer
    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    renderer_classes = [JSONRenderer]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["fecha_resolucion", "vigente", "created_at"]
    ordering = ["-vigente", "-fecha_resolucion"]

    def get_queryset(self):
        if not hasattr(self, "action") or self.action is None:
            return ResolucionFacturacion.objects.none()
        if self.action == "list":
            return self.get_qs_list()
        return self.get_qs_detail()

    def get_object(self):
        uuid_val = self.kwargs.get(self.lookup_url_kwarg)
        empresa_id = self._get_empresa_id_seguro()
        obj = ResolucionFacturacion.objects.filter(uuid=uuid_val, empresa_id=empresa_id).first()
        if not obj:
            from rest_framework.exceptions import NotFound
            raise NotFound("ResolucionFacturacion no encontrada en su organizacion.")
        self.check_object_permissions(self.request, obj)
        return obj

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        try:
            ctx["empresa_id"] = self.get_empresa_id()
        except Exception:
            ctx["empresa_id"] = None
        return ctx

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(self, request, *args, **kwargs):
        empresa = self._get_empresa()
        if not empresa:
            return Response(
                {"detail": "No se pudo determinar la empresa activa."},
                status=status.HTTP_403_FORBIDDEN,
            )
        payload = request.data if isinstance(request.data, dict) else dict(request.data)
        ok, result, status_code = self.service_crear_resolucion(empresa, payload)
        if not ok:
            return Response(result, status=status_code)
        out = ResolucionFacturacionSerializer(result, context=self.get_serializer_context())
        return Response(out.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        resolucion = self.get_object()
        empresa_id = self._get_empresa_id_seguro()
        payload = request.data if isinstance(request.data, dict) else dict(request.data)
        ok, result, status_code = self.service_actualizar_resolucion(
            str(resolucion.uuid), empresa_id, payload
        )
        if not ok:
            return Response(result, status=status_code)
        out = ResolucionFacturacionSerializer(result, context=self.get_serializer_context())
        return Response(out.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        resolucion = self.get_object()
        empresa_id = self._get_empresa_id_seguro()
        ok, result, status_code = self.service_eliminar_resolucion(str(resolucion.uuid), empresa_id)
        if not ok:
            return Response(result, status=status_code)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ------------------------------------------------------------------
    # HTMX offcanvas renders
    # ------------------------------------------------------------------

    @action(
        detail=False,
        methods=["get"],
        renderer_classes=[TemplateHTMLRenderer],
        url_path="panel",
    )
    def render_panel(self, request):
        empresa_id = self._get_empresa_id_seguro()
        resoluciones = (
            ResolucionFacturacion.objects.filter(empresa_id=empresa_id)
            .only(
                "id", "uuid", "numero_resolucion", "prefijo", "tipo",
                "fecha_resolucion", "fecha_desde", "fecha_hasta",
                "rango_desde", "rango_hasta", "consecutivo_actual", "vigente",
            )
            .order_by("-vigente", "-fecha_resolucion")
        )
        return Response(
            {"resoluciones": resoluciones},
            template_name="tenant/ventas/panel_resoluciones.html",
        )

    @action(
        detail=False,
        methods=["get"],
        renderer_classes=[TemplateHTMLRenderer],
        url_path="render-offcanvas/crear",
    )
    def render_offcanvas_crear(self, request):
        return Response(
            {},
            template_name="tenant/ventas/offcanvas_crear_resolucion.html",
        )

    @action(
        detail=False,
        methods=["get"],
        renderer_classes=[TemplateHTMLRenderer],
        url_path="render-offcanvas/editar",
    )
    def render_offcanvas_editar(self, request):
        resolucion_uuid = request.query_params.get("uuid")
        empresa_id = self._get_empresa_id_seguro()
        resolucion = ResolucionFacturacion.objects.filter(
            uuid=resolucion_uuid, empresa_id=empresa_id
        ).first()
        return Response(
            {"resolucion": resolucion},
            template_name="tenant/ventas/offcanvas_editar_resolucion.html",
        )
