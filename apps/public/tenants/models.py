from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_tenants.models import TenantMixin, DomainMixin
from .validators import validate_schema_name


class Client(TenantMixin):
    """
    Modelo de Tenant conforme a la instalación oficial de django-tenants.
    Configuración crítica: auto_create_schema = True.
    """
    nombre = models.CharField(max_length=100)
    paid_until = models.DateField(null=True, blank=True)
    on_trial = models.BooleanField(default=True)
    created_on = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Activo"),
        help_text=_("Desactiva para suspender el servicio. El tenant no recibirá tráfico.")
    )

    auto_create_schema = True
    auto_drop_schema = True  # ⚠️ BORRADO TOTAL: Elimina el esquema automáticamente al borrar el Client

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'

    def clean(self) -> None:
        if self.schema_name:
            self.schema_name = self.schema_name.strip().lower()
            validate_schema_name(self.schema_name)

    def delete(self, *args, **kwargs):
        """
        Sobreescribe el método delete() para proteger el tenant público y registrar eliminaciones.
        
        ⚠️ CANDADO DE SEGURIDAD:
        - IMPOSIBLE borrar el tenant 'public' (núcleo del sistema)
        - Registra eliminaciones para auditoría
        
        ⚠️ BORRADO TOTAL:
        - Con auto_drop_schema=True, django-tenants eliminará automáticamente el esquema PostgreSQL
        - Las relaciones CASCADE eliminarán Domain y TenantMembership automáticamente
        - Los usuarios globales (User) NO se eliminan (pueden pertenecer a otros tenants)
        """
        from django_tenants.utils import get_public_schema_name
        import logging
        
        logger = logging.getLogger(__name__)
        public_schema = get_public_schema_name()
        
        # CANDADO DE SEGURIDAD: Proteger el tenant público (defensa en profundidad - capa modelo)
        if self.schema_name == public_schema:
            error_msg = "El esquema público no puede eliminarse bajo ningún motivo. Es el núcleo del sistema y es indeletable."
            import datetime
            security_logger = logging.getLogger('security.tenants')
            security_logger.critical(
                f"🚨 MODELO: INTENTO DE ELIMINAR TENANT PÚBLICO RECHAZADO | "
                f"schema={public_schema} | "
                f"time={datetime.datetime.now().isoformat()}"
            )
            logger.critical(f"INTENTO DE ELIMINAR TENANT PÚBLICO: {self.schema_name}")
            raise ValueError(error_msg)
        
        # Logging de seguridad para auditoría (sin emojis para evitar problemas de encoding)
        logger.warning(
            f"ELIMINANDO TENANT: {self.schema_name} ({self.nombre}) - "
            f"Esto borrara el esquema PostgreSQL y todos sus datos de forma permanente."
        )
        
        # Llamar al método padre (django-tenants manejará el borrado del esquema)
        return super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.schema_name} · {self.nombre}"

class Domain(DomainMixin):
    """Dominio asociado al tenant."""
    # CORRECCIÓN: Usamos 'tenant' para cumplir el estándar y evitar choques
    tenant = models.ForeignKey(
        Client,
        related_name="domains",
        on_delete=models.CASCADE
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant"],
                condition=models.Q(is_primary=True),
                name="unique_primary_domain_per_tenant",
            )
        ]

    def __str__(self):
        return getattr(self, "domain", f"Domain<{self.pk}>")


class TenantMembership(models.Model):
    """
    Modelo de membresía de usuarios a tenants.
    
    Relaciona usuarios globales con tenants específicos,
    permitiendo que un usuario sea miembro de múltiples tenants
    con diferentes roles.
    """
    ROLE_CHOICES = (
        ("ADMIN", "Admin"),
        ("STAFF", "Staff"),
        ("USER", "User"),
    )
    
    client = models.ForeignKey(
        "tenants.Client",
        on_delete=models.CASCADE,
        related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tenant_memberships"
    )
    rol = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default="ADMIN"
    )
    is_primary_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Activo"),
        help_text=_("Desactiva para revocar el acceso del usuario a este tenant.")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = (("client", "user"),)
        indexes = [
            models.Index(fields=["client", "user"]),
        ]
        verbose_name = "Membresía de Tenant"
        verbose_name_plural = "Membresías de Tenants"
    
    def clean(self):
        """
        Garantiza que solo exista un primary admin por tenant.

        Regla:
        - Si is_primary_admin=True, no puede existir otra TenantMembership
          con el mismo client y is_primary_admin=True.
        """
        super().clean()

        if self.is_primary_admin and self.client_id:
            qs = TenantMembership.objects.filter(
                client_id=self.client_id,
                is_primary_admin=True,
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)

            if qs.exists():
                raise ValidationError(
                    _("Ya existe un administrador principal para este tenant. "
                      "Solo puede haber un 'is_primary_admin=True' por tenant.")
                )

    def __str__(self):
        return f"{self.user.email} - {self.client.nombre} ({self.rol})"
