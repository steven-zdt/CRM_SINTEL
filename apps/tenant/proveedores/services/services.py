"""
Backward-compatibility layer for Proveedores services.
[ARCHITECTURE v3.5] Direct usage of specialized services is preferred.
"""
from apps.tenant.proveedores.models import Proveedor
from apps.tenant.proveedores.services.business_service import ProveedorBusinessService
from apps.tenant.proveedores.services.selectors import ProveedorSelector
from apps.tenant.proveedores.services.crud_service import ProveedorCRUDService

def crear_proveedor(empresa_id_or_obj, data):
    """
    Backward-compatibility function returning (proveedor, creado) for TestIdempotencia.
    """
    empresa_id = getattr(empresa_id_or_obj, "id", empresa_id_or_obj)
    
    # Check if exists by numero_documento to determine if created
    nit = data.get("numero_documento") or data.get("nit")
    if nit:
        nit = str(nit).strip().upper()
        existing = Proveedor.objects.filter(empresa_id=empresa_id, numero_documento=nit).exists()
    else:
        existing = False
        
    creado = not existing
    service = ProveedorBusinessService()
    
    # Ensure empresa_id is in the data dictionary for registrar_proveedor_con_contactos
    data_copy = dict(data)
    data_copy["empresa_id"] = empresa_id
    
    proveedor, _ = service.registrar_proveedor_con_contactos(data_copy, None)
    return proveedor, creado

def actualizar_proveedor(proveedor, data):
    """
    Backward-compatibility function to update a provider.
    """
    service = ProveedorBusinessService()
    return service.actualizar_proveedor(proveedor, data)

def qs_list(empresa_id, search=None):
    """
    Backward-compatibility function to get list of providers.
    """
    return ProveedorSelector.get_list(empresa_id, search)
