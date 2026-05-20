"""
Selectors para la app contabilidad (v3.5).

[ARCHITECTURE v3.5]
- Centralización de todas las consultas GET optimizadas.
- Definición de LIST_FIELDS y DETAIL_FIELDS para alineación con Serializers.
- Zero Waste: Uso estricto de only(), select_related() y prefetch_related().
"""
from datetime import date
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
    MovimientoContable,
    TipoComprobante,
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
    "total_debe", "total_haber", "tipo_comprobante", "numero_comprobante",
    "created_at", "updated_at",
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

TIPO_COMPROBANTE_LIST_FIELDS = (
    "id", "uuid", "codigo", "nombre", "prefijo", "activa",
)

TIPO_COMPROBANTE_DETAIL_FIELDS = (
    "id", "uuid", "codigo", "nombre", "prefijo", "consecutivo_actual", "activa", "created_at",
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
# PREFIJOS PUC POR APP ORIGEN — SSoT para filtrado contextual de cuentas
# ============================================================================
# Mapea app_label → lista de prefijos de codigo PUC (startswith) relevantes.
# Usado en CuentaContableViewSet.get_queryset() cuando llega ?app_origen=X.
# Incluye tanto cuentas de nivel 6 como de nivel 4 para que el usuario
# pueda buscar por grupo (ej. "5135") y ver todas las auxiliares del grupo.
APP_ORIGEN_PREFIJOS: dict = {
    'facturas': [
        # Activo — Cartera clientes
        '130505', '130510', '1305',
        # Activo — Retenciones a favor
        '135515', '135517', '135518', '1355',
        # Ingresos operacionales
        '413505', '413510', '4135',
        # Devoluciones y descuentos en ventas
        '4175', '418',
        # IVA generado
        '240805',
        # Retenciones por pagar (aplicadas por el cliente)
        '236505', '236510', '236515', '236525', '236540', '2365',
        '236805', '2368',
    ],
    'clientes': [
        # Activo — Cartera clientes (Cuenta Control)
        '1305', '130505',
        # Ingresos por ventas (para vincular facturas a clientes)
        '4135', '413505', '413510',
        # Retenciones por cobrar (retefuente, reteica, reteiva)
        '1375',
    ],
    'gastos': [
        # Pasivo — Cuentas por pagar proveedores
        '233505', '233550', '233595', '2335',
        # Pasivo — Retenciones practicadas
        '236505', '236510', '236515', '236525', '236540', '2365',
        '236805', '2368',
        # Pasivo — IVA descontable
        '240810',
        # Gastos administrativos (grupos y auxiliares comunes)
        '510506', '511005', '511505', '512010',
        '513505', '513520', '513525', '513530', '513535',
        '514510', '514525', '519525', '519530',
        '5110', '5115', '5120', '5130', '5135', '5140', '5145', '5150', '5155', '5195', '5199',
        # Gastos generales (Clase 5 — Gastos)
        '51',
        # Costos de venta (si hay compra de inventario)
        '6',
    ],
    'empleados': [
        # Gastos de personal — Clase 5 nomina
        '5105',  # Sueldos y salarios
        '5110',  # Horas extras y recargos
        '5115',  # Comisiones
        '5120',  # Auxilios (transporte, alimentacion)
        '5125',  # Prestaciones sociales directas
        '5130',  # Aportes sobre nomina (EPS, AFP, ARL, parafiscales)
        '5140',  # Gastos de personal (bonificaciones)
        '510506', '510527', '510530', '510533', '510536', '510539', '510568', '510570',
        # Gastos generales de personal (prefijo genérico)
        '51',
        # Pasivo — Nomina por pagar (cuenta mas usada en PyMEs colombianas)
        '2335',  # Costos y gastos por pagar — nomina por pagar
        '233505', '233550', '233595',
        # Pasivo — Obligaciones laborales (clase 25 completa)
        '25',    # Cubre 2505 salarios, 2510 cesantias, 2515 intereses ces.,
                 # 2520 prima, 2525 vacaciones, 2530 prestaciones extralegales,
                 # 2540 pensiones, 2550 aportes EPS/AFP/ARL empleado
        # Pasivo — Retenciones de nomina
        '2370',  # Retenciones en la fuente (retefuente salarios)
        '2375',  # Cuotas sindicales
        '2380',  # Acreedores varios (prestamos empleados)
        # Pasivo — Seguridad social por pagar
        '2590',  # Otros pasivos laborales
    ],
    'inventario': [
        # Activo — Inventarios
        '143505', '143510', '1435',
        # Costos de ventas
        '613505', '613510', '6135',
        # Ingresos (contraparte de salida inventario)
        '413505', '413510', '4135',
        # Gastos de personal / depreciación
        '51',
        # Propiedades, Planta y Equipo (Activos Fijos)
        '15',
    ],
    'proveedores': [
        # Pasivo — Proveedores nacionales
        '2205', '220501', '220505',
        # Pasivo — Cuentas por pagar
        '2335', '233505', '233550', '233595',
        # Pasivo — Retenciones practicadas (retefuente, reteica, reteiva)
        '2365', '236505', '236510', '236515', '236525', '236540',
        '236805', '2368',
        # Pasivo — Anticipos recibidos de clientes
        '2805', '280505',
    ],
}



def filtrar_cuentas_por_app_origen(qs, app_origen: str):
    """
    Aplica filtro de prefijos PUC a un queryset de CuentaContable
    segun el app de origen del documento. Retorna el queryset filtrado
    si app_origen es reconocido, o el queryset original si no lo es.
    """
    prefijos = APP_ORIGEN_PREFIJOS.get(app_origen, [])
    if not prefijos:
        return qs
    q_filter = Q()
    for p in prefijos:
        q_filter |= Q(codigo__startswith=p)
    return qs.filter(q_filter)


# ============================================================================
# SELECTORS (QuerySets Optimizados)
# ============================================================================

class CuentaContableSelector:
    @staticmethod
    def get_qs_list(empresa_id: Optional[int] = None):
        qs = CuentaContable.objects.only(*CUENTA_LIST_FIELDS)
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)
        return qs

    @staticmethod
    def get_qs_detail(empresa_id: Optional[int] = None):
        qs = CuentaContable.objects.select_related("cuenta_padre", "catalogo_referencia").only(
            *CUENTA_DETAIL_FIELDS, "catalogo_referencia"
        )
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)
        return qs

    @staticmethod
    def get_by_uuid(uuid: Any, empresa_id: int) -> Optional[CuentaContable]:
        return CuentaContable.objects.filter(uuid=uuid, empresa_id=empresa_id).first()

    @staticmethod
    def exists_by_uuid(uuid: Any, empresa_id: int) -> bool:
        if not uuid:
            return False
        return CuentaContable.objects.filter(uuid=uuid, empresa_id=empresa_id).exists()

    @staticmethod
    def get_label_by_uuid(uuid: Any, empresa_id: int) -> str:
        if not uuid:
            return ""
        try:
            cuenta = CuentaContable.objects.filter(
                uuid=uuid, 
                empresa_id=empresa_id
            ).only('codigo', 'nombre').first()
            if cuenta:
                return f"{cuenta.codigo} - {cuenta.nombre}"
        except Exception:
            pass
        return ""

    @staticmethod
    def resolve_label_by_uuid(uuid: Any, empresa_id: int) -> Tuple[str, str]:
        """Retorna tupla (codigo, nombre) para uso en DTOs de integracion."""
        if not uuid:
            return "", ""
        try:
            cuenta = CuentaContable.objects.filter(
                uuid=uuid, 
                empresa_id=empresa_id
            ).only('codigo', 'nombre').first()
            if cuenta:
                return cuenta.codigo, cuenta.nombre
        except Exception:
            pass
        return "", ""

