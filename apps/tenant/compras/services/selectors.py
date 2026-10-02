from decimal import Decimal

from django.db.models import DecimalField, ExpressionWrapper, F, Max, Q, Sum

from apps.tenant.compras.models import ItemOrdenCompra, OrdenCompra, PlantillaOrdenCompra, RecepcionCompra
from apps.tenant.core.services.organizational_filters import filter_by_scope

PLANTILLA_LIST_FIELDS = (
    "id",
    "uuid",
    "tipo_documento",
    "nombre",
    "prefijo",
    "rango_desde",
    "rango_hasta",
    "consecutivo_actual",
    "vigente",
    "empresa_id",
    "created_at",
    "updated_at",
)

PLANTILLA_DETAIL_FIELDS = PLANTILLA_LIST_FIELDS

ORDEN_COMPRA_LIST_FIELDS = (
    "id",
    "uuid",
    "consecutivo",
    "numero_documento",
    "plantilla_id",
    "fecha",
    "fecha_entrega",
    "estado",
    "subtotal",
    "impuestos",
    "total",
    "empresa_id",
    "sede_id",
    "area_id",
    "proveedor_id",
    "proyecto_id",
    "documento_soporte_id",
)

ORDEN_COMPRA_DETAIL_FIELDS = (
    "id",
    "uuid",
    "consecutivo",
    "numero_documento",
    "plantilla_id",
    "fecha",
    "fecha_entrega",
    "estado",
    "subtotal",
    "impuestos",
    "total",
    "observaciones",
    "empresa_id",
    "sede_id",
    "area_id",
    "proveedor_id",
    "proyecto_id",
    "documento_soporte_id",
    "created_at",
    "updated_at",
)

_PLANTILLA_TRAVERSALS = (
    "plantilla__uuid",
    "plantilla__nombre",
    "plantilla__prefijo",
)

_PROVEEDOR_TRAVERSALS = (
    "proveedor__razon_social",
    "proveedor__numero_documento",
)

_PROYECTO_TRAVERSALS = ("proyecto__nombre",)

_DOCUMENTO_SOPORTE_TRAVERSALS = ("documento_soporte__numero_documento_proveedor",)

# [OSF Fase F5] Hallazgo: ni el selector ni los serializers exponian de
# donde (sede/area) era una Orden de Compra - invisible incluso para un
# ADMIN viendo ordenes de varias sedes mezcladas en el mismo listado.
# Necesario ahora que get_list() puede devolver ordenes de MULTIPLES sedes/
# areas a la vez (F5, ver mas abajo) - antes, con una sola sede activa
# filtrada, era menos critico distinguir visualmente.
_SEDE_TRAVERSALS = ("sede__nombre",)

_AREA_TRAVERSALS = ("area__nombre",)


def _expr_valor_recibido(prefix: str = ""):
    """
    Expresion SQL SSoT (PLAN_INTEGRACION_PROYECTOS_ORDENES_COMPRA_VENTA_
    OPCIONAL.md #16.4: "calcular indicadores con agregaciones SQL, no
    iterando cada Orden en Python") del valor recibido de un item de Orden
    de Compra: cantidad_recibida * valor_unitario, incluyendo IVA
    proporcional -- misma formula que `_calcular_item()` en crud_service.py,
    sin reimplementarla. `prefix` permite reutilizarla tanto agregando
    directo sobre ItemOrdenCompra ("") como vía join reverso desde
    OrdenCompra ("items__").
    """
    return ExpressionWrapper(
        F(f"{prefix}valor_unitario")
        * F(f"{prefix}cantidad_recibida")
        * (Decimal("1.00") + F(f"{prefix}porcentaje_iva") / Decimal("100.00")),
        output_field=DecimalField(max_digits=15, decimal_places=2),
    )


