"""
Servicio de dominio para reset de contraseña (tenant).

⚠️ POLÍTICA:
- Trabaja con User global (esquema public)
- No renderiza HTML
- Lanza excepciones tipadas para tokens inválidos/expirados
- Rate-limiting: TODO (usar decorador project-wide si existe)
"""
import logging
from typing import Optional, Dict, Any
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.db import connection
from django_tenants.utils import schema_context

from apps.public.tenants.models import TenantMembership

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
            logger.info(
                "✅ PasswordResetService.request_reset: Usuario encontrado - user_id=%s, email=%s",
                user.id, user.email
            )
        except User.DoesNotExist:
            # Idempotente: no revelar si el usuario existe
            logger.warning(
                "⚠️ PasswordResetService.request_reset: Usuario no encontrado (idempotente): email=%s, tenant=%s",
                email_or_username, tenant.schema_name
            )
            return  # No lanzar error para evitar enumeración de usuarios
        
        # Verificar membresía en tenant
        logger.info(
            "PasswordResetService.request_reset: Verificando membresía - user_id=%s, tenant=%s",
            user.id, tenant.schema_name
        )
        membership = TenantMembership.objects.filter(
            client=tenant,
            user=user,
            is_active=True,
        ).first()
        
        if not membership:
            # Idempotente: no revelar
            logger.warning(
                "⚠️ PasswordResetService.request_reset: Usuario sin membresía (idempotente): user=%s, tenant=%s",
                user.email, tenant.schema_name
            )
            return
        
        logger.info(
            "✅ PasswordResetService.request_reset: Membresía verificada - user_id=%s, tenant=%s, rol=%s",
            user.id, tenant.schema_name, membership.rol if membership else 'N/A'
        )
        
        # Verificar que el usuario tenga contraseña usable (no es activación)
        if not user.has_usable_password():
            raise UserNotFoundError("Este usuario aún no ha activado su cuenta. Usa el enlace de activación.")
        
        # Generar token Django estándar
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        
        # Construir URL de reset (tenant domain)
        from apps.public.tenants.models import Domain
        from django.conf import settings
        
        with schema_context('public'):
            domain_obj = Domain.objects.filter(tenant=tenant, is_primary=True).first()
        
        if not domain_obj:
            raise TenantNotFoundError("Error: tenant sin dominio primario.")
        
        protocol = 'https' if getattr(settings, 'SECURE_SSL_REDIRECT', False) else 'http'
        reset_url = f"{protocol}://{domain_obj.domain}/static/tenant/landing/reset-confirm.html?uid={uidb64}&token={token}"
        
        # Enviar email usando servicio público existente
        from apps.public.tenants.services.password_reset import send_password_reset_email
        logger.info(
            "PasswordResetService.request_reset: Intentando enviar email de reset - user=%s, tenant=%s, reset_url=%s",
            user.email, tenant.schema_name, reset_url
        )
        try:
            email_sent = send_password_reset_email(user, tenant, reset_url)
            if email_sent:
                logger.info(
                    "✅ PasswordResetService.request_reset: Email ENVIADO EXITOSAMENTE - user=%s, tenant=%s",
                    user.email, tenant.schema_name
                )
            else:
                logger.warning(
                    "⚠️ PasswordResetService.request_reset: Email NO enviado (idempotente): user=%s, tenant=%s",
                    user.email, tenant.schema_name
                )
        except Exception as e:
            logger.error(
                "❌ PasswordResetService.request_reset: Error enviando email: user=%s, tenant=%s, error=%s",
                user.email, tenant.schema_name, str(e),
                exc_info=True
            )
            # No lanzar excepción para mantener idempotencia
        
    finally:
        connection.set_schema(current_schema)


def validate_token(uid: str, token: str, tenant) -> Dict[str, Any]:
    """
    Valida un token de reset de contraseña.
    
    Args:
        uid: User ID codificado en base64 URL-safe
        token: Token de reset
        tenant: Instancia del tenant (Client)
        
    Returns:
        Dict con:
            - valid: bool
            - email: str (si válido)
            - expires_at: str ISO (opcional, si se puede determinar)
        
    Raises:
        InvalidTokenError: Si el token es inválido o expirado
        TenantNotFoundError: Si no se puede determinar el tenant
    """
    if not tenant:
        raise TenantNotFoundError("No se pudo determinar el tenant actual.")
    
    if not uid or not token:
        raise InvalidTokenError("Token de reset inválido o expirado.")
    
    current_schema = connection.schema_name
    try:
        connection.set_schema_to_public()
        
        # Decodificar uidb64
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise InvalidTokenError("Token de reset inválido o expirado.")
        
        # Validar token
        if not default_token_generator.check_token(user, token):
            raise InvalidTokenError("Token de reset inválido o expirado.")
        
        # Verificar membresía en tenant
        membership = TenantMembership.objects.filter(
            client=tenant,
            user=user,
            is_active=True,
        ).first()
        
        if not membership:
            raise InvalidTokenError("Token de reset inválido o expirado.")
        
        return {
            'valid': True,
            'email': user.email,
        }
        
    finally:
        connection.set_schema(current_schema)


def confirm_reset(uid: str, token: str, new_password: str, tenant) -> None:
    """
    Confirma el reset de contraseña y establece la nueva contraseña.
    
    Args:
        uid: User ID codificado en base64 URL-safe
        token: Token de reset
        new_password: Nueva contraseña
        tenant: Instancia del tenant (Client)
        
    Raises:
        InvalidTokenError: Si el token es inválido o expirado
        TenantNotFoundError: Si no se puede determinar el tenant
        ValueError: Si la contraseña no cumple requisitos
    """
    if not tenant:
        raise TenantNotFoundError("No se pudo determinar el tenant actual.")
    
    if not uid or not token:
        raise InvalidTokenError("Token de reset inválido o expirado.")
    
    if not new_password or len(new_password) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres.")
    
    current_schema = connection.schema_name
    try:
        connection.set_schema_to_public()
        
        # Decodificar uidb64
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise InvalidTokenError("Token de reset inválido o expirado.")
        
        # Validar token
        if not default_token_generator.check_token(user, token):
            raise InvalidTokenError("Token de reset inválido o expirado.")
        
        # Verificar membresía en tenant
        membership = TenantMembership.objects.filter(
            client=tenant,
            user=user,
            is_active=True,
        ).first()
        
        if not membership:
            raise InvalidTokenError("Token de reset inválido o expirado.")
        
        # Establecer nueva contraseña
        user.set_password(new_password)
        user.save(update_fields=['password'])
        
        # Verificar que el password quedó usable
        user.refresh_from_db()
        if not user.has_usable_password():
            logger.error(
                "PasswordResetService.confirm_reset: Password NO usable después de set_password: user=%s, tenant=%s",
                user.email, tenant.schema_name
            )
            raise ValueError("Error al establecer la nueva contraseña. Por favor, intenta nuevamente.")
        
        logger.info(
            "PasswordResetService.confirm_reset: Password establecido exitosamente: user=%s, tenant=%s",
            user.email, tenant.schema_name
        )
        
        return user  # Retornar usuario para que Core pueda construir redirect
        
    finally:
        connection.set_schema(current_schema)
