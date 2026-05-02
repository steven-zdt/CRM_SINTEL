"""
Servicios de autenticación centralizados en Core (v2.30).

# WARNING: POLÍTICA v2.30:
- Todos los flujos de auth (login, logout, password-reset) están centralizados en Core
- Trabajan con User global (esquema public) pero ejecutan bajo tenant hostname
- No renderizan HTML; lanzan excepciones tipadas
- Retornan redirect_url absoluta para que la UI pueda redirigir
"""
import logging
from typing import Any

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, logout
from django.db import connection
from django_tenants.utils import schema_context

from apps.public.tenants.models import Domain, TenantMembership

logger = logging.getLogger(__name__)

User = get_user_model()


class AuthError(Exception):
    """Excepción base para errores de autenticación."""
    pass


class InvalidCredentialsError(AuthError):
    """Credenciales inválidas."""
    pass


class NoMembershipError(AuthError):
    """Usuario sin membresía activa en el tenant."""
    pass


class TenantNotFoundError(AuthError):
    """No se pudo determinar el tenant."""
    pass


def login_user(tenant, identifier: str, password: str) -> dict[str, Any]:
    """
    Autentica y loguea un usuario en el tenant.
    
    Args:
        tenant: Instancia del tenant (Client)
        identifier: Email o username del usuario
        password: Contraseña del usuario
        
    Returns:
        Dict con user y redirect_url (absoluta)
        
    Raises:
        InvalidCredentialsError: Si las credenciales son inválidas
        NoMembershipError: Si el usuario no tiene membresía activa
        TenantNotFoundError: Si no se puede determinar el tenant
    """
    if not tenant:
        raise TenantNotFoundError("No se pudo determinar el tenant actual.")
    
    if not identifier or not password:
        raise InvalidCredentialsError("Email/username y contraseña son requeridos.")
    
    # Normalizar identifier
    identifier = identifier.lower().strip() if identifier else None
    
    current_schema = connection.schema_name
    try:
        connection.set_schema_to_public()
        
        # Intentar autenticar directamente con email
        user = authenticate(username=identifier, password=password)
        
        # Si falla, intentar buscar usuario por email y autenticar con username
        if not user:
            try:
                user_by_email = User.objects.get(email=identifier, is_active=True)
                # Intentar autenticar con el username real del usuario
                user = authenticate(username=user_by_email.username, password=password)
            except User.DoesNotExist:
                pass
        
        if not user:
            raise InvalidCredentialsError("Nombre de usuario o contraseña incorrectos.")
        
        # Verificar membresía en tenant
        membership = TenantMembership.objects.filter(
            client=tenant,
            user=user,
            is_active=True,
        ).first()
        
        if not membership:
            raise NoMembershipError("Tu cuenta existe, pero no tienes acceso a esta empresa.")
        
        # Verificar que el tenant esté activo
        if not tenant.is_active:
            raise NoMembershipError("Esta empresa está inactiva. Por favor, contacta al administrador.")
        
        # Construir redirect_url absoluta
        redirect_url = build_login_redirect(tenant, user, absolute=True)
        
        return {
            'user': user,
            'redirect_url': redirect_url,
        }
        
    finally:
        connection.set_schema(current_schema)


def logout_user(tenant, request) -> dict[str, Any]:
    """
    Cierra la sesión del usuario.
    
    Args:
        tenant: Instancia del tenant (Client)
        request: HttpRequest con la sesión activa
        
    Returns:
        Dict con redirect_url (absoluta)
        
    Raises:
        TenantNotFoundError: Si no se puede determinar el tenant
    """
    if not tenant:
        raise TenantNotFoundError("No se pudo determinar el tenant actual.")
    
    logout(request)
    logger.info(
        "AuthService.logout_user: Sesión cerrada para tenant=%s",
        tenant.schema_name
    )
    
    # Construir redirect_url absoluta
    redirect_url = build_logout_redirect(tenant, absolute=True)
    
    return {
        'redirect_url': redirect_url,
    }


