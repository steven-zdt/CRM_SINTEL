"""
Servicio de activación de owner (Core).

⚠️ POLÍTICA v2.61:
- Migrado desde Landing para centralización en Core API.
- Solo activación de owner (establecer contraseña inicial).
- Una sola activación por usuario (409 si ya tiene contraseña usable).
- No maneja login/logout (eso es CoreAuthViewSet).
"""
import logging
from typing import Dict, Any
from django.contrib.auth import get_user_model
from django.conf import settings
from django.http import HttpRequest
from django_tenants.utils import schema_context

from apps.public.tenants.models import Domain
from apps.public.tenants.services.invitations import verify_invitation_token

logger = logging.getLogger(__name__)

User = get_user_model()


class ActivationError(Exception):
    """Excepción base para errores de activación."""
    pass


class InvalidTokenError(ActivationError):
    """Token inválido o expirado."""
    pass


class UserNotFoundError(ActivationError):
    """Usuario no encontrado o inactivo."""
    pass


class TenantMismatchError(ActivationError):
    """El token no corresponde al tenant actual."""
    pass


class AlreadyActivatedError(ActivationError):
    """Usuario ya tiene contraseña usable (ya activado)."""
    pass


class ActivationService:
    """
    Servicio de activación de owner.
    Wrapper class para funciones de activación.
    """

    @staticmethod
    def verify_token(request: HttpRequest, token: str) -> Dict[str, Any]:
        """Verifica un token de activación."""
        return verify_activation_token(request, token)

    @staticmethod
    def activate(request: HttpRequest, token: str, password1: str, password2: str) -> Dict[str, Any]:
        """Procesa la activación del owner."""
        return process_activation(request, token, password1, password2)


def verify_activation_token(request: HttpRequest, token: str) -> Dict[str, Any]:
    """
    Verifica un token de activación y retorna información del usuario/tenant.
    
    Args:
        request: HttpRequest con tenant inyectado
        token: Token de activación
        
    Returns:
        Dict con:
            - status: 200 (válido) o 409 (ya activado)
            - user: datos del usuario
            - tenant: datos del tenant
            - token_valid: bool
            
    Raises:
        InvalidTokenError: Si el token es inválido o expirado
        UserNotFoundError: Si el usuario no existe
        TenantMismatchError: Si el token no corresponde al tenant
        AlreadyActivatedError: Si el usuario ya tiene contraseña usable
    """
    if not token:
        raise InvalidTokenError("Token de activación no proporcionado.")
    
    tenant = getattr(request, 'tenant', None)
    if not tenant:
        raise ValueError("No se pudo determinar el tenant actual.")
    
    # Verificar token
    payload = verify_invitation_token(token)
    
    if not payload:
        raise InvalidTokenError("Token de activación inválido o expirado. Solicita una nueva invitación.")
    
    # Obtener usuario
    try:
        user = User.objects.get(pk=payload['user_id'], is_active=True)
    except User.DoesNotExist:
        raise UserNotFoundError("Usuario no encontrado o inactivo.")
    
    # Verificar que el token corresponde al tenant
    if not tenant or tenant.id != payload['tenant_id']:
        raise TenantMismatchError("El token no corresponde al tenant actual.")
    
    # ⚠️ v2.30: Retornar 409 si ya tiene contraseña usable
    if user.has_usable_password():
        raise AlreadyActivatedError("Cuenta ya activada. Inicia sesión.")
    
    # Token válido y usuario sin contraseña usable
    return {
        'status': 200,
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.get_full_name() or user.email,
            'has_usable_password': False,
        },
        'tenant': {
            'id': tenant.id,
            'nombre': tenant.nombre,
            'schema_name': tenant.schema_name,
        },
        'token_valid': True,
    }


def process_activation(request: HttpRequest, token: str, password1: str, password2: str) -> Dict[str, Any]:
    """
    Procesa la activación del owner (establece contraseña).
    
    Args:
        request: HttpRequest con tenant inyectado
        token: Token de activación
        password1: Nueva contraseña
        password2: Confirmación de contraseña
        
    Returns:
        Dict con:
            - detail: mensaje de éxito
            - redirect_url: URL absoluta de redirección
            - user: datos del usuario
            - tenant: datos del tenant
            
    Raises:
        InvalidTokenError: Si el token es inválido
        UserNotFoundError: Si el usuario no existe
        TenantMismatchError: Si el token no corresponde al tenant
        AlreadyActivatedError: Si el usuario ya tiene contraseña usable
        ValueError: Si las contraseñas no coinciden o no cumplen requisitos
    """
    if not token:
        raise InvalidTokenError("Token de activación no proporcionado.")
    
    if not password1 or not password2:
        raise ValueError("Ambas contraseñas son requeridas.")
    
    if password1 != password2:
        raise ValueError("Las contraseñas no coinciden.")
    
    if len(password1) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres.")
    
    tenant = getattr(request, 'tenant', None)
    if not tenant:
        raise ValueError("No se pudo determinar el tenant actual.")
    
    # Verificar token primero
    verify_result = verify_activation_token(request, token)
    
    # Si llegamos aquí, el token es válido y el usuario no tiene contraseña usable
    user = User.objects.get(pk=verify_result['user']['id'], is_active=True)
    
    # Establecer contraseña. NO se usa emojis ni caracteres especiales en código (AGENTS.md)
    user.set_password(password1)
    user.save(update_fields=['password'])
    
    # Verificar que el password quedó usable
    user.refresh_from_db()
    if not user.has_usable_password():
        logger.error(
            "ActivationService.process_activation: Password NO usable despues de set_password: user=%s, tenant=%s",
            user.email, tenant.schema_name
        )
        raise ValueError("Error al establecer la contraseña. Por favor, intenta nuevamente.")
    
    logger.info(
        "ActivationService.process_activation: Activacion exitosa - password usable confirmado: user=%s, tenant=%s",
        user.email, tenant.schema_name
    )
    
    # ⚠️ v2.40: NO loguear automáticamente después de activación
    
    # Obtener dominio para construir URL de login
    with schema_context('public'):
        domain = Domain.objects.filter(tenant=tenant, is_primary=True).first()
    
    if not domain:
        raise ValueError("Error critico: tenant sin dominio primario. Contacta al administrador.")
    
    # Redirigir al login después de activar la cuenta
    protocol = 'https' if getattr(settings, 'SECURE_SSL_REDIRECT', False) else 'http'
    # Intentar incluir puerto si estamos en DEBUG
    app_port = getattr(settings, 'APP_PORT', None)
    if settings.DEBUG and app_port and str(app_port) not in ('80', '443'):
        domain_with_port = f"{domain.domain}:{app_port}"
    else:
        domain_with_port = domain.domain
        
    redirect_url = f"{protocol}://{domain_with_port}/static/tenant/core/auth/login.html"
    
    return {
        'detail': f"Bienvenido a {tenant.nombre}! Tu cuenta ha sido activada.",
        'redirect_url': redirect_url,
        'user': {
            'id': user.id,
            'email': user.email,
        },
        'tenant': {
            'id': tenant.id,
            'nombre': tenant.nombre,
        },
    }
