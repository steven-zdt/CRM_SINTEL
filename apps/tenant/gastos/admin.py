"""
Admin para gastos (aislado por tenant).

WARNING: v2.40: Sistema de Documento Soporte Inmutable según normativa DIAN.
django-tenants maneja automáticamente el aislamiento por esquema.
"""
from django.contrib import admin

from .models import DocumentoSoporte, Gasto, ResolucionDIAN


@admin.register(ResolucionDIAN)
class ResolucionDIANAdmin(admin.ModelAdmin):
    """Admin para Resoluciones DIAN."""
    list_display = ['numero_resolucion', 'prefijo', 'rango_desde', 'rango_hasta', 'fecha_resolucion', 'vigente', 'empresa']
    list_filter = ['vigente', 'fecha_resolucion']
    search_fields = ['numero_resolucion', 'prefijo']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(DocumentoSoporte)
class DocumentoSoporteAdmin(admin.ModelAdmin):
    """Admin para Documentos Soporte."""
    list_display = ['numero_documento', 'fecha', 'vendedor_nombre', 'vendedor_nit', 'subtotal', 'retefuente', 'reteica', 'total', 'anulado']
    list_filter = ['anulado', 'fecha', 'resolucion_dian']
    search_fields = ['numero_documento', 'vendedor_nombre', 'vendedor_nit', 'numero_factura_proveedor']
    date_hierarchy = 'fecha'
    readonly_fields = ['consecutivo', 'created_at', 'updated_at', 'numero_documento']


@admin.register(Gasto)
class GastoAdmin(admin.ModelAdmin):
    """Admin para Gastos (clasificación contable)."""
    list_display = ['id', 'numero_documento', 'fecha', 'periodo', 'centro_costo', 'categoria_contable', 'total']
    list_filter = ['periodo', 'centro_costo', 'categoria_contable']
    search_fields = ['descripcion', 'observaciones', 'documento_soporte__numero_documento']
    readonly_fields = ['created_at', 'updated_at', 'numero_documento', 'fecha', 'subtotal', 'retefuente', 'reteica', 'total']
    
    def numero_documento(self, obj):
        """Muestra el número del documento soporte."""
        return obj.numero_documento
    numero_documento.short_description = 'Documento'
    
    def fecha(self, obj):
        """Muestra la fecha del documento soporte."""
        return obj.fecha
    fecha.short_description = 'Fecha'
    
    def subtotal(self, obj):
        """Muestra el subtotal del documento soporte."""
        return obj.subtotal
    subtotal.short_description = 'Subtotal'
    
    def retefuente(self, obj):
        """Muestra la retefuente del documento soporte."""
        return obj.retefuente
    retefuente.short_description = 'Retefuente'
    
    def reteica(self, obj):
        """Muestra la reteica del documento soporte."""
        return obj.reteica
    reteica.short_description = 'ReteICA'
    
    def total(self, obj):
        """Muestra el total del documento soporte."""
        return obj.total
    total.short_description = 'Total'
