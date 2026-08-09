from django.db.models import Q, Max, Sum, Count
from apps.tenant.compras.models import OrdenCompra, PlantillaOrdenCompra
from apps.tenant.core.services.organizational_filters import filter_by_scope


PLANTILLA_LIST_FIELDS = (
    'id', 'uuid', 'nombre', 'prefijo', 'rango_desde', 'rango_hasta',
    'consecutivo_actual', 'vigente', 'empresa_id', 'created_at', 'updated_at'
)

PLANTILLA_DETAIL_FIELDS = PLANTILLA_LIST_FIELDS

ORDEN_COMPRA_LIST_FIELDS = (
    'id', 'uuid', 'consecutivo', 'numero_documento', 'plantilla_id', 'fecha', 'fecha_entrega',
    'estado', 'subtotal', 'impuestos', 'total', 'empresa_id', 'sede_id', 'area_id',
    'proveedor_id', 'proyecto_id', 'documento_soporte_id'
)

ORDEN_COMPRA_DETAIL_FIELDS = (
    'id', 'uuid', 'consecutivo', 'numero_documento', 'plantilla_id', 'fecha', 'fecha_entrega',
    'estado', 'subtotal', 'impuestos', 'total', 'observaciones',
    'empresa_id', 'sede_id', 'area_id', 'proveedor_id', 'proyecto_id', 'documento_soporte_id',
    'created_at', 'updated_at'
)

_PLANTILLA_TRAVERSALS = (
    'plantilla__uuid',
    'plantilla__nombre',
    'plantilla__prefijo',
)

_PROVEEDOR_TRAVERSALS = (
    'proveedor__razon_social',
    'proveedor__numero_documento',
)

_PROYECTO_TRAVERSALS = (
    'proyecto__nombre',
)

_DOCUMENTO_SOPORTE_TRAVERSALS = (
    'documento_soporte__numero_documento_proveedor',
)

# [OSF Fase F5] Hallazgo: ni el selector ni los serializers exponian de
# donde (sede/area) era una Orden de Compra - invisible incluso para un
# ADMIN viendo ordenes de varias sedes mezcladas en el mismo listado.
# Necesario ahora que get_list() puede devolver ordenes de MULTIPLES sedes/
# areas a la vez (F5, ver mas abajo) - antes, con una sola sede activa
# filtrada, era menos critico distinguir visualmente.
_SEDE_TRAVERSALS = (
    'sede__nombre',
)

_AREA_TRAVERSALS = (
    'area__nombre',
)


class PlantillaOrdenCompraSelector:
    """
    Selectores optimizados de solo lectura para PlantillaOrdenCompra.
    """

    @staticmethod
    def get_list(empresa_id: int, vigente_only: bool = False):
        """
        Retorna el listado de plantillas de orden de compra.
        """
        qs = PlantillaOrdenCompra.objects.filter(empresa_id=empresa_id).only(*PLANTILLA_LIST_FIELDS)
        if vigente_only:
            qs = qs.filter(vigente=True)
        return qs.order_by('-vigente', '-created_at')

    @staticmethod
    def get_detail(empresa_id: int, plantilla_uuid: str):
        """
        Retorna el QuerySet optimizado para obtener el detalle de una plantilla.
        """
        return PlantillaOrdenCompra.objects.filter(
            empresa_id=empresa_id,
            uuid=plantilla_uuid
        ).only(*PLANTILLA_DETAIL_FIELDS)

    @staticmethod
    def get_vigentes(empresa_id: int):
        """
        Retorna las plantillas vigentes disponibles para asociar a una orden de compra.
        """
        return PlantillaOrdenCompra.objects.filter(
            empresa_id=empresa_id,
            vigente=True
        ).only(*PLANTILLA_LIST_FIELDS).order_by('-created_at')


class OrdenCompraSelector:
    """
    Selectores optimizados de solo lectura para OrdenCompra.
    """

    @staticmethod
    def get_list(empresa_id: int, search: str = None, estado: str = None, sede_ids=None, area_ids=None):
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
        qs = filter_by_scope(OrdenCompra.objects.all(), empresa_id, sede_ids=sede_ids, area_ids=area_ids).select_related(
            'proveedor', 'proyecto', 'documento_soporte', 'plantilla', 'sede', 'area'
        ).only(
            *ORDEN_COMPRA_LIST_FIELDS,
            *_PLANTILLA_TRAVERSALS,
            *_PROVEEDOR_TRAVERSALS,
            *_PROYECTO_TRAVERSALS,
            *_DOCUMENTO_SOPORTE_TRAVERSALS,
            *_SEDE_TRAVERSALS,
            *_AREA_TRAVERSALS,
        )

        if estado:
            qs = qs.filter(estado=estado)

        if search:
            qs = qs.filter(
                Q(consecutivo__icontains=search) |
                Q(numero_documento__icontains=search) |
                Q(proveedor__razon_social__icontains=search) |
                Q(observaciones__icontains=search)
            )

        return qs.order_by('-fecha', '-consecutivo')

    @staticmethod
    def get_detail(empresa_id: int, orden_uuid: str):
        """
        Retorna el QuerySet optimizado para obtener el detalle de una Orden de Compra.
        """
        return OrdenCompra.objects.filter(
            empresa_id=empresa_id,
            uuid=orden_uuid
        ).select_related(
            'proveedor', 'proyecto', 'documento_soporte', 'plantilla', 'sede', 'area'
        ).prefetch_related(
            'items'
        )

    @staticmethod
    def get_siguiente_consecutivo(empresa_id: int) -> int:
        """
        Obtiene de manera preliminar el siguiente consecutivo disponible.
        """
        max_consecutivo = OrdenCompra.objects.filter(
            empresa_id=empresa_id
        ).aggregate(max_val=Max('consecutivo'))['max_val']

        return (max_consecutivo + 1) if max_consecutivo is not None else 1

