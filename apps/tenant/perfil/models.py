"""
Modelo de Perfil Privado del Colaborador.

ARQUITECTURA MULTI-TENANT:
- Este modelo vive en el esquema del tenant (TENANT_APPS)
- Tiene una relacion OneToOneField con User (que esta en SHARED_APPS/public)
- Django permite relaciones FK/OneToOne desde tenant hacia public (pero no al reves)

PATRON DE DATOS:
- User global: Datos personales (nombre, email, telefono personal)
- TenantProfile: Datos especificos del tenant (cargo, departamento, telefono corporativo, preferencias)
"""
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.tenant.core.models import SintelTenantBaseModel


class RolTenant(models.TextChoices):
    """Roles posibles de un colaborador dentro del tenant."""
    ADMIN = 'ADMIN', 'Administrador'
    OPERADOR = 'OPERADOR', 'Operador'
    VISOR = 'VISOR', 'Visor'


class TenantProfile(SintelTenantBaseModel):
    """
    Perfil privado del colaborador dentro de un tenant especifico.
    
    ARQUITECTURA MULTI-TENANT:
    - Este modelo vive en el esquema del tenant (TENANT_APPS)
    - Tiene una relacion OneToOneField con User (que esta en SHARED_APPS/public)
    
    REGLA DE ORO:
    - La relacion es UNIDIRECCIONAL: TenantProfile -> User (NO al reves)
    - TenantProfile (esquema privado) SI puede referenciar a User (esquema public)
    
    PATRON DE DATOS:
    - User global: Datos personales
    - TenantProfile: Datos especificos del tenant
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tenant_profile',
        verbose_name=_('Usuario'),
        help_text=_('Usuario global al que pertenece este perfil (reside en esquema public)')
    )

    empresa = models.ForeignKey(
        'empresa.Empresa',
        on_delete=models.CASCADE,
        related_name='perfiles_tenant',
        verbose_name=_('Empresa'),
        help_text=_('Empresa a la que pertenece este perfil (multi-tenant isolation)')
    )
    
    cargo = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Cargo'),
        help_text=_('Cargo del colaborador en esta empresa')
    )
    
    departamento = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Departamento'),
        help_text=_('Departamento al que pertenece el colaborador')
    )
    
    telefono_corporativo = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_('Telefono Corporativo'),
        help_text=_('Telefono corporativo del colaborador (diferente al personal)')
    )
    
    avatar = models.ImageField(
        upload_to='perfiles/avatars/',
        blank=True,
        null=True,
        verbose_name=_('Avatar'),
        help_text=_('Foto de perfil del colaborador')
    )
    
    configuracion = models.JSONField(
        default=dict,
        null=True,
        blank=True,
        verbose_name=_('Configuracion'),
        help_text=_('Preferencias de UI y configuracion personalizada del colaborador (JSON).')
    )

    rol = models.CharField(
        max_length=20,
        choices=RolTenant.choices,
        default=RolTenant.OPERADOR,
        db_index=True,
        verbose_name=_('Rol'),
        help_text=_('Rol del colaborador en el tenant: ADMIN (admin), OPERADOR (puede editar), VISOR (solo lectura).')
    )

    class Meta:
        db_table = 'perfil_tenantprofile'
        unique_together = ('user', 'empresa')
        verbose_name = 'Perfil del Colaborador'
        verbose_name_plural = 'Perfiles de Colaboradores'
        indexes = [
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.cargo}"