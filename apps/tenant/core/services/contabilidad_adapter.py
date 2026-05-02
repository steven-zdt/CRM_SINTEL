"""
Core Service Adapter para Contabilidad.

# WARNING: v2.30: Core API como orquestador único de la UI privada.
- Este adapter consume el Service Layer del dominio Contabilidad (apps/tenant/contabilidad/services)
- Compone el DTO final estandarizando respuestas
- NO reimplementa lógica del dominio; solo orquesta y compone respuestas

Uso:
    from apps.tenant.core.services.contabilidad_adapter import (
        core_cuentas_list,
        core_cuentas_create,
        core_cuentas_update,
        core_cuentas_delete,
        core_asientos_list,
        core_asientos_create,
        core_asientos_update,
        core_asientos_delete,
        core_asientos_aprobar,
        core_movimientos_list,
        core_movimientos_create,
        core_movimientos_update,
        core_movimientos_delete,
    )
"""
from typing import Any

# ============================================================================
# CUENTAS CONTABLES
# ============================================================================

def core_cuentas_list(
    filters: dict[str, Any] | None = None,
    ordering: str | None = None,
    page: int = 1,
    page_size: int = 20
) -> dict[str, Any]:
    """
    Lista cuentas contables (paginado).
    
    # WARNING: v2.30: Core API - Delega 1:1 al Service Layer del dominio.
    
    Args:
        filters: Diccionario con filtros
        ordering: Campo de ordenamiento
        page: Número de página (1-indexed)
        page_size: Tamaño de página
    
    Returns:
        dict: DTO con resultados paginados
    """
    from apps.tenant.contabilidad.services.cuentas_service import list_cuentas
    
    return list_cuentas(filters=filters, ordering=ordering, page=page, page_size=page_size)


def core_cuentas_create(data: dict[str, Any]) -> dict[str, Any]:
    """
    Crea una cuenta contable.
    
    # WARNING: v2.30: Core API - Delega 1:1 al Service Layer del dominio.
    
    Args:
        data: Diccionario con datos de la cuenta
    
    Returns:
        dict: DTO con datos de la cuenta creada
    
    Raises:
        ValueError: Si los datos no son válidos (propagado desde el Service Layer)
    """
    from apps.tenant.contabilidad.services.cuentas_service import create_cuenta
    
    return create_cuenta(data)


def core_cuentas_update(cuenta_id: int, data: dict[str, Any]) -> dict[str, Any]:
    """
    Actualiza una cuenta contable.
    
    # WARNING: v2.30: Core API - Delega 1:1 al Service Layer del dominio.
    
    Args:
        cuenta_id: ID de la cuenta
        data: Diccionario con campos a actualizar
    
    Returns:
        dict: DTO con datos de la cuenta actualizada
    
    Raises:
        ValueError: Si los datos no son válidos (propagado desde el Service Layer)
    """
    from apps.tenant.contabilidad.services.cuentas_service import update_cuenta
    
    return update_cuenta(cuenta_id, data)


def core_cuentas_delete(cuenta_id: int) -> None:
    """
    Elimina una cuenta contable.
    
    # WARNING: v2.30: Core API - Delega 1:1 al Service Layer del dominio.
    
    Args:
        cuenta_id: ID de la cuenta
    
    Raises:
        CuentaContable.DoesNotExist: Si la cuenta no existe
    """
    from apps.tenant.contabilidad.services.cuentas_service import delete_cuenta
    
    delete_cuenta(cuenta_id)


# ============================================================================
# ASIENTOS CONTABLES
# ============================================================================

def core_asientos_list(
    filters: dict[str, Any] | None = None,
    ordering: str | None = None,
    page: int = 1,
    page_size: int = 20
) -> dict[str, Any]:
    """
    Lista asientos contables (paginado).
    
    # WARNING: v2.30: Core API - Delega 1:1 al Service Layer del dominio.
    
    Args:
        filters: Diccionario con filtros
        ordering: Campo de ordenamiento
        page: Número de página (1-indexed)
        page_size: Tamaño de página
    
    Returns:
        dict: DTO con resultados paginados
    """
    from apps.tenant.contabilidad.services.asientos_service import list_asientos
    
    return list_asientos(filters=filters, ordering=ordering, page=page, page_size=page_size)


def core_asientos_create(data: dict[str, Any]) -> dict[str, Any]:
    """
    Crea un asiento contable.
    
    # WARNING: v2.30: Core API - Delega 1:1 al Service Layer del dominio.
    
    Args:
        data: Diccionario con datos del asiento
    
    Returns:
        dict: DTO con datos del asiento creado
    
    Raises:
        ValueError: Si los datos no son válidos (propagado desde el Service Layer)
    """
    from apps.tenant.contabilidad.services.asientos_service import create_asiento
    
    return create_asiento(data)


