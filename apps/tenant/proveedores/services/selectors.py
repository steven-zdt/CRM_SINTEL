"""
Selectors for Proveedores v3.5 - Zero Waste Queries.
"""
from django.db.models import Q, Prefetch
from ..models import Proveedor

LIST_FIELDS = (
    "id",
    "tipo_persona",
    "tipo_documento",
    "numero_documento",
    "digito_verificacion",
    "razon_social",
    "nombre_comercial",
    "regimen_tributario",
    "responsable_iva",
    "autoretenedor",
    "email_contacto",
    "telefono_contacto",
    "ciudad",
    "activo",
    "codigo_contable",
    "created_at",
)

DETAIL_FIELDS = (
    "id",
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
    "observaciones",
    "created_at",
    "updated_at",
)

def qs_list(empresa_id, search=None):
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

def qs_detail(empresa_id, pk):
    """Retorna detalle completo para edición."""
    # Nota: No hay ContactoProveedor en models.py, omitimos prefetch_related por ahora.
    return Proveedor.objects.filter(empresa_id=empresa_id, pk=pk).only(*DETAIL_FIELDS).first()

class ProveedorSelector:
    """Clase selectora para inyección en mixins."""
    def get_list(self, empresa_id, search=None):
        return qs_list(empresa_id, search)
    
    def get_by_id(self, empresa_id, pk):
        return qs_detail(empresa_id, pk)
