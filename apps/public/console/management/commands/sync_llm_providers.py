"""
Fase 8, PLAN_MAESTRO_LLM_PROVIDER_HUB_SINTEL_CONSOLE_20260924.md.

Sincroniza LLMProviderConfig/LLMModelConfig (DB) con la configuracion REAL
del entorno (variables de entorno que apps/services/ai/providers/__init__.py
ya lee) -- para que la consola arranque mostrando datos reales, no vacios.
Idempotente (update_or_create) -- correr las veces que haga falta.

Secretos: nunca en texto plano en la DB -- se cifran con
apps.services.security.crypto (Fernet, mismo mecanismo ya en produccion
para passwords de buzones de correo).

Uso:
    docker compose exec web python manage.py sync_llm_providers
"""

from __future__ import annotations

import os

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.public.console.models import LLMModelConfig, LLMProviderConfig
from apps.services.security.crypto import encrypt_password

PROVIDER_SEEDS = [
    {
        "slug": "anthropic",
        "name": "Anthropic",
        "provider_type": "anthropic",
        "is_local": False,
        "base_url": "",
        "api_key_env": ["AI_API_KEY", "ANTHROPIC_API_KEY"],
        "default_model": os.environ.get("AI_MODEL", "claude-haiku-4-5-20251001"),
    },
    {
        "slug": "ollama",
        "name": "Ollama",
        "provider_type": "ollama",
        "is_local": True,
        "base_url": os.environ.get("AI_OLLAMA_BASE_URL", "http://ollama:11434"),
        "api_key_env": [],
        "default_model": os.environ.get("AI_OLLAMA_MODEL", "qwen3.5:4b"),
    },
    {
        "slug": "openai-compatible",
        "name": "OpenAI-compatible REST",
        "provider_type": "openai_compatible",
        "is_local": False,
        "base_url": os.environ.get("AI_OPENAI_COMPAT_BASE_URL", ""),
        "api_key_env": ["AI_OPENAI_COMPAT_API_KEY"],
        "default_model": os.environ.get("AI_OPENAI_COMPAT_MODEL", ""),
    },
]


class Command(BaseCommand):
    help = "Sincroniza LLMProviderConfig/LLMModelConfig con la configuracion real (env vars)."

    @transaction.atomic
    def handle(self, *args, **options):
        from apps.services.ai.providers import get_ai_provider

        for seed in PROVIDER_SEEDS:
            secret = ""
            for env_name in seed["api_key_env"]:
                value = os.environ.get(env_name, "")
                if value:
                    secret = value
                    break

            provider, created = LLMProviderConfig.objects.update_or_create(
                slug=seed["slug"],
                defaults={
                    "name": seed["name"],
                    "provider_type": seed["provider_type"],
                    "is_local": seed["is_local"],
                    "base_url": seed["base_url"],
                    "secret_encrypted": encrypt_password(secret) if secret else "",
                    "enabled": True,
                },
            )
            self.stdout.write(f"Provider {seed['slug']}: {'creado' if created else 'actualizado'}")

            if not seed["default_model"]:
                self.stdout.write(
                    self.style.WARNING(
                        f"  sin modelo default configurado para {seed['slug']} -- se omite"
                    )
                )
                continue

            # Capacidades reales si el provider las puede reportar sin gastar
            # una llamada cara (Ollama via /api/tags) -- nunca asumidas para
            # providers que todavia no lo implementan (Regla Absoluta del
            # plan "NO ASUMIR CAPACIDADES").
            caps_kwargs = {}
            try:
                real_provider = get_ai_provider(seed["provider_type"])
                caps = real_provider.get_capabilities()
                if caps.verified:
                    caps_kwargs = {
                        "supports_tools": caps.tool_calling,
                        "supports_streaming": caps.streaming,
                        "supports_structured_output": caps.structured_output,
                        "supports_vision": caps.vision,
                        "supports_reasoning": caps.reasoning,
                        "verified": True,
                        "verified_at": caps.verified_at,
                    }
            except Exception as exc:
                self.stdout.write(
                    self.style.WARNING(
                        f"  no se pudieron leer capacidades reales de {seed['slug']}: {exc}"
                    )
                )

            model_config, m_created = LLMModelConfig.objects.update_or_create(
                provider=provider,
                model_identifier=seed["default_model"],
                defaults={
                    "display_name": seed["default_model"],
                    "enabled": True,
                    **caps_kwargs,
                },
            )
            self.stdout.write(
                f"  modelo {seed['default_model']}: {'creado' if m_created else 'actualizado'}"
            )

        self.stdout.write(self.style.SUCCESS("Sincronizacion completa."))