class AsientoContableSelector:
    @staticmethod
    def get_qs_list(empresa_id: Optional[int] = None):
        qs = AsientoContable.objects.only(*ASIENTO_LIST_FIELDS).prefetch_related('movimientos')
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)
        return qs

    @staticmethod
    def get_qs_detail(empresa_id: Optional[int] = None):
        qs = AsientoContable.objects.prefetch_related(
            "movimientos", "movimientos__cuenta"
        ).only(*ASIENTO_DETAIL_FIELDS)
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)
        return qs

class PeriodoContableSelector:
    @staticmethod
    def get_qs_list(empresa_id: Optional[int] = None):
        qs = PeriodoContable.objects.select_related("cerrado_por").only(*PERIODO_LIST_FIELDS, "cerrado_por")
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)
        return qs

    @staticmethod
    def get_qs_detail(empresa_id: Optional[int] = None):
        qs = PeriodoContable.objects.select_related("cerrado_por").only(*PERIODO_DETAIL_FIELDS, "cerrado_por")
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)
        return qs


def qs_periodos_disponibles(empresa_id: int):
    """
    Retorna los periodos contables abiertos utilizables para contabilización.
    Optimizado (Zero-Waste).
    """
    return (
        PeriodoContable.objects.filter(empresa_id=empresa_id, estado='ABIERTO')
        .only('uuid', 'periodo', 'fecha_inicio', 'fecha_fin')
        .order_by('-periodo')
    )