class PlantillaOrdenCompraSelector:
    """
    Selectores optimizados de solo lectura para PlantillaOrdenCompra.
    """

    @staticmethod
    def get_list(empresa_id: int, vigente_only: bool = False, tipo_documento: str = None):
        """
        Retorna el listado de plantillas de numeracion. `tipo_documento`
        (PLAN_NUEVA_REQUISICION_NUMERACION_CLIENTE_COTIZACIONES.md Fase A):
        filtra por ORDEN_COMPRA/REQUISICION -- None (default) devuelve todas,
        mismo comportamiento previo a esta Fase.
        """
        qs = PlantillaOrdenCompra.objects.filter(empresa_id=empresa_id).only(*PLANTILLA_LIST_FIELDS)
        if vigente_only:
            qs = qs.filter(vigente=True)
        if tipo_documento:
            qs = qs.filter(tipo_documento=tipo_documento)
        return qs.order_by("-vigente", "-created_at")

    @staticmethod
    def get_detail(empresa_id: int, plantilla_uuid: str):
        """
        Retorna el QuerySet optimizado para obtener el detalle de una plantilla.
        """
        return PlantillaOrdenCompra.objects.filter(empresa_id=empresa_id, uuid=plantilla_uuid).only(
            *PLANTILLA_DETAIL_FIELDS
        )

    @staticmethod
    def get_vigentes(empresa_id: int):
        """
        Retorna las plantillas vigentes disponibles para asociar a una orden de compra.
        """
        return (
            PlantillaOrdenCompra.objects.filter(empresa_id=empresa_id, vigente=True)
            .only(*PLANTILLA_LIST_FIELDS)
            .order_by("-created_at")
        )


class OrdenCompraSelector:
    """
    Selectores optimizados de solo lectura para OrdenCompra.
    """

    @staticmethod
    def get_list(
        empresa_id: int, search: str = None, estado: str = None, sede_ids=None, area_ids=None
    ):
        """
        Retorna el listado de Ordenes de Compra filtrado y optimizado.

        [OSF Fase F5] `sede_ids`/`area_ids=None` (default) no restringe por
        ese nivel - lo pasa asi un perfil con alcance EMPRESA. El ViewSet/
        mixin/vista decide cuando pasar el conjunto COMPLETO de sedes/areas
        permitidas (OrganizationalScope, no una sola "activa" - ver hallazgo
        de F4/F5: filtrar por una sola sede ocultaba ordenes de las demas
        sedes asignadas a un perfil con alcance SEDE/AREA); este selector
        solo aplica el filtro via el helper reusable filter_by_scope().
        """
        qs = (
            filter_by_scope(
                OrdenCompra.objects.all(), empresa_id, sede_ids=sede_ids, area_ids=area_ids
            )
            .select_related(
                "proveedor", "proyecto", "documento_soporte", "plantilla", "sede", "area"
            )
            .only(
                *ORDEN_COMPRA_LIST_FIELDS,
                *_PLANTILLA_TRAVERSALS,
                *_PROVEEDOR_TRAVERSALS,
                *_PROYECTO_TRAVERSALS,
                *_DOCUMENTO_SOPORTE_TRAVERSALS,
                *_SEDE_TRAVERSALS,
                *_AREA_TRAVERSALS,
            )
        )

        if estado:
            qs = qs.filter(estado=estado)

        if search:
            qs = qs.filter(
                Q(consecutivo__icontains=search)
                | Q(numero_documento__icontains=search)
                | Q(proveedor__razon_social__icontains=search)
                | Q(observaciones__icontains=search)
            )

        return qs.order_by("-fecha", "-consecutivo")

    @staticmethod
    def get_detail(empresa_id: int, orden_uuid: str):
        """
        Retorna el QuerySet optimizado para obtener el detalle de una Orden de Compra.
        """
        return (
            OrdenCompra.objects.filter(empresa_id=empresa_id, uuid=orden_uuid)
            .select_related(
                "proveedor", "proyecto", "documento_soporte", "plantilla", "sede", "area"
            )
            .prefetch_related("items")
        )

    @staticmethod
    def get_siguiente_consecutivo(empresa_id: int) -> int:
        """
        Obtiene de manera preliminar el siguiente consecutivo disponible.
        """
        max_consecutivo = OrdenCompra.objects.filter(empresa_id=empresa_id).aggregate(
            max_val=Max("consecutivo")
        )["max_val"]

        return (max_consecutivo + 1) if max_consecutivo is not None else 1

    @staticmethod
    def get_disponibles_para_proyecto(
        empresa_id: int, search: str = None, sede_ids=None, area_ids=None
    ):
        """
        Ordenes elegibles para el flujo 'Proyecto -> Agregar Orden de Compra'
        (PLAN_INTEGRACION_PROYECTOS_ORDENES_COMPRA_VENTA_OPCIONAL.md Paso
        7.4): empresa + estado APROBADA + sin proyecto asignado + alcance
        organizacional. Nunca descarga todas las Ordenes al navegador.
        """
        qs = (
            filter_by_scope(
                OrdenCompra.objects.filter(estado="APROBADA", proyecto__isnull=True),
                empresa_id,
                sede_ids=sede_ids,
                area_ids=area_ids,
            )
            .select_related("proveedor", "sede")
            .only(*ORDEN_COMPRA_LIST_FIELDS, *_PROVEEDOR_TRAVERSALS, *_SEDE_TRAVERSALS)
        )
        if search:
            qs = qs.filter(
                Q(numero_documento__icontains=search)
                | Q(proveedor__razon_social__icontains=search)
            )
        return qs.order_by("-fecha", "-consecutivo")

    @staticmethod
    def get_by_proyecto(empresa_id: int, proyecto_uuid: str):
        """
        Ordenes de Compra ya asociadas a un Proyecto (Paso 7.5 del plan),
        para el bloque "Ordenes de Compra del Proyecto". Anota
        `valor_recibido` via agregacion SQL -- nunca iterando en Python.
        """
        qs = (
            OrdenCompra.objects.filter(empresa_id=empresa_id, proyecto__uuid=proyecto_uuid)
            .select_related("proveedor")
            .only(*ORDEN_COMPRA_LIST_FIELDS, *_PROVEEDOR_TRAVERSALS)
            .annotate(valor_recibido=Sum(_expr_valor_recibido("items__")))
        )
        return qs.order_by("-fecha", "-consecutivo")

    @staticmethod
    def get_resumen_proyecto(empresa_id: int, proyecto_uuid: str) -> dict:
        """
        Agregacion SQL de los indicadores de compras de un Proyecto (#16.4
        del plan: cantidad, comprometido, recibido, pendiente). Excluye
        ANULADA del compromiso -- unico estado terminal negativo real (ver
        ESTADOS_ORDEN_ACTIVA en budget_control_service.py).
        """
        ordenes_qs = OrdenCompra.objects.filter(
            empresa_id=empresa_id, proyecto__uuid=proyecto_uuid
        ).exclude(estado="ANULADA")

        _CENTS = Decimal("0.01")

        cantidad = ordenes_qs.count()
        comprometido = (
            ordenes_qs.aggregate(total=Sum("total"))["total"] or Decimal("0.00")
        ).quantize(_CENTS)

        # [SHIELD] la expresion de valor recibido involucra division (IVA/100)
        # -- Postgres/Decimal pueden devolver una escala con muchos decimales
        # (ej. Decimal('0E-24')) aun siendo numericamente cero/exacto.
        # quantize() normaliza siempre a 2 decimales antes de salir del
        # selector, nunca se expone la escala interna a la API/UI.
        recibido = (
            ItemOrdenCompra.objects.filter(orden_compra__in=ordenes_qs).aggregate(
                total=Sum(_expr_valor_recibido())
            )["total"]
            or Decimal("0.00")
        ).quantize(_CENTS)

        return {
            "cantidad_ordenes": cantidad,
            "comprometido": comprometido,
            "recibido": recibido,
            "pendiente": comprometido - recibido,
        }


