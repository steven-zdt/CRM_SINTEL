"""
Servicio de dominio para reset de contraseña (Core).

⚠️ POLÍTICA v2.61:
- Migrado desde Landing para centralización en Core API.
- Trabaja con User global (esquema public).
- No renderiza HTML.
- Lanza excepciones tipadas para tokens inválidos/expirados.
"""
import logging
from typing import Optional, Dict, Any
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str, force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.db import connection
from django_tenants.utils import schema_context
from django.conf import settings

from apps.public.tenants.models import TenantMembership, Domain

logger = logging.getLogger(__name__)

User = get_user_model()


class PasswordResetError(Exception):
    """Excepción base para errores de reset de contraseña."""
    pass


class InvalidTokenError(PasswordResetError):
    """Token inválido o expirado."""
    pass


class UserNotFoundError(PasswordResetError):
    """Usuario no encontrado o sin membresía activa."""
    pass


class TenantNotFoundError(PasswordResetError):
    """No se pudo determinar el tenant."""
    pass


def request_reset(email_or_username: str, tenant) -> None:
    """
    Solicita reset de contraseña para un usuario.
    
    Args:
        email_or_username: Email o username del usuario
        tenant: Instancia del tenant (Client)
        
    Raises:
        UserNotFoundError: Si el usuario no existe o no tiene membresía activa
        TenantNotFoundError: Si no se puede determinar el tenant
        
    Returns:
        None (envía email si todo es válido)
    """
    if not tenant:
        raise TenantNotFoundError("No se pudo determinar el tenant.")
    
    # Normalizar email/username
    email_or_username = email_or_username.lower().strip() if email_or_username else None
    
    if not email_or_username:
        raise UserNotFoundError("Email o username requerido.")
    
    current_schema = connection.schema_name
    try:
        connection.set_schema_to_public()
        
        # Buscar usuario
        logger.info(
            "PasswordResetService.request_reset: Buscando usuario - email=%s, tenant=%s",
            email_or_username, tenant.schema_name
        )
        try:
            user = User.objects.get(email=email_or_username, is_active=True)
        except User.DoesNotExist:
            # Idempotente: no revelar si el usuario existe
            logger.warning(
                "PasswordResetService.request_reset: Usuario no encontrado (idempotente): email=%s, tenant=%s",
                email_or_username, tenant.schema_name
            )
            return
        
        # Verificar membresía en tenant
        membership = TenantMembership.objects.filter(
            client=tenant,
            user=user,
            is_active=True,
        ).first()
        
        if not membership:
            # Idempotente: no revelar
            logger.warning(
                "PasswordResetService.request_reset: Usuario sin membresia (idempotente): user=%s, tenant=%s",
                user.email, tenant.schema_name
            )
            return
        
        # Verificar que el usuario tenga contraseña usable (no es activación)
        if not user.has_usable_password():
            raise UserNotFoundError("Este usuario aun no ha activado su cuenta. Usa el enlace de activacion.")
        
        # Generar token Django estándar
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        
        # Construir URL de reset (tenant domain)
        with schema_context('public'):
            domain_obj = Domain.objects.filter(tenant=tenant, is_primary=True).first()
        
        if not domain_obj:
            raise TenantNotFoundError("Error: tenant sin dominio primario.")
        
        protocol = 'https' if getattr(settings, 'SECURE_SSL_REDIRECT', False) else 'http'
        app_port = getattr(settings, 'APP_PORT', None)
        if settings.DEBUG and app_port and str(app_port) not in ('80', '443'):
            domain_with_port = f"{domain_obj.domain}:{app_port}"
        else:
            domain_with_port = domain_obj.domain
            
        reset_url = f"{protocol}://{domain_with_port}/static/tenant/landing/reset-confirm.html?uid={uidb64}&token={token}"
        
        # Enviar email usando servicio público existente
        from apps.public.tenants.services.password_reset import send_password_reset_email
        try:
            send_password_reset_email(user, tenant, reset_url)
            logger.info(
                "PasswordResetService.request_reset: Email ENVIADO EXITOSAMENTE - user=%s, tenant=%s",
                user.email, tenant.schema_name
            )
        except Exception as e:
            logger.error(
                "PasswordResetService.request_reset: Error enviando email: user=%s, tenant=%s, error=%s",
                user.email, tenant.schema_name, str(e),
                exc_info=True
            )
        
    finally:
        connection.set_schema(current_schema)


def validate_token(uid: str, token: str, tenant) -> Dict[str, Any]:
    """
    Valida un token de reset de contraseña.
    """
    if not tenant:
        raise TenantNotFoundError("No se pudo determinar el tenant actual.")
    
    if not uid or not token:
        raise InvalidTokenError("Token de reset invalido o expirado.")
    
    current_schema = connection.schema_name
    try:
        connection.set_schema_to_public()
        
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise InvalidTokenError("Token de reset invalido o expirado.")
        
        if not default_token_generator.check_token(user, token):
            raise InvalidTokenError("Token de reset invalido o expirado.")
        
        membership = TenantMembership.objects.filter(
            client=tenant,
            user=user,
            is_active=True,
        ).first()
        
        if not membership:
            raise InvalidTokenError("Token de reset invalido o expirado.")
        
        return {
            'valid': True,
            'email': user.email,
        }
        
    finally:
        connection.set_schema(current_schema)


def confirm_reset(uid: str, token: str, new_password: str, tenant) -> Any:
    """
    Confirma el reset de contraseña y establece la nueva contraseña.
    """
    if not tenant:
        raise TenantNotFoundError("No se pudo determinar el tenant actual.")
    
    if not uid or not token:
        raise InvalidTokenError("Token de reset invalido o expirado.")
    
    if not new_password or len(new_password) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres.")
    
    current_schema = connection.schema_name
    try:
        connection.set_schema_to_public()
        
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise InvalidTokenError("Token de reset invalido o expirado.")
        
        if not default_token_generator.check_token(user, token):
            raise InvalidTokenError("Token de reset invalido o expirado.")
        
        membership = TenantMembership.objects.filter(
            client=tenant,
            user=user,
            is_active=True,
        ).first()
        
        if not membership:
            raise InvalidTokenError("Token de reset invalido o expirado.")
        
        user.set_password(new_password)
        user.save(update_fields=['password'])
        
        user.refresh_from_db()
        if not user.has_usable_password():
            raise ValueError("Error al establecer la nueva contrasena. Por favor, intenta nuevamente.")
        
        return user
        
    finally:
        connection.set_schema(current_schema)


class PasswordResetService:
    """
    Servicio de reset de contrasena.
    Wrapper class para funciones de password reset.
    """

    @staticmethod
    def request_reset(email_or_username, tenant):
        """Solicita reset de contrasena."""
        return request_reset(email_or_username, tenant)

    @staticmethod
    def validate_token(uid, token, tenant):
        """Valida token de reset de contrasena."""
        return validate_token(uid, token, tenant)

    @staticmethod
    def confirm_reset(uid, token, new_password, tenant):
        """Confirma reset de contrasena."""
        return confirm_reset(uid, token, new_password, tenant)
