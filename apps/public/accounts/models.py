from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class User(AbstractUser):
    """
    Modelo de usuario personalizado (Usuarios Globales).

    WARNING: ARQUITECTURA MULTI-TENANT:
    - Este modelo vive en el esquema 'public' (SHARED_APPS)
    - Los usuarios son GLOBALES y se comparten entre todos los tenants
    - NO puede tener dependencias hacia esquemas privados (apps.tenant.*)
    - NO puede tener ForeignKey, OneToOneField o ManyToMany hacia modelos de tenant

    WARNING: REGLA DE ORO:
    - La relación es UNIDIRECCIONAL: TenantProfile -> User (NO al revés)
    - TenantProfile (en esquema privado) puede referenciar a User (esquema public)
    - User (en esquema public) NO puede referenciar a TenantProfile (esquema privado)

    WARNING: PATRÓN DE DATOS:
    - User global: Datos personales (nombre, email, teléfono personal)
    - TenantProfile: Datos específicos del tenant (cargo, departamento, preferencias)

    El username se genera automáticamente desde el email si no se proporciona.
    """

    email = models.EmailField(
        _("email address"),
        unique=True,
        help_text=_("El email se usará para generar el username si no se proporciona uno."),
    )

    # Campos adicionales opcionales
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")

    # Manager personalizado que genera username desde email cuando no se proporciona
    objects = UserManager()

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        ordering = ["email"]

    def __str__(self):
        return self.email or self.username

    # La lógica de generación de username se delega al UserManager.


class DeletionAudit(models.Model):
    """Audit record for destructive user deletions.

    Stored in `public` schema so it survives tenant schema drops and
    provides traceability for administrative deletions.
    """

    target_user_id = models.BigIntegerField()
    deleted_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deletions_performed",
    )
    reason = models.CharField(max_length=255, blank=True, null=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "accounts_deletionaudit"
        verbose_name = "Deletion Audit"
        verbose_name_plural = "Deletion Audits"

    def __str__(self):
        return f"DeletionAudit target={self.target_user_id} by={self.deleted_by_id} at={self.created_at}"
