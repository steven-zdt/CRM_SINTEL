"""
Servicio de dominio para reset de contrasena (Core).

v3.13.0: Migrado a codigos alfanumericos de 8 chars via Redis (mismo patron
que activacion de cuentas). Eliminada dependencia de uidb64 + Django tokens
en URLs — Gmail bloqueaba links con tokens largos.

Flujo nuevo:
  1. request_reset(email, tenant) → genera codigo → envia email con codigo
  2. confirm_reset_with_code(code, tenant_schema, new_password) → valida + set_password
"""
import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from django.contrib.auth import get_user_model
from django.db import connection
from django.conf import settings

from apps.public.tenants.models import TenantMembership

logger = logging.getLogger(__name__)
User = get_user_model()

# ---------------------------------------------------------------------------
# Configuracion del codigo de reset
# ---------------------------------------------------------------------------
_RESET_ALPHABET: str = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # sin O/0/I/1/L
_RESET_CODE_LEN: int = 8
_RESET_TTL_HOURS: int = 1  # 1 hora por seguridad (vs 48h de activacion)


def _redis():
    import redis as _redis_lib
    return _redis_lib.from_url(getattr(settings, "REDIS_URL", "redis://redis:6379/0"))


def generate_reset_code(user_id: int, tenant_schema: str, ttl_hours: int = _RESET_TTL_HOURS) -> str:
    """
    Genera un codigo alfanumerico de 8 chars para reset de contrasena y lo persiste
    en Redis con clave `reset:code:{tenant_schema}:{code}`.

    Incluye tenant_schema en la clave para evitar uso cross-tenant del mismo codigo.
    Uso unico: confirm_reset_with_code() elimina la clave al consumir.

    Args:
        user_id: PK del usuario.
        tenant_schema: schema_name del tenant para aislamiento.
        ttl_hours: Tiempo de vida (default 1 hora).

    Returns:
        str: Codigo de 8 chars en mayusculas (ej. "AKBT3M7Q").
    """
    code = "".join(secrets.choice(_RESET_ALPHABET) for _ in range(_RESET_CODE_LEN))
    key = f"reset:code:{tenant_schema}:{code}"
    payload = {
        "user_id": user_id,
        "tenant_schema": tenant_schema,
        "expires_at": (datetime.now() + timedelta(hours=ttl_hours)).isoformat(),
    }
    ttl_seconds = int(timedelta(hours=ttl_hours).total_seconds())
    _redis().set(key, json.dumps(payload), ex=ttl_seconds)
    logger.info("Reset code generado: user_id=%s tenant=%s", user_id, tenant_schema)
    return code


def validate_reset_code(code: str, tenant_schema: str) -> dict | None:
    """
    Valida el codigo de reset. Uso unico — elimina la clave de Redis al consumir.

    Args:
        code: Codigo de 8 chars del formulario (acepta minusculas).
        tenant_schema: schema_name del tenant para verificacion cross-tenant.

    Returns:
        dict con user_id y tenant_schema, o None si invalido/expirado.
    """
    if not code or len(str(code).strip()) != _RESET_CODE_LEN:
        return None
    normalized = str(code).strip().upper()
    if not all(c in _RESET_ALPHABET for c in normalized):
        return None

    key = f"reset:code:{tenant_schema}:{normalized}"
    r = _redis()
    raw = r.get(key)
    if not raw:
        logger.warning("Reset code no encontrado o expirado: tenant=%s", tenant_schema)
        return None

    try:
        data = json.loads(raw)
    except Exception:
        r.delete(key)
        return None

    expires_at = datetime.fromisoformat(data["expires_at"])
    if datetime.now() > expires_at:
        r.delete(key)
        logger.warning("Reset code expirado: tenant=%s", tenant_schema)
        return None

    r.delete(key)  # uso unico
    return data

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
        
        # v3.13.0: Codigo de 8 chars via Redis — reemplaza uidb64+token en URL
        code = generate_reset_code(user.pk, tenant.schema_name, ttl_hours=_RESET_TTL_HOURS)

        # Enviar email con codigo
        from apps.public.core.services.email_service import EmailService
        try:
            EmailService.send_password_reset_code_email(user, tenant, code)
            logger.info(
                "PasswordResetService.request_reset: codigo enviado user=%s tenant=%s",
                user.email, tenant.schema_name,
            )
        except Exception as e:
            logger.error(
                "PasswordResetService.request_reset: error email user=%s tenant=%s: %s",
                user.email, tenant.schema_name, str(e), exc_info=True,
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


def confirm_reset_with_code(code: str, tenant_schema: str, new_password: str) -> User:
    """
    Confirma reset de contrasena usando codigo Redis de 8 chars (v3.13.0).

    Args:
        code: Codigo de 8 chars recibido en el formulario.
        tenant_schema: schema_name del tenant para aislamiento cross-tenant.
        new_password: Nueva contrasena del usuario.

    Returns:
        User actualizado.

    Raises:
        InvalidTokenError: Si el codigo no existe, expiro o pertenece a otro tenant.
    """
    payload = validate_reset_code(code, tenant_schema)
    if not payload:
        raise InvalidTokenError("Codigo de reset invalido o expirado.")

    if payload.get("tenant_schema") != tenant_schema:
        raise InvalidTokenError("Codigo de reset invalido o expirado.")

    current_schema = connection.schema_name
    try:
        connection.set_schema_to_public()
        try:
            user = User.objects.get(pk=payload["user_id"], is_active=True)
        except User.DoesNotExist:
            raise InvalidTokenError("Codigo de reset invalido o expirado.")

        membership = TenantMembership.objects.filter(
            client__schema_name=tenant_schema,
            user=user,
            is_active=True,
        ).first()
        if not membership:
            raise InvalidTokenError("Codigo de reset invalido o expirado.")

        user.set_password(new_password)
        user.save(update_fields=["password"])
        logger.info("Contrasena restablecida via codigo: user=%s tenant=%s", user.email, tenant_schema)
        return user
    finally:
        connection.set_schema(current_schema)


class PasswordResetService:
    """Wrapper class para funciones de password reset."""

    @staticmethod
    def request_reset(email_or_username, tenant):
        return request_reset(email_or_username, tenant)

    @staticmethod
    def validate_token(uid, token, tenant):
        return validate_token(uid, token, tenant)

    @staticmethod
    def confirm_reset(uid, token, new_password, tenant):
        return confirm_reset(uid, token, new_password, tenant)

    @staticmethod
    def confirm_reset_with_code(code, tenant_schema, new_password):
        return confirm_reset_with_code(code, tenant_schema, new_password)
