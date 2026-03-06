"""
Service Layer interno para MovimientoContable (dominio Contabilidad).

⚠️ v2.30: Service Layer Pattern - Lógica de negocio del dominio Contabilidad.
- Sin signals: Toda la lógica es explícita
- Sin HTTP: Funciones puras que operan sobre modelos
- Multi-tenant: Transparente (django-tenants maneja el aislamiento por esquema)
- Validaciones: Importes numéricos, vinculación a asiento válido
"""
from typing import Dict, Any, List, Optional
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Q
from decimal import Decimal


def list_movimientos(
    filters: Optional[Dict[str, Any]] = None,
    ordering: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
) -> Dict[str, Any]:
    """
    Lista movimientos contables (paginado).
    
    Args:
        filters: Diccionario con filtros (asiento, cuenta, search)
        ordering: Campo de ordenamiento (asiento, orden, debe, haber)
        page: Número de página (1-indexed)
        page_size: Tamaño de página
    
    Returns:
        dict: DTO con resultados paginados
    """
    from apps.tenant.contabilidad.models import MovimientoContable
    
    qs = MovimientoContable.objects.only(
        'id', 'asiento_id', 'cuenta_id', 'orden', 'debe', 'haber', 'descripcion'
    ).select_related('cuenta')
    
    # Aplicar filtros
    if filters:
        if 'asiento' in filters:
            qs = qs.filter(asiento_id=filters['asiento'])
        if 'cuenta' in filters:
            qs = qs.filter(cuenta_id=filters['cuenta'])
        if 'search' in filters:
            search = filters['search']
            qs = qs.filter(
                Q(descripcion__icontains=search) |
                Q(cuenta__nombre__icontains=search)
            )
    
    # Aplicar ordenamiento (whitelist)
    ordering_fields = [
        'asiento', 'orden', 'debe', 'haber',
        '-asiento', '-orden', '-debe', '-haber'
    ]
    if ordering and ordering in ordering_fields:
        qs = qs.order_by(ordering)
    else:
        qs = qs.order_by('asiento', 'orden')
    
    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)
    
    results = []
    for movimiento in page_obj:
        results.append({
            'id': movimiento.id,
            'asiento': movimiento.asiento_id,
            'cuenta': movimiento.cuenta_id,
            'cuenta_nombre': movimiento.cuenta.nombre if movimiento.cuenta else '',
            'cuenta_codigo': movimiento.cuenta.codigo if movimiento.cuenta else '',
            'orden': movimiento.orden,
            'debe': str(movimiento.debe),
            'haber': str(movimiento.haber),
            'descripcion': movimiento.descripcion or '',
        })
    
    return {
        'count': paginator.count,
        'next': page_obj.next_page_number() if page_obj.has_next() else None,
        'previous': page_obj.previous_page_number() if page_obj.has_previous() else None,
        'results': results,
    }


