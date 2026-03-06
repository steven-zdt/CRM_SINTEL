"""
Admin para la app contabilidad (por tenant).
"""
from django.contrib import admin
from .models import CuentaContable, AsientoContable, MovimientoContable


@admin.register(CuentaContable)
class CuentaContableAdmin(admin.ModelAdmin):
    """Admin para el modelo CuentaContable."""
    list_display = ['codigo', 'nombre', 'tipo', 'activa', 'created_at']
    list_filter = ['tipo', 'activa', 'created_at']
    search_fields = ['codigo', 'nombre']
    ordering = ['codigo']


class MovimientoContableInline(admin.TabularInline):
    """Inline para movimientos de asiento."""
    model = MovimientoContable
    extra = 2
    fields = ['orden', 'cuenta', 'debe', 'haber', 'descripcion']


@admin.register(AsientoContable)
class AsientoContableAdmin(admin.ModelAdmin):
    """Admin para el modelo AsientoContable."""
    list_display = ['numero', 'fecha', 'descripcion', 'estado', 
                    'total_debe', 'total_haber', 'created_at']
    list_filter = ['estado', 'fecha', 'created_at']
    search_fields = ['numero', 'descripcion']
    readonly_fields = ['total_debe', 'total_haber', 'created_at', 'updated_at']
    inlines = [MovimientoContableInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('numero', 'fecha', 'descripcion', 'estado')
        }),
        ('Totales', {
            'fields': ('total_debe', 'total_haber')
        }),
        ('Relaciones', {
            'fields': ('factura',)
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(MovimientoContable)
class MovimientoContableAdmin(admin.ModelAdmin):
    """Admin para el modelo MovimientoContable."""
    list_display = ['asiento', 'orden', 'cuenta', 'debe', 'haber']
    list_filter = ['asiento', 'cuenta']
    search_fields = ['descripcion']
    ordering = ['asiento', 'orden']
