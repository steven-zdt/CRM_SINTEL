from django.contrib import admin

from .models import (
    ActivoFijo,
    CategoriaItem,
    HistorialServicio,
    MovimientoInventario,
    Producto,
    Servicio,
)


@admin.register(CategoriaItem)
class CategoriaItemAdmin(admin.ModelAdmin):
    list_display = ("nombre", "aplicacion", "empresa", "activo")
    list_filter = ("aplicacion", "activo", "empresa")
    search_fields = ("nombre", "descripcion")
    list_editable = ("activo",)


@admin.register(ActivoFijo)
class ActivoFijoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "categoria", "empresa", "estado", "costo_adquisicion")
    list_filter = ("estado", "empresa", "categoria")
    search_fields = ("codigo", "nombre", "marca", "modelo")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "categoria", "precio_venta", "stock_actual", "stock_minimo", "activo")
    list_filter = ("activo", "categoria", "empresa")
    search_fields = ("codigo", "nombre", "descripcion")
    list_editable = ("activo",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "categoria", "precio_venta", "activo")
    list_filter = ("activo", "categoria", "empresa")
    search_fields = ("codigo", "nombre", "descripcion")
    list_editable = ("activo",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = ("producto", "tipo", "cantidad", "costo_unitario", "created_at")
    list_filter = ("tipo", "created_at", "empresa")
    search_fields = ("producto__codigo", "producto__nombre", "origen_referencia")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"


@admin.register(HistorialServicio)
class HistorialServicioAdmin(admin.ModelAdmin):
    list_display = ("servicio", "fecha_registro", "cantidad", "valor_cobrado", "cliente_referencia")
    list_filter = ("fecha_registro", "empresa")
    search_fields = ("servicio__nombre", "cliente_referencia", "origen_referencia")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "fecha_registro"
