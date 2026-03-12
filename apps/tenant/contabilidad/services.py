"""
Service Layer para la app contabilidad.

⚠️ v2.37: Service Layer Pattern - LIST_FIELDS y DETAIL_FIELDS para alineación.
"""
from typing import Optional, Dict, Any, Tuple
from decimal import Decimal
from django.db.models import Q
from apps.tenant.contabilidad.models import CuentaContable, AsientoContable, PeriodoContable

# ⚠️ v2.37: LIST_FIELDS y DETAIL_FIELDS para alineación Serializers ↔ Services ↔ UI
# ⚠️ v2.37: uuid incluido para lookup público
# CuentaContable
CUENTA_LIST_FIELDS = (
    "id",
    "uuid",
    "codigo",
    "nombre",
    "tipo",
    "activa",
    "created_at",
)

CUENTA_DETAIL_FIELDS = (
    "id",
    "uuid",
    "codigo",
    "nombre",
    "tipo",
    "descripcion",
    "cuenta_padre",
    "activa",
    "nivel",  # ⚠️ NORMATIVA: Campo agregado para validación de nivel 6
    "created_at",
)

# AsientoContable
ASIENTO_LIST_FIELDS = (
    "id",
    "uuid",
    "numero",
    "fecha",
    "descripcion",
    "estado",
    "total_debe",
    "total_haber",
    "created_at",
)

ASIENTO_DETAIL_FIELDS = (
    "id",
    "uuid",
    "numero",
    "fecha",
    "descripcion",
    "estado",
    "total_debe",
    "total_haber",
    "factura",
    "created_at",
    "updated_at",
)

# PeriodoContable ⚠️ v2.61
PERIODO_LIST_FIELDS = (
    "id",
    "uuid",
    "periodo",
    "fecha_inicio",
    "fecha_fin",
    "estado",
    "fecha_cierre",
    "created_at",
)

PERIODO_DETAIL_FIELDS = (
    "id",
    "uuid",
    "periodo",
    "fecha_inicio",
    "fecha_fin",
    "estado",
    "fecha_cierre",
    "cerrado_por",
    "observaciones",
    "created_at",
    "updated_at",
)


def qs_cuenta_list():
    """
    QuerySet optimizado para listado de cuentas (DataTables).
    
    ⚠️ v2.37: Usa CUENTA_LIST_FIELDS con only().
    ✅ Solo carga campos necesarios para la tabla
    """
    return CuentaContable.objects.only(*CUENTA_LIST_FIELDS)


def qs_cuenta_detail():
    """
    QuerySet optimizado para detalle de cuenta (retrieve).
    
    ⚠️ v2.37: Usa CUENTA_DETAIL_FIELDS con only() y select_related.
    ⚠️ v2.61: Incluye select_related para catalogo_referencia (necesario para serializer).
    ✅ Solo carga campos necesarios para el detalle
    """
    # ⚠️ Incluir catalogo_referencia en select_related para evitar N+1 queries
    return CuentaContable.objects.select_related("cuenta_padre", "catalogo_referencia").only(*CUENTA_DETAIL_FIELDS, "catalogo_referencia")


def qs_asiento_list():
    """
    QuerySet optimizado para listado de asientos (Tabulator v2.40).
    
    ⚠️ v2.60: Usa ASIENTO_LIST_FIELDS con only() y prefetch_related para evitar N+1.
    ✅ Solo carga campos necesarios para la tabla
    ✅ Prefetch de movimientos para conteo eficiente
    """
    return AsientoContable.objects.only(*ASIENTO_LIST_FIELDS).prefetch_related('movimientos')


def qs_asiento_detail():
    """
    QuerySet optimizado para detalle de asiento (retrieve).
    
    ⚠️ v2.37: Usa ASIENTO_DETAIL_FIELDS con only() y prefetch_related.
    ✅ Solo carga campos necesarios para el detalle
    """
    return AsientoContable.objects.select_related("factura").prefetch_related("movimientos").only(*ASIENTO_DETAIL_FIELDS)