@transaction.atomic
def create_movimiento(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea un movimiento contable.
    
    ⚠️ VALIDACIONES: Importes numéricos, vinculación a asiento válido.
    ⚠️ REGLA: Un movimiento debe tener débito o crédito mayor a cero, pero no ambos.
    
    Args:
        data: Diccionario con datos del movimiento
    
    Returns:
        dict: DTO con datos del movimiento creado
    
    Raises:
        ValueError: Si los datos no son válidos
    """
    from apps.tenant.contabilidad.models import MovimientoContable, AsientoContable, CuentaContable
    
    # Validaciones
    if 'asiento' in data:
        asiento_id = data['asiento']
        if not AsientoContable.objects.filter(id=asiento_id).exists():
            raise ValueError(f"El asiento con ID {asiento_id} no existe.")
    
    if 'cuenta' in data:
        cuenta_id = data['cuenta']
        if not CuentaContable.objects.filter(id=cuenta_id).exists():
            raise ValueError(f"La cuenta con ID {cuenta_id} no existe.")
    
    debe = Decimal(str(data.get('debe', 0)))
    haber = Decimal(str(data.get('haber', 0)))
    
    # Validar que debe o haber sea mayor a 0, pero no ambos
    if debe > 0 and haber > 0:
        raise ValueError("Un movimiento no puede tener débito y crédito simultáneamente.")
    if debe == 0 and haber == 0:
        raise ValueError("Un movimiento debe tener débito o crédito mayor a cero.")
    
    movimiento = MovimientoContable.objects.create(**data)
    
    # Actualizar totales del asiento
    asiento = movimiento.asiento
    asiento.total_debe = sum(m.debe for m in asiento.movimientos.all())
    asiento.total_haber = sum(m.haber for m in asiento.movimientos.all())
    asiento.save(update_fields=['total_debe', 'total_haber'])
    
    return {
        'id': movimiento.id,
        'asiento': movimiento.asiento_id,
        'cuenta': movimiento.cuenta_id,
        'cuenta_nombre': movimiento.cuenta.nombre if movimiento.cuenta else '',
        'cuenta_codigo': movimiento.cuenta.codigo if movimiento.cuenta else '',
        'orden': movimiento.orden,
        'debe': str(movimiento.debe),
        'haber': str(movimiento.haber),
        'descripcion': movimiento.descripcion or '',
    }


@transaction.atomic
def update_movimiento(movimiento_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Actualiza un movimiento contable.
    
    ⚠️ VALIDACIONES: Importes numéricos, vinculación a asiento válido.
    
    Args:
        movimiento_id: ID del movimiento
        data: Diccionario con campos a actualizar
    
    Returns:
        dict: DTO con datos del movimiento actualizado
    
    Raises:
        ValueError: Si los datos no son válidos
        MovimientoContable.DoesNotExist: Si el movimiento no existe
    """
    from apps.tenant.contabilidad.models import MovimientoContable, AsientoContable, CuentaContable
    
    movimiento = MovimientoContable.objects.get(id=movimiento_id)
    
    # Validaciones (mismas que create)
    if 'asiento' in data:
        asiento_id = data['asiento']
        if not AsientoContable.objects.filter(id=asiento_id).exists():
            raise ValueError(f"El asiento con ID {asiento_id} no existe.")
    
    if 'cuenta' in data:
        cuenta_id = data['cuenta']
        if not CuentaContable.objects.filter(id=cuenta_id).exists():
            raise ValueError(f"La cuenta con ID {cuenta_id} no existe.")
    
    # Validar debe/haber si se actualizan
    if 'debe' in data or 'haber' in data:
        debe = Decimal(str(data.get('debe', movimiento.debe)))
        haber = Decimal(str(data.get('haber', movimiento.haber)))
        
        if debe > 0 and haber > 0:
            raise ValueError("Un movimiento no puede tener débito y crédito simultáneamente.")
        if debe == 0 and haber == 0:
            raise ValueError("Un movimiento debe tener débito o crédito mayor a cero.")
    
    campos_permitidos = ['asiento', 'cuenta', 'orden', 'debe', 'haber', 'descripcion']
    update_fields = []
    for campo in campos_permitidos:
        if campo in data:
            setattr(movimiento, campo, data[campo])
            update_fields.append(campo)
    
    if update_fields:
        movimiento.save(update_fields=update_fields)
        
        # Actualizar totales del asiento
        asiento = movimiento.asiento
        asiento.total_debe = sum(m.debe for m in asiento.movimientos.all())
        asiento.total_haber = sum(m.haber for m in asiento.movimientos.all())
        asiento.save(update_fields=['total_debe', 'total_haber'])
    
    return {
        'id': movimiento.id,
        'asiento': movimiento.asiento_id,
        'cuenta': movimiento.cuenta_id,
        'cuenta_nombre': movimiento.cuenta.nombre if movimiento.cuenta else '',
        'cuenta_codigo': movimiento.cuenta.codigo if movimiento.cuenta else '',
        'orden': movimiento.orden,
        'debe': str(movimiento.debe),
        'haber': str(movimiento.haber),
        'descripcion': movimiento.descripcion or '',
    }


@transaction.atomic
def delete_movimiento(movimiento_id: int) -> None:
    """
    Elimina un movimiento contable.
    
    ⚠️ IMPORTANTE: Al eliminar un movimiento, se actualizan los totales del asiento.
    
    Args:
        movimiento_id: ID del movimiento
    
    Raises:
        MovimientoContable.DoesNotExist: Si el movimiento no existe
    """
    from apps.tenant.contabilidad.models import MovimientoContable
    
    movimiento = MovimientoContable.objects.get(id=movimiento_id)
    asiento = movimiento.asiento
    movimiento.delete()
    
    # Actualizar totales del asiento
    asiento.total_debe = sum(m.debe for m in asiento.movimientos.all())
    asiento.total_haber = sum(m.haber for m in asiento.movimientos.all())
    asiento.save(update_fields=['total_debe', 'total_haber'])
