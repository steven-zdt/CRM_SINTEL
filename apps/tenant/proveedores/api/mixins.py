"""
API Mixins for Proveedores v3.5.
"""
from ..services import ProveedorSelector, ProveedorCRUDService, ProveedorBusinessService

class ProveedorServiceMixin:
    """
    Mixin providing property-based access to the service layer.
    Used to decouple ViewSets from service instantiation.
    """
    @property
    def proveedor_selector(self):
        return ProveedorSelector()

    @property
    def proveedor_service(self):
        return ProveedorBusinessService()

    @property
    def proveedor_crud(self):
        return ProveedorCRUDService()
