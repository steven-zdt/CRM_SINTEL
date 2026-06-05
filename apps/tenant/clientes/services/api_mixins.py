"""
API Mixins para Clientes - Inyeccion de servicios en ViewSets (v3.10.1).

SINTEL v3.10.1: Arquitectura Service Layer Modular.
- Hereda de BaseServiceMixin (canonical, consolidado)
- Mantiene properties y service_* methods específicos de Clientes
"""
import logging

from apps.tenant.api.mixins import BaseServiceMixin
from apps.tenant.clientes.services.selectors import (
    ClienteSelector,
    ContactoSelector,
    CarteraSelector,
    LIST_FIELDS,
    DETAIL_FIELDS,
)
from apps.tenant.clientes.services.business_service import (
    ClienteBusinessService,
    CarteraBusinessService,
)
from apps.tenant.clientes.services.crud_service import (
    ClienteCRUDService,
    ContactoCRUDService,
    CarteraCRUDService,
)

logger = logging.getLogger(__name__)


class ClienteServiceMixin(BaseServiceMixin):
    """
    Service mixin para Cliente ViewSet.
    Hereda de BaseServiceMixin para get_qs_list(), get_qs_detail(), etc.
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
        empresa_id = self._get_empresa_id_seguro()
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None
        return self.selector_class.get_cliente_list(empresa_id, search=search)

    def get_qs_detail(self):
        """Retorna queryset de detalle usando selector."""
        empresa_id = self._get_empresa_id_seguro()
        uuid_val = self.kwargs.get('uuid')
        return self.selector_class.get_cliente_detail(empresa_id, uuid_val)

    def service_registrar_cliente(self, empresa_id, data, contactos_raw=None):
        """Crea o actualiza cliente usando business service."""
        svc = self.business_service_class()
        cliente, _ = svc.registrar_cliente_completo(empresa_id, data, contactos_raw)
        return cliente


class ContactoClienteServiceMixin(BaseServiceMixin):
    """
    Service mixin para ContactoCliente ViewSet.
    Hereda de BaseServiceMixin para _get_empresa_id_seguro(), etc.
    """

    selector_class = ContactoSelector
    crud_service_class = ContactoCRUDService

    @property
    def contacto_selector(self):
        return ContactoSelector()

    @property
    def contacto_crud(self):
        return self.crud_service_class()

    def get_qs_contactos(self, cliente_id=None):
        """Retorna queryset de contactos usando selector."""
        empresa_id = self._get_empresa_id_seguro()
        return self.selector_class.get_contacto_list(empresa_id, cliente_id=cliente_id)


# Alias de compatibilidad
ContactoServiceMixin = ContactoClienteServiceMixin


class CarteraServiceMixin(BaseServiceMixin):
    """
    Service mixin para Cartera ViewSet.
    """

    selector_class = CarteraSelector
    business_service_class = CarteraBusinessService
    crud_service_class = CarteraCRUDService

    @property
    def cartera_selector(self):
        return self.selector_class()

    @property
    def cartera_service(self):
        return self.business_service_class()

    @property
    def cartera_crud(self):
        return self.crud_service_class()

    def get_qs_list(self):
        empresa_id   = self._get_empresa_id_seguro()
        req = getattr(self, 'request', None)
        cliente_uuid = (req.query_params.get('cliente_uuid') or req.query_params.get('cliente_id')) if req else None
        estado_pago  = self.request.query_params.get('estado_pago')
        search       = self.request.query_params.get('search')
        return self.selector_class.qs_list_facturas_venta(
            empresa_id=empresa_id,
            cliente_uuid=cliente_uuid,
            estado_pago=estado_pago,
            search=search,
        )