def core_asientos_update(asiento_id: int, data: dict[str, Any]) -> dict[str, Any]:
    """
    Actualiza un asiento contable.
    
    # WARNING: v2.30: Core API - Delega 1:1 al Service Layer del dominio.
    
    Args:
        asiento_id: ID del asiento
        data: Diccionario con campos a actualizar
    
    Returns:
        dict: DTO con datos del asiento actualizado
    
    Raises:
        ValueError: Si los datos no son válidos (propagado desde el Service Layer)
    """
    from apps.tenant.contabilidad.services.asientos_service import update_asiento
    
    return update_asiento(asiento_id, data)


def core_asientos_delete(asiento_id: int) -> None:
    """
    Elimina un asiento contable.
    
    # WARNING: v2.30: Core API - Delega 1:1 al Service Layer del dominio.
    
    Args:
        asiento_id: ID del asiento
    
    Raises:
        AsientoContable.DoesNotExist: Si el asiento no existe
    """
    from apps.tenant.contabilidad.services.asientos_service import delete_asiento
    
    delete_asiento(asiento_id)


def core_asientos_aprobar(asiento_id: int) -> dict[str, Any]:
    """
    Aprueba un asiento contable.
    
    # WARNING: v2.30: Core API - Delega 1:1 al Service Layer del dominio.
    # WARNING: VALIDACIÓN: Un asiento solo puede ser aprobado si total_debe == total_haber.
    
    Args:
        asiento_id: ID del asiento
    
    Returns:
        dict: DTO con datos del asiento aprobado
    
    Raises:
        ValueError: Si el asiento no puede ser aprobado (debe != haber)
    """
    from apps.tenant.contabilidad.services.asientos_service import aprobar_asiento
    
    return aprobar_asiento(asiento_id)


# ============================================================================
# MOVIMIENTOS CONTABLES
# ============================================================================

def core_movimientos_list(
    filters: dict[str, Any] | None = None,
    ordering: str | None = None,
    page: int = 1,
    page_size: int = 20
) -> dict[str, Any]:
    """
    Lista movimientos contables (paginado).
    
    # WARNING: v2.30: Core API - Delega 1:1 al Service Layer del dominio.
    
    Args:
        filters: Diccionario con filtros
        ordering: Campo de ordenamiento
        page: Número de página (1-indexed)
        page_size: Tamaño de página
    
    Returns:
        dict: DTO con resultados paginados
    """
    from apps.tenant.contabilidad.services.movimientos_service import list_movimientos
    
    return list_movimientos(filters=filters, ordering=ordering, page=page, page_size=page_size)


def core_movimientos_create(data: dict[str, Any]) -> dict[str, Any]:
    """
    Crea un movimiento contable.
    
    # WARNING: v2.30: Core API - Delega 1:1 al Service Layer del dominio.
    
    Args:
        data: Diccionario con datos del movimiento
    
    Returns:
        dict: DTO con datos del movimiento creado
    
    Raises:
        ValueError: Si los datos no son válidos (propagado desde el Service Layer)
    """
    from apps.tenant.contabilidad.services.movimientos_service import create_movimiento
    
    return create_movimiento(data)


def core_movimientos_update(movimiento_id: int, data: dict[str, Any]) -> dict[str, Any]:
    """
    Actualiza un movimiento contable.
    
    # WARNING: v2.30: Core API - Delega 1:1 al Service Layer del dominio.
    
    Args:
        movimiento_id: ID del movimiento
        data: Diccionario con campos a actualizar
    
    Returns:
        dict: DTO con datos del movimiento actualizado
    
    Raises:
        ValueError: Si los datos no son válidos (propagado desde el Service Layer)
    """
    from apps.tenant.contabilidad.services.movimientos_service import update_movimiento
    
    return update_movimiento(movimiento_id, data)


def core_movimientos_delete(movimiento_id: int) -> None:
    """
    Elimina un movimiento contable.
    
    # WARNING: v2.30: Core API - Delega 1:1 al Service Layer del dominio.
    
    Args:
        movimiento_id: ID del movimiento
    
    Raises:
        MovimientoContable.DoesNotExist: Si el movimiento no existe
    """
    from apps.tenant.contabilidad.services.movimientos_service import delete_movimiento
    
    delete_movimiento(movimiento_id)
