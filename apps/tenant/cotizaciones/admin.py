"""
Admin de Cotizaciones v2.60 - RESILIENTE
# WARNING: v2.60: Alineado con Desacoplamiento Radical.
Permite gestion de cotizaciones incluso con fallos en otros modulos.
"""
from django.contrib import admin
from django.db import connection
from django.utils.translation import gettext_lazy as _

from .configuracion.models import ConfiguracionCotizacion
from .models import Cotizacion, CotizacionItem, Producto, Servicio


class CotizacionItemInline(admin.TabularInline):
    """Edicion de items con Snapshot (Marca/Ref/Costo) visible."""
    model = CotizacionItem
    extra = 0
    fields = (
        'tipo_item', 'descripcion', 'marca', 'referencia', 
        'cantidad', 'unidad', 'costo_unitario', 'porcentaje_utilidad', 
        'precio_unitario_venta', 'subtotal_linea', 'orden'
    )
    readonly_fields = ('precio_unitario_venta', 'subtotal_linea')

@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    """
    Admin de Cabecera v2.60.
    Muestra el cliente real o el nombre manual de respaldo (Resiliencia).
    """
    list_display = (
        'numero_cotizacion', 'get_cliente_display', 'fecha_emision', 
        'total_con_impuestos', 'estado', 'tipo_cotizacion'
    )
    list_filter = ('estado', 'tipo_cotizacion', 'fecha_emision')
    search_fields = ('numero_cotizacion', 'cliente__razon_social', 'cliente__numero_documento')
    inlines = [CotizacionItemInline]
    
    fieldsets = (
        (_('Identificacion y Resiliencia'), {
            'fields': ('numero_cotizacion', 'empresa', 'estado', 'configuracion')
        }),
        (_('Datos del Cliente'), {
            'fields': ('cliente',)
        }),
        (_('DNA Financiero'), {
            'fields': (
                'tipo_cotizacion', 'fecha_vencimiento', 'iva_porcentaje',
                'porcentaje_aiu_admin', 'porcentaje_aiu_imprevistos', 'porcentaje_aiu_utilidad'
            )
        }),
        (_('Resultados'), {
            'fields': ('total_con_impuestos',),
        }),
    )
    readonly_fields = ('total_con_impuestos',)

    def get_cliente_display(self, obj):
        """Muestra el cliente en la lista."""
        return str(obj.cliente or _("Sin cliente definido"))
    get_cliente_display.short_description = _("Cliente / Respaldo")

    def has_module_permission(self, request):
        """Prevenir visualizacion en esquema publico (Tenancy)."""
        if connection.schema_name == 'public':
            return False
        return True

@admin.register(ConfiguracionCotizacion)
class ConfiguracionCotizacionAdmin(admin.ModelAdmin):
    """
    # WARNING: v2.60: Admin simplificado para modo User-Driven.
    
    Solo gestiona:
    1. Generacion de codigos (Prefijo, Sufijo, Semilla)
    2. Dias de validez de la cotizacion
    """
    list_display = ('nombre_configuracion', 'dias_validez', 'es_activo', 'empresa', 'ultimo_numero')
    list_filter = ('es_activo', 'empresa')
    search_fields = ('nombre_configuracion', 'prefijo_secuencia', 'sufijo_secuencia')
    
    fieldsets = (
        (_('Informacion General'), {
            'fields': ('empresa', 'nombre_configuracion', 'es_activo')
        }),
        (_('Configuracion de Validez'), {
            'description': _("Define los dias de validez de la cotizacion. Se usa para calcular automaticamente la fecha de vencimiento."),
            'fields': ('dias_validez',)
        }),
        (_('Generacion de Codigos (Folios Dinamicos)'), {
            'description': _("Configuracion para la generacion automatica de numeros de cotizacion."),
            'fields': (
                'prefijo_secuencia', 
                'sufijo_secuencia', 
                'semilla_inicial', 
                'ultimo_numero'
            )
        }),
    )
    
    readonly_fields = ('ultimo_numero',)
    
    def has_module_permission(self, request):
        """Prevenir visualizacion en esquema publico (Tenancy)."""
        if connection.schema_name == 'public':
            return False
        return True

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'marca', 'nombre', 'referencia', 'precio_venta', 'activo')
    search_fields = ('codigo', 'nombre', 'marca', 'referencia')

@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio_venta', 'activo')
    search_fields = ('nombre',)
