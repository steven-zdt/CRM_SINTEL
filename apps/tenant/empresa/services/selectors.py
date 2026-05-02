"""
Selectores para Empresa v3.5 - Zero Waste Queries.
"""
from django.db.models import Q
from apps.tenant.empresa.models import Empresa

# Campos canónicos alineados con los serializers y UI
LIST_FIELDS = (
    "id",
    "razon_social",
    "nit",
    "dv",
    "direccion",
    "telefono",
    "email_contacto",
    "owner_email",
    "regimen_tributario",
    "moneda",
    "created_at",
    "updated_at",
)

DETAIL_FIELDS = (
    "id",
    "razon_social",
    "nit",
    "dv",
    "direccion",
    "telefono",
    "email_contacto",
    "owner_email",
    "regimen_tributario",
    "logo",
    "website",
    "moneda",
    "created_at",
    "updated_at",
)


class EmpresaSelector:
    """Selector para modelo Empresa (singleton por tenant)."""

    @staticmethod
    def get_list(search=None):
        """Retorna listado optimizado."""
        qs = Empresa.objects.only(*LIST_FIELDS)
        if search:
            qs = qs.filter(
                Q(razon_social__icontains=search) |
                Q(nit__icontains=search) |
                Q(email_contacto__icontains=search)
            )
        return qs

    @staticmethod
    def get_detail():
        """Retorna detalle de la empresa (singleton)."""
        return Empresa.objects.only(*DETAIL_FIELDS).first()

    @staticmethod
    def get_by_id(pk):
        """Retorna empresa por ID."""
        return Empresa.objects.filter(pk=pk).only(*DETAIL_FIELDS).first()