class TipoComprobanteSelector:
    @staticmethod
    def get_qs_list(empresa_id: Optional[int] = None):
        qs = TipoComprobante.objects.only(*TIPO_COMPROBANTE_LIST_FIELDS)
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)
        return qs

    @staticmethod
    def get_qs_detail(empresa_id: Optional[int] = None):
        qs = TipoComprobante.objects.only(*TIPO_COMPROBANTE_DETAIL_FIELDS)
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)
        return qs

# [LEGACY WRAPPER] Para compatibilidad con modulos que ya usan ContabilidadSelector
class ContabilidadSelector(CuentaContableSelector):
    """v3.5: Fachada de compatibilidad para CuentaContableSelector."""
    pass

def get_asiento_by_identifier(identifier: Any, empresa_id: Optional[int] = None) -> AsientoContable:
    """Obtiene un asiento por ID numerico o UUID."""
    qs = AsientoContableSelector.get_qs_detail(empresa_id)
    try:
        return qs.get(id=int(identifier))
    except (ValueError, TypeError):
        pass
    try:
        return qs.get(uuid=identifier)
    except AsientoContable.DoesNotExist:
        raise ValidationError({"detail": [f"Asiento contable no encontrado: {identifier}"]})

def get_cuenta_by_identifier(identifier: Any, empresa_id: Optional[int] = None) -> CuentaContable:
    """Obtiene una cuenta por ID numerico o UUID."""
    qs = CuentaContableSelector.get_qs_detail(empresa_id)
    try:
        return qs.get(id=int(identifier))
    except (ValueError, TypeError):
        pass
    try:
        return qs.get(uuid=identifier)
    except CuentaContable.DoesNotExist:
        raise ValidationError({"detail": [f"Cuenta contable no encontrada: {identifier}"]})

def get_periodo_by_identifier(identifier: Any, empresa_id: Optional[int] = None) -> PeriodoContable:
    """Obtiene un periodo por ID numerico o UUID."""
    qs = PeriodoContableSelector.get_qs_detail(empresa_id)
    try:
        return qs.get(id=int(identifier))
    except (ValueError, TypeError):
        pass
    try:
        return qs.get(uuid=identifier)
    except PeriodoContable.DoesNotExist:
        raise ValidationError({"detail": [f"Periodo contable no encontrado: {identifier}"]})

def get_tipo_comprobante_by_identifier(identifier: Any, empresa_id: Optional[int] = None) -> TipoComprobante:
    """Obtiene un tipo de comprobante por ID numérico o UUID."""
    qs = TipoComprobanteSelector.get_qs_detail(empresa_id)
    try:
        return qs.get(id=int(identifier))
    except (ValueError, TypeError):
        return qs.get(uuid=identifier)
    except TipoComprobante.DoesNotExist:
        raise ValidationError({"detail": [f"Tipo de comprobante no encontrado con identificador: {identifier}"]})

