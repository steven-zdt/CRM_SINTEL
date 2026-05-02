"""
Selectors para la app contabilidad (v3.5).

[ARCHITECTURE v3.5]
- Centralización de todas las consultas GET optimizadas.
- Definición de LIST_FIELDS y DETAIL_FIELDS para alineación con Serializers.
- Zero Waste: Uso estricto de only(), select_related() y prefetch_related().
"""
from decimal import Decimal
from typing import Any, List, Optional, Tuple

from django.db.models import Q, Sum, F, DecimalField
from django.db.models.functions import Coalesce
from rest_framework.exceptions import ValidationError

from apps.tenant.contabilidad.models import (
    AsientoContable, 
    CuentaContable, 
    PeriodoContable, 
    CatalogoMaestroNIIF,
    MovimientoContable
)

# ============================================================================
# FIELD SETS (SSoT para Serializers)
# ============================================================================

CUENTA_LIST_FIELDS = (
    "id", "uuid", "codigo", "nombre", "tipo", "activa", "created_at",
)

CUENTA_DETAIL_FIELDS = (
    "id", "uuid", "codigo", "nombre", "tipo", "descripcion", 
    "cuenta_padre", "activa", "nivel", "created_at",
)

ASIENTO_LIST_FIELDS = (
    "id", "uuid", "numero", "fecha", "descripcion", "estado", 
    "total_debe", "total_haber", "created_at",
)

ASIENTO_DETAIL_FIELDS = (
    "id", "uuid", "numero", "fecha", "descripcion", "estado", 
    "total_debe", "total_haber", "factura", "created_at", "updated_at",
)

PERIODO_LIST_FIELDS = (
    "id", "uuid", "periodo", "fecha_inicio", "fecha_fin", "estado", 
    "fecha_cierre", "created_at",
)

PERIODO_DETAIL_FIELDS = (
    "id", "uuid", "periodo", "fecha_inicio", "fecha_fin", "estado", 
    "fecha_cierre", "cerrado_por", "observaciones", "created_at", "updated_at",
)

CATALOGO_LIST_FIELDS = (
    "id", "codigo", "nombre", "nivel", "naturaleza", "activa",
)

MOVIMIENTO_LIST_FIELDS = (
    "id", "cuenta", "debe", "haber", "descripcion", "orden",
)

MOVIMIENTO_DETAIL_FIELDS = (
    "id", "asiento", "cuenta", "tipo_tercero", "tercero_id", "tercero_nit", 
    "tercero_razon_social", "debe", "haber", "descripcion", "base_iva", 
    "iva_generado", "iva_descontable", "retefuente", "reteica", "orden",
)

# ============================================================================
# SELECTORS (QuerySets Optimizados)
# ============================================================================

def qs_cuenta_list(empresa_id: Optional[int] = None):
    qs = CuentaContable.objects.only(*CUENTA_LIST_FIELDS)
    if empresa_id:
        qs = qs.filter(empresa_id=empresa_id)
    return qs

def qs_cuenta_detail(empresa_id: Optional[int] = None):
    qs = CuentaContable.objects.select_related("cuenta_padre", "catalogo_referencia").only(
        *CUENTA_DETAIL_FIELDS, "catalogo_referencia"
    )
    if empresa_id:
        qs = qs.filter(empresa_id=empresa_id)
    return qs

def qs_asiento_list(empresa_id: Optional[int] = None):
    qs = AsientoContable.objects.only(*ASIENTO_LIST_FIELDS).prefetch_related('movimientos')
    if empresa_id:
        qs = qs.filter(empresa_id=empresa_id)
    return qs

def qs_asiento_detail(empresa_id: Optional[int] = None):
    qs = AsientoContable.objects.select_related("factura").prefetch_related(
        "movimientos", "movimientos__cuenta"
    ).only(*ASIENTO_DETAIL_FIELDS)
    if empresa_id:
        qs = qs.filter(empresa_id=empresa_id)
    return qs

def qs_periodo_list(empresa_id: Optional[int] = None):
    qs = PeriodoContable.objects.select_related("cerrado_por").only(*PERIODO_LIST_FIELDS, "cerrado_por")
    if empresa_id:
        qs = qs.filter(empresa_id=empresa_id)
    return qs

def qs_periodo_detail(empresa_id: Optional[int] = None):
    qs = PeriodoContable.objects.select_related("cerrado_por").only(*PERIODO_DETAIL_FIELDS, "cerrado_por")
    if empresa_id:
        qs = qs.filter(empresa_id=empresa_id)
    return qs

def qs_catalogo_list(empresa_id: Optional[int] = None):
    qs = CatalogoMaestroNIIF.objects.only(*CATALOGO_LIST_FIELDS)
    if empresa_id:
        qs = qs.filter(empresa_id=empresa_id)
    return qs

def get_asiento_by_identifier(identifier: Any, empresa_id: Optional[int] = None) -> AsientoContable:
    """Obtiene un asiento por ID numérico o UUID."""
    qs = qs_asiento_detail(empresa_id)
    try:
        return qs.get(id=int(identifier))
    except (ValueError, TypeError):
        return qs.get(uuid=identifier)
    except AsientoContable.DoesNotExist:
        raise ValidationError({"detail": [f"Asiento contable no encontrado con identificador: {identifier}"]})

