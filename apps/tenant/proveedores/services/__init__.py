"""
Servicios de proveedores v3.5 - Modular Export.
"""
from .selectors import ProveedorSelector, LIST_FIELDS, DETAIL_FIELDS
from .crud_service import ProveedorCRUDService
from .business_service import ProveedorBusinessService

__all__ = [
    "ProveedorSelector",
    "ProveedorCRUDService",
    "ProveedorBusinessService",
    "LIST_FIELDS",
    "DETAIL_FIELDS",
]