# ============================================================================
# PENDIENTES DE CONTABILIZAR (Flujo Manual On-Demand)
# ============================================================================

PENDIENTE_FACTURA_FIELDS = (
    'id', 'numero', 'fecha_emision', 'emisor_nit', 'emisor_razon_social',
    'receptor_nit', 'receptor_razon_social', 'subtotal', 'impuestos', 'total',
    'naturaleza', 'estado',
)

PENDIENTE_GASTO_FIELDS = (
    'id', 'consecutivo', 'fecha', 'subtotal', 'retefuente', 'reteica', 'total',
)

PENDIENTE_NOMINA_FIELDS = (
    'id', 'periodo_mes', 'fecha_pago', 'neto_pagar', 'anulado',
)

PENDIENTE_INVENTARIO_FIELDS = (
    'id', 'tipo', 'cantidad', 'costo_unitario', 'created_at',
)


def qs_facturas_pendientes(empresa_id: int):
    """Facturas del tenant que aun no tienen AsientoContable asociado."""
    from apps.tenant.facturas.models import Factura
    ya_ids = AsientoContable.objects.filter(
        empresa_id=empresa_id,
        documento_origen_app='facturas',
        documento_origen_modelo='Factura',
        documento_origen_id__isnull=False,
    ).values_list('documento_origen_id', flat=True)
    return (
        Factura.objects.filter(empresa_id=empresa_id)
        .exclude(id__in=ya_ids)
        .only(*PENDIENTE_FACTURA_FIELDS)
        .order_by('-fecha_emision')
    )


def qs_gastos_pendientes(empresa_id: int):
    """DocumentosSoporte activos del tenant que aun no tienen AsientoContable asociado."""
    from apps.tenant.gastos.models import DocumentoSoporte
    ya_ids = AsientoContable.objects.filter(
        empresa_id=empresa_id,
        documento_origen_app='gastos',
        documento_origen_modelo='DocumentoSoporte',
        documento_origen_id__isnull=False,
    ).values_list('documento_origen_id', flat=True)
    return (
        DocumentoSoporte.objects.filter(empresa_id=empresa_id, anulado=False)
        .exclude(id__in=ya_ids)
        .select_related('proveedor', 'resolucion_dian')
        .only(*PENDIENTE_GASTO_FIELDS, 'proveedor', 'resolucion_dian')
        .order_by('-fecha')
    )


def qs_nominas_pendientes(empresa_id: int):
    """Nominas del tenant que aun no tienen AsientoContable asociado."""
    from apps.tenant.empleados.models import Devengo
    ya_ids = AsientoContable.objects.filter(
        empresa_id=empresa_id,
        documento_origen_app='empleados',
        documento_origen_modelo='Devengo',
        documento_origen_id__isnull=False,
    ).values_list('documento_origen_id', flat=True)
    return (
        Devengo.objects.filter(empresa_id=empresa_id, anulado=False)
        .exclude(id__in=ya_ids)
        .select_related('empleado')
        .only(*PENDIENTE_NOMINA_FIELDS, 'empleado__numero_documento', 'empleado__primer_nombre', 'empleado__primer_apellido')
        .order_by('-fecha_pago')
    )


def qs_inventario_pendientes(empresa_id: int):
    """Movimientos de inventario del tenant que aun no tienen AsientoContable asociado."""
    from apps.tenant.inventario.models import MovimientoInventario
    ya_ids = AsientoContable.objects.filter(
        empresa_id=empresa_id,
        documento_origen_app='inventario',
        documento_origen_modelo='MovimientoInventario',
        documento_origen_id__isnull=False,
    ).values_list('documento_origen_id', flat=True)
    return (
        MovimientoInventario.objects.filter(empresa_id=empresa_id)
        .exclude(id__in=ya_ids)
        .select_related('producto')
        .only(*PENDIENTE_INVENTARIO_FIELDS, 'producto__codigo', 'producto__nombre')
        .order_by('-created_at')
    )


