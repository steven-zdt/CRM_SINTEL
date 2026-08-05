"""
Servicios de proveedores v3.5+ - Modular Export.
Incluye v3.17.0: Representante Business Service.
"""
from .selectors import (
    ProveedorSelector,
    RepresentanteSelector,
    LIST_FIELDS,
    DETAIL_FIELDS,
    LIST_FIELDS_REPRESENTANTE,
    DETAIL_FIELDS_REPRESENTANTE,
)
from .crud_service import ProveedorCRUDService, RepresentanteCRUDService
from .business_service import ProveedorBusinessService, RepresentanteBusinessService
from .api_mixins import ProveedorServiceMixin, RepresentanteServiceMixin
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
    # Proveedor (v3.5+)
    "ProveedorSelector",
    "ProveedorCRUDService",
    "ProveedorBusinessService",
    "ProveedorServiceMixin",
    "LIST_FIELDS",
    "DETAIL_FIELDS",
    # Representante (v3.17.0)
    "RepresentanteSelector",
    "RepresentanteCRUDService",
    "RepresentanteBusinessService",
    "RepresentanteServiceMixin",
    "LIST_FIELDS_REPRESENTANTE",
    "DETAIL_FIELDS_REPRESENTANTE",
    # Legacy
    "crear_proveedor",
    "actualizar_proveedor",
    "qs_list",
]