def get_cuenta_by_identifier(identifier: Any, empresa_id: Optional[int] = None) -> CuentaContable:
    """Obtiene una cuenta por ID numérico o UUID."""
    qs = qs_cuenta_detail(empresa_id)
    try:
        return qs.get(id=int(identifier))
    except (ValueError, TypeError):
        return qs.get(uuid=identifier)
    except CuentaContable.DoesNotExist:
        raise ValidationError({"detail": [f"Cuenta contable no encontrada con identificador: {identifier}"]})

def get_periodo_by_identifier(identifier: Any, empresa_id: Optional[int] = None) -> PeriodoContable:
    """Obtiene un periodo por ID numérico o UUID."""
    qs = qs_periodo_detail(empresa_id)
    try:
        return qs.get(id=int(identifier))
    except (ValueError, TypeError):
        return qs.get(uuid=identifier)
    except PeriodoContable.DoesNotExist:
        raise ValidationError({"detail": [f"Periodo contable no encontrado con identificador: {identifier}"]})

# ============================================================================
# HELPER SELECTORS (Lógica de Lectura)
# ============================================================================

def verificar_periodo_cerrado(fecha: Any, empresa_id: int) -> Tuple[bool, Optional[str]]:
    """Verifica si una fecha pertenece a un periodo cerrado."""
    if hasattr(fecha, 'date'):
        fecha = fecha.date()
    
    periodo = PeriodoContable.objects.filter(
        empresa_id=empresa_id,
        estado='CERRADO',
        fecha_inicio__lte=fecha,
        fecha_fin__gte=fecha
    ).only('periodo').first()
    
    if periodo:
        return True, periodo.periodo
    return False, None

def calcular_saldos_cuenta(cuenta_id: int, fecha_hasta: Optional[Any] = None) -> dict:
    """Calcula saldo de una cuenta sumando movimientos."""
    qs = MovimientoContable.objects.filter(cuenta_id=cuenta_id).only('debe', 'haber')
    if fecha_hasta:
        qs = qs.filter(asiento__fecha__lte=fecha_hasta)

    aggregation = qs.aggregate(
        total_debe=Coalesce(Sum('debe'), Decimal('0.00'), output_field=DecimalField()),
        total_haber=Coalesce(Sum('haber'), Decimal('0.00'), output_field=DecimalField()),
        count=Sum(1)
    )

    total_debe = aggregation['total_debe']
    total_haber = aggregation['total_haber']
    saldo = total_debe - total_haber
    
    return {
        'total_debe': total_debe,
        'total_haber': total_haber,
        'saldo_neto': saldo,
        'saldo_deudor': saldo if saldo > 0 else Decimal('0.00'),
        'saldo_acreedor': abs(saldo) if saldo < 0 else Decimal('0.00'),
        'movimientos_count': aggregation['count'] or 0,
    }

def get_balance_prueba(empresa_id: int, fecha_hasta: Optional[Any] = None) -> dict:
    """Genera balance de prueba agrupado por cuenta."""
    qs = CuentaContable.objects.filter(
        empresa_id=empresa_id, 
        activa=True, 
        nivel=6
    ).only('id', 'codigo', 'nombre', 'tipo').order_by('codigo')

    filas = []
    total_debitos = Decimal('0.00')
    total_creditos = Decimal('0.00')

    for cuenta in qs:
        saldo_info = calcular_saldos_cuenta(cuenta.id, fecha_hasta)
        filas.append({
            'codigo': cuenta.codigo,
            'nombre': cuenta.nombre,
            'tipo': cuenta.tipo,
            'debe_total': str(saldo_info['saldo_deudor']),
            'haber_total': str(saldo_info['saldo_acreedor']),
            'saldo': str(saldo_info['saldo_neto'])
        })
        total_debitos += saldo_info['saldo_deudor']
        total_creditos += saldo_info['saldo_acreedor']

    return {
        'cuentas': filas,
        'totales': {
            'debe_total': str(total_debitos),
            'haber_total': str(total_creditos),
            'diferencia': str(total_debitos - total_creditos)
        }
    }

def get_tercero_movimiento(tipo_tercero: str, tercero_id: int) -> Optional[Any]:
    """Obtiene el objeto del tercero según tipo e ID."""
    if not tipo_tercero or not tercero_id:
        return None

    try:
        if tipo_tercero == 'CLIENTE':
            from apps.tenant.clientes.models import Cliente
            return Cliente.objects.filter(id=tercero_id).only('id', 'nombre', 'nit').first()
        elif tipo_tercero == 'PROVEEDOR':
            from apps.tenant.proveedores.models import Proveedor
            return Proveedor.objects.filter(id=tercero_id).only('id', 'nombre', 'nit').first()
        elif tipo_tercero == 'EMPLEADO':
            from apps.tenant.empleados.models import Empleado
            return Empleado.objects.filter(id=tercero_id).only('id', 'nombre', 'nit').first()
    except Exception:
        return None
    return None