def get_documento_pendiente(app_label: str, modelo: str, documento_id: int, empresa_id: int):
    """
    Obtiene un documento especifico para el offcanvas de contabilizacion manual.
    Aplica DSV: filtra por empresa_id para garantizar aislamiento de tenant.
    """
    if app_label == 'facturas' and modelo == 'Factura':
        from apps.tenant.facturas.models import Factura
        return (
            Factura.objects.filter(empresa_id=empresa_id, id=documento_id)
            .only(*PENDIENTE_FACTURA_FIELDS)
            .first()
        )
    if app_label == 'gastos' and modelo == 'DocumentoSoporte':
        from apps.tenant.gastos.models import DocumentoSoporte
        return (
            DocumentoSoporte.objects.filter(empresa_id=empresa_id, id=documento_id)
            .select_related('proveedor', 'resolucion_dian')
            .only(*PENDIENTE_GASTO_FIELDS, 'proveedor__numero_documento', 'proveedor__razon_social',
                  'resolucion_dian__prefijo', 'resolucion_dian__consecutivo')
            .first()
        )
    if app_label == 'empleados' and modelo == 'Devengo':
        from apps.tenant.empleados.models import Devengo
        return (
            Devengo.objects.filter(empresa_id=empresa_id, id=documento_id, anulado=False)
            .select_related('empleado', 'contrato')
            .only(*PENDIENTE_NOMINA_FIELDS, 'empleado__numero_documento', 'empleado__primer_nombre', 'empleado__primer_apellido', 
                  'contrato__salario_mensual', 'auxilio_transporte', 'otros_devengos', 'salud_empleado', 'pension_empleado', 'prestamos', 'descuentos_operativos')
            .first()
        )
    if app_label == 'inventario' and modelo == 'MovimientoInventario':
        from apps.tenant.inventario.models import MovimientoInventario
        return (
            MovimientoInventario.objects.filter(empresa_id=empresa_id, id=documento_id)
            .select_related('producto')
            .only(*PENDIENTE_INVENTARIO_FIELDS, 'producto__codigo', 'producto__nombre')
            .first()
        )
    return None


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
            return Cliente.objects.filter(id=tercero_id).only('id', 'razon_social', 'numero_documento').first()
        elif tipo_tercero == 'PROVEEDOR':
            from apps.tenant.proveedores.models import Proveedor
            return Proveedor.objects.filter(id=tercero_id).only('id', 'nombre', 'nit').first()
        elif tipo_tercero == 'EMPLEADO':
            from apps.tenant.empleados.models import Empleado
            return Empleado.objects.filter(id=tercero_id).only('id', 'nombre', 'nit').first()
    except Exception:
        return None
    return None
# ============================================================================
# REPORTES FINANCIEROS (SELECTORS)
# ============================================================================

