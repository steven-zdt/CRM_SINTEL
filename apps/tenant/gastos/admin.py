"""
Admin para gastos (aislado por tenant).

v2.62: FLEXIBILIDAD OPERATIVA - Inmutabilidad deshabilitada.
django-tenants maneja automaticamente el aislamiento por esquema.
"""
from django.contrib import admin

from .models import DocumentoSoporte, ResolucionDIAN


@admin.register(ResolucionDIAN)
class ResolucionDIANAdmin(admin.ModelAdmin):
    """Admin para Resoluciones DIAN."""
    list_display = ['numero_resolucion', 'prefijo', 'rango_desde', 'rango_hasta', 'fecha_resolucion', 'vigente', 'empresa']
    list_filter = ['vigente', 'fecha_resolucion']
    search_fields = ['numero_resolucion', 'prefijo']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(DocumentoSoporte)
class DocumentoSoporteAdmin(admin.ModelAdmin):
    """Admin para Documentos Soporte (Gasto Unificado)."""
    list_display = [
        'numero_documento', 'fecha', 'proveedor', 
        'categoria_contable', 'total', 'anulado'
    ]
    list_filter = ['anulado', 'fecha', 'categoria_contable', 'resolucion_dian']
    search_fields = [
        'prefijo', 'consecutivo', 'proveedor__razon_social', 
        'descripcion', 'numero_documento_proveedor'
    ]
    date_hierarchy = 'fecha'
    readonly_fields = [
        'consecutivo', 'created_at', 'updated_at', 
        'numero_documento', 'subtotal', 'total'
    ]
