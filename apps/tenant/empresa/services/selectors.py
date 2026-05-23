"""
Selectores para Empresa v3.5 - Zero Waste Queries.
"""
from django.db.models import Q
from apps.tenant.empresa.models import Empresa, Sede, Area

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

SEDE_LIST_FIELDS = (
    "id",
    "uuid",
    "nombre",
    "direccion",
    "telefono",
    "encargado_nombre",
    "created_at",
    "updated_at",
)

SEDE_DETAIL_FIELDS = SEDE_LIST_FIELDS

AREA_LIST_FIELDS = (
    "id",
    "uuid",
    "sede__id",
    "sede__uuid",
    "sede__nombre",
    "nombre",
    "codigo_funcionamiento",
    "created_at",
    "updated_at",
)

AREA_DETAIL_FIELDS = AREA_LIST_FIELDS


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


class SedeSelector:
    """Selector para el modelo Sede."""

    @staticmethod
    def get_list(empresa_id, search=None):
        """Retorna listado optimizado de sedes para una empresa."""
        qs = Sede.objects.filter(empresa_id=empresa_id).only(*SEDE_LIST_FIELDS)
        if search:
            qs = qs.filter(
                Q(nombre__icontains=search) |
                Q(direccion__icontains=search) |
                Q(encargado_nombre__icontains=search)
            )
        return qs

    @staticmethod
    def get_by_uuid(empresa_id, uuid):
        """Retorna una sede especifica por su UUID y empresa_id (anti-IDOR)."""
        return Sede.objects.filter(empresa_id=empresa_id, uuid=uuid).only(*SEDE_DETAIL_FIELDS).first()


class AreaSelector:
    """Selector para el modelo Area."""

    @staticmethod
    def get_list(empresa_id, search=None):
        """Retorna listado optimizado de areas con relacion de sede."""
        qs = Area.objects.filter(empresa_id=empresa_id).select_related('sede').only(*AREA_LIST_FIELDS)
        if search:
            qs = qs.filter(
                Q(nombre__icontains=search) |
                Q(codigo_funcionamiento__icontains=search) |
                Q(sede__nombre__icontains=search)
            )
        return qs

    @staticmethod
    def get_by_uuid(empresa_id, uuid):
        """Retorna una area especifica por su UUID."""
        return Area.objects.filter(empresa_id=empresa_id, uuid=uuid).select_related('sede').only(*AREA_DETAIL_FIELDS).first()

