from django.contrib import admin
from .models import OrdenCompra, ItemOrdenCompra


class ItemOrdenCompraInline(admin.TabularInline):
    model = ItemOrdenCompra
    extra = 0
    readonly_fields = ('valor_iva', 'subtotal', 'total')


@admin.register(OrdenCompra)
class OrdenCompraAdmin(admin.ModelAdmin):
    list_display = ('consecutivo', 'fecha', 'proveedor', 'proyecto', 'estado', 'total')
    list_filter = ('estado', 'fecha')
    search_fields = ('consecutivo', 'proveedor__razon_social', 'observaciones')
    inlines = [ItemOrdenCompraInline]
    readonly_fields = ('subtotal', 'impuestos', 'total', 'created_at', 'updated_at')
