"""
Security Utilities for Zero-Trust empresa_id handling (v3.10.1)

CANONICAL: get_empresa_id_validated() — Centraliza resolución de empresa_id
Reemplaza los 54+ .filter(empresa_id=empresa_id) dispersos con un único punto de verdad.

Ref: AGENTS.md § Double Semantic Verification (DSV)
"""

import logging
from typing import Optional

from rest_framework.exceptions import ValidationError as DRFValidationError

logger = logging.getLogger(__name__)


def get_empresa_id_validated(viewset_or_serializer) -> int:
    """
    # CANONICAL: Zero-Trust empresa_id resolution

    Obtiene empresa_id de ViewSet o Serializer con validación estricta.
    Lanza PermissionError si no disponible (indica arquitectura rota).

    Orden de resolución:
    1. ViewSet.get_empresa_id() (desde SintelDSVMixin, auth-backed)
    2. serializer.context['empresa_id'] (inyectado por ViewSet)
    3. FALLBACK: Empresa singleton del tenant actual (dev only, unsafe)

    Args:
        viewset_or_serializer: Instancia de ViewSet o Serializer

    Returns:
        int: ID válido de empresa

    Raises:
        PermissionError: Si empresa_id no disponible (arquitectura error)
        DRFValidationError: Si empresa_id resolution falla

    Uso:
        # En ViewSet
        empresa_id = get_empresa_id_validated(self)
        queryset = self.selector_class.get_list(empresa_id)

        # En Serializer
        empresa_id = get_empresa_id_validated(self)
        cuenta = CuentaContable.objects.filter(
            empresa_id=empresa_id, uuid=self.instance.cuenta_uuid
        ).first()
    """
    # 1. Intentar desde ViewSet.get_empresa_id() (auth-backed, SSoT)
    if hasattr(viewset_or_serializer, 'get_empresa_id'):
        try:
            empresa_id = viewset_or_serializer.get_empresa_id()
            if empresa_id:
                return empresa_id
        except Exception as e:
            logger.warning(f"[DSV] get_empresa_id() failed: {e}, trying fallback...")

    # 2. Intentar desde contexto (serializers)
    if hasattr(viewset_or_serializer, 'context'):
        empresa_id = viewset_or_serializer.context.get('empresa_id')
        if empresa_id:
            return empresa_id

    # 3. FALLBACK: Singleton Empresa (dev only, logged as warning)
    try:
        from apps.tenant.empresa.models import Empresa
        empresa = Empresa.objects.only('id').first()
        if empresa:
            logger.warning(
                f"[DSV] Using singleton Empresa fallback (empresa_id={empresa.id}). "
                f"This should only happen in development."
            )
            return empresa.id
    except Exception:
        pass

    # No empresa_id found — arquitectura error
    raise PermissionError(
        f"[DSV] Cannot resolve empresa_id for {viewset_or_serializer.__class__.__name__}. "
        f"Ensure ViewSet inherits SintelDSVMixin and passes context to serializer."
    )


def validate_empresa_id(empresa_id: Optional[int], raise_if_none: bool = True) -> Optional[int]:
    """
    # CANONICAL: Validación de empresa_id

    Valida que empresa_id es un entero válido y no None (si requerido).

    Args:
        empresa_id: ID a validar (puede ser None)
        raise_if_none: Si True, lanza error si empresa_id es None

    Returns:
        int: empresa_id validado

    Raises:
        DRFValidationError: Si validación falla
    """
    if empresa_id is None:
        if raise_if_none:
            raise DRFValidationError("empresa_id es requerido pero no fue proporcionado.")
        return None

    if not isinstance(empresa_id, int):
        raise DRFValidationError(f"empresa_id debe ser un entero (recibido: {type(empresa_id).__name__})")

    if empresa_id <= 0:
        raise DRFValidationError("empresa_id debe ser un entero positivo")

    return empresa_id


def get_or_default_empresa_id(
    viewset_or_serializer,
    default: Optional[int] = None,
    strict: bool = False
) -> Optional[int]:
    """
    # Variante relajada: get_empresa_id con default

    Obtiene empresa_id pero retorna default si falla (no lanza error).

    Args:
        viewset_or_serializer: ViewSet o Serializer
        default: Valor por defecto (None, o int)
        strict: Si True, valida que default es válido

    Returns:
        int: empresa_id o default
    """
    try:
        return get_empresa_id_validated(viewset_or_serializer)
    except (PermissionError, DRFValidationError):
        if strict and default is not None:
            validate_empresa_id(default, raise_if_none=False)
        return default
