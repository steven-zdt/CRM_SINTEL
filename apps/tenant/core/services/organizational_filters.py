"""
Filtro reusable del Contexto Organizacional (ADR-003): centraliza el patron
`empresa_id AND sede_id (AND area_id)` para que cada app que adopte
SedeAwareModel (apps/tenant/core/models.py) lo reutilice en sus selectors en
vez de reimplementar el mismo `.filter()` encadenado por su cuenta (Fase 7
del pedido original: "la resolucion del contexto debe ser transparente para
las consultas, evitando que cada modulo implemente su propia logica").

Piloto: apps/tenant/compras/services/selectors.py's OrdenCompraSelector.
"""
from django.db.models import Q, QuerySet


def filter_by_context(
    queryset: QuerySet,
    empresa_id: int,
    sede_id: int | None = None,
    area_id: int | None = None,
) -> QuerySet:
    """Aplica el filtro de aislamiento organizacional a `queryset`.

    `sede_id`/`area_id` en None significa "no restringir por ese nivel" (ej.
    un perfil con alcance EMPRESA debe ver todas las sedes) - el llamador
    decide cuando pasar None, este helper nunca lo decide por su cuenta.
    """
    queryset = queryset.filter(empresa_id=empresa_id)
    if sede_id is not None:
        queryset = queryset.filter(sede_id=sede_id)
    if area_id is not None:
        queryset = queryset.filter(area_id=area_id)
    return queryset


def filter_by_scope(
    queryset: QuerySet,
    empresa_id: int,
    sede_ids=None,
    area_ids=None,
) -> QuerySet:
    """[OSF Fase F5] Version basada en OrganizationalScope (apps/tenant/core/
    services/organizational_scope.py) de filter_by_context(): filtra por el
    conjunto COMPLETO de sedes/areas permitidas (`sede_id__in`/`area_id__in`),
    no por una sola sede/area activa.

    `sede_ids`/`area_ids` en None significa "no restringir por ese nivel"
    (alcance EMPRESA) - un `frozenset()`/lista vacia SI restringe (alcance
    SEDE/AREA sin ninguna asignacion todavia, "no puede ver nada"), igual que
    OrganizationalScope.filter(). El llamador decide cuando pasar None, este
    helper nunca lo decide por su cuenta.
    """
    queryset = queryset.filter(empresa_id=empresa_id)
    if sede_ids is not None:
        queryset = queryset.filter(sede_id__in=sede_ids)
    if area_ids is not None:
        queryset = queryset.filter(area_id__in=area_ids)
    return queryset


def filter_by_scope_null_safe(
    queryset: QuerySet,
    empresa_id: int,
    sede_ids=None,
    area_ids=None,
) -> QuerySet:
    """[OSF Fase F7] Variante NULL-safe de filter_by_scope(), para modelos
    donde `sede`/`area` es opcional Y los datos historicos existentes nunca
    lo completaron (verificado empiricamente en Fase F7: 100% de los
    registros reales de Factura/Cotizacion/DocumentoSoporte/
    MovimientoInventario/Proyecto/Empleado tienen sede=NULL hoy - el campo
    era puramente informativo para un reporte KPI, nunca se exigio).

    Decision explicita del usuario (F7): un registro con `sede`/`area` en
    NULL queda VISIBLE para todos los alcances (EMPRESA/SEDE/AREA), no solo
    para EMPRESA - preserva el 100% del comportamiento actual (toda la data
    real esta en NULL hoy) mientras la capacidad de filtrado real se activa
    progresivamente a medida que se asignen sedes/areas reales a nuevos
    registros. Sin este NULL-safety, activar el filtrado estricto
    (filter_by_scope(), usado por compras porque su `sede` es NOT NULL)
    habria ocultado el 100% de los datos existentes a cualquier usuario con
    alcance SEDE/AREA.

    `sede_ids`/`area_ids` en None sigue significando "no restringir por ese
    nivel" (alcance EMPRESA) - igual que filter_by_scope().
    """
    queryset = queryset.filter(empresa_id=empresa_id)
    if sede_ids is not None:
        queryset = queryset.filter(Q(sede_id__isnull=True) | Q(sede_id__in=sede_ids))
    if area_ids is not None:
        queryset = queryset.filter(Q(area_id__isnull=True) | Q(area_id__in=area_ids))
    return queryset
