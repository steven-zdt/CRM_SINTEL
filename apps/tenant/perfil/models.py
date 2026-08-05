import uuid
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.tenant.core.models import SintelTenantBaseModel


class RolTenant(models.TextChoices):
    """Roles posibles de un colaborador dentro del tenant."""
    ADMIN = 'ADMIN', 'Administrador'
    OPERADOR = 'OPERADOR', 'Operador'
    VISOR = 'VISOR', 'Visor'


class Departamento(SintelTenantBaseModel):
    """
    Departamento o area organizacional para agrupar perfiles dentro del tenant.
    """
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True,
        editable=False,
        verbose_name=_('UUID')
    )
    nombre = models.CharField(
        max_length=100,
        verbose_name=_('Nombre'),
        help_text=_('Nombre del departamento')
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Descripcion'),
        help_text=_('Descripcion del departamento')
    )
    activo = models.BooleanField(
        default=True,
        verbose_name=_('Activo'),
        help_text=_('Determina si el departamento esta activo')
    )

    class Meta:
        db_table = 'perfil_departamento'
        unique_together = ('nombre', 'empresa')
        verbose_name = 'Departamento'
        verbose_name_plural = 'Departamentos'

    def __str__(self):
        return f"{self.nombre}"


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
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True,
        editable=False,
        verbose_name=_('UUID')
    )
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tenant_profile',
        verbose_name=_('Usuario'),
        help_text=_('Usuario global al que pertenece este perfil (reside en esquema public)')
    )

    # WARNING: [ARQ-A2] Excepcion documentada e intencional a SintelTenantBaseModel
    # (que inyecta empresa con on_delete=PROTECT). EmpresaViewSet.destroy() (STAFF/ADMIN
    # unicamente, ver apps/tenant/empresa/api/viewsets.py) permite eliminar la Empresa
    # del tenant; un TenantProfile no tiene sentido sin la empresa a la que pertenece y
    # debe desaparecer junto con ella, no bloquear su eliminacion.
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
    
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='perfiles',
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

    sedes_asignadas = models.ManyToManyField(
        'empresa.Sede',
        blank=True,
        related_name='perfiles_asignados',
        verbose_name=_('Sedes Asignadas'),
        help_text=_('Sedes a las que el colaborador tiene acceso asignado')
    )

    areas_asignadas = models.ManyToManyField(
        'empresa.Area',
        blank=True,
        related_name='perfiles_asignados',
        verbose_name=_('Areas Asignadas'),
        help_text=_('Areas a las que el colaborador tiene acceso asignado')
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
        email = getattr(self.user, 'email', 'Sin email')
        cargo_str = self.cargo or 'Sin cargo'
        return f"{email} - {cargo_str}"