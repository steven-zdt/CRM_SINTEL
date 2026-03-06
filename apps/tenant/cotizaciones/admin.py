"""
Admin de Cotizaciones v2.60 - RESILIENTE
⚠️ v2.60: Alineado con Desacoplamiento Radical.
Permite gestión de cotizaciones incluso con fallos en otros módulos.
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.db.utils import ProgrammingError, OperationalError
from django.db import connection
from .models import Producto, Servicio, Cotizacion, CotizacionItem
from .configuracion.models import ConfiguracionCotizacion

class CotizacionItemInline(admin.TabularInline):
    """Edición de ítems con Snapshot (Marca/Ref/Costo) visible."""
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
        (_('Identificación y Resiliencia'), {
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
        """Prevenir visualización en esquema público (Tenancy)."""
        if connection.schema_name == 'public':
            return False
        return True

@admin.register(ConfiguracionCotizacion)
class ConfiguracionCotizacionAdmin(admin.ModelAdmin):
    """
    ⚠️ v2.60: Admin simplificado para modo User-Driven.
    
    Solo gestiona:
    1. Generación de códigos (Prefijo, Sufijo, Semilla)
    2. Días de validez de la cotización
    """
    list_display = ('nombre_configuracion', 'dias_validez', 'es_activo', 'empresa', 'ultimo_numero')
    list_filter = ('es_activo', 'empresa')
    search_fields = ('nombre_configuracion', 'prefijo_secuencia', 'sufijo_secuencia')
    
    fieldsets = (
        (_('Información General'), {
            'fields': ('empresa', 'nombre_configuracion', 'es_activo')
        }),
        (_('Configuración de Validez'), {
            'description': _("Define los días de validez de la cotización. Se usa para calcular automáticamente la fecha de vencimiento."),
            'fields': ('dias_validez',)
        }),
        (_('Generación de Códigos (Folios Dinámicos)'), {
            'description': _("Configuración para la generación automática de números de cotización."),
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
        """Prevenir visualización en esquema público (Tenancy)."""
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