"""
Servicios de proveedores v3.5 - Modular Export.
"""
from .selectors import ProveedorSelector, LIST_FIELDS, DETAIL_FIELDS
from .crud_service import ProveedorCRUDService
from .business_service import ProveedorBusinessService
from .api_mixins import ProveedorServiceMixin
from .services import (
    crear_proveedor as _svc_crear_proveedor,
    actualizar_proveedor as _svc_actualizar_proveedor,
    qs_list as _svc_qs_list,
)

# Legacy wrappers for test_proveedores_api_and_service
def crear_proveedor(empresa, data):
    """Legacy wrapper returning just the provider instance for compatibility."""
    prov, _ = _svc_crear_proveedor(empresa, data)
    return prov

def actualizar_proveedor(proveedor, data):
    """Legacy wrapper to update a provider."""
    return _svc_actualizar_proveedor(proveedor, data)

def qs_list(empresa_id, search=None):
    """Legacy wrapper to get queryset list."""
    return _svc_qs_list(empresa_id, search)

__all__ = [
    "ProveedorSelector",
    "ProveedorCRUDService",
    "ProveedorBusinessService",
    "ProveedorServiceMixin",
    "LIST_FIELDS",
    "DETAIL_FIELDS",
    "crear_proveedor",
    "actualizar_proveedor",
    "qs_list",
]
