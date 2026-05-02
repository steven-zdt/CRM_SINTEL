"""
Admin para la app facturas (por tenant).
"""
from django.contrib import admin

from .models import Factura, FacturaAnexos, ItemFactura


class ItemFacturaInline(admin.TabularInline):
    """Inline para items de factura."""
    model = ItemFactura
    extra = 1
    fields = ['orden', 'codigo', 'descripcion', 'cantidad', 'unidad_medida', 
              'valor_unitario', 'porcentaje_iva', 'subtotal', 'total']


@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    """Admin para el modelo Factura."""
    list_display = ['numero', 'tipo', 'estado', 'fecha_emision', 
                    'receptor_razon_social', 'total', 'created_at']
    list_filter = ['tipo', 'estado', 'fecha_emision', 'created_at']
    search_fields = ['numero', 'receptor_razon_social', 'receptor_nit', 'cufe']
    readonly_fields = ['created_at', 'updated_at', 'cufe', 'qr_code']
    inlines = [ItemFacturaInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('numero', 'prefijo', 'consecutivo', 'tipo', 'estado')
        }),
        ('Fechas', {
            'fields': ('fecha_emision', 'fecha_vencimiento')
        }),
        ('Emisor', {
            'fields': ('emisor_nit', 'emisor_razon_social')
        }),
        ('Receptor', {
            'fields': ('receptor_nit', 'receptor_razon_social', 'receptor_direccion')
        }),
        ('Totales', {
            'fields': ('subtotal', 'impuestos', 'total')
        }),
        ('DIAN', {
            'fields': ('cufe', 'qr_code', 'xml_content', 'xml_file_path')
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ItemFactura)
class ItemFacturaAdmin(admin.ModelAdmin):
    """Admin para el modelo ItemFactura."""
    list_display = ['factura', 'orden', 'descripcion', 'cantidad', 'valor_unitario', 'total']
    list_filter = ['factura']
    search_fields = ['descripcion', 'codigo']
    ordering = ['factura', 'orden']


@admin.register(FacturaAnexos)
class FacturaAnexosAdmin(admin.ModelAdmin):
    """Admin para el modelo FacturaAnexos."""
    list_display = ['factura', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['factura__numero']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Factura', {
            'fields': ('factura',)
        }),
        ('Archivos', {
            'fields': ('pdf_file', 'ubl_xml', 'application_response_xml'),
            'classes': ('collapse',)
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
