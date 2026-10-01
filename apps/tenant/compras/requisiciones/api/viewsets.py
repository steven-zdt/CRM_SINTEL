import logging

from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response

from apps.config.api.pagination import StandardResultsSetPagination
from apps.shared.datatable import ColumnFilter, ColumnFilterType, DataTableServer, DataTableSpec
from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.api.permissions import (
    HasOrganizationalScope,
    IsTenantAdminOrReadOnly,
    IsTenantMember,
)
from apps.tenant.compras.requisiciones.models import RequisicionCompra
from apps.tenant.compras.requisiciones.services import (
    RequisicionCompraBusinessService,
    RequisicionCompraServiceMixin,
)
from apps.tenant.core.services.organizational_context import OrganizationalContextMixin

from .serializers import (
    RequisicionCompraCreateUpdateSerializer,
    RequisicionCompraDetailSerializer,
    RequisicionCompraListSerializer,
)

logger = logging.getLogger(__name__)


class RequisicionCompraViewSet(
    OrganizationalContextMixin, RequisicionCompraServiceMixin, SintelDSVMixin, BaseTenantViewSet
):
    """
    ViewSet para Requisiciones de Compra. Mismo patron que
    OrdenCompraViewSet (apps.tenant.compras.api.viewsets) -- SedeAwareModel,
    alcance organizacional, Service Layer via Tuple[bool, Any, int].
    """

    queryset = RequisicionCompra.objects.none()
    serializer_class = RequisicionCompraDetailSerializer
    service_class = RequisicionCompraBusinessService
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    pagination_class = StandardResultsSetPagination
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    renderer_classes = [JSONRenderer]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["estado", "prioridad", "tipo"]
    search_fields = ["numero_documento", "justificacion", "observaciones"]
    ordering_fields = ["fecha_solicitud", "total_estimado", "created_at"]
    ordering = ["-fecha_solicitud", "-consecutivo"]

    def get_permissions(self):
        return [IsTenantMember(), IsTenantAdminOrReadOnly(), HasOrganizationalScope()]

    def get_queryset(self):
        if not hasattr(self, "action") or self.action is None:
            return RequisicionCompra.objects.none()
        if self.action == "list":
            return self.get_qs_list()
        uuid_val = self.kwargs.get(self.lookup_url_kwarg or self.lookup_field)
        return self.get_qs_detail(uuid_val)

    def get_serializer_class(self):
        if self.action == "list":
            return RequisicionCompraListSerializer
        if self.action in ["create", "update", "partial_update"]:
            return RequisicionCompraCreateUpdateSerializer
        return RequisicionCompraDetailSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        try:
            context["empresa_id"] = self.get_empresa_id()
        except Exception:
            context["empresa_id"] = None
        return context

    def create(self, request, *args, **kwargs):
        try:
            empresa = self._get_empresa()
            if not empresa:
                return Response(
                    {
                        "error": "empresa_no_configurada",
                        "message": "No se pudo determinar la empresa activa.",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            serializer = RequisicionCompraCreateUpdateSerializer(
                data=request.data,
                context={"empresa_id": empresa.id},
            )
            serializer.is_valid(raise_exception=True)

            validated_data = serializer.validated_data
            items_data = validated_data.pop("items")

            success, result, status_code = self.service_crear_requisicion(
                validated_data, items_data, empresa
            )
            if not success:
                logger.warning(f"[RequisicionCompraViewSet:create] Fallo creacion: {result}")
                return Response(result, status=status_code)

            out_serializer = RequisicionCompraDetailSerializer(result)
            return Response(out_serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error en RequisicionCompraViewSet.create: {e}", exc_info=True)
            return Response(
                {"error": "error_interno", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            empresa_id = self.get_empresa_id()

            serializer = RequisicionCompraCreateUpdateSerializer(
                data=request.data,
                context={"empresa_id": empresa_id},
                partial=True,
            )
            serializer.is_valid(raise_exception=True)

            validated_data = serializer.validated_data
            items_data = validated_data.pop("items", None)

            success, result, status_code = self.service_actualizar_requisicion(
                instance.uuid,
                validated_data,
                items_data,
            )
            if not success:
                return Response(result, status=status_code)

            out_serializer = RequisicionCompraDetailSerializer(result)
            return Response(out_serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            success, result, status_code = self.service_eliminar_requisicion(instance.uuid)
            if not success:
                return Response(result, status=status_code)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=True, methods=["post"], url_path="enviar-aprobacion")
    def enviar_aprobacion(self, request, uuid=None):
        try:
            success, result, status_code = self.service_enviar_a_aprobacion(uuid)
            if not success:
                return Response(result, status=status_code)
            out_serializer = RequisicionCompraDetailSerializer(result)
            return Response(out_serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=True, methods=["post"], url_path="aprobar")
    def aprobar(self, request, uuid=None):
        try:
            comentario = request.data.get("comentario", "")
            success, result, status_code = self.service_aprobar_requisicion(uuid, comentario)
            if not success:
                return Response(result, status=status_code)
            out_serializer = RequisicionCompraDetailSerializer(result)
            return Response(out_serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=True, methods=["post"], url_path="rechazar")
    def rechazar(self, request, uuid=None):
        try:
            motivo = request.data.get("motivo", "")
            if not motivo:
                return Response(
                    {"error": "motivo_requerido", "message": "Debe indicar el motivo de rechazo."},
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )
            success, result, status_code = self.service_rechazar_requisicion(uuid, motivo)
            if not success:
                return Response(result, status=status_code)
            out_serializer = RequisicionCompraDetailSerializer(result)
            return Response(out_serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=True, methods=["post"], url_path="cancelar")
    def cancelar(self, request, uuid=None):
        try:
            motivo = request.data.get("motivo", "")
            success, result, status_code = self.service_cancelar_requisicion(uuid, motivo)
            if not success:
                return Response(result, status=status_code)
            out_serializer = RequisicionCompraDetailSerializer(result)
            return Response(out_serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=True, methods=["post"], url_path="vincular-cotizacion")
    def vincular_cotizacion(self, request, uuid=None):
        try:
            cotizacion_uuid = request.data.get("cotizacion_uuid")
            success, result, status_code = self.service_vincular_cotizacion(
                uuid,
                cotizacion_uuid,
                tipo_relacion=request.data.get("tipo_relacion", "CONTEXTO"),
                es_principal=bool(request.data.get("es_principal", False)),
                observacion=request.data.get("observacion", ""),
            )
            if not success:
                return Response(result, status=status_code)
            return Response({"detail": "Cotizacion vinculada."}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=True, methods=["post"], url_path="vincular-factura")
    def vincular_factura(self, request, uuid=None):
        try:
            factura_uuid = request.data.get("factura_uuid")
            success, result, status_code = self.service_vincular_factura(
                uuid,
                factura_uuid,
                tipo_relacion=request.data.get("tipo_relacion", "EVIDENCIA"),
                es_principal=bool(request.data.get("es_principal", False)),
                observacion=request.data.get("observacion", ""),
            )
            if not success:
                return Response(result, status=status_code)
            return Response({"detail": "Factura vinculada."}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=True, methods=["post"], url_path="sincronizar-trazabilidad")
    def sincronizar_trazabilidad(self, request, uuid=None):
        """Re-resuelve y vincula la Cotizacion/Factura de origen del
        Proyecto de esta requisicion (ver RequisicionCompraBusinessService.
        _sincronizar_trazabilidad_desde_proyecto -- ya se dispara
        automaticamente al crear la requisicion; este endpoint es para
        re-disparlarlo manualmente si el proyecto se asigna/cambia despues,
        o si la Venta/Factura aparece mas tarde)."""
        try:
            success, result, status_code = self.service_sincronizar_trazabilidad_proyecto(uuid)
            if not success:
                return Response(result, status=status_code)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=True, methods=["post"], url_path="crear-orden")
    def crear_orden(self, request, uuid=None):
        """Genera una OrdenCompra a partir de esta requisicion. Delega toda
        la logica DSV de plantilla/proveedor a OrdenCompraBusinessService --
        ver RequisicionCompraBusinessService.crear_orden_desde_requisicion()."""
        try:
            empresa = self._get_empresa()
            if not empresa:
                return Response(
                    {
                        "error": "empresa_no_configurada",
                        "message": "No se pudo determinar la empresa activa.",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
            oc_data = request.data.get("orden", {})
            items_ordenados = request.data.get("items", [])

            success, result, status_code = self.service_crear_orden_desde_requisicion(
                uuid,
                oc_data,
                items_ordenados,
                empresa,
            )
            if not success:
                return Response(result, status=status_code)

            from apps.tenant.compras.api.serializers import OrdenCompraDetailSerializer

            out_serializer = OrdenCompraDetailSerializer(result)
            return Response(out_serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=True, methods=["get"], url_path="historial")
    def historial(self, request, uuid=None):
        try:
            empresa_id = self.get_empresa_id()
            instance = RequisicionCompra.objects.filter(uuid=uuid, empresa_id=empresa_id).first()
            if not instance:
                return Response({"detail": "No encontrada."}, status=status.HTTP_404_NOT_FOUND)
            historial = instance.historial_estados.select_related("usuario").all()
            data = [
                {
                    "estado_anterior": h.estado_anterior,
                    "estado_nuevo": h.estado_nuevo,
                    "usuario": str(h.usuario) if h.usuario_id else None,
                    "comentario": h.comentario,
                    "created_at": h.created_at,
                }
                for h in historial
            ]
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=True, methods=["post"], url_path="documentos")
    def documentos(self, request, uuid=None):
        try:
            success, result, status_code = self.service_adjuntar_documento(uuid, request.data)
            if not success:
                return Response(result, status=status_code)
            from .serializers import RequisicionDocumentoSerializer

            out_serializer = RequisicionDocumentoSerializer(result)
            return Response(out_serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=False, methods=["get"], url_path="siguiente-consecutivo")
    def siguiente_consecutivo(self, request):
        try:
            consecutivo = self.service_get_siguiente_consecutivo()
            return Response({"siguiente_consecutivo": consecutivo}, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=False, methods=["get"], url_path="disponibles-para-orden")
    def disponibles_para_orden(self, request):
        """Fase 7 del plan (#32): listado minimo para el selector de
        Requisiciones al crear una Orden de Compra. El saldo se calcula
        via ProcurementBudgetControlService (#20 del plan: "una regla, una
        implementacion") -- nunca recalculado aqui."""
        try:
            from apps.tenant.compras.requisiciones.services.selectors import (
                _COTIZACION_ORIGEN_PREFETCH,
            )
            from apps.tenant.compras.services.budget_control_service import (
                ProcurementBudgetControlService,
            )

            qs = self.service_get_disponibles_para_orden().prefetch_related(
                _COTIZACION_ORIGEN_PREFETCH
            )
            data = []
            for req in qs:
                origen_list = getattr(req, "_cotizacion_origen_list", [])
                origen = origen_list[0] if origen_list else None
                saldo = ProcurementBudgetControlService.obtener_saldo_requisicion(req)
                data.append(
                    {
                        "uuid": str(req.uuid),
                        "numero_documento": req.numero_documento,
                        "cotizacion": {
                            "uuid": str(origen.cotizacion.uuid),
                            "numero_cotizacion": origen.cotizacion.numero_cotizacion,
                        }
                        if origen
                        else None,
                        "proyecto": {
                            "id": req.proyecto_id,
                            "nombre": req.proyecto.nombre,
                        }
                        if req.proyecto_id
                        else None,
                        "valor_total": str(req.total_estimado),
                        "valor_comprometido": str(req.total_estimado - saldo),
                        "saldo": str(saldo),
                        "estado": req.estado,
                    }
                )
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=False, methods=["get"], url_path="cotizaciones-disponibles")
    def cotizaciones_disponibles(self, request):
        """PLAN_NUEVA_REQUISICION_FORMULARIO.md #4/#12: cotizaciones que
        pueden vincularse a una Requisicion NUEVA o EXISTENTE. Dos filtros:

        1. Estado = APROBADA (pedido explicito del usuario, 2026-09-28):
           una Cotizacion sin aprobar no es una base de compra valida
           todavia -- BORRADOR/ENVIADA/RECHAZADA/ARCHIVADA quedan fuera.
        2. Excluye las que ya tengan CUALQUIER Requisicion asociada
           (related_name `requisiciones_vinculadas` del FK
           RequisicionCotizacion.cotizacion, ver models.py).

        Mismo criterio que `excluir_vinculadas` en FacturaViewSet
        (facturas/api/viewsets.py) y que `disponibles_para_orden` arriba: el
        filtro se aplica en backend, la busqueda es solo un GET simple (sin
        DataTables) -- el frontend la cachea client-side (mismo patron que
        `disponiblesParaOrden`) y filtra por numero/cliente sobre esa
        cache, pero la exclusividad REAL se revalida de nuevo al vincular
        (`_validar_y_reservar_cotizacion`, con select_for_update) para
        cerrar la condicion de carrera entre dos usuarios."""
        try:
            from apps.tenant.cotizaciones.models import Cotizacion

            empresa_id = self.get_empresa_id()
            qs = (
                Cotizacion.objects.filter(empresa_id=empresa_id, estado=Cotizacion.Estado.APROBADA)
                .exclude(requisiciones_vinculadas__isnull=False)
                .select_related("cliente")
                .only(
                    "id",
                    "uuid",
                    "numero_cotizacion",
                    "total_con_impuestos",
                    "cliente_id",
                    "cliente__razon_social",
                )
                .order_by("-created_at")
            )
            data = [
                {
                    "uuid": str(c.uuid),
                    "numero_cotizacion": c.numero_cotizacion,
                    "cliente_id": c.cliente_id,
                    "cliente_nombre": c.cliente.razon_social if c.cliente_id else "",
                    "total_con_impuestos": str(c.total_con_impuestos),
                }
                for c in qs
            ]
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=False, methods=["post"], url_path="dt")
    def dt(self, request):
        """DataTables 3.x server-side (mismo patron que OrdenCompraViewSet.dt())."""
        base_qs = self.get_qs_list()
        spec = DataTableSpec(
            fields_map={
                0: "numero_documento",
                1: "fecha_solicitud",
                2: "fecha_necesidad",
                6: "total_estimado",
                7: "estado",
            },
            search_fields=["numero_documento", "justificacion", "observaciones"],
            base_qs=base_qs,
            serializer=RequisicionCompraListSerializer,
            column_filters={
                0: ColumnFilter("numero_documento", ColumnFilterType.ICONTAINS),
                1: ColumnFilter("fecha_solicitud", ColumnFilterType.DATE_RANGE),
                6: ColumnFilter("total_estimado", ColumnFilterType.NUMBER_RANGE),
                7: ColumnFilter("estado", ColumnFilterType.EXACT),
            },
        )
        return DataTableServer(spec).handle(request)

    # --- Acciones de Renderizado (UI/HTMX) ---

    @action(
        detail=False,
        methods=["get"],
        renderer_classes=[TemplateHTMLRenderer],
        url_path="render-offcanvas/crear",
    )
    def render_offcanvas_crear(self, request):
        """`proyecto` se carga client-side via AJAX contra /api/v1/proyectos/
        (mismo patron que compras.utils.js::loadProyectosSelect para
        OrdenCompra) -- no se resuelve server-side aqui. `plantillas` y
        `clientes` SI se resuelven server-side (PLAN_NUEVA_REQUISICION_
        NUMERACION_CLIENTE_COTIZACIONES.md Fases B/C): Plantilla replica el
        mismo patron ya usado por OrdenCompraViewSet.render_offcanvas_crear
        (select server-side + preview readonly); Cliente replica el patron
        `{% for c in clientes %}` ya usado en Ventas/Cotizaciones (nunca un
        buscador AJAX nuevo)."""
        import datetime

        from apps.tenant.clientes.services.selectors import ClienteSelector
        from apps.tenant.compras.models import PlantillaOrdenCompra
        from apps.tenant.compras.services.selectors import PlantillaOrdenCompraSelector

        empresa_id = self.get_empresa_id()
        fecha_default = datetime.date.today().isoformat()
        plantillas = PlantillaOrdenCompraSelector.get_list(
            empresa_id=empresa_id,
            vigente_only=True,
            tipo_documento=PlantillaOrdenCompra.TipoDocumento.REQUISICION,
        )
        clientes = ClienteSelector.get_cliente_list(empresa_id=empresa_id, filters={"activo": True})
        context = {
            "offcanvas_id": "offcanvas-requisicion-crear",
            "mode": "create",
            "fecha_default": fecha_default,
            "plantillas": plantillas,
            "clientes": clientes,
        }
        return Response(
            context, template_name="tenant/compras/requisiciones/offcanvas_crear_requisicion.html"
        )

    @action(
        detail=False,
        methods=["get"],
        renderer_classes=[TemplateHTMLRenderer],
        url_path="render-offcanvas/editar",
    )
    def render_offcanvas_editar(self, request):
        uuid_val = request.query_params.get("uuid") or request.query_params.get("id")
        empresa_id = self.get_empresa_id()
        if not uuid_val:
            return Response({"error": "ID requerido"}, status=status.HTTP_400_BAD_REQUEST)

        instance = get_object_or_404(
            RequisicionCompra.objects.select_related(
                "plantilla", "cliente", "proyecto"
            ).prefetch_related("items"),
            uuid=uuid_val,
            empresa_id=empresa_id,
        )
        self.check_object_permissions(request, instance)

        # Cliente SI es editable en BORRADOR (documento original #13) --
        # Plantilla/numero_documento nunca (#22, se muestran solo-lectura
        # via `instance.plantilla`/`instance.numero_documento` en el
        # template).
        from apps.tenant.clientes.services.selectors import ClienteSelector

        clientes = ClienteSelector.get_cliente_list(empresa_id=empresa_id, filters={"activo": True})

        context = {
            "instance": instance,
            "offcanvas_id": "offcanvas-requisicion-crear",
            "mode": "edit",
            "clientes": clientes,
        }
        return Response(
            context, template_name="tenant/compras/requisiciones/offcanvas_crear_requisicion.html"
        )

    @action(
        detail=False,
        methods=["get"],
        renderer_classes=[TemplateHTMLRenderer],
        url_path="render-offcanvas/detalle",
    )
    def render_offcanvas_detalle(self, request):
        uuid_val = request.query_params.get("uuid") or request.query_params.get("id")
        empresa_id = self.get_empresa_id()
        if not uuid_val:
            return Response({"error": "ID requerido"}, status=status.HTTP_400_BAD_REQUEST)

        instance = get_object_or_404(
            RequisicionCompra.objects.select_related(
                "proyecto", "sede", "area", "solicitante"
            ).prefetch_related(
                "items",
                "documentos",
                "ordenes_compra_vinculadas__orden_compra",
                "historial_estados",
                "cotizaciones_vinculadas__cotizacion",
                "facturas_vinculadas__factura",
            ),
            uuid=uuid_val,
            empresa_id=empresa_id,
        )
        self.check_object_permissions(request, instance)
        return Response(
            {"instance": instance, "offcanvas_id": "offcanvas-requisicion-detalle"},
            template_name="tenant/compras/requisiciones/offcanvas_detalle_requisicion.html",
        )
