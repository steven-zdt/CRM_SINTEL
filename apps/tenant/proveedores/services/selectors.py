"""
Selectors for Proveedores v3.5 - Zero Waste Queries.
"""
from django.db.models import Q, Prefetch
from ..models import Proveedor

LIST_FIELDS = (
    "id",
    "uuid",
    "tipo_persona",
    "tipo_documento",
    "numero_documento",
    "digito_verificacion",
    "razon_social",
    "nombre_comercial",
    "regimen_tributario",
    "responsable_iva",
    "autoretenedor",
    "es_retenedor",
    "aplica_retefuente",
    "retefuente_porcentaje",
    "aplica_reteica",
    "reteica_porcentaje",
    "aplica_reteiva",
    "reteiva_porcentaje",
    "email_contacto",

    "telefono_contacto",
    "direccion",
    "ciudad",
    "activo",
    "codigo_contable",
    "cuenta_contable_uuid",
    "created_at",
)

DETAIL_FIELDS = (
    "id",
    "uuid",
    "tipo_persona",
    "tipo_documento",
    "numero_documento",
    "digito_verificacion",
    "razon_social",
    "nombre_comercial",
    "regimen_tributario",
    "actividad_economica_ciiu",
    "responsable_iva",
    "gran_contribuyente",
    "autoretenedor",
    "es_retenedor",
    "aplica_retefuente",
    "retefuente_porcentaje",
    "aplica_reteica",
    "reteica_porcentaje",
    "aplica_reteiva",
    "reteiva_porcentaje",
    "email_contacto",

    "telefono_contacto",
    "direccion",
    "ciudad",
    "plazo_pago_dias",
    "banco",
    "tipo_cuenta",
    "numero_cuenta",
    "activo",
    "codigo_contable",
    "cuenta_contable_uuid",
    "observaciones",
    "created_at",
    "updated_at",
)

class ProveedorSelector:
    """Clase selectora para inyección en mixins."""
    
    @staticmethod
    def get_list(empresa_id: int, search: str = None):
        """Retorna listado optimizado para Tabulator."""
        qs = Proveedor.objects.filter(empresa_id=empresa_id).only(*LIST_FIELDS).order_by('razon_social')
        
        if search:
            qs = qs.filter(
                Q(razon_social__icontains=search) | 
                Q(numero_documento__icontains=search) |
                Q(email_contacto__icontains=search) |
                Q(nombre_comercial__icontains=search)
            ).distinct()
        return qs
    
    @staticmethod
    def get_by_id(empresa_id: int, pk: int):
        """Retorna detalle completo para edición por PK."""
        return Proveedor.objects.filter(empresa_id=empresa_id, pk=pk).only(*DETAIL_FIELDS).first()

    @staticmethod
    def get_by_uuid(empresa_id: int, uuid_val: str):
        """Retorna detalle completo para edición por UUID."""
        return Proveedor.objects.filter(empresa_id=empresa_id, uuid=uuid_val).only(*DETAIL_FIELDS).first()
