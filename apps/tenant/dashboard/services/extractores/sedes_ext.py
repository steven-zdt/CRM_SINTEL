"""
Extractor de KPIs por sede para Dashboard.
Pull Model: usa selectors de apps fuente y agrupa por sede_id.
"""
from decimal import Decimal

from django.db.models import Count, Sum

from apps.tenant.dashboard.services.dtos import KpiSedeDTO

_ZERO = Decimal('0.00')


def _money(value):
    """Normaliza valores monetarios a Decimal(0.01)."""
    return Decimal(str(value or 0)).quantize(Decimal('0.01'))


def _date_filter(qs, field_name, fecha_inicio=None, fecha_fin=None, use_date_lookup=False):
    """Aplica filtro de rango opcional sin asumir campo fecha fijo."""
    if fecha_inicio:
        lookup = f"{field_name}__date__gte" if use_date_lookup else f"{field_name}__gte"
        qs = qs.filter(**{lookup: fecha_inicio})
    if fecha_fin:
        lookup = f"{field_name}__date__lte" if use_date_lookup else f"{field_name}__lte"
        qs = qs.filter(**{lookup: fecha_fin})
    return qs


def _sum_by_sede(qs, field_name):
    """Retorna mapa sede_id -> suma."""
    rows = qs.values('sede_id').annotate(total=Sum(field_name))
    return {row['sede_id']: _money(row['total']) for row in rows}


def _count_by_sede(qs):
    """Retorna mapa sede_id -> conteo."""
    rows = qs.values('sede_id').annotate(total=Count('id'))
    return {row['sede_id']: int(row['total'] or 0) for row in rows}


class SedesExtractor:
    """Agrega indicadores operativos y financieros por sede."""

    @staticmethod
    def extraer_kpis(empresa_id: int, fecha_inicio=None, fecha_fin=None) -> list[KpiSedeDTO]:
        from apps.tenant.empresa.services.selectors import SedeSelector
        from apps.tenant.facturas.services.selectors import FacturaSelectors
        from apps.tenant.gastos.services.selectors import DocumentoSelector
        from apps.tenant.inventario.services.selectors import MovimientoInventarioSelector
        from apps.tenant.proyectos.services.selectors import qs_list as proyectos_qs_list

        sedes = list(SedeSelector.get_list(empresa_id).order_by('nombre'))
        sede_ids = {sede.id for sede in sedes}

        gastos_qs = DocumentoSelector.get_list(empresa_id).filter(anulado=False)
        gastos_qs = _date_filter(gastos_qs, 'fecha', fecha_inicio, fecha_fin)
        gastos_map = _sum_by_sede(gastos_qs, 'total')

        facturas_qs = FacturaSelectors.qs_list(empresa_id).filter(
            estado='ACEPTADA',
            naturaleza='VENTA',
        )
        facturas_qs = _date_filter(
            facturas_qs,
            'fecha_emision',
            fecha_inicio,
            fecha_fin,
            use_date_lookup=True,
        )
        ingresos_map = _sum_by_sede(facturas_qs, 'total')

        proyectos_qs = proyectos_qs_list(empresa_id)
        proyectos_activos_qs = proyectos_qs.exclude(fase_actual='CIERRE')
        proyectos_count_map = _count_by_sede(proyectos_activos_qs)
        proyectos_valor_map = _sum_by_sede(proyectos_activos_qs, 'valor_contrato_proyectado')

        movimientos_qs = MovimientoInventarioSelector.get_list(empresa_id)
        movimientos_qs = _date_filter(
            movimientos_qs,
            'created_at',
            fecha_inicio,
            fecha_fin,
            use_date_lookup=True,
        )
        movimientos_map = _count_by_sede(movimientos_qs)

        seen_sede_ids = set(sede_ids)
        for data_map in (
            gastos_map,
            ingresos_map,
            proyectos_count_map,
            proyectos_valor_map,
            movimientos_map,
        ):
            seen_sede_ids.update(key for key in data_map.keys() if key is not None)

        rows = []
        for sede in sedes:
            ingresos = ingresos_map.get(sede.id, _ZERO)
            gastos = gastos_map.get(sede.id, _ZERO)
            rows.append(KpiSedeDTO(
                sede_uuid=str(sede.uuid),
                sede_nombre=sede.nombre,
                gastos_total=gastos,
                ingresos_total=ingresos,
                proyectos_activos=proyectos_count_map.get(sede.id, 0),
                valor_proyectos=proyectos_valor_map.get(sede.id, _ZERO),
                movimientos_inventario=movimientos_map.get(sede.id, 0),
                margen=(ingresos - gastos).quantize(Decimal('0.01')),
            ))

        if None in seen_sede_ids:
            ingresos = ingresos_map.get(None, _ZERO)
            gastos = gastos_map.get(None, _ZERO)
            rows.append(KpiSedeDTO(
                sede_uuid=None,
                sede_nombre='Sin sede asignada',
                gastos_total=gastos,
                ingresos_total=ingresos,
                proyectos_activos=proyectos_count_map.get(None, 0),
                valor_proyectos=proyectos_valor_map.get(None, _ZERO),
                movimientos_inventario=movimientos_map.get(None, 0),
                margen=(ingresos - gastos).quantize(Decimal('0.01')),
            ))

        return rows
