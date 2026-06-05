"""
Service Layer DTOs (Data Transfer Objects) — Response Envelopes v3.10.1

CANONICAL: ServiceResponse — Respuesta unificada para todos los servicios.
Elimina inconsistencia de retorno entre gastos, inventario, clientes, etc.

Uso:
    # BEFORE (inconsistent):
    return True, {"gasto": data}, 201
    return (gasto, None, 200)
    return CustomResponse(success=True, data=...)

    # AFTER (canonical):
    return ServiceResponse(success=True, data={"gasto": data}, status_code=201)
    return ServiceResponse(success=False, errors=["invalid_amount"], status_code=422)
"""

from typing import Any, Dict, List, Optional, NamedTuple


class ServiceResponse(NamedTuple):
    """
    Respuesta estándar de todos los servicios (business_service.py).

    Attributes:
        success: True si operación fue exitosa, False si falló
        data: Dict con datos retornados (None si error)
        status_code: HTTP status code (200, 201, 400, 422, 500, etc.)
        errors: List de mensajes de error (None si success=True)
        message: Mensaje descriptivo adicional (opcional)
    """
    success: bool
    data: Optional[Dict[str, Any]] = None
    status_code: int = 200
    errors: Optional[List[str]] = None
    message: Optional[str] = None

    @staticmethod
    def ok(data: Dict[str, Any], status_code: int = 200) -> "ServiceResponse":
        """Respuesta exitosa."""
        return ServiceResponse(success=True, data=data, status_code=status_code)

    @staticmethod
    def created(data: Dict[str, Any]) -> "ServiceResponse":
        """Creación exitosa (201)."""
        return ServiceResponse(success=True, data=data, status_code=201)

    @staticmethod
    def error(
        errors: List[str],
        status_code: int = 422,
        message: Optional[str] = None
    ) -> "ServiceResponse":
        """Error en validación o negocio."""
        return ServiceResponse(
            success=False,
            errors=errors,
            status_code=status_code,
            message=message
        )

    @staticmethod
    def validation_error(errors: List[str], message: Optional[str] = None) -> "ServiceResponse":
        """Error de validación (422)."""
        return ServiceResponse.error(errors, status_code=422, message=message)

    @staticmethod
    def not_found(message: str = "Recurso no encontrado") -> "ServiceResponse":
        """Recurso no encontrado (404)."""
        return ServiceResponse(
            success=False,
            errors=[message],
            status_code=404,
            message=message
        )

    @staticmethod
    def server_error(message: str = "Error interno del servidor") -> "ServiceResponse":
        """Error del servidor (500)."""
        return ServiceResponse(
            success=False,
            errors=[message],
            status_code=500,
            message=message
        )


class CreateResponse(NamedTuple):
    """Response específico para operaciones CREATE (legacy, usar ServiceResponse.created())."""
    instance: Any
    message: Optional[str] = None
    status_code: int = 201


class UpdateResponse(NamedTuple):
    """Response específico para operaciones UPDATE (legacy, usar ServiceResponse.ok())."""
    instance: Any
    message: Optional[str] = None
    status_code: int = 200


class DeleteResponse(NamedTuple):
    """Response específico para operaciones DELETE."""
    success: bool
    message: Optional[str] = None
    status_code: int = 204
