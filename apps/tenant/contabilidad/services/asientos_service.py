"""
Service Layer interno para AsientoContable (dominio Contabilidad).

⚠️ v2.30: Service Layer Pattern - Lógica de negocio del dominio Contabilidad.
- Sin signals: Toda la lógica es explícita
- Sin HTTP: Funciones puras que operan sobre modelos
- Multi-tenant: Transparente (django-tenants maneja el aislamiento por esquema)
- Validaciones: Estados, aprobar con validación de cuadratura (sumas debe/haber)

⚠️ v2.60: Contabilidad Invisible (Event-Driven)
- materializar_asiento_desde_factura(): Crea asiento automático cuando factura se acepta
- materializar_asiento_desde_gasto(): Crea asiento automático cuando gasto se crea activo
- SSoT: Hereda datos inmutables (NIT, fecha, valores) de facturas/gastos
"""
from typing import Dict, Any, List, Optional
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Q
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


def list_asientos(
    filters: Optional[Dict[str, Any]] = None,
    ordering: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
) -> Dict[str, Any]:
    """
    Lista asientos contables (paginado).
    
    Args:
        filters: Diccionario con filtros (estado, fecha, search)
        ordering: Campo de ordenamiento (fecha, numero, total_debe, total_haber, created_at)
        page: Número de página (1-indexed)
        page_size: Tamaño de página
    
    Returns:
        dict: DTO con resultados paginados
    """
    from apps.tenant.contabilidad.models import AsientoContable
    
    qs = AsientoContable.objects.only(
        'id', 'numero', 'fecha', 'descripcion', 'estado',
        'total_debe', 'total_haber', 'created_at'
    )
    
    # Aplicar filtros
    if filters:
        if 'estado' in filters:
            qs = qs.filter(estado=filters['estado'])
        if 'fecha' in filters:
            qs = qs.filter(fecha=filters['fecha'])
        if 'search' in filters:
            search = filters['search']
            qs = qs.filter(
                Q(numero__icontains=search) |
                Q(descripcion__icontains=search)
            )
    
    # Aplicar ordenamiento (whitelist)
    ordering_fields = [
        'fecha', 'numero', 'total_debe', 'total_haber', 'created_at',
        '-fecha', '-numero', '-total_debe', '-total_haber', '-created_at'
    ]
    if ordering and ordering in ordering_fields:
        qs = qs.order_by(ordering)
    else:
        qs = qs.order_by('-fecha', '-numero')
    
    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)
    
    results = []
    for asiento in page_obj:
        results.append({
            'id': asiento.id,
            'numero': asiento.numero,
            'fecha': asiento.fecha.isoformat() if asiento.fecha else None,
            'descripcion': asiento.descripcion,
            'estado': asiento.estado,
            'total_debe': str(asiento.total_debe),
            'total_haber': str(asiento.total_haber),
            'created_at': asiento.created_at.isoformat() if asiento.created_at else None,
        })
    
    return {
        'count': paginator.count,
        'next': page_obj.next_page_number() if page_obj.has_next() else None,
        'previous': page_obj.previous_page_number() if page_obj.has_previous() else None,
        'results': results,
    }


