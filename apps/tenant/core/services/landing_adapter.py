"""
Adaptador Core para servicios de Landing (v2.30).

⚠️ POLÍTICA v2.30:
- Core orquesta servicios de Landing para exponer UI única
- Consume apps/tenant/landing/services/* directamente
- Mantiene separación de responsabilidades: Landing = dominio, Core = orquestación/UI
"""
import logging
from typing import Dict, Any
from django.http import HttpRequest

from apps.tenant.landing.services.landing_info_service import get_public_info
from apps.tenant.landing.services.activation_service import (
    verify_activation_token,
    process_activation,
    InvalidTokenError,
    UserNotFoundError,
    TenantMismatchError,
    AlreadyActivatedError,
)

logger = logging.getLogger(__name__)


def get_public_info_from_landing(request: HttpRequest) -> Dict[str, Any]:
    """
    Obtiene información pública del tenant desde Landing service.
    
    Args:
        request: HttpRequest con tenant inyectado
        
    Returns:
        Dict con tenant y request (para serialización)
        
    Raises:
        ValueError: Si no se puede determinar el tenant
    """
    try:
        return get_public_info(request)
    except ValueError as e:
        logger.error(
            "LandingAdapter.get_public_info_from_landing: Error: %s",
            str(e)
        )
        raise
    except Exception as e:
        logger.error(
            "LandingAdapter.get_public_info_from_landing: Error inesperado: %s",
            str(e),
            exc_info=True
        )
        raise ValueError("Error interno al obtener información del tenant.")


def verify_activation_via_landing(request: HttpRequest, token: str) -> Dict[str, Any]:
    """
    Verifica token de activación desde Landing service.
    
    Args:
        request: HttpRequest con tenant inyectado
        token: Token de activación
        
    Returns:
        Dict con información del usuario/tenant y token_valid
        
    Raises:
        InvalidTokenError: Si el token es inválido
        UserNotFoundError: Si el usuario no existe
        TenantMismatchError: Si el token no corresponde al tenant
        AlreadyActivatedError: Si el usuario ya tiene contraseña usable
    """
    try:
        return verify_activation_token(request, token)
    except (InvalidTokenError, UserNotFoundError, TenantMismatchError, AlreadyActivatedError) as e:
        logger.warning(
            "LandingAdapter.verify_activation_via_landing: Error de validación: %s",
            str(e)
        )
        raise
    except Exception as e:
        logger.error(
            "LandingAdapter.verify_activation_via_landing: Error inesperado: %s",
            str(e),
            exc_info=True
        )
        raise InvalidTokenError("Error interno al validar el token de activación.")


def process_activation_via_landing(request: HttpRequest, token: str, password1: str, password2: str) -> Dict[str, Any]:
    """
    Procesa activación desde Landing service.
    
    Args:
        request: HttpRequest con tenant inyectado
        token: Token de activación
        password1: Nueva contraseña
        password2: Confirmación de contraseña
        
    Returns:
        Dict con detail, redirect_url, user y tenant
        
    Raises:
        InvalidTokenError: Si el token es inválido
        UserNotFoundError: Si el usuario no existe
        TenantMismatchError: Si el token no corresponde al tenant
        AlreadyActivatedError: Si el usuario ya tiene contraseña usable
        ValueError: Si las contraseñas no coinciden o no cumplen requisitos
    """
    try:
        return process_activation(request, token, password1, password2)
    except (InvalidTokenError, UserNotFoundError, TenantMismatchError, AlreadyActivatedError, ValueError) as e:
        logger.warning(
            "LandingAdapter.process_activation_via_landing: Error de procesamiento: %s",
            str(e)
        )
        raise
    except Exception as e:
        logger.error(
            "LandingAdapter.process_activation_via_landing: Error inesperado: %s",
            str(e),
            exc_info=True
        )
        raise ValueError("Error interno al procesar la activación.")
