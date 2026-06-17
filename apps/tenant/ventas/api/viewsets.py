"""
ViewSet para Ventas — OrdenVenta.

Endpoints REST + acciones HTMX:
- GET  /api/v1/ventas/                        Lista paginada (Tabulator)
- GET  /api/v1/ventas/{uuid}/                  Detalle
- POST /api/v1/ventas/                         Crear orden
- PATCH/PUT /api/v1/ventas/{uuid}/             Actualizar (solo BORRADOR/CONFIRMADA)
- DELETE /api/v1/ventas/{uuid}/                Anular (logico)
- POST /api/v1/ventas/{uuid}/confirmar/        BORRADOR -> CONFIRMADA
- POST /api/v1/ventas/{uuid}/facturar/         CONFIRMADA -> FACTURADA (genera Factura)
- POST /api/v1/ventas/{uuid}/anular/           -> ANULADA
- GET  /api/v1/ventas/render-offcanvas/crear/  HTML offcanvas crear (HTMX)
- GET  /api/v1/ventas/render-offcanvas/detalle/ HTML offcanvas detalle (HTMX)
"""
import datetime
import logging

from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response

from apps.config.api.pagination import StandardResultsSetPagination
from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.api.permissions import IsTenantAdminOrReadOnly, IsTenantMember
from apps.tenant.ventas.api.serializers import (
    OrdenVentaCreateUpdateSerializer,
    OrdenVentaDetailSerializer,
    OrdenVentaListSerializer,
)
from apps.tenant.ventas.models import OrdenVenta
from apps.tenant.ventas.services import OrdenVentaBusinessService
from apps.tenant.ventas.services.api_mixins import OrdenVentaServiceMixin

logger = logging.getLogger(__name__)


