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

import logging
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode, unquote

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.mail import send_mail
from django.template.loader import render_to_string

User = get_user_model()
logger = logging.getLogger(__name__)

# TTL por defecto: 24 horas
DEFAULT_TOKEN_TTL_HOURS = 24


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


def send_invitation_email(user, tenant, activation_url: str) -> bool:
    """
    Envía email de invitación al owner via EmailService centralizado.
    """
    from apps.public.core.services.email_service import EmailService
    return EmailService.send_invitation_email(user, tenant, activation_url)


def build_activation_url(domain: str, token: str) -> str:
    """
    Construye URL absoluta de activación en el subdominio del tenant.

    [WARNING] v2.30: Shell estático - URL apunta a /activate/?token=... que sirve el shell HTML
    El shell HTML consume la API /api/v1/landing/auth/activate/ internamente.

    [WARNING] v2.30: Hardening - Incluye puerto en DEV cuando APP_PORT está configurado.
    - Domain.domain SIEMPRE es FQDN puro (sin puerto), tal como dicta la normalización.
    - En DEV, si APP_PORT=8000, se agrega :8000 a la URL.
    - En PROD, se omite puerto (80/443 implícitos).

    Args:
        domain: Dominio del tenant FQDN puro (ej: acme.localhost, acme.sintel.com) - SIN puerto
        token: Token de invitación

    Returns:
        str: URL absoluta (ej: http://acme.localhost:8000/activate/?token=... en DEV, http://acme.sintel.com/activate/?token=... en PROD)
    """
    from django.conf import settings

    # Determinar protocolo
    if not settings.DEBUG and getattr(settings, "SECURE_SSL_REDIRECT", False):
        protocol = "https"
    else:
        protocol = "http"

    # [WARNING] v2.30: Incluir puerto en DEV si APP_PORT está configurado
    app_port = getattr(settings, "APP_PORT", None)
    if settings.DEBUG and app_port and str(app_port) not in ("80", "443"):
        # En DEV, agregar puerto a la URL
        domain_with_port = f"{domain}:{app_port}"
    else:
        # En PROD o sin puerto, usar dominio sin puerto
        domain_with_port = domain

    # Construir URL al shell estático (v2.30)
    # El shell HTML consume la API /api/v1/landing/auth/activate/ internamente
    # IMPORTANTE: urlencode garantiza que los ':' del token Django (separadores de firma)
    # queden como %3A en el href del email. Sin esto, ciertos clientes de email
    # truncan la URL en el primer ':' del token, rompiendo la firma al leer.
    url = f"{protocol}://{domain_with_port}/activate/?{urlencode({'token': token})}"

    logger.info("[OK] URL de activacion construida (Shell estatico v2.30): %s", url)
    return url