@transaction.atomic
def create_asiento(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea un asiento contable.
    
    ⚠️ VALIDACIONES: Estados, número único.
    
    Args:
        data: Diccionario con datos del asiento
    
    Returns:
        dict: DTO con datos del asiento creado
    
    Raises:
        ValueError: Si los datos no son válidos
    """
    from apps.tenant.contabilidad.models import AsientoContable
    
    # Validaciones
    if 'numero' in data:
        numero = data['numero']
        if not isinstance(numero, str) or len(numero) > 50:
            raise ValueError("El campo 'numero' debe ser una cadena de texto de máximo 50 caracteres.")
        if not numero.strip():
            raise ValueError("El campo 'numero' no puede estar vacío.")
        # Verificar unicidad
        if AsientoContable.objects.filter(numero=numero).exists():
            raise ValueError(f"Ya existe un asiento con el número '{numero}'.")
    
    if 'estado' in data:
        estado = data['estado']
        estados_validos = ['BORRADOR', 'APROBADO', 'CERRADO']
        if estado not in estados_validos:
            raise ValueError(f"El campo 'estado' debe ser uno de: {', '.join(estados_validos)}.")
    
    asiento = AsientoContable.objects.create(**data)
    
    return {
        'id': asiento.id,
        'numero': asiento.numero,
        'fecha': asiento.fecha.isoformat() if asiento.fecha else None,
        'descripcion': asiento.descripcion,
        'estado': asiento.estado,
        'total_debe': str(asiento.total_debe),
        'total_haber': str(asiento.total_haber),
        'created_at': asiento.created_at.isoformat() if asiento.created_at else None,
        'updated_at': asiento.updated_at.isoformat() if asiento.updated_at else None,
    }


@transaction.atomic
def update_asiento(asiento_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Actualiza un asiento contable.
    
    ⚠️ VALIDACIONES: Estados, número único.
    
    Args:
        asiento_id: ID del asiento
        data: Diccionario con campos a actualizar
    
    Returns:
        dict: DTO con datos del asiento actualizado
    
    Raises:
        ValueError: Si los datos no son válidos
        AsientoContable.DoesNotExist: Si el asiento no existe
    """
    from apps.tenant.contabilidad.models import AsientoContable
    
    asiento = AsientoContable.objects.get(id=asiento_id)
    
    # Validaciones (mismas que create)
    if 'numero' in data:
        numero = data['numero']
        if not isinstance(numero, str) or len(numero) > 50:
            raise ValueError("El campo 'numero' debe ser una cadena de texto de máximo 50 caracteres.")
        if not numero.strip():
            raise ValueError("El campo 'numero' no puede estar vacío.")
        # Verificar unicidad (excluyendo el asiento actual)
        if AsientoContable.objects.filter(numero=numero).exclude(id=asiento_id).exists():
            raise ValueError(f"Ya existe otro asiento con el número '{numero}'.")
    
    campos_permitidos = ['numero', 'fecha', 'descripcion', 'estado', 'factura']
    update_fields = []
    for campo in campos_permitidos:
        if campo in data:
            setattr(asiento, campo, data[campo])
            update_fields.append(campo)
    
    if update_fields:
        asiento.save(update_fields=update_fields)
    
    return {
        'id': asiento.id,
        'numero': asiento.numero,
        'fecha': asiento.fecha.isoformat() if asiento.fecha else None,
        'descripcion': asiento.descripcion,
        'estado': asiento.estado,
        'total_debe': str(asiento.total_debe),
        'total_haber': str(asiento.total_haber),
        'created_at': asiento.created_at.isoformat() if asiento.created_at else None,
        'updated_at': asiento.updated_at.isoformat() if asiento.updated_at else None,
    }


@transaction.atomic
def aprobar_asiento(asiento_id: int) -> Dict[str, Any]:
    """
    Aprueba un asiento contable.
    
    ⚠️ VALIDACIÓN: Un asiento solo puede ser aprobado si total_debe == total_haber.
    
    Args:
        asiento_id: ID del asiento
    
    Returns:
        dict: DTO con datos del asiento aprobado
    
    Raises:
        ValueError: Si el asiento no puede ser aprobado (debe != haber)
        AsientoContable.DoesNotExist: Si el asiento no existe
    """
    from apps.tenant.contabilidad.models import AsientoContable
    
    asiento = AsientoContable.objects.get(id=asiento_id)
    
    # Validar cuadratura
    if asiento.total_debe != asiento.total_haber:
        raise ValueError(
            f"Un asiento no puede ser aprobado si débito ({asiento.total_debe}) "
            f"no es igual a crédito ({asiento.total_haber})."
        )
    
    asiento.estado = 'APROBADO'
    asiento.save(update_fields=['estado'])
    
    return {
        'id': asiento.id,
        'numero': asiento.numero,
        'fecha': asiento.fecha.isoformat() if asiento.fecha else None,
        'descripcion': asiento.descripcion,
        'estado': asiento.estado,
        'total_debe': str(asiento.total_debe),
        'total_haber': str(asiento.total_haber),
        'created_at': asiento.created_at.isoformat() if asiento.created_at else None,
        'updated_at': asiento.updated_at.isoformat() if asiento.updated_at else None,
    }


@transaction.atomic
def delete_asiento(asiento_id: int) -> None:
    """
    Elimina un asiento contable.
    
    Args:
        asiento_id: ID del asiento
    
    Raises:
        AsientoContable.DoesNotExist: Si el asiento no existe
    """
    from apps.tenant.contabilidad.models import AsientoContable
    
    asiento = AsientoContable.objects.get(id=asiento_id)
    asiento.delete()


def _obtener_cuenta_por_codigo(empresa, codigo: str):
    """
    Helper: Obtiene una cuenta contable por código.
    
    ⚠️ v2.60: SSoT - Busca cuenta por código y empresa.
    
    Args:
        empresa: Instancia de Empresa (SSoT)
        codigo: Código de la cuenta contable
    
    Returns:
        CuentaContable o None
    """
    from apps.tenant.contabilidad.models import CuentaContable
    
    try:
        return CuentaContable.objects.get(codigo=codigo, empresa=empresa, activa=True)
    except CuentaContable.DoesNotExist:
        return None


def _obtener_cuenta_por_tipo(empresa, tipo: str):
    """
    Helper: Obtiene una cuenta contable por tipo.
    
    ⚠️ v2.60: SSoT - Busca cuenta por tipo y empresa.
    Usa la primera cuenta activa del tipo especificado.
    
    Args:
        empresa: Instancia de Empresa (SSoT)
        tipo: Tipo de cuenta (ACTIVO, PASIVO, INGRESO, GASTO, PATRIMONIO)
    
    Returns:
        CuentaContable o None
    """
    from apps.tenant.contabilidad.models import CuentaContable
    
    try:
        return CuentaContable.objects.filter(
            tipo=tipo, 
            empresa=empresa, 
            activa=True
        ).first()
    except Exception:
        return None


def _obtener_cuenta_por_prefijo(empresa, prefijo: str):
    """
    Helper: Obtiene una cuenta contable por prefijo de código.
    
    ⚠️ v2.60: SSoT - Busca cuenta que comience con el prefijo (ej: "51" para gastos 51xx).
    Útil para buscar cuentas genéricas cuando no hay código exacto.
    
    Args:
        empresa: Instancia de Empresa (SSoT)
        prefijo: Prefijo del código de cuenta (ej: "51", "41")
    
    Returns:
        CuentaContable o None
    """
    from apps.tenant.contabilidad.models import CuentaContable
    
    try:
        return CuentaContable.objects.filter(
            codigo__startswith=prefijo,
            empresa=empresa, 
            activa=True
        ).first()
    except Exception:
        return None


# ⚠️ v2.60: Mapeo Automático de Cuentas Contables (Siigo Contador Style)
# Configuración centralizada de códigos de cuenta según tipo de operación
MAPEO_CUENTAS = {
    'VENTA': {
        'clientes': '1305',      # Clientes
        'ingresos': '4135',      # Ingresos
        'iva': '2408',           # IVA por Pagar (si aplica)
    },
    'COMPRA': {
        'compras': '6105',       # Compras
        'proveedores': '2335',   # Costos por Pagar (Proveedores)
        'iva': '2408',           # IVA por Pagar
    },
    'GASTO': {
        'gastos': '5105',        # Gastos (prefijo 51xx)
        'proveedores': '2335',   # Costos por Pagar
        'retefuente': '2365',    # Retefuente
        'reteica': '2368',       # ReteICA
    }
}


@transaction.atomic
def materializar_asiento_desde_factura(factura) -> Dict[str, Any]:
    """
    Materializa automáticamente un asiento contable desde una factura aceptada.
    
    ⚠️ v2.60: Contabilidad Invisible - Event-Driven
    ⚠️ SSoT: Hereda datos inmutables de la factura (NIT, fecha, valores)
    ⚠️ Idempotencia: Si ya existe un asiento para esta factura, no crea otro
    
    Reglas de Negocio:
    - Si naturaleza = VENTA: Debe a Clientes (1305), Haber a Ingresos (41XX)
    - Si naturaleza = COMPRA: Debe a Compras (61XX), Haber a Proveedores (22XX)
    - Incluye IVA si aplica
    
    Args:
        factura: Instancia de Factura (debe estar en estado ACEPTADA)
    
    Returns:
        dict: DTO con datos del asiento creado
    
    Raises:
        ValueError: Si la factura no está en estado ACEPTADA o ya tiene asiento
    """
    from apps.tenant.contabilidad.models import AsientoContable, MovimientoContable
    from apps.tenant.facturas.models import Factura
    
    # Validar estado
    if factura.estado != Factura.Estado.ACEPTADA:
        raise ValueError(f"La factura debe estar en estado ACEPTADA. Estado actual: {factura.estado}")
    
    # ⚠️ Idempotencia: Verificar si ya existe un asiento para esta factura
    if AsientoContable.objects.filter(factura=factura).exists():
        asiento_existente = AsientoContable.objects.get(factura=factura)
        logger.info(f"[asientos.service] Asiento ya existe para factura {factura.numero}: {asiento_existente.numero}")
        return {
            'id': asiento_existente.id,
            'numero': asiento_existente.numero,
            'fecha': asiento_existente.fecha.isoformat() if asiento_existente.fecha else None,
            'descripcion': asiento_existente.descripcion,
            'estado': asiento_existente.estado,
            'total_debe': str(asiento_existente.total_debe),
            'total_haber': str(asiento_existente.total_haber),
            'created_at': asiento_existente.created_at.isoformat() if asiento_existente.created_at else None,
        }
    
    # ⚠️ SSoT: Obtener empresa del tenant
    empresa = factura.empresa
    
    # Generar número de asiento único
    from datetime import datetime
    numero_asiento = f"AS-{factura.numero}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # ⚠️ SSoT: Heredar datos inmutables de la factura
    descripcion = f"Asiento automático desde Factura {factura.numero} - {factura.emisor_razon_social if factura.naturaleza == Factura.Naturaleza.VENTA else factura.receptor_razon_social}"
    
    # Crear asiento
    asiento = AsientoContable.objects.create(
        numero=numero_asiento,
        fecha=factura.fecha_emision.date() if hasattr(factura.fecha_emision, 'date') else factura.fecha_emision,
        descripcion=descripcion,
        estado='APROBADO',  # ⚠️ Automático: Se crea aprobado porque la factura ya está aceptada
        empresa=empresa,
        factura=factura
    )
    
    # Crear movimientos según naturaleza
    movimientos = []
    orden = 1
    
    if factura.naturaleza == Factura.Naturaleza.VENTA:
        # ⚠️ v2.60: VENTA - Mapeo Siigo Contador Style
        # DB: 1305 (Clientes) / CR: 4135 (Ingresos)
        cuenta_clientes = (
            _obtener_cuenta_por_codigo(empresa, MAPEO_CUENTAS['VENTA']['clientes']) or
            _obtener_cuenta_por_tipo(empresa, 'ACTIVO')
        )
        cuenta_ingresos = (
            _obtener_cuenta_por_codigo(empresa, MAPEO_CUENTAS['VENTA']['ingresos']) or
            _obtener_cuenta_por_tipo(empresa, 'INGRESO')
        )
        cuenta_iva = _obtener_cuenta_por_codigo(empresa, MAPEO_CUENTAS['VENTA']['iva']) or None
        
        if not cuenta_clientes or not cuenta_ingresos:
            raise ValueError(
                f"No se encontraron las cuentas contables necesarias para VENTA. "
                f"Configure: {MAPEO_CUENTAS['VENTA']['clientes']} (Clientes) y "
                f"{MAPEO_CUENTAS['VENTA']['ingresos']} (Ingresos)."
            )
        
        # Movimiento 1: Debe a Clientes (Total factura)
        movimientos.append({
            'asiento': asiento,
            'cuenta': cuenta_clientes,
            'debe': factura.total,
            'haber': Decimal('0.00'),
            'descripcion': f"Factura {factura.numero} - {factura.receptor_razon_social}",
            'orden': orden
        })
        orden += 1
        
        # Movimiento 2: Haber a Ingresos (Subtotal)
        movimientos.append({
            'asiento': asiento,
            'cuenta': cuenta_ingresos,
            'debe': Decimal('0.00'),
            'haber': factura.subtotal,
            'descripcion': f"Ingresos por venta - Factura {factura.numero}",
            'orden': orden
        })
        orden += 1
        
        # Movimiento 3: Haber a IVA (si aplica)
        if factura.impuestos > 0 and cuenta_iva:
            movimientos.append({
                'asiento': asiento,
                'cuenta': cuenta_iva,
                'debe': Decimal('0.00'),
                'haber': factura.impuestos,
                'descripcion': f"IVA por venta - Factura {factura.numero}",
                'orden': orden
            })
            orden += 1
    
    elif factura.naturaleza == Factura.Naturaleza.COMPRA:
        # ⚠️ v2.60: COMPRA - Mapeo Siigo Contador Style
        # DB: 6105 (Compras) / CR: 2335 (Costos por Pagar)
        cuenta_compras = (
            _obtener_cuenta_por_codigo(empresa, MAPEO_CUENTAS['COMPRA']['compras']) or
            _obtener_cuenta_por_tipo(empresa, 'GASTO')
        )
        cuenta_proveedores = (
            _obtener_cuenta_por_codigo(empresa, MAPEO_CUENTAS['COMPRA']['proveedores']) or
            _obtener_cuenta_por_tipo(empresa, 'PASIVO')
        )
        cuenta_iva = _obtener_cuenta_por_codigo(empresa, MAPEO_CUENTAS['COMPRA']['iva']) or None
        
        if not cuenta_compras or not cuenta_proveedores:
            raise ValueError(
                f"No se encontraron las cuentas contables necesarias para COMPRA. "
                f"Configure: {MAPEO_CUENTAS['COMPRA']['compras']} (Compras) y "
                f"{MAPEO_CUENTAS['COMPRA']['proveedores']} (Costos por Pagar)."
            )
        
        # Movimiento 1: Debe a Compras (Subtotal)
        movimientos.append({
            'asiento': asiento,
            'cuenta': cuenta_compras,
            'debe': factura.subtotal,
            'haber': Decimal('0.00'),
            'descripcion': f"Compra - Factura {factura.numero} - {factura.emisor_razon_social}",
            'orden': orden
        })
        orden += 1
        
        # Movimiento 2: Debe a IVA (si aplica)
        if factura.impuestos > 0 and cuenta_iva:
            movimientos.append({
                'asiento': asiento,
                'cuenta': cuenta_iva,
                'debe': factura.impuestos,
                'haber': Decimal('0.00'),
                'descripcion': f"IVA por compra - Factura {factura.numero}",
                'orden': orden
            })
            orden += 1
        
        # Movimiento 3: Haber a Proveedores (Total factura)
        movimientos.append({
            'asiento': asiento,
            'cuenta': cuenta_proveedores,
            'debe': Decimal('0.00'),
            'haber': factura.total,
            'descripcion': f"Factura {factura.numero} - {factura.emisor_razon_social}",
            'orden': orden
        })
        orden += 1
    
    # Crear movimientos
    for mov_data in movimientos:
        MovimientoContable.objects.create(**mov_data)
    
    # Recalcular totales del asiento
    asiento.refresh_from_db()
    
    logger.info(f"[asientos.service] Asiento {asiento.numero} materializado desde factura {factura.numero}")
    
    return {
        'id': asiento.id,
        'numero': asiento.numero,
        'fecha': asiento.fecha.isoformat() if asiento.fecha else None,
        'descripcion': asiento.descripcion,
        'estado': asiento.estado,
        'total_debe': str(asiento.total_debe),
        'total_haber': str(asiento.total_haber),
        'created_at': asiento.created_at.isoformat() if asiento.created_at else None,
    }


@transaction.atomic
def materializar_asiento_desde_gasto(gasto) -> Dict[str, Any]:
    """
    Materializa automáticamente un asiento contable desde un gasto activo.
    
    ⚠️ v2.60: Contabilidad Invisible - Event-Driven
    ⚠️ SSoT: Hereda datos inmutables del gasto (NIT, fecha, valores)
    ⚠️ Idempotencia: Si ya existe un asiento para este gasto, no crea otro
    
    Reglas de Negocio:
    - Debe a Gastos (61XX), Haber a Proveedores (22XX)
    - Incluye Retefuente y ReteICA si aplican
    
    Args:
        gasto: Instancia de Gasto (debe estar activo y no anulado)
    
    Returns:
        dict: DTO con datos del asiento creado
    
    Raises:
        ValueError: Si el gasto no está activo o ya tiene asiento
    """
    from apps.tenant.contabilidad.models import AsientoContable, MovimientoContable
    from apps.tenant.gastos.models import Gasto, DocumentoSoporte
    
    # Validar que el gasto esté activo y no anulado
    ds = gasto.documento_soporte
    if not ds.activo:
        raise ValueError(f"El gasto debe estar activo para materializar asiento. Estado: activo={ds.activo}")
    
    if ds.anulado:
        raise ValueError(f"El gasto no puede estar anulado para materializar asiento. Estado: anulado={ds.anulado}")
    
    # ⚠️ Idempotencia: Verificar si ya existe un asiento para este gasto
    # Nota: AsientoContable no tiene FK directa a Gasto, pero podemos usar la descripción
    # Para una mejor implementación, se podría agregar un campo `gasto` al modelo AsientoContable
    # Por ahora, usamos la descripción como identificador
    descripcion_busqueda = f"Asiento automático desde Gasto {ds.numero_documento}"
    if AsientoContable.objects.filter(descripcion__startswith=descripcion_busqueda).exists():
        asiento_existente = AsientoContable.objects.filter(descripcion__startswith=descripcion_busqueda).first()
        logger.info(f"[asientos.service] Asiento ya existe para gasto {ds.numero_documento}: {asiento_existente.numero}")
        return {
            'id': asiento_existente.id,
            'numero': asiento_existente.numero,
            'fecha': asiento_existente.fecha.isoformat() if asiento_existente.fecha else None,
            'descripcion': asiento_existente.descripcion,
            'estado': asiento_existente.estado,
            'total_debe': str(asiento_existente.total_debe),
            'total_haber': str(asiento_existente.total_haber),
            'created_at': asiento_existente.created_at.isoformat() if asiento_existente.created_at else None,
        }
    
    # ⚠️ SSoT: Obtener empresa del tenant
    empresa = ds.empresa
    
    # Generar número de asiento único
    from datetime import datetime
    numero_asiento = f"AS-GASTO-{ds.numero_documento}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # ⚠️ SSoT: Heredar datos inmutables del gasto
    descripcion = f"Asiento automático desde Gasto {ds.numero_documento} - {ds.vendedor_nombre}"
    
    # Crear asiento
    asiento = AsientoContable.objects.create(
        numero=numero_asiento,
        fecha=ds.fecha,
        descripcion=descripcion,
        estado='APROBADO',  # ⚠️ Automático: Se crea aprobado porque el gasto está activo
        empresa=empresa
    )
    
    # ⚠️ v2.60: GASTO - Mapeo Siigo Contador Style
    # DB: 51xx (Gasto) / CR: 2335 (Costos por Pagar)
    # Retenciones: CR: 2365 (Retefuente) / 2368 (ReteICA)
    movimientos = []
    orden = 1
    
    # Buscar cuentas contables según mapeo Siigo
    cuenta_gastos = (
        _obtener_cuenta_por_codigo(empresa, MAPEO_CUENTAS['GASTO']['gastos']) or
        _obtener_cuenta_por_prefijo(empresa, '51') or
        _obtener_cuenta_por_tipo(empresa, 'GASTO')
    )
    cuenta_proveedores = (
        _obtener_cuenta_por_codigo(empresa, MAPEO_CUENTAS['GASTO']['proveedores']) or
        _obtener_cuenta_por_tipo(empresa, 'PASIVO')
    )
    cuenta_retefuente = _obtener_cuenta_por_codigo(empresa, MAPEO_CUENTAS['GASTO']['retefuente']) or None
    cuenta_reteica = _obtener_cuenta_por_codigo(empresa, MAPEO_CUENTAS['GASTO']['reteica']) or None
    
    if not cuenta_gastos or not cuenta_proveedores:
        raise ValueError(
            f"No se encontraron las cuentas contables necesarias para GASTO. "
            f"Configure: {MAPEO_CUENTAS['GASTO']['gastos']} (Gastos) y "
            f"{MAPEO_CUENTAS['GASTO']['proveedores']} (Costos por Pagar)."
        )
    
    # Movimiento 1: Debe a Gastos (Subtotal)
    movimientos.append({
        'asiento': asiento,
        'cuenta': cuenta_gastos,
        'debe': ds.subtotal,
        'haber': Decimal('0.00'),
        'descripcion': f"Gasto {ds.numero_documento} - {ds.vendedor_nombre}",
        'orden': orden
    })
    orden += 1
    
    # Movimiento 2: Debe a Retefuente (si aplica)
    if ds.retefuente > 0 and cuenta_retefuente:
        movimientos.append({
            'asiento': asiento,
            'cuenta': cuenta_retefuente,
            'debe': ds.retefuente,
            'haber': Decimal('0.00'),
            'descripcion': f"Retefuente - Gasto {ds.numero_documento}",
            'orden': orden
        })
        orden += 1
    
    # Movimiento 3: Debe a ReteICA (si aplica)
    if ds.reteica > 0 and cuenta_reteica:
        movimientos.append({
            'asiento': asiento,
            'cuenta': cuenta_reteica,
            'debe': ds.reteica,
            'haber': Decimal('0.00'),
            'descripcion': f"ReteICA - Gasto {ds.numero_documento}",
            'orden': orden
        })
        orden += 1
    
    # Movimiento 4: Haber a Proveedores (Total)
    movimientos.append({
        'asiento': asiento,
        'cuenta': cuenta_proveedores,
        'debe': Decimal('0.00'),
        'haber': ds.total,
        'descripcion': f"Gasto {ds.numero_documento} - {ds.vendedor_nombre}",
        'orden': orden
    })
    orden += 1
    
    # Crear movimientos
    for mov_data in movimientos:
        MovimientoContable.objects.create(**mov_data)
    
    # Recalcular totales del asiento
    asiento.refresh_from_db()
    
    logger.info(f"[asientos.service] Asiento {asiento.numero} materializado desde gasto {ds.numero_documento}")
    
    return {
        'id': asiento.id,
        'numero': asiento.numero,
        'fecha': asiento.fecha.isoformat() if asiento.fecha else None,
        'descripcion': asiento.descripcion,
        'estado': asiento.estado,
        'total_debe': str(asiento.total_debe),
        'total_haber': str(asiento.total_haber),
        'created_at': asiento.created_at.isoformat() if asiento.created_at else None,
    }