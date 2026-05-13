from django.db.models import Q
from ..models import Cliente, ContactoCliente

LIST_FIELDS = (
    "id",
    "empresa_id",
    "tipo_persona",
    "tipo_documento",
    "numero_documento",
    "razon_social",
    "nombre_comercial",
    "regimen_tributario",
    "es_retenedor",
    "aplica_retefuente",
    "retefuente_porcentaje",
    "aplica_reteica",
    "reteica_porcentaje",
    "aplica_reteiva",
    "reteiva_porcentaje",
    "email",
    "telefono",
    "ciudad",
    "activo",
)

DETAIL_FIELDS = (
    "id",
    "empresa_id",
    "tipo_persona",
    "tipo_documento",
    "numero_documento",
    "razon_social",
    "nombre_comercial",
    "regimen_tributario",
    "es_retenedor",
    "aplica_retefuente",
    "retefuente_porcentaje",
    "aplica_reteica",
    "reteica_porcentaje",
    "aplica_reteiva",
    "reteiva_porcentaje",
    "email",
    "telefono",
    "direccion",
    "ciudad",
    "activo",
    "observaciones",
    "cuenta_contable_uuid",
)

CONTACT_FIELDS = (
    "id",
    "empresa_id",
    "cliente_id",
    "nombre_completo",
    "cargo",
    "email",
    "telefono",
    "activo",
    "is_principal",
)

class ClienteSelector:
    """Read-only optimized queries for Clientes."""
    
    @staticmethod
    def get_cliente_list(empresa_id: int, search: str = None):
        """Returns optimized queryset for list view."""
        qs = Cliente.objects.filter(empresa_id=empresa_id).only(*LIST_FIELDS).order_by("razon_social")
        if search:
            qs = qs.filter(
                Q(razon_social__icontains=search)
                | Q(numero_documento__icontains=search)
                | Q(email__icontains=search)
                | Q(nombre_comercial__icontains=search)
            )
        return qs

    @staticmethod
    def get_cliente_detail(empresa_id: int, pk: int):
        """Returns single cliente instance filtered by tenant."""
        return Cliente.objects.filter(empresa_id=empresa_id, pk=pk).only(*DETAIL_FIELDS).first()


class ContactoSelector:
    """Read-only optimized queries for Contactos de Cliente."""
    
    @staticmethod
    def get_contacto_list(empresa_id: int, cliente_id: int = None):
        """Returns optimized queryset for contacts."""
        qs = (
            ContactoCliente.objects.filter(empresa_id=empresa_id)
            .select_related("cliente")
            .only(
                *CONTACT_FIELDS,
                "cliente__id",
                "cliente__empresa_id",
                "cliente__razon_social",
            )
            .order_by("-is_principal", "nombre_completo")
        )
        if cliente_id:
            qs = qs.filter(cliente_id=cliente_id)
        return qs
