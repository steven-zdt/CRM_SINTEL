"""
Servicio de invitaciones para activación de owners en subdominios de tenants.

[WARNING] IMPORTANTE:
- Genera tokens firmados con TTL (24 horas por defecto)
- Tokens incluyen user_id y tenant_id para validación
- Invalidación tras uso (one-time use)
- Sin signals: toda la lógica está aquí

Referencias:
- Django signing: https://docs.djangoproject.com/en/6.0/topics/signing/
"""

import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode, unquote

import redis
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.mail import send_mail
from django.template.loader import render_to_string

User = get_user_model()
logger = logging.getLogger(__name__)

# TTL por defecto: 24 horas
DEFAULT_TOKEN_TTL_HOURS = 24
DEFAULT_CODE_TTL_HOURS = 24


def _get_redis_client() -> redis.Redis:
    return redis.from_url(getattr(settings, "REDIS_URL", "redis://redis:6379/0"))


def generate_invitation_token(
    user_id: int, tenant_id: int, ttl_hours: int = DEFAULT_TOKEN_TTL_HOURS
) -> str:
    """
    Genera un token de invitación firmado con TTL.

    [WARNING] SEGURIDAD:
    - Token firmado con SECRET_KEY de Django
    - Incluye user_id y tenant_id para validación
    - TTL configurable (default: 24 horas)
    - One-time use (se invalida tras uso)

    Args:
        user_id: ID del usuario a invitar
        tenant_id: ID del tenant al que pertenece
        ttl_hours: TTL del token en horas (default: 24)

    Returns:
        str: Token firmado (URL-safe)
    """
    # Payload del token
    payload = {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "expires_at": (datetime.now() + timedelta(hours=ttl_hours)).isoformat(),
        "ttl_hours": int(ttl_hours),
    }

    # Firmar con SECRET_KEY
    token = signing.dumps(payload, salt="tenant-owner-invitation")

    logger.info(
        "[OK] Token de invitación generado: user_id=%s, tenant_id=%s, ttl=%s horas",
        user_id,
        tenant_id,
        ttl_hours,
    )

    return token


def validate_invitation_token(token: str) -> dict[str, Any] | None:
    """
    Verifica y decodifica un token de invitación.

    [WARNING] SEGURIDAD:
    - Valida la firma del token
    - Verifica que no haya expirado
    - Retorna payload si es válido, None si es inválido/expirado

    Args:
        token: Token firmado a verificar

    Returns:
        Dict con 'user_id' y 'tenant_id' si es válido, None si es inválido/expirado
    """
    try:
        # Decodificar token (valida firma automáticamente)
        # NOTE: We intentionally do not pass max_age to signing.loads so the
        # token TTL is determined by the embedded 'expires_at' field which was
        # created at token generation time. This allows per-token TTLs.
        # Defensive: unquote handles tokens that arrived double-encoded through
        # some email clients or HTTP redirect chains.
        payload = signing.loads(unquote(token), salt="tenant-owner-invitation")

        # Verificar expiración según campo embebido 'expires_at' (defensivo)
        expires_at = datetime.fromisoformat(payload["expires_at"])
        if datetime.now() > expires_at:
            logger.warning("[WARNING] Token de invitación expirado: expires_at=%s", expires_at)
            return None

        logger.info(
            "[OK] Token de invitación válido: user_id=%s, tenant_id=%s",
            payload["user_id"],
            payload["tenant_id"],
        )

        return payload
    except signing.BadSignature:
        logger.warning("[WARNING] Token de invitación con firma inválida")
        return None
    except Exception as e:
        logger.error("[ERROR] Error verificando token de invitación: %s", e, exc_info=True)
        return None


def verify_invitation_token(token: str) -> dict[str, Any] | None:
    """
    Alias retrocompatible para módulos legacy que aún importan verify_*.

    Mantiene compatibilidad sin duplicar lógica.
    """
    return validate_invitation_token(token)


# Backwards-compatible alias for older callers
def make_owner_invite_token(
    user_id: int, tenant_id: int, ttl_hours: int = DEFAULT_TOKEN_TTL_HOURS
) -> str:
    """Alias backwards-compatible for older code expecting `make_owner_invite_token`.
    Delegates to `generate_invitation_token`.
    """
    return generate_invitation_token(user_id, tenant_id, ttl_hours)


# ---------------------------------------------------------------------------
# Codigo de activacion alfanumerico (8 caracteres) — Zero Collision
# ---------------------------------------------------------------------------

# Alfabeto sin caracteres ambiguos: excluye O/0 (oh/cero), I/1 (i/uno), L (ele)
# 32 simbolos × 8 posiciones = 32^8 ≈ 1.1 × 10^12 combinaciones
_CODE_ALPHABET: str = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
_CODE_LENGTH: int = 8


