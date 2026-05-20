"""
API Mixins para Clientes - Inyeccion de servicios en ViewSets.

SINTEL v3.5: Arquitectura Service Layer Modular.
- Inyecta acceso estandarizado a Selectors, CRUDService y BusinessService.
- Usa get_empresa_id() de SintelDSVMixin para Zero Trust.
"""
import logging

from apps.tenant.clientes.services.selectors import (
    ClienteSelector,
    ContactoSelector,
    LIST_FIELDS,
    DETAIL_FIELDS,
)
from apps.tenant.clientes.services.business_service import (
    ClienteBusinessService,
)
from apps.tenant.clientes.services.crud_service import (
    ClienteCRUDService,
    ContactoCRUDService,
)

logger = logging.getLogger(__name__)


class ClienteServiceMixin:
    """
    Service mixin para Cliente ViewSet.
    Inyecta acceso a Selectors y BusinessService.
    Requiere que el ViewSet herede de SintelDSVMixin (para get_empresa_id).
    """

    selector_class = ClienteSelector
    business_service_class = ClienteBusinessService
    crud_service_class = ClienteCRUDService

    @property
    def cliente_selector(self):
        return self.selector_class()

    @property
    def cliente_service(self):
        return self.business_service_class()

    @property
    def cliente_crud(self):
        return self.crud_service_class()

    def get_qs_list(self):
        """Retorna queryset de lista usando selector."""
        empresa_id = self.get_empresa_id() if hasattr(self, 'get_empresa_id') else (self.get_empresa().id if hasattr(self, 'get_empresa') else None)
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None
        return self.selector_class.get_cliente_list(empresa_id, search=search)

    def get_qs_detail(self):
        """Retorna queryset de detalle usando selector."""
        empresa_id = self.get_empresa_id() if hasattr(self, 'get_empresa_id') else (self.get_empresa().id if hasattr(self, 'get_empresa') else None)
        uuid_val = self.kwargs.get('uuid')
        return self.selector_class.get_cliente_detail(empresa_id, uuid_val)

    def service_registrar_cliente(self, empresa_id, data, contactos_raw=None):
        """Crea o actualiza cliente usando business service."""
        svc = self.business_service_class()
        cliente, _ = svc.registrar_cliente_completo(empresa_id, data, contactos_raw)
        return cliente

    def _get_empresa(self):
        """Helper para obtener empresa actual."""
        from apps.tenant.empresa.models import Empresa
        empresa_id = self.get_empresa_id() if hasattr(self, 'get_empresa_id') else (self.get_empresa().id if hasattr(self, 'get_empresa') else None)
        return Empresa.objects.filter(id=empresa_id).first()


class ContactoClienteServiceMixin:
    """
    Service mixin para ContactoCliente ViewSet.
    Inyecta acceso a ContactoSelector.
    """

    selector_class = ContactoSelector
    crud_service_class = ContactoCRUDService

    @property
    def contacto_selector(self):
        return self.selector_class()

    @property
    def contacto_crud(self):
        return self.crud_service_class()

    def get_qs_contactos(self, cliente_id=None):
        """Retorna queryset de contactos usando selector."""
        empresa_id = self.get_empresa_id() if hasattr(self, 'get_empresa_id') else (self.get_empresa().id if hasattr(self, 'get_empresa') else None)
        return self.selector_class.get_contacto_list(empresa_id, cliente_id=cliente_id)


# Alias de compatibilidad
ContactoServiceMixin = ContactoClienteServiceMixin