def balance_prueba_selector(empresa_id: int, fecha_inicio: Any, fecha_fin: Any):
    """
    Calcula el Balance de Prueba (Saldos y Movimientos) para un periodo.
    
    Retorna una lista de dicts con:
    - codigo, nombre, nivel
    - saldo_anterior
    - debito_periodo, credito_periodo
    - nuevo_saldo
    """
    from apps.tenant.contabilidad.models import MovimientoContable
    from django.db.models import Sum, Case, When, Value, DecimalField, F
    
    # 1. Movimientos del periodo
    qs_periodo = MovimientoContable.objects.filter(
        asiento__empresa_id=empresa_id,
        asiento__fecha__range=(fecha_inicio, fecha_fin),
        asiento__estado='APROBADO'
    ).exclude(
        cuenta__isnull=True
    ).values(
        'cuenta__codigo',
        'cuenta__nombre',
        'cuenta__nivel'
    ).annotate(
        debito=Sum('debe'),
        credito=Sum('haber')
    )

    # 2. Saldos anteriores (fecha < fecha_inicio)
    qs_anterior = MovimientoContable.objects.filter(
        asiento__empresa_id=empresa_id,
        asiento__fecha__lt=fecha_inicio,
        asiento__estado='APROBADO'
    ).exclude(
        cuenta__isnull=True
    ).values(
        'cuenta__codigo'
    ).annotate(
        total_debe_ant=Sum('debe'),
        total_haber_ant=Sum('haber')
    )

    anteriores_map = {x['cuenta__codigo']: x for x in qs_anterior}
    
    resultado = []
    # Usamos todas las cuentas que tienen movimientos en el periodo o saldo anterior
    # Por simplicidad en esta v1, iteramos sobre las del periodo
    # TODO: Unir ambos QuerySets para cubrir cuentas con saldo pero sin movimiento
    
    for item in qs_periodo:
        codigo = item['cuenta__codigo']
        if not codigo:
            continue

        ant = anteriores_map.get(codigo, {'total_debe_ant': Decimal('0'), 'total_haber_ant': Decimal('0')})

        debito_ant = ant['total_debe_ant'] or Decimal('0')
        credito_ant = ant['total_haber_ant'] or Decimal('0')

        debito_p = item['debito'] or Decimal('0')
        credito_p = item['credito'] or Decimal('0')

        # Determinar naturaleza por primer digito
        naturaleza = 'D' if codigo[0] in ['1', '5', '6'] else 'C'
        
        if naturaleza == 'D':
            saldo_ant = debito_ant - credito_ant
            nuevo_saldo = saldo_ant + debito_p - credito_p
        else:
            saldo_ant = credito_ant - debito_ant
            nuevo_saldo = saldo_ant + credito_p - debito_p
            
        resultado.append({
            'codigo': codigo,
            'nombre': item['cuenta__nombre'],
            'nivel': item['cuenta__nivel'],
            'saldo_anterior': saldo_ant,
            'debito': debito_p,
            'credito': credito_p,
            'nuevo_saldo': nuevo_saldo,
        })
        
    return sorted(resultado, key=lambda x: x['codigo'])


def estado_resultados_selector(empresa_id: int, fecha_inicio: Any, fecha_fin: Any):
    """
    Calcula el Estado de Resultados (P&G) para un periodo.
    Filtra cuentas de Clase 4 (Ingresos), 5 (Gastos) y 6 (Costos).
    """
    from apps.tenant.contabilidad.models import MovimientoContable
    from django.db.models import Sum
    
    # Movimientos del periodo para cuentas de resultado (4, 5, 6)
    qs = MovimientoContable.objects.filter(
        asiento__empresa_id=empresa_id,
        asiento__fecha__range=(fecha_inicio, fecha_fin),
        asiento__estado='APROBADO',
        cuenta__codigo__regex=r'^[456]'
    ).values(
        'cuenta__codigo', 
        'cuenta__nombre', 
        'cuenta__nivel'
    ).annotate(
        debito=Sum('debe'),
        credito=Sum('haber')
    ).order_by('cuenta__codigo')
    
    ingresos = []
    gastos = []
    costos = []
    
    total_ingresos = Decimal('0')
    total_gastos = Decimal('0')
    total_costos = Decimal('0')
    
    for item in qs:
        codigo = item['cuenta__codigo']
        debito = item['debito'] or Decimal('0')
        credito = item['credito'] or Decimal('0')
        
        # Valor neto según naturaleza
        if codigo.startswith('4'): # Ingresos (C)
            valor = credito - debito
            ingresos.append({'codigo': codigo, 'nombre': item['cuenta__nombre'], 'valor': valor})
            total_ingresos += valor
        elif codigo.startswith('5'): # Gastos (D)
            valor = debito - credito
            gastos.append({'codigo': codigo, 'nombre': item['cuenta__nombre'], 'valor': valor})
            total_gastos += valor
        elif codigo.startswith('6'): # Costos (D)
            valor = debito - credito
            costos.append({'codigo': codigo, 'nombre': item['cuenta__nombre'], 'valor': valor})
            total_costos += valor
            
    utilidad_bruta = total_ingresos - total_costos
    utilidad_neta = utilidad_bruta - total_gastos
    
    return {
        'ingresos': ingresos,
        'gastos': gastos,
        'costos': costos,
        'totales': {
            'ingresos': total_ingresos,
            'gastos': total_gastos,
            'costos': total_costos,
            'utilidad_bruta': utilidad_bruta,
            'utilidad_neta': utilidad_neta
        }
    }