class OrdenVentaViewSet(OrdenVentaServiceMixin, SintelDSVMixin, BaseTenantViewSet):
    """
    ViewSet para gestion de Ordenes de Venta.
    Dual-Auth: JWT (API) + Session (HTMX/browser).
    """

    queryset = OrdenVenta.objects.none()
    serializer_class = OrdenVentaDetailSerializer
    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    renderer_classes = [JSONRenderer]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["observaciones"]
    ordering_fields = ["fecha_emision", "total", "created_at"]
    ordering = ["-created_at"]

    # ------------------------------------------------------------------
    # QuerySet y Serializador
    # ------------------------------------------------------------------

    def get_queryset(self):
        if not hasattr(self, "action") or self.action is None:
            return OrdenVenta.objects.none()
        if self.action == "list":
            return self.get_qs_list()
        return self.get_qs_detail()

    def get_serializer_class(self):
        if self.action == "list":
            return OrdenVentaListSerializer
        if self.action in ("create", "update", "partial_update"):
            return OrdenVentaCreateUpdateSerializer
        return OrdenVentaDetailSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        try:
            ctx["empresa_id"] = self.get_empresa_id()
        except Exception:
            ctx["empresa_id"] = None
        return ctx

    def get_object(self):
        """DSV: valida que el objeto pertenezca a la empresa del tenant."""
        uuid_val = self.kwargs.get(self.lookup_url_kwarg)
        empresa_id = self._get_empresa_id_seguro()
        obj = OrdenVenta.objects.filter(
            uuid=uuid_val,
            empresa_id=empresa_id,
        ).first()
        if not obj:
            logger.warning(
                "[OrdenVentaViewSet:DSV] UUID %s no encontrado para empresa %s",
                uuid_val,
                empresa_id,
            )
            from rest_framework.exceptions import NotFound
            raise NotFound("Orden de venta no encontrada en su organizacion.")
        self.check_object_permissions(self.request, obj)
        return obj

    # ------------------------------------------------------------------
    # CRUD estandar
    # ------------------------------------------------------------------

    def create(self, request, *args, **kwargs):
        empresa = self._get_empresa()
        if not empresa:
            return Response(
                {"error": "empresa_no_configurada", "message": "No se pudo determinar la empresa activa."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = OrdenVentaCreateUpdateSerializer(
            data=request.data,
            context={"empresa_id": empresa.id, "request": request},
        )
        serializer.is_valid(raise_exception=True)

        validated = dict(serializer.validated_data)
        items_raw = validated.pop("items", [])
        validated["cliente_id"] = validated.pop("cliente").id if "cliente" in validated else None

        items_data = [
            {
                "descripcion": item.get("descripcion", ""),
                "cantidad": str(item.get("cantidad", "1")),
                "precio_unitario": str(item.get("precio_unitario", "0")),
                "tasa_iva": str(item.get("tasa_iva", "0")),
                "producto_id": item.get("producto_id"),
                "servicio_id": item.get("servicio_id"),
            }
            for item in items_raw
        ]
        validated["items"] = items_data

        try:
            orden = self.service_crear_orden(validated, empresa)
        except Exception as exc:
            return self.handle_service_error(exc)

        out = OrdenVentaDetailSerializer(orden, context=self.get_serializer_context())
        return Response(out.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        orden = self.get_object()
        empresa = self._get_empresa()

        serializer = OrdenVentaCreateUpdateSerializer(
            orden,
            data=request.data,
            partial=partial,
            context={"empresa_id": empresa.id, "request": request},
        )
        serializer.is_valid(raise_exception=True)

        validated = dict(serializer.validated_data)
        items_raw = validated.pop("items", None)
        if "cliente" in validated:
            validated["cliente_id"] = validated.pop("cliente").id

        if items_raw is not None:
            validated["items"] = [
                {
                    "descripcion": item.get("descripcion", ""),
                    "cantidad": str(item.get("cantidad", "1")),
                    "precio_unitario": str(item.get("precio_unitario", "0")),
                    "tasa_iva": str(item.get("tasa_iva", "0")),
                    "producto_id": item.get("producto_id"),
                    "servicio_id": item.get("servicio_id"),
                }
                for item in items_raw
            ]

        try:
            orden = self.service_actualizar_orden(orden, validated, empresa)
        except Exception as exc:
            return self.handle_service_error(exc)

        out = OrdenVentaDetailSerializer(orden, context=self.get_serializer_context())
        return Response(out.data, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        orden = self.get_object()
        try:
            motivo = request.data.get("motivo", "Eliminacion solicitada por usuario.")
            self.service_anular_orden(orden, motivo)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as exc:
            return self.handle_service_error(exc)

    # ------------------------------------------------------------------
    # Acciones de maquina de estados
    # ------------------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="confirmar")
    def confirmar(self, request, uuid=None):
        """Transiciona la orden: BORRADOR -> CONFIRMADA."""
        orden = self.get_object()
        try:
            orden = self.service_confirmar_orden(orden)
            out = OrdenVentaDetailSerializer(orden, context=self.get_serializer_context())
            return Response(out.data, status=status.HTTP_200_OK)
        except Exception as exc:
            return self.handle_service_error(exc)

    @action(detail=True, methods=["post"], url_path="facturar")
    def facturar(self, request, uuid=None):
        """Genera Factura electronica desde la orden CONFIRMADA."""
        orden = self.get_object()
        try:
            success, result, status_code = self.service_generar_factura(orden)
            if not success:
                return Response(result, status=status_code)
            from apps.tenant.facturas.api.serializers import FacturaSerializer
            try:
                out = FacturaSerializer(result).data
            except Exception:
                out = {"factura_id": result.id, "factura_uuid": str(result.uuid)}
            return Response(
                {"message": "Factura generada correctamente.", "factura": out},
                status=status.HTTP_201_CREATED,
            )
        except Exception as exc:
            return self.handle_service_error(exc)

    @action(detail=True, methods=["post"], url_path="anular")
    def anular(self, request, uuid=None):
        """Anula la orden (estado ANULADA, inmutable)."""
        orden = self.get_object()
        motivo = request.data.get("motivo", "")
        try:
            self.service_anular_orden(orden, motivo)
            return Response({"message": "Orden anulada correctamente."}, status=status.HTTP_200_OK)
        except Exception as exc:
            return self.handle_service_error(exc)

    # ------------------------------------------------------------------
    # Acciones de renderizado HTMX
    # ------------------------------------------------------------------

    @action(
        detail=False,
        methods=["get"],
        renderer_classes=[TemplateHTMLRenderer],
        url_path="render-offcanvas/crear",
    )
    def render_offcanvas_crear(self, request):
        """Renderiza el offcanvas de creacion de orden (HTMX)."""
        from apps.tenant.clientes.models import Cliente

        empresa_id = self._get_empresa_id_seguro()
        clientes_qs = Cliente.objects.filter(
            empresa_id=empresa_id,
            activo=True,
        ).only("id", "uuid", "razon_social", "numero_documento").order_by("razon_social")

        return Response(
            {
                "clientes": clientes_qs,
                "fecha_default": datetime.date.today().isoformat(),
            },
            template_name="tenant/ventas/offcanvas_crear_orden.html",
        )

    @action(
        detail=False,
        methods=["get"],
        renderer_classes=[TemplateHTMLRenderer],
        url_path="render-offcanvas/detalle",
    )
    def render_offcanvas_detalle(self, request):
        """Renderiza el offcanvas de detalle de una orden (HTMX)."""
        orden_uuid = request.query_params.get("uuid")
        empresa_id = self._get_empresa_id_seguro()

        orden = (
            OrdenVenta.objects.filter(uuid=orden_uuid, empresa_id=empresa_id)
            .select_related("cliente", "factura")
            .prefetch_related("items", "items__producto", "items__servicio")
            .first()
        )

        if not orden:
            return Response(
                {"error": "Orden no encontrada."},
                template_name="tenant/ventas/offcanvas_detalle_orden.html",
            )

        return Response(
            {"orden": orden},
            template_name="tenant/ventas/offcanvas_detalle_orden.html",
        )
