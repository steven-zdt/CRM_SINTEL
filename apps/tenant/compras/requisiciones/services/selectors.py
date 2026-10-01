from django.db.models import Max, Prefetch, Q

from apps.tenant.compras.requisiciones.models import RequisicionCompra, RequisicionCotizacion
from apps.tenant.core.services.organizational_filters import filter_by_scope

# Cotizacion de origen (OBLIGATORIA desde 2026-09-26) para el listado --
# Prefetch filtrado en vez de acceder a `.cotizaciones_vinculadas.all()` sin
# restriccion (evitaria N+1 en el listado). `to_attr` deja el resultado ya
# filtrado disponible sin otra query por fila.
_COTIZACION_ORIGEN_PREFETCH = Prefetch(
    "cotizaciones_vinculadas",
    queryset=RequisicionCotizacion.objects.filter(tipo_relacion="ORIGEN")
    .select_related("cotizacion")
    .only(
        "id",
        "requisicion_id",
        "cotizacion_id",
        "tipo_relacion",
        "cotizacion__uuid",
        "cotizacion__numero_cotizacion",
    ),
    to_attr="_cotizacion_origen_list",
)

REQUISICION_LIST_FIELDS = (
    "id",
    "uuid",
    "numero_documento",
    "consecutivo",
    "fecha_solicitud",
    "fecha_necesidad",
    "tipo",
    "prioridad",
    "estado",
    "moneda",
    "subtotal_estimado",
    "impuestos_estimados",
    "total_estimado",
    "empresa_id",
    "sede_id",
    "area_id",
    "solicitante_id",
    "responsable_aprobacion_id",
    "proyecto_id",
)

REQUISICION_DETAIL_FIELDS = REQUISICION_LIST_FIELDS + (
    "justificacion",
    "observaciones",
    "created_at",
    "updated_at",
)

# TenantProfile no tiene campos nombres/apellidos propios (__str__ usa
# user.email + cargo, apps/tenant/perfil/models.py:200-203) -- no se listan
# traversals aqui a proposito: con select_related('solicitante') sin ningun
# 'solicitante__x' en .only(), Django carga el objeto relacionado completo
# (sin restriccion) en vez de fallar por buscar columnas inexistentes.
_PROYECTO_TRAVERSALS = ("proyecto__nombre",)
_SEDE_TRAVERSALS = ("sede__nombre",)
_AREA_TRAVERSALS = ("area__nombre",)

# Estados considerados "activos" para efectos de flujo de compra -- una vez
# APROBADA, la requisicion puede generar ordenes hasta quedar ATENDIDA.
ESTADOS_DISPONIBLES_PARA_COMPRA = (
    RequisicionCompra.Estado.APROBADA,
    RequisicionCompra.Estado.EN_PROCESO_COMPRA,
    RequisicionCompra.Estado.PARCIALMENTE_ATENDIDA,
)


class RequisicionCompraSelector:
    """Selectores optimizados de solo lectura para RequisicionCompra."""

    @staticmethod
    def get_list(
        empresa_id: int, search: str = None, estado: str = None, sede_ids=None, area_ids=None
    ):
        qs = (
            filter_by_scope(
                RequisicionCompra.objects.all(),
                empresa_id,
                sede_ids=sede_ids,
                area_ids=area_ids,
            )
            .select_related(
                "solicitante",
                "responsable_aprobacion",
                "proyecto",
                "sede",
                "area",
            )
            .prefetch_related(
                _COTIZACION_ORIGEN_PREFETCH,
            )
            .only(
                *REQUISICION_LIST_FIELDS,
                *_PROYECTO_TRAVERSALS,
                *_SEDE_TRAVERSALS,
                *_AREA_TRAVERSALS,
            )
        )

        if estado:
            qs = qs.filter(estado=estado)

        if search:
            qs = qs.filter(
                Q(numero_documento__icontains=search)
                | Q(justificacion__icontains=search)
                | Q(observaciones__icontains=search)
            )

        return qs.order_by("-fecha_solicitud", "-consecutivo")

    @staticmethod
    def get_detail(empresa_id: int, requisicion_uuid: str):
        return (
            RequisicionCompra.objects.filter(
                empresa_id=empresa_id,
                uuid=requisicion_uuid,
            )
            .select_related(
                "solicitante",
                "responsable_aprobacion",
                "proyecto",
                "sede",
                "area",
            )
            .prefetch_related(
                "items",
                "documentos",
                "cotizaciones_vinculadas__cotizacion",
                "facturas_vinculadas__factura",
                "ordenes_compra_vinculadas__orden_compra",
                "historial_estados",
            )
        )

    @staticmethod
    def get_pending_approval(empresa_id: int, sede_ids=None, area_ids=None):
        return RequisicionCompraSelector.get_list(
            empresa_id,
            estado=RequisicionCompra.Estado.PENDIENTE_APROBACION,
            sede_ids=sede_ids,
            area_ids=area_ids,
        )

    @staticmethod
    def get_available_for_purchase(empresa_id: int, sede_ids=None, area_ids=None):
        """Requisiciones que aun pueden generar (mas) OrdenCompra."""
        qs = (
            filter_by_scope(
                RequisicionCompra.objects.all(),
                empresa_id,
                sede_ids=sede_ids,
                area_ids=area_ids,
            )
            .filter(estado__in=ESTADOS_DISPONIBLES_PARA_COMPRA)
            .select_related(
                "proyecto",
                "sede",
                "area",
            )
            .only(
                *REQUISICION_LIST_FIELDS,
                *_PROYECTO_TRAVERSALS,
                *_SEDE_TRAVERSALS,
                *_AREA_TRAVERSALS,
            )
        )
        return qs.order_by("-fecha_solicitud")

    @staticmethod
    def get_siguiente_consecutivo(empresa_id: int) -> int:
        max_consecutivo = RequisicionCompra.objects.filter(
            empresa_id=empresa_id,
        ).aggregate(max_val=Max("consecutivo"))["max_val"]
        return (max_consecutivo + 1) if max_consecutivo is not None else 1
