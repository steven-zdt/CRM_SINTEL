"""
Serializers del LLM Provider Hub (Fase 8,
PLAN_MAESTRO_LLM_PROVIDER_HUB_SINTEL_CONSOLE_20260924.md).

Archivo separado de serializers.py (dominio distinto: proveedores de IA,
no tenants/usuarios) -- evita mezclar dos areas que no comparten nada.
"""

from __future__ import annotations

from rest_framework import serializers

from apps.public.console.models import (
    LLMActiveConfig,
    LLMModelConfig,
    LLMProviderAuditLog,
    LLMProviderConfig,
)


class LLMModelConfigSerializer(serializers.ModelSerializer):
    provider_slug = serializers.CharField(source="provider.slug", read_only=True)

    class Meta:
        model = LLMModelConfig
        fields = [
            "id",
            "provider",
            "provider_slug",
            "model_identifier",
            "display_name",
            "enabled",
            "context_window",
            "max_output_tokens",
            "supports_tools",
            "supports_streaming",
            "supports_structured_output",
            "supports_vision",
            "supports_reasoning",
            "verified",
            "verified_at",
            "last_health_check_at",
            "last_health_reachable",
            "fallback_priority",
            "created_at",
            "updated_at",
        ]
        # Capacidades/verified/last_health_* NUNCA editables a mano por API
        # -- solo un capability probe/health check real las puebla (Regla
        # Absoluta del plan "NO ASUMIR CAPACIDADES"). model_identifier/
        # display_name/enabled/fallback_priority si son editables (ver
        # ViewSet) -- fallback_priority es la UNICA "policy" que configura
        # el usuario (plan Seccion 28: "definir una policy, no una cadena
        # hardcoded").
        read_only_fields = [
            "id",
            "provider_slug",
            "supports_tools",
            "supports_streaming",
            "supports_structured_output",
            "supports_vision",
            "supports_reasoning",
            "verified",
            "verified_at",
            "last_health_check_at",
            "last_health_reachable",
            "created_at",
            "updated_at",
        ]


class LLMProviderConfigSerializer(serializers.ModelSerializer):
    models_config = LLMModelConfigSerializer(many=True, read_only=True)
    secret_masked = serializers.SerializerMethodField()
    # Solo escritura -- nunca se devuelve en la respuesta (ver to_representation
    # implicito de DRF: write_only excluye el campo de la salida).
    secret = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = LLMProviderConfig
        fields = [
            "id",
            "name",
            "slug",
            "provider_type",
            "description",
            "enabled",
            "is_local",
            "base_url",
            "secret",
            "secret_masked",
            "default_timeout_s",
            "created_at",
            "updated_at",
            "models_config",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "models_config", "secret_masked"]

    def get_secret_masked(self, obj) -> str | None:
        """Plan Seccion 7: 'API Key: ••••••••••••9F3A' -- NUNCA el secreto completo."""
        if not obj.secret_encrypted:
            return None
        from apps.services.security.crypto import decrypt_password

        try:
            real = decrypt_password(obj.secret_encrypted)
        except Exception:
            return "(no se pudo descifrar -- clave rotada?)"
        if not real:
            return None
        if len(real) <= 4:
            return "•" * len(real)
        return "•" * 12 + real[-4:]

    def _save_secret(self, instance, secret_plain: str | None):
        if secret_plain is None:
            return
        from apps.services.security.crypto import encrypt_password

        instance.secret_encrypted = encrypt_password(secret_plain) if secret_plain else ""

    def create(self, validated_data):
        secret_plain = validated_data.pop("secret", None)
        instance = LLMProviderConfig(**validated_data)
        self._save_secret(instance, secret_plain)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        secret_plain = validated_data.pop("secret", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        self._save_secret(instance, secret_plain)
        instance.save()
        return instance


class LLMActiveConfigSerializer(serializers.ModelSerializer):
    provider_slug = serializers.CharField(source="model_config.provider.slug", read_only=True)
    provider_name = serializers.CharField(source="model_config.provider.name", read_only=True)
    model_identifier = serializers.CharField(source="model_config.model_identifier", read_only=True)
    activated_by_email = serializers.CharField(
        source="activated_by.email", read_only=True, default=None
    )

    class Meta:
        model = LLMActiveConfig
        fields = [
            "id",
            "model_config",
            "provider_slug",
            "provider_name",
            "model_identifier",
            "activated_by_email",
            "activated_at",
            "reason",
        ]
        read_only_fields = [
            "id",
            "provider_slug",
            "provider_name",
            "model_identifier",
            "activated_by_email",
            "activated_at",
        ]


class LLMProviderAuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.CharField(source="actor.email", read_only=True, default=None)
    provider_slug = serializers.CharField(source="provider.slug", read_only=True, default=None)

    class Meta:
        model = LLMProviderAuditLog
        fields = ["id", "action", "actor_email", "provider_slug", "timestamp", "detail", "result"]
        read_only_fields = fields
