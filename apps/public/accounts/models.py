from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class User(AbstractUser):
    """
    Modelo de usuario personalizado (Usuarios Globales).
    
    ⚠️ ARQUITECTURA MULTI-TENANT:
    - Este modelo vive en el esquema 'public' (SHARED_APPS)
    - Los usuarios son GLOBALES y se comparten entre todos los tenants
    - NO puede tener dependencias hacia esquemas privados (apps.tenant.*)
    - NO puede tener ForeignKey, OneToOneField o ManyToMany hacia modelos de tenant
    
    ⚠️ REGLA DE ORO:
    - La relación es UNIDIRECCIONAL: TenantProfile -> User (NO al revés)
    - TenantProfile (en esquema privado) puede referenciar a User (esquema public)
    - User (en esquema public) NO puede referenciar a TenantProfile (esquema privado)
    
    ⚠️ PATRÓN DE DATOS:
    - User global: Datos personales (nombre, email, teléfono personal)
    - TenantProfile: Datos específicos del tenant (cargo, departamento, preferencias)
    
    El username se genera automáticamente desde el email si no se proporciona.
    """
    email = models.EmailField(
        _('email address'),
        unique=True,
        help_text=_('El email se usará para generar el username si no se proporciona uno.')
    )
    
    # Campos adicionales opcionales
    telefono = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='Teléfono'
    )
    
    # Manager personalizado que genera username desde email cuando no se proporciona
    objects = UserManager()

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['email']

    def __str__(self):
        return self.email or self.username

    # La lógica de generación de username se delega al UserManager.