def build_login_redirect(tenant, user, absolute: bool = False) -> str:
    """
    Construye la URL de redirección después del login.
    
    # WARNING: POLÍTICA v2.30: Todos los usuarios se redirigen al workspace orquestado por Core.
    El workspace consume Core API para mostrar datos del dashboard y otras apps.
    
    Args:
        tenant: Instancia del tenant (Client)
        user: Usuario autenticado
        absolute: Si True, retorna URL absoluta (con protocolo y dominio)
        
    Returns:
        URL de redirección al workspace (relativa o absoluta según absolute)
    """
    # # WARNING: v2.30: Redirigir siempre al workspace (Core orquesta todo)
    # El workspace consume Core API para mostrar datos del dashboard y otras apps
    relative_url = "/workspace/"
    
    if not absolute:
        return relative_url
    
    # Construir URL absoluta
    try:
        with schema_context('public'):
            domain = Domain.objects.filter(tenant=tenant, is_primary=True).first()
        
        if domain:
            protocol = 'https' if getattr(settings, 'SECURE_SSL_REDIRECT', False) else 'http'
            # # WARNING: v2.30: Incluir puerto en DEV si APP_PORT está configurado
            app_port = getattr(settings, 'APP_PORT', None)
            if settings.DEBUG and app_port and str(app_port) not in ('80', '443'):
                domain_with_port = f"{domain.domain}:{app_port}"
            else:
                domain_with_port = domain.domain
            return f"{protocol}://{domain_with_port}{relative_url}"
    except Exception as e:
        logger.warning(
            "AuthService.build_login_redirect: Error construyendo URL absoluta: %s",
            str(e)
        )
    
    # Fallback: retornar ruta relativa
    return relative_url


def build_logout_redirect(tenant, absolute: bool = False) -> str:
    """
    Construye la URL de redirección después del logout.
    
    Args:
        tenant: Instancia del tenant (Client)
        absolute: Si True, retorna URL absoluta (con protocolo y dominio)
        
    Returns:
        URL de redirección (relativa o absoluta según absolute)
    """
    if absolute:
        with schema_context('public'):
            domain = Domain.objects.filter(tenant=tenant, is_primary=True).first()
        
        if domain:
            protocol = 'https' if getattr(settings, 'SECURE_SSL_REDIRECT', False) else 'http'
            # # WARNING: v2.30: Incluir puerto en DEV si APP_PORT está configurado
            app_port = getattr(settings, 'APP_PORT', None)
            if settings.DEBUG and app_port and str(app_port) not in ('80', '443'):
                domain_with_port = f"{domain.domain}:{app_port}"
            else:
                domain_with_port = domain.domain
            return f"{protocol}://{domain_with_port}/"
    
    return "/"


def password_reset_request(email_or_username: str, tenant) -> dict[str, Any]:
    """
    Solicita reset de contraseña para un usuario.
    
    Args:
        email_or_username: Email o username del usuario
        tenant: Instancia del tenant (Client)
        
    Returns:
        Dict con respuesta genérica (idempotente)
        
    Raises:
        TenantNotFoundError: Si no se puede determinar el tenant
        UserNotFoundError: Si el usuario no tiene activación pendiente
    """
    from apps.tenant.core.services.password_reset import (
        TenantNotFoundError,
        UserNotFoundError,
        request_reset,
    )
    
    try:
        request_reset(email_or_username, tenant)
        # Idempotente: siempre retornar 200
        return {
            "detail": "Si el email existe y tiene acceso a este tenant, recibirás un correo con instrucciones."
        }
    except TenantNotFoundError as e:
        logger.error(
            "AuthService.password_reset_request: Error de tenant: %s",
            str(e)
        )
        raise
    except UserNotFoundError as e:
        # Para activación pendiente, retornar error específico
        logger.warning(
            "AuthService.password_reset_request: Usuario sin activacion: %s",
            str(e)
        )
        raise
    except Exception as e:
        logger.error(
            "AuthService.password_reset_request: Error inesperado: %s",
            str(e),
            exc_info=True
        )
        # Idempotente: retornar respuesta genérica
        return {
            "detail": "Si el email existe y tiene acceso a este tenant, recibirás un correo con instrucciones."
        }


def password_reset_validate(uid: str, token: str, tenant) -> dict[str, Any]:
    """
    Valida un token de reset de contraseña.
    
    Args:
        uid: User ID codificado en base64 URL-safe
        token: Token de reset
        tenant: Instancia del tenant (Client)
        
    Returns:
        Dict con valid, email, etc.
        
    Raises:
        InvalidTokenError: Si el token es inválido o expirado
        TenantNotFoundError: Si no se puede determinar el tenant
    """
    from apps.tenant.core.services.password_reset import (
        InvalidTokenError,
        TenantNotFoundError,
        validate_token,
    )
    
    try:
        result = validate_token(uid, token, tenant)
        return result
    except InvalidTokenError:
        logger.warning(
            "AuthService.password_reset_validate: Token invalido: tenant=%s",
            tenant.schema_name if tenant else 'none'
        )
        raise
    except TenantNotFoundError as e:
        logger.error(
            "AuthService.password_reset_validate: Error de tenant: %s",
            str(e)
        )
        raise
    except Exception as e:
        logger.error(
            "AuthService.password_reset_validate: Error inesperado: %s",
            str(e),
            exc_info=True
        )
        raise InvalidTokenError("Token de reset invalido o expirado.")