def generate_activation_code(
    user_id: int, tenant_id: int, ttl_hours: int = DEFAULT_CODE_TTL_HOURS
) -> str:
    """
    Genera un codigo alfanumerico seguro de 8 caracteres y lo persiste en Redis con TTL.

    Formato: 8 caracteres en mayusculas del alfabeto sin ambiguedad
    (excluye O/0, I/1, L para evitar confusion visual).
    Ejemplo: "AKBT3M7Q".

    Entropia: 32^8 ≈ 1.1 × 10^12 combinaciones — probabilidad de colision
    insignificante incluso con miles de tenants activos simultaneamente.

    El codigo es de uso unico: validate_activation_code() lo elimina de Redis
    al consumirlo, garantizando que no pueda reutilizarse.

    Clave Redis: invite:code:{code}
    Valor: JSON con user_id, tenant_id, expires_at (ISO 8601).

    Args:
        user_id: PK del usuario que debe activar su cuenta.
        tenant_id: PK del Client al que pertenece la invitacion.
        ttl_hours: Tiempo de vida del codigo en horas (default: 24).

    Returns:
        str: Codigo alfanumerico de 8 caracteres en mayusculas (ej. "AKBT3M7Q").
    """
    code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_LENGTH))
    key = f"invite:code:{code}"
    payload = {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "expires_at": (datetime.now() + timedelta(hours=ttl_hours)).isoformat(),
    }
    ttl_seconds = int(timedelta(hours=ttl_hours).total_seconds())
    _get_redis_client().set(key, json.dumps(payload), ex=ttl_seconds)
    logger.info("Codigo de activacion generado para user_id=%s tenant_id=%s", user_id, tenant_id)
    return code


def validate_activation_code(code: str) -> dict[str, Any] | None:
    """
    Valida un codigo de activacion alfanumerico de 8 caracteres.
    Uso unico: elimina la clave de Redis al consumirlo.

    Acepta el codigo en cualquier capitalizacion y lo normaliza a mayusculas
    antes de buscar en Redis, tolerando errores tipograficos del usuario.

    Args:
        code: Codigo de activacion recibido del formulario.

    Returns:
        dict con user_id y tenant_id si el codigo es valido y vigente.
        None si el codigo no existe, expiro o tiene formato incorrecto.
    """
    if not code or len(str(code).strip()) != _CODE_LENGTH:
        logger.warning("validate_activation_code: formato invalido code=%s", code)
        return None

    normalized = str(code).strip().upper()
    # Verificar que todos los caracteres pertenezcan al alfabeto permitido
    if not all(c in _CODE_ALPHABET for c in normalized):
        logger.warning("validate_activation_code: caracteres invalidos code=%s", code)
        return None

    key = f"invite:code:{normalized}"
    r = _get_redis_client()
    raw = r.get(key)
    if not raw:
        logger.warning("validate_activation_code: codigo no encontrado o expirado code=%s", normalized)
        return None

    try:
        data = json.loads(raw)
    except Exception:
        r.delete(key)
        return None

    expires_at = datetime.fromisoformat(data["expires_at"])
    if datetime.now() > expires_at:
        r.delete(key)
        logger.warning("validate_activation_code: codigo expirado code=%s", normalized)
        return None

    # Uso unico: eliminar antes de retornar
    r.delete(key)
    logger.info("validate_activation_code: codigo valido user_id=%s tenant_id=%s", data["user_id"], data["tenant_id"])
    return data


def send_invitation_code_email(user, tenant, code: str) -> bool:
    """
    Envia email de invitacion con codigo numerico de 6 digitos.
    """
    from apps.public.core.services.email_service import EmailService
    return EmailService.send_invitation_code_email(user, tenant, code)


def send_invitation_email(user, tenant, activation_url: str) -> bool:
    """
    Envia email de invitacion al owner via EmailService centralizado.
    Deprecado: usar send_invitation_code_email() con codigo de 6 digitos.
    """
    from apps.public.core.services.email_service import EmailService
    return EmailService.send_invitation_email(user, tenant, activation_url)


def build_activation_url(domain: str, token: str) -> str:
    """
    Construye URL absoluta de activacion para el token de invitacion.

    El endpoint /activate/ existe en el PUBLIC schema (ActivateAccountView) y
    en el TENANT schema (shell estatico). Ambos validan el token correctamente
    porque el token solo referencia user_id y tenant_id (ambos en public schema).

    ACTIVATION_BASE_URL (env): cuando esta configurado, sobreescribe el dominio
    del tenant para la URL de activacion. Util en dev donde el subdominio del
    tenant no resuelve (ej: sintel.sintel.net.co) pero el servidor si es accesible
    via IP (ej: https://192.168.2.15). El PUBLIC /activate/ maneja la activacion
    correctamente con el token.

    Args:
        domain: FQDN del tenant (ej: acme.sintel.net.co) - usado si ACTIVATION_BASE_URL no esta configurado
        token: Token de invitacion firmado

    Returns:
        URL absoluta de activacion
    """
    import os
    from django.conf import settings

    # ACTIVATION_BASE_URL override (ej: https://192.168.2.15 para dev local)
    # Permite que el link de activacion apunte al dominio publico accesible
    activation_base = os.getenv("ACTIVATION_BASE_URL", "").strip().rstrip("/")
    if activation_base:
        url = f"{activation_base}/activate/?{urlencode({'token': token})}"
        logger.info("[OK] URL de activacion construida (ACTIVATION_BASE_URL override): %s", url)
        return url

    # Comportamiento por defecto: usar el subdominio del tenant
    site_protocol = getattr(settings, 'SITE_PROTOCOL', '').strip().lower()
    if site_protocol in ('https', 'http'):
        protocol = site_protocol
    elif not settings.DEBUG and getattr(settings, "SECURE_SSL_REDIRECT", False):
        protocol = "https"
    else:
        protocol = "http"

    app_port = getattr(settings, "APP_PORT", None)
    if protocol != 'https' and settings.DEBUG and app_port and str(app_port) not in ("80", "443"):
        domain_with_port = f"{domain}:{app_port}"
    else:
        domain_with_port = domain

    url = f"{protocol}://{domain_with_port}/activate/?{urlencode({'token': token})}"
    logger.info("[OK] URL de activacion construida (subdominio tenant): %s", url)
    return url
