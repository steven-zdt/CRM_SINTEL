"""
Admin para proveedores (aislado por tenant).

⚠️ v2.40: Alineado con modelo actual.
django-tenants maneja automáticamente el aislamiento por esquema.
"""
from django.contrib import admin
from .models import Proveedor


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    """
    ⚠️ v2.40: Admin alineado con modelo actual.
    """
    list_display = ("razon_social", "numero_documento", "tipo_persona", "tipo_documento", "regimen_tributario", "activo")
    search_fields = ("razon_social", "numero_documento", "nombre_comercial", "email_contacto")
    list_filter = ("tipo_persona", "tipo_documento", "regimen_tributario", "activo", "ciudad")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Identificación Legal", {
            "fields": ("tipo_persona", "tipo_documento", "numero_documento", "digito_verificacion", "razon_social", "nombre_comercial")
        }),
        ("Información Tributaria", {
            "fields": ("regimen_tributario", "actividad_economica_ciiu", "responsable_iva", "gran_contribuyente", "autoretenedor")
        }),
        ("Contacto y Ubicación", {
            "fields": ("email_contacto", "telefono_contacto", "direccion", "ciudad")
        }),
        ("Información Comercial y Bancaria", {
            "fields": ("plazo_pago_dias", "banco", "tipo_cuenta", "numero_cuenta")
        }),
        ("Estado", {
            "fields": ("activo", "observaciones")
        }),
        ("Auditoría", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

