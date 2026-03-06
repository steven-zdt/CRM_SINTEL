"""
Admin para clientes (aislado por tenant).

django-tenants maneja automáticamente el aislamiento por esquema.
"""
from django.contrib import admin
from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("razon_social", "numero_documento", "tipo_persona", "tipo_documento", "regimen_tributario", "activo")
    search_fields = ("razon_social", "numero_documento", "nombre_comercial", "email", "telefono")
    list_filter = ("tipo_persona", "tipo_documento", "regimen_tributario", "activo", "ciudad", "empresa")
    readonly_fields = ("created_at", "updated_at")
    
    fieldsets = (
        ("Identificación", {
            "fields": ("empresa", "tipo_persona", "tipo_documento", "numero_documento", "razon_social", "nombre_comercial")
        }),
        ("Información Tributaria", {
            "fields": ("regimen_tributario",)
        }),
        ("Contacto", {
            "fields": ("email", "telefono", "direccion", "ciudad")
        }),
        ("Estado y Observaciones", {
            "fields": ("activo", "observaciones")
        }),
        ("Auditoría", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    
    ordering = ["razon_social"]