RECEPCION_LIST_FIELDS = (
    "id",
    "uuid",
    "fecha",
    "estado",
    "observaciones",
    "empresa_id",
    "sede_id",
    "area_id",
    "orden_compra_id",
    "usuario_id",
    "created_at",
    "updated_at",
)

RECEPCION_DETAIL_FIELDS = RECEPCION_LIST_FIELDS


class RecepcionCompraSelector:
    """Selectores optimizados de solo lectura para RecepcionCompra (F21)."""

    @staticmethod
    def get_list(
        empresa_id: int,
        orden_compra_uuid: str = None,
        estado: str = None,
        sede_ids=None,
        area_ids=None,
    ):
        qs = (
            filter_by_scope(
                RecepcionCompra.objects.all(),
                empresa_id,
                sede_ids=sede_ids,
                area_ids=area_ids,
            )
            .select_related("orden_compra", "sede", "area", "usuario")
            .only(
                *RECEPCION_LIST_FIELDS,
                "orden_compra__uuid",
                "orden_compra__numero_documento",
                "sede__nombre",
                "area__nombre",
            )
        )
        if orden_compra_uuid:
            qs = qs.filter(orden_compra__uuid=orden_compra_uuid)
        if estado:
            qs = qs.filter(estado=estado)
        return qs.order_by("-fecha", "-id")

    @staticmethod
    def get_detail(empresa_id: int, recepcion_uuid: str):
        return (
            RecepcionCompra.objects.filter(
                empresa_id=empresa_id,
                uuid=recepcion_uuid,
            )
            .select_related("orden_compra", "sede", "area", "usuario")
            .prefetch_related("items")
        )
