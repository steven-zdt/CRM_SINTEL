"""
Admin para la app contabilidad (por tenant).

⚠️ NORMATIVA: Actualizado para mostrar campos de normativa NIIF Colombia.
"""
from django.contrib import admin
from decimal import Decimal
from .models import CuentaContable, AsientoContable, MovimientoContable


@admin.register(CuentaContable)
class CuentaContableAdmin(admin.ModelAdmin):
    """
    Admin para el modelo CuentaContable.
    
    ⚠️ NORMATIVA: Incluye campo nivel para validación de normativa.
    """
    list_display = ['codigo', 'nombre', 'tipo', 'nivel', 'activa', 'created_at']
    list_filter = ['tipo', 'nivel', 'activa', 'created_at']
    search_fields = ['codigo', 'nombre']
    ordering = ['codigo']
    fieldsets = (
        ('Información Básica', {
            'fields': ('codigo', 'nombre', 'tipo', 'nivel', 'descripcion')
        }),
        ('Relaciones', {
            'fields': ('cuenta_padre', 'catalogo_referencia', 'empresa')
        }),
        ('Estado', {
            'fields': ('activa',)
        }),
        ('Metadatos', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


class MovimientoContableInline(admin.TabularInline):
    """
    Inline para movimientos de asiento.
    
    ⚠️ NORMATIVA: Incluye campos de terceros y tributarios.
    """
    model = MovimientoContable
    extra = 2
    fields = [
        'orden', 'cuenta', 'debe', 'haber', 'descripcion',
        'tipo_tercero', 'tercero_nit', 'tercero_razon_social'
    ]
    readonly_fields = ['base_iva', 'iva_generado', 'iva_descontable', 'retefuente', 'reteica']


@admin.register(AsientoContable)
class AsientoContableAdmin(admin.ModelAdmin):
    """
    Admin para el modelo AsientoContable.
    
    ⚠️ NORMATIVA: Incluye campos de comprobante y validación de partida doble.
    """
    list_display = [
        'numero', 'fecha', 'descripcion', 'estado',
        'tipo_comprobante', 'numero_comprobante',
        'total_debe', 'total_haber', 'diferencia_display', 'created_at'
    ]
    list_filter = ['estado', 'tipo_comprobante', 'fecha', 'created_at']
    search_fields = ['numero', 'descripcion', 'numero_comprobante']
    readonly_fields = ['total_debe', 'total_haber', 'created_at', 'updated_at', 'diferencia_display']
    inlines = [MovimientoContableInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('numero', 'fecha', 'descripcion', 'estado')
        }),
        ('Comprobante (Trazabilidad)', {
            'fields': ('tipo_comprobante', 'numero_comprobante')
        }),
        ('Totales', {
            'fields': ('total_debe', 'total_haber', 'diferencia_display')
        }),
        ('Relaciones', {
            'fields': ('factura', 'empresa')
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def diferencia_display(self, obj):
        """Muestra la diferencia entre debe y haber (debe ser 0 para estar cuadrado)."""
        diferencia = abs(obj.total_debe - obj.total_haber)
        if diferencia < Decimal('0.01'):
            return f"✓ ${diferencia:,.2f}"
        return f"❌ ${diferencia:,.2f}"
    diferencia_display.short_description = 'Diferencia (Partida Doble)'


@admin.register(MovimientoContable)
class MovimientoContableAdmin(admin.ModelAdmin):
    """
    Admin para el modelo MovimientoContable.
    
    ⚠️ NORMATIVA: Incluye campos de terceros y tributarios según normativa colombiana.
    """
    list_display = [
        'asiento', 'orden', 'cuenta', 'tercero_razon_social', 'tercero_nit',
        'debe', 'haber', 'iva_generado', 'iva_descontable', 'retefuente', 'reteica'
    ]
    list_filter = ['tipo_tercero', 'asiento__estado', 'cuenta']
    search_fields = ['descripcion', 'tercero_nit', 'tercero_razon_social', 'cuenta__codigo']
    readonly_fields = [
        'base_iva', 'iva_generado', 'iva_descontable', 'retefuente', 'reteica'
    ]
    ordering = ['asiento', 'orden']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('asiento', 'cuenta', 'descripcion', 'orden')
        }),
        ('Valores', {
            'fields': ('debe', 'haber')
        }),
        ('Tercero (Obligatorio según Normativa)', {
            'fields': ('tipo_tercero', 'tercero_id', 'tercero_nit', 'tercero_razon_social')
        }),
        ('Cálculos Tributarios (Automáticos)', {
            'fields': ('base_iva', 'iva_generado', 'iva_descontable', 'retefuente', 'reteica'),
            'classes': ('collapse',)
        }),
    )