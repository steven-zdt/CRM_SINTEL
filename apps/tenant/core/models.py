"""
Modelos base para arquitectura SSoT (Single Source of Truth) de SINTEL v2.61.4.

Este módulo define:
1. SintelTenantBaseModel: Modelo abstracto que todos los modelos de TENANT_APPS deben heredar
2. Campos obligatorios: empresa (ForeignKey NOT NULL), created_at, updated_at
3. Índices automáticos para optimización de queries

[ARCHITECTURE v2.61.4] REGLA FUNDAMENTAL:
- TODA clase de modelo en TENANT_APPS debe heredar de SintelTenantBaseModel
- El campo `empresa` es obligatorio (null=False, blank=False)
- django-tenants maneja el aislamiento de esquemas automáticamente
- Los servicios SIEMPRE reciben `empresa` como primer parámetro

Ejemplo:
    class MiModelo(SintelTenantBaseModel):
        nombre = models.CharField(max_length=255)
        
        class Meta:
            ordering = ['-created_at']
            indexes = [
                models.Index(fields=['empresa', 'nombre']),  # Añade más índices si necesita
            ]

Ventajas:
- Herencia automática de auditoría (created_at, updated_at)
- Aislamiento automático por tenant via empresa FK
- Patrón consistente en toda la codebase
- Facilita migraciones y refactoring
- Garantiza SSoT (empresa es la única fuente de verdad de contexto)
"""

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class SintelTenantBaseModel(models.Model):
    """
    Modelo abstracto base para TODA data en TENANT_APPS.
    
    [REGLA GOLDENA v2.61.4] TODOS los modelos de tenant DEBEN heredar de esto.
    
    Campos:
    - empresa: ForeignKey obligatoria a Empresa (SSoT de contexto multi-tenant)
    - created_at: Timestamp de creación automático
    - updated_at: Timestamp de última modificación automático
    
    Índices:
    - Meta.indexes SIEMPRE debe incluir models.Index(fields=["empresa"])
      (django-tenants lo usa para consultas eficientes por tenant)
    
    [TECHNICAL NOTE] Abstract=True significa:
    - Esta clase NO tiene tabla de BD
    - Solo proporciona campos y comportamiento heredables
    - Cada clase hija tiene su propia tabla
    - Favorece DRY (Don't Repeat Yourself)
    """
    
    empresa = models.ForeignKey(
        'empresa.Empresa',
        on_delete=models.PROTECT,
        related_name='%(app_label)s_%(class)s_related',
        verbose_name=_('Empresa'),
        help_text=_('Empresa propietaria (SSoT por tenant). Requerido.'),
        null=False,  # [CRITICAL] No puede ser NULL
        blank=False,  # [CRITICAL] Obligatorio en formularios
        db_index=True,  # [PERFORMANCE] Índice automático para queries frecuentes
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Creado'),
        help_text=_('Timestamp auto-asignado al crear el registro.'),
        db_index=True,  # [PERFORMANCE] Útil para ordenar por fecha
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Actualizado'),
        help_text=_('Timestamp auto-actualizado al modificar.'),
        db_index=True,  # [PERFORMANCE] Útil para detectar cambios recientes
    )
    
    class Meta:
        abstract = True  # [CRITICAL] Este modelo no tiene tabla de BD
        ordering = ['-created_at']  # Defecto: más recientes primero
        
        # [SHIELD v2.61.4] Índices OBLIGATORIOS para todos los modelos hijos
        # Los modelos hijos PUEDEN añadir más índices específicos en su Meta.indexes
        indexes = [
            models.Index(fields=['empresa']),  # [CRITICAL] Requerido por django-tenants
            models.Index(fields=['empresa', '-created_at']),  # Patrón común: empresa + fecha
        ]
    
    def __str__(self):
        if hasattr(self, 'nombre'):
            return f"{self.nombre}"
        elif hasattr(self, 'razon_social'):
            return f"{self.razon_social}"
        elif hasattr(self, 'titulo'):
            return f"{self.titulo}"
        elif hasattr(self, 'description'):
            return f"{self.description}"
        else:
            return f"{self.__class__.__name__}({self.pk})"
    
    def save(self, *args, **kwargs):
        """
        Sobrescribe save() para garantizar que empresa NUNCA sea NULL.
        [SHIELD] Protección adicional contra asignación accidental de NULL.
        """
        if not getattr(self, 'empresa_id', None):
            raise ValueError(
                f"[ERROR] {self.__class__.__name__}.empresa no puede ser NULL. "
                f"Todos los registros en TENANT_APPS deben tener empresa asignada explícitamente."
            )
        super().save(*args, **kwargs)


__all__ = ['SintelTenantBaseModel']