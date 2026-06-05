"""
Servicio de Onboarding sin fricción (One-Time Token, OTT) usando Redis.

Flujo:
- `create_onboarding_ott`: crea tenant + admin (si es necesario) y genera un OTT UUID almacenado en Redis
- El OTT tiene TTL corto y se borra al consumirse.

Este módulo usa `apps.public.tenants.services.crear_tenant_con_owner` para crear el tenant.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import timedelta
from typing import Any

import redis
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

import importlib.util
from pathlib import Path

_TENANTS_DIR = Path(__file__).resolve().parents[1]


logger = logging.getLogger(__name__)
User = get_user_model()


DEFAULT_OTT_TTL_SECONDS = 60 * 5  # 5 minutos


def _get_redis_client() -> redis.Redis:
    return redis.from_url(getattr(settings, "REDIS_URL", "redis://redis:6379/0"))


def create_onboarding_ott(company_name: str, admin_email: str, schema_name: str | None = None, ttl_seconds: int = DEFAULT_OTT_TTL_SECONDS) -> dict[str, Any]:
    """Crea tenant + admin user (si no existe) y devuelve una URL con OTT.

    Retorna dict con keys: `ott`, `redirect_url` (absolute tenant URL with ott query param),
    `schema_name`.
    """
    admin_user, created = User.objects.get_or_create(
        email=admin_email,
        defaults={"username": admin_email, "is_active": True},
    )
    if created:
        admin_user.set_unusable_password()
        admin_user.save()
    else:
        if not admin_user.is_active:
            admin_user.is_active = True
            admin_user.save()

    # 2. Crear tenant usando servicio existente
    try:
        # Usar el servicio centralizado de onboarding (apps.services.onboarding.empresa_service)
        from apps.services.onboarding.empresa_service import crear_tenant_con_owner as crear_tenant_service

        # La función en apps.services.onboarding espera kwargs: nombre, schema_name, owner_email/admin_user_id
        payload_kwargs = {
            'nombre': company_name,
            'schema_name': schema_name or company_name.replace(' ', '_').lower(),
            'owner_email': admin_email,
        }
        result = crear_tenant_service(**payload_kwargs)
        # El servicio retorna un dict con client_id, domain, membership_id, login_url
        # Recuperar client and domain info desde el modelo público
        from apps.public.tenants.models import Client, Domain

        client = Client.objects.get(schema_name=payload_kwargs['schema_name'])
        domain = Domain.objects.filter(tenant=client, is_primary=True).first()
        membership = None
        login_url = result.get('login_url') if isinstance(result, dict) else None
    except ValidationError as ve:
        # Propagar validación para que la API lo maneje
        logger.error("Onboarding: error creando tenant: %s", ve)
        raise

    # 3. Generar OTT y guardarlo en Redis
    redis_client = _get_redis_client()
    ott = str(uuid.uuid4())
    key = f"onboard:{ott}"
    payload = {
        "user_id": admin_user.id,
        "schema_name": client.schema_name,
        "domain": domain.domain,
    }
    redis_client.set(key, json.dumps(payload), ex=ttl_seconds)

    # 4. Construir redirect URL al tenant con ott
    # Añadir ott como query param a la ruta /onboard/
    if getattr(settings, "DEBUG", False) and getattr(settings, "APP_PORT", None):
        domain_with_port = f"{domain.domain}:{settings.APP_PORT}"
    else:
        domain_with_port = domain.domain

    protocol = "https" if (not settings.DEBUG and getattr(settings, "SECURE_SSL_REDIRECT", False)) else "http"
    # Redirigir al asset estático onboard.html dentro de core
    redirect_url = f"{protocol}://{domain_with_port}/static/core/onboard.html?ott={ott}"

    logger.info("Onboarding OTT creado: %s -> %s", ott, redirect_url)

    return {"ott": ott, "redirect_url": redirect_url, "schema_name": client.schema_name}


def consume_onboarding_ott(ott: str) -> dict[str, Any] | None:
    """Consume el OTT (uso unico) desde Redis y retorna el payload enriquecido.

    Validacion de seguridad — cuenta preexistente:
    -----------------------------------------------
    Si el usuario asociado al OTT ya tiene una contrasena usable (is_active
    con password real, no set_unusable_password), el tenant ya fue vinculado
    a una cuenta global previa. En ese caso NO se debe forzar un nuevo
    seteo de contrasena. El payload retorna `already_activated=True` y un
    mensaje informativo para que la vista redirija al login con contexto.

    Retorna:
        dict con keys:
            user_id        (int)
            schema_name    (str)
            domain         (str)
            already_activated (bool) — True si user.has_usable_password()
            message        (str)     — mensaje para mostrar al usuario
        None si el OTT no existe o expiro.
    """
    redis_client = _get_redis_client()
    key = f"onboard:{ott}"
    raw = redis_client.get(key)
    if not raw:
        return None

    try:
        data = json.loads(raw)
    except Exception:
        redis_client.delete(key)
        return None

    # Uso unico: eliminar de Redis antes de cualquier validacion posterior
    redis_client.delete(key)

    # Validar si el usuario ya tiene contrasena usable
    user_id = data.get("user_id")
    already_activated = False
    message = ""

    if user_id:
        try:
            user = User.objects.filter(pk=user_id).first()
            if user and user.has_usable_password():
                already_activated = True
                message = (
                    "El tenant ha sido anadido a tu cuenta existente. "
                    "Inicia sesion con tus credenciales habituales."
                )
                logger.info(
                    "consume_onboarding_ott: user_id=%s ya tiene contrasena usable "
                    "(schema=%s) — omitiendo flujo de activacion",
                    user_id, data.get("schema_name"),
                )
        except Exception as exc:
            logger.warning("consume_onboarding_ott: error verificando user_id=%s: %s", user_id, exc)

    data["already_activated"] = already_activated
    data["message"] = message
    return data
