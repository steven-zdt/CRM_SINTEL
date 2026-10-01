"""
Modelos para la consola de administración.
"""

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class ConsoleActionLog(models.Model):
    """
    Registro de auditoría para acciones realizadas desde la consola.

    Permite rastrear quién, cuándo y qué acción se realizó en la consola.
    """

    ACTION_CHOICES = [
        ("TENANT_CREATE", "Creación de tenant"),
        ("TENANT_UPDATE", "Actualización de tenant"),
        ("TENANT_DELETE", "Eliminación de tenant"),
        ("USER_CREATE", "Creación de usuario"),
        ("USER_UPDATE", "Actualización de usuario"),
        ("USER_DELETE", "Eliminación de usuario"),
        ("USER_ACTIVATE", "Activación de cuenta"),
        ("SECURITY_ALERT", "Alerta de seguridad"),
    ]

    action = models.CharField(max_length=50, choices=ACTION_CHOICES, verbose_name="Acción")
    actor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        related_name="console_actions",
        verbose_name="Actor",
    )
    tenant = models.ForeignKey(
        "tenants.Client",  # Referencia al modelo Client (app_label es 'tenants')
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="console_action_logs",
        verbose_name="Tenant",
    )
    target_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="console_action_targets",
        verbose_name="Usuario objetivo",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Metadatos",
        help_text="Datos adicionales de la acción (URLs, tokens, etc.)",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")

    class Meta:
        verbose_name = "Log de Acción de Consola"
        verbose_name_plural = "Logs de Acciones de Consola"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["tenant", "created_at"]),
            models.Index(fields=["actor", "created_at"]),
            models.Index(fields=["target_user", "created_at"]),
        ]

    def __str__(self):
        return f"{self.action} - {self.actor} - {self.created_at}"


# ─────────────────────────────────────────────────────────────────────────
# LLM Provider Hub (Fase 8, PLAN_MAESTRO_LLM_PROVIDER_HUB_SINTEL_CONSOLE_20260924.md)
#
# Modelos AGREGADOS aqui (apps/public/console/), no en un app nuevo bajo
# apps/public/ -- edicion autorizada explicitamente por el usuario para
# esta tarea (apps/public/ esta bloqueado por hook, RFC + needs-admin-
# approval, ver CLAUDE.md). System-wide, NO tenant-scoped (docs/ai/
# LLM_PROVIDER_BASELINE.md GAP-6: ninguna decision de producto tomada
# sobre overrides por tenant -- estos modelos viven en el schema PUBLICO
# a proposito).
#
# Auditoria propia (LLMProviderAuditLog) en vez de reutilizar
# ConsoleActionLog de arriba -- su ACTION_CHOICES es un enum cerrado de
# dominio distinto (tenants/usuarios); acoplarlo aqui violaria "no
# duplicar" en el sentido opuesto (mezclar dos dominios que no deberian
# compartir un choices field). Mismo patron real (actor/timestamp/accion),
# tabla separada (GAP-7 de docs/ai/LLM_PROVIDER_MIGRATION_GAPS.md).
# ─────────────────────────────────────────────────────────────────────────

PROVIDER_TYPE_CHOICES = [
    ("anthropic", "Anthropic"),
    ("ollama", "Ollama"),
    ("openai_compatible", "OpenAI-compatible REST"),
]


class LLMProviderConfig(models.Model):
    """
    Proveedor LLM registrado (plan Seccion 6, LLMProvider conceptual).

    `provider_type` debe coincidir con una entrada real de
    `apps.services.ai.providers._AI_PROVIDERS` -- este modelo NO
    reemplaza esa factory, la complementa: guarda la CONFIGURACION que
    antes solo vivia en variables de entorno, para que la consola pueda
    administrarla sin editar `.env` ni reiniciar el contenedor.
    """

    name = models.CharField(max_length=100, verbose_name="Nombre")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="Slug")
    provider_type = models.CharField(
        max_length=30, choices=PROVIDER_TYPE_CHOICES, verbose_name="Tipo"
    )
    description = models.TextField(blank=True, default="", verbose_name="Descripción")
    enabled = models.BooleanField(default=True, verbose_name="Habilitado")
    is_local = models.BooleanField(default=False, verbose_name="Local/self-hosted")
    base_url = models.CharField(max_length=500, blank=True, default="", verbose_name="Base URL")
    # Secreto CIFRADO (Fernet, apps.services.security.crypto -- mismo
    # mecanismo ya en produccion para passwords de buzones). NUNCA texto
    # plano, NUNCA se serializa completo hacia la API/UI (ver serializers).
    secret_encrypted = models.TextField(blank=True, default="", verbose_name="Secreto (cifrado)")
    default_timeout_s = models.PositiveIntegerField(
        default=120, verbose_name="Timeout por defecto (s)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "console_llm_provider"
        verbose_name = "Proveedor LLM"
        verbose_name_plural = "Proveedores LLM"
        ordering = ["name"]

    def __str__(self):
        return self.name


class LLMModelConfig(models.Model):
    """Modelo concreto dentro de un provider (plan Seccion 6, LLMModel conceptual)."""

    provider = models.ForeignKey(
        LLMProviderConfig,
        on_delete=models.CASCADE,
        related_name="models_config",
        verbose_name="Proveedor",
    )
    model_identifier = models.CharField(max_length=200, verbose_name="Identificador del modelo")
    display_name = models.CharField(
        max_length=200, blank=True, default="", verbose_name="Nombre visible"
    )
    enabled = models.BooleanField(default=True, verbose_name="Habilitado")
    context_window = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="Ventana de contexto"
    )
    max_output_tokens = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="Máx. tokens de salida"
    )
    supports_tools = models.BooleanField(default=False, verbose_name="Tool calling")
    supports_streaming = models.BooleanField(default=False, verbose_name="Streaming")
    supports_structured_output = models.BooleanField(
        default=False, verbose_name="Structured output"
    )
    supports_vision = models.BooleanField(default=False, verbose_name="Visión")
    supports_reasoning = models.BooleanField(default=False, verbose_name="Reasoning")
    # verified/verified_at: Regla Absoluta del plan "NO ASUMIR CAPACIDADES"
    # -- las 6 columnas de arriba solo deben marcarse True tras un
    # capability probe real (LLMCapabilities.verified, ver
    # apps/services/ai/providers/base.py), nunca a mano por adivinanza.
    verified = models.BooleanField(default=False, verbose_name="Capacidades verificadas")
    verified_at = models.DateTimeField(null=True, blank=True)
    # Fase 10 (Fallback + Health, plan Seccion 29/45): "ultimo health check"
    # es parte explicita del modelo de datos conceptual del plan (Seccion
    # 6, "last_health_check") -- separado de verified/verified_at (que es
    # sobre CAPACIDADES, no sobre si el servidor respondio la ULTIMA vez
    # que se probo). Poblado unicamente por LLMProviderTestConnectionView,
    # nunca a mano.
    last_health_check_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Ultimo health check"
    )
    last_health_reachable = models.BooleanField(
        null=True, blank=True, verbose_name="Alcanzable (ultimo check)"
    )
    # Fase 10: prioridad de fallback (plan Seccion 28, "definir una policy,
    # no una cadena hardcoded"). NULL = no es candidato de fallback (default
    # -- ver Regla Absoluta "NO ACTIVAR SIN HEALTH + CAPABILITY CHECK", un
    # modelo no debe entrar en la cadena de fallback solo por existir).
    # Numero MAS BAJO = MAS prioridad. Unicidad NO forzada a nivel de DB
    # (permite empates deliberados/reordenar sin migraciones); el resolver
    # ordena por este campo y desempata por verified_at.
    fallback_priority = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="Prioridad de fallback (menor = primero)"
    )
    metadata = models.JSONField(default=dict, blank=True, verbose_name="Metadata")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "console_llm_model"
        verbose_name = "Modelo LLM"
        verbose_name_plural = "Modelos LLM"
        unique_together = [("provider", "model_identifier")]
        ordering = ["provider__name", "model_identifier"]

    def __str__(self):
        return f"{self.provider.slug}/{self.model_identifier}"


class LLMActiveConfig(models.Model):
    """
    Configuración activa del sistema (plan Seccion 24, "Active Model").
    Se espera UNA sola fila real (la más reciente por `activated_at`) --
    no se fuerza a nivel de DB (permite historial completo + rollback,
    plan Seccion 27, sin borrar filas anteriores).
    """

    model_config = models.ForeignKey(
        LLMModelConfig, on_delete=models.PROTECT, related_name="activations", verbose_name="Modelo"
    )
    activated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="+", verbose_name="Activado por"
    )
    activated_at = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=500, blank=True, default="", verbose_name="Motivo")

    class Meta:
        db_table = "console_llm_active_config"
        verbose_name = "Configuración LLM activa"
        verbose_name_plural = "Historial de configuración LLM activa"
        ordering = ["-activated_at"]

    def __str__(self):
        return f"{self.model_config} (desde {self.activated_at:%Y-%m-%d %H:%M})"


class LLMProviderAuditLog(models.Model):
    """Auditoría de acciones sobre providers/modelos (plan Seccion 33). Nunca secretos."""

    ACTION_CHOICES = [
        ("PROVIDER_CREATE", "Creación de provider"),
        ("PROVIDER_UPDATE", "Actualización de provider"),
        ("PROVIDER_DELETE", "Eliminación de provider"),
        ("PROVIDER_TEST", "Prueba de conexión"),
        ("MODEL_ACTIVATE", "Activación de modelo"),
        ("MODEL_ROLLBACK", "Rollback a configuración anterior"),
    ]

    action = models.CharField(max_length=30, choices=ACTION_CHOICES, verbose_name="Acción")
    actor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="+", verbose_name="Actor"
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    provider = models.ForeignKey(
        LLMProviderConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="Proveedor",
    )
    # detail: JSON libre para contexto (provider/modelo anterior y nuevo,
    # latencia de la prueba, etc.) -- NUNCA claves/secretos (Regla Absoluta
    # del plan "NO REGISTRAR SECRETOS"). Los serializers/vistas que escriben
    # aqui son responsables de sanear antes de guardar.
    detail = models.JSONField(default=dict, blank=True, verbose_name="Detalle")
    result = models.CharField(max_length=20, default="OK", verbose_name="Resultado")

    class Meta:
        db_table = "console_llm_audit_log"
        verbose_name = "Auditoría LLM"
        verbose_name_plural = "Auditoría LLM"
        ordering = ["-timestamp"]
        indexes = [models.Index(fields=["action", "timestamp"])]

    def __str__(self):
        return f"{self.action} - {self.actor} - {self.timestamp}"
