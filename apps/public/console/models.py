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