def password_reset_confirm(uid: str, token: str, new_password: str, tenant) -> dict[str, Any]:
    """
    Confirma el reset de contraseña y establece la nueva contraseña.
    
    Args:
        uid: User ID codificado en base64 URL-safe
        token: Token de reset
        new_password: Nueva contraseña
        tenant: Instancia del tenant (Client)
        
    Returns:
        Dict con detail y redirect_url (absoluta)
        
    Raises:
        InvalidTokenError: Si el token es inválido o expirado
        TenantNotFoundError: Si no se puede determinar el tenant
        ValueError: Si la contraseña no cumple requisitos
    """
    from apps.tenant.core.services.password_reset import (
        InvalidTokenError,
        TenantNotFoundError,
        confirm_reset,
    )
    
    try:
        # confirm_reset retorna el usuario
        user = confirm_reset(uid, token, new_password, tenant)
        redirect_url = build_password_reset_confirm_redirect(tenant, user, absolute=True)
        return {
            "detail": "Tu contraseña ha sido restablecida exitosamente. Por favor, inicia sesión.",
            "redirect_url": redirect_url
        }
    except InvalidTokenError:
        logger.warning(
            "AuthService.password_reset_confirm: Token invalido: tenant=%s",
            tenant.schema_name if tenant else 'none'
        )
        raise
    except TenantNotFoundError as e:
        logger.error(
            "AuthService.password_reset_confirm: Error de tenant: %s",
            str(e)
        )
        raise
    except ValueError as e:
        logger.warning(
            "AuthService.password_reset_confirm: Error de validacion: %s",
            str(e)
        )
        raise
    except Exception as e:
        logger.error(
            "AuthService.password_reset_confirm: Error inesperado: %s",
            str(e),
            exc_info=True
        )
        raise ValueError("Error al establecer la nueva contraseña. Por favor, intenta nuevamente.")


def build_password_reset_confirm_redirect(tenant, user, absolute: bool = False) -> str:
    """
    Construye la URL de redireccion despues de confirmar el reset de contrasena.
    
    Args:
        tenant: Instancia del tenant (Client)
        user: Usuario que confirmo el reset
        absolute: Si True, retorna URL absoluta (con protocolo y dominio)
        
    Returns:
        URL de redireccion (relativa o absoluta segun absolute)
    """
    # Despues de reset, redirigir a la landing para que el usuario pueda iniciar sesion
    if absolute:
        with schema_context('public'):
            domain = Domain.objects.filter(tenant=tenant, is_primary=True).first()
        
        if domain:
            protocol = 'https' if getattr(settings, 'SECURE_SSL_REDIRECT', False) else 'http'
            # # WARNING: v2.30: Incluir puerto en DEV si APP_PORT esta configurado
            app_port = getattr(settings, 'APP_PORT', None)
            if settings.DEBUG and app_port and str(app_port) not in ('80', '443'):
                domain_with_port = f"{domain.domain}:{app_port}"
            else:
                domain_with_port = domain.domain
            return f"{protocol}://{domain_with_port}/"
    
    return "/"


class AuthService:
    """
    Servicio de autenticacion centralizado.
    Wrapper class para funciones de auth.
    """

    @staticmethod
    def login(tenant, identifier, password):
        """Autentica y loguea un usuario."""
        return login_user(tenant, identifier, password)

    @staticmethod
    def logout(tenant, request):
        """Cierra sesion de un usuario."""
        return logout_user(tenant, request)

    @staticmethod
    def request_password_reset(email_or_username, tenant):
        """Solicita reset de contrasena."""
        return password_reset_request(email_or_username, tenant)

    @staticmethod
    def validate_password_reset(uid, token, tenant):
        """Valida token de reset de contrasena."""
        return password_reset_validate(uid, token, tenant)

    @staticmethod
    def confirm_password_reset(uid, token, new_password, tenant):
        """Confirma reset de contrasena."""
        return password_reset_confirm(uid, token, new_password, tenant)
