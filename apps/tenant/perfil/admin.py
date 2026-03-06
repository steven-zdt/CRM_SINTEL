"""
Admin para la app de perfil.
"""
from django.contrib import admin
from apps.tenant.perfil.models import TenantProfile


@admin.register(TenantProfile)
class TenantProfileAdmin(admin.ModelAdmin):
    """
    Admin para TenantProfile.
    
    ⚠️ IMPORTANTE: django-tenants maneja automáticamente el aislamiento por esquema.
    No es necesario filtrar manualmente por tenant_id.
    """
    list_display = ['user', 'cargo', 'departamento', 'telefono_corporativo', 'created_at']
    list_filter = ['departamento', 'created_at']
    search_fields = ['user__email', 'user__username', 'cargo', 'departamento']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Usuario', {
            'fields': ('user',)
        }),
        ('Información Laboral', {
            'fields': ('cargo', 'departamento', 'telefono_corporativo')
        }),
        ('Perfil', {
            'fields': ('avatar',)
        }),
        ('Configuración', {
            'fields': ('configuracion',),
            'description': 'Preferencias de UI y configuración personalizada (JSON)'
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
