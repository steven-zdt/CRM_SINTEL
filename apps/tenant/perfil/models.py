"""
Modelo de Perfil Privado del Colaborador.

⚠️ ARQUITECTURA MULTI-TENANT:
- Este modelo vive en el esquema del tenant (TENANT_APPS)
- Tiene una relación OneToOneField con User (que está en SHARED_APPS/public)
- Django permite relaciones FK/OneToOne desde tenant hacia public (pero no al revés)

⚠️ PATRÓN DE DATOS:
- User global: Datos personales (nombre, email, teléfono personal)
- TenantProfile: Datos específicos del tenant (cargo, departamento, teléfono corporativo, preferencias)
"""
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class TenantProfile(models.Model):
    """
    Perfil privado del colaborador dentro de un tenant específico.
    
    ⚠️ ARQUITECTURA MULTI-TENANT:
    - Este modelo vive en el esquema del tenant (TENANT_APPS)
    - Tiene una relación OneToOneField con User (que está en SHARED_APPS/public)
    - Django permite relaciones FK/OneToOne desde tenant hacia public (pero no al revés)
    
    ⚠️ REGLA DE ORO:
    - La relación es UNIDIRECCIONAL: TenantProfile -> User (NO al revés)
    - TenantProfile (esquema privado) SÍ puede referenciar a User (esquema public)
    - User (esquema public) NO puede referenciar a TenantProfile (esquema privado)
    
    ⚠️ PATRÓN DE DATOS:
    - User global: Datos personales (nombre, email, teléfono personal)
    - TenantProfile: Datos específicos del tenant (cargo, departamento, teléfono corporativo, preferencias)
    
    Este modelo almacena datos específicos del usuario que solo aplican
    dentro del contexto de un tenant particular, sin "contaminar" el
    modelo de usuario global.
    
    Ejemplo:
    - Usuario: juan@example.com (global, en esquema public)
    - Tenant A: Cargo="Contador Senior", Departamento="Finanzas" (en esquema tenant_a)
    - Tenant B: Cargo="Auxiliar Administrativo", Departamento="RRHH" (en esquema tenant_b)
    
    El mismo usuario puede tener diferentes perfiles en diferentes tenants.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,  # ✅ CORRECTO: Referencia a User (esquema public)
        on_delete=models.CASCADE,
        related_name='tenant_profile',  # ✅ CORRECTO: related_name permite acceso desde User
        verbose_name=_('Usuario'),
        help_text=_('Usuario global al que pertenece este perfil (reside en esquema public)')
    )
    
    cargo = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Cargo'),
        help_text=_('Cargo del colaborador en esta empresa (ej: "Contador Senior", "Auxiliar Administrativo")')
    )
    
    departamento = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Departamento'),
        help_text=_('Departamento al que pertenece el colaborador (opcional)')
    )
    
    telefono_corporativo = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_('Teléfono Corporativo'),
        help_text=_('Teléfono corporativo del colaborador (diferente al teléfono personal del User global)')
    )
    
    avatar = models.ImageField(
        upload_to='perfiles/avatars/',
        blank=True,
        null=True,
        verbose_name=_('Avatar'),
        help_text=_('Foto de perfil del colaborador (opcional)')
    )
    
    configuracion = models.JSONField(
        default=dict,
        null=True,
        blank=True,
        verbose_name=_('Configuración'),
        help_text=_('Preferencias de UI y configuración personalizada del colaborador (JSON). Si es NULL, se normaliza a {} en la aplicación.')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Fecha de Creación')
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Fecha de Actualización')
    )
    
    class Meta:
        verbose_name = 'Perfil del Colaborador'
        verbose_name_plural = 'Perfiles de Colaboradores'
        indexes = [
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        """
        Representación legible del perfil.
        
        Retorna: "email@example.com - Cargo"
        """
        return f"{self.user.email} - {self.cargo}"