def get_balance_prueba(empresa_id: Optional[int] = None, fecha_desde: Optional[str] = None, fecha_hasta: Optional[str] = None) -> Dict[str, Any]:
    """
    Genera Balance de Prueba agrupado por CuentaContable.codigo.
    
    ⚠️ v2.60 Fase 3: Estándar SSoT para Reportes
    ⚠️ Zero Waste: QuerySet optimizado con select_related y prefetch_related
    ⚠️ Inmutabilidad: Solo incluye asientos APROBADOS o CERRADOS
    
    Args:
        empresa_id: ID de la empresa (opcional, filtra por empresa si se proporciona)
        fecha_desde: Fecha inicio (YYYY-MM-DD) - Opcional
        fecha_hasta: Fecha fin (YYYY-MM-DD) - Opcional
    
    Returns:
        Dict con balance agrupado por cuenta:
        {
            "cuentas": [
                {
                    "codigo": "1305",
                    "nombre": "Clientes",
                    "tipo": "ACTIVO",
                    "debe_total": Decimal,
                    "haber_total": Decimal,
                    "saldo": Decimal  # debe - haber (positivo = deudor, negativo = acreedor)
                },
                ...
            ],
            "totales": {
                "debe_total": Decimal,
                "haber_total": Decimal,
                "diferencia": Decimal
            }
        }
    """
    from apps.tenant.contabilidad.models import MovimientoContable
    from django.db.models import Sum, Q
    from django.db.models.functions import Coalesce
    from datetime import datetime
    
    # Filtro base: solo asientos aprobados o cerrados
    filtro_asientos = Q(asiento__estado__in=['APROBADO', 'CERRADO'])
    
    # Filtro por empresa si se proporciona
    if empresa_id:
        filtro_asientos &= Q(asiento__empresa_id=empresa_id)
    
    # Filtro por fechas si se proporcionan
    if fecha_desde:
        try:
            fecha_desde_obj = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
            filtro_asientos &= Q(asiento__fecha__gte=fecha_desde_obj)
        except ValueError:
            pass
    
    if fecha_hasta:
        try:
            fecha_hasta_obj = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
            filtro_asientos &= Q(asiento__fecha__lte=fecha_hasta_obj)
        except ValueError:
            pass
    
    # Agrupar movimientos por cuenta contable
    movimientos = MovimientoContable.objects.filter(filtro_asientos).select_related(
        'cuenta', 'asiento'
    ).values('cuenta__codigo', 'cuenta__nombre', 'cuenta__tipo').annotate(
        debe_total=Coalesce(Sum('debe'), Decimal('0.00')),
        haber_total=Coalesce(Sum('haber'), Decimal('0.00'))
    ).order_by('cuenta__codigo')
    
    cuentas = []
    total_debe = Decimal('0.00')
    total_haber = Decimal('0.00')
    
    for mov in movimientos:
        debe = Decimal(str(mov['debe_total']))
        haber = Decimal(str(mov['haber_total']))
        saldo = debe - haber
        
        cuentas.append({
            'codigo': mov['cuenta__codigo'],
            'nombre': mov['cuenta__nombre'],
            'tipo': mov['cuenta__tipo'],
            'debe_total': str(debe),
            'haber_total': str(haber),
            'saldo': str(saldo)
        })
        
        total_debe += debe
        total_haber += haber
    
    diferencia = total_debe - total_haber
    
    return {
        'cuentas': cuentas,
        'totales': {
            'debe_total': str(total_debe),
            'haber_total': str(total_haber),
            'diferencia': str(diferencia)
        }
    }


def qs_periodo_list():
    """
    QuerySet optimizado para listado de periodos contables.
    
    ⚠️ v2.61: Usa PERIODO_LIST_FIELDS con only() y select_related.
    ✅ Solo carga campos necesarios para la tabla
    """
    return PeriodoContable.objects.select_related("empresa", "cerrado_por").only(*PERIODO_LIST_FIELDS, "empresa", "cerrado_por")


def qs_periodo_detail():
    """
    QuerySet optimizado para detalle de periodo contable.
    
    ⚠️ v2.61: Usa PERIODO_DETAIL_FIELDS con only() y select_related.
    ✅ Solo carga campos necesarios para el detalle
    """
    return PeriodoContable.objects.select_related("empresa", "cerrado_por").only(*PERIODO_DETAIL_FIELDS, "empresa", "cerrado_por")


def verificar_periodo_cerrado(fecha, empresa_id: Optional[int] = None) -> Tuple[bool, Optional[str]]:
    """
    Verifica si una fecha está dentro de un periodo contable cerrado.
    
    ⚠️ v2.60 Fase 3: Validación de Inmutabilidad de Periodos Cerrados
    
    Args:
        fecha: datetime.date o datetime.datetime - Fecha a verificar
        empresa_id: ID de la empresa (opcional)
    
    Returns:
        Tuple (esta_cerrado: bool, periodo: str | None)
        - Si está cerrado: (True, "2024-01")
        - Si está abierto: (False, None)
    """
    from apps.tenant.contabilidad.models import PeriodoContable
    
    if hasattr(fecha, 'date'):
        fecha = fecha.date()
    
    # Buscar periodos cerrados que contengan esta fecha
    filtro = Q(estado='CERRADO', fecha_inicio__lte=fecha, fecha_fin__gte=fecha)
    if empresa_id:
        filtro &= Q(empresa_id=empresa_id)
    
    periodo_cerrado = PeriodoContable.objects.filter(filtro).first()
    
    if periodo_cerrado:
        return True, periodo_cerrado.periodo
    
    return False, None