# ============================================================================
# LIBRO DIARIO UNIFICADO (v3.7.1)
# ============================================================================

def get_libro_diario_periodo(empresa_id: int, fecha_inicio: date, fecha_fin: date) -> dict:
    """
    Consolida documentos de todas las apps de negocio para el Libro Diario.
    Arquitectura Pull: Interroga a cada extractor por su 'DocumentoEnriquecido'.
    Orden cronológico estricto según Art. 48 Código de Comercio.

    Retorna dict con:
    - periodo: YYYY-MM
    - documentos: lista de DocumentoEnriquecido.to_dict()
    - resumen: totales, cuadratura y clasificación normativa
    """
    from ..integracion.extractores.facturas import ExtractorFacturas
    from ..integracion.extractores.gastos import ExtractorGastos
    from ..integracion.extractores.nomina import ExtractorNomina
    import logging

    extractores = [
        ExtractorFacturas(empresa_id),
        ExtractorGastos(empresa_id),
        ExtractorNomina(empresa_id),
    ]

    libro_diario = []
    for ext in extractores:
        try:
            documentos = ext.get_documentos_enriquecidos(empresa_id, fecha_inicio, fecha_fin)
            libro_diario.extend(documentos)
        except Exception as e:
            logging.getLogger(__name__).error(f"[LibroDiario] Error en {ext.__class__.__name__}: {str(e)}")

    # Orden cronológico (Art. 48 Código de Comercio)
    documentos_ordenados = sorted(libro_diario, key=lambda x: (x.fecha, x.numero))

    # Clasificar por estado contable
    contabilizados = [d for d in documentos_ordenados if d.estado_contable == 'CONTABILIZADO']
    pendientes = [d for d in documentos_ordenados if d.estado_contable == 'PENDIENTE']

    # Calcular totales del período (solo documentos contabilizados)
    total_debe = Decimal('0')
    total_haber = Decimal('0')
    for d in contabilizados:
        for mov in d.movimientos:
            total_debe += mov.debe
            total_haber += mov.haber

    # Clasificación normativa de comprobantes
    clasificacion = {
        'CI': 0,  # Comprobante de Ingreso
        'CE': 0,  # Comprobante de Egreso
        'CN': 0,  # Comprobante de Nómina
        'CD': 0,  # Comprobante de Diario
        'NC': 0,  # Nota de Crédito
        'CA': 0,  # Comprobante de Ajuste
    }
    for d in contabilizados:
        tipo = d.tipo_comprobante
        if tipo in clasificacion:
            clasificacion[tipo] += 1

    # Resumen del período
    resumen = {
        'total_documentos': len(documentos_ordenados),
        'contabilizados': len(contabilizados),
        'pendientes': len(pendientes),
        'total_debe': str(total_debe),
        'total_haber': str(total_haber),
        'diferencia': str(abs(total_debe - total_haber)),
        'cuadra': abs(total_debe - total_haber) < Decimal('0.01'),
        'por_tipo_comprobante': {
            'CI': clasificacion['CI'],
            'CE': clasificacion['CE'],
            'CN': clasificacion['CN'],
            'CD': clasificacion['CD'],
            'NC': clasificacion['NC'],
            'CA': clasificacion['CA'],
        }
    }

    return {
        'periodo': fecha_inicio.strftime('%Y-%m'),
        'fecha_inicio': str(fecha_inicio),
        'fecha_fin': str(fecha_fin),
        'documentos': [d.to_dict() for d in documentos_ordenados],
        'resumen': resumen,
    }
