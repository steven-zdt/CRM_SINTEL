from apps.tenant.clientes.services.selectors import ClienteSelector, ContactoSelector
from apps.tenant.clientes.services.crud_service import ClienteCRUDService, ContactoCRUDService
from apps.tenant.clientes.services.business_service import ClienteBusinessService

class ClienteServiceMixin:
    @property
    def cliente_selector(self):
        return ClienteSelector()
    
    @property
    def cliente_service(self):
        return ClienteBusinessService()
    
    @property
    def cliente_crud(self):
        return ClienteCRUDService()

class ContactoClienteServiceMixin:
    @property
    def contacto_selector(self):
        return ContactoSelector()
    
    @property
    def contacto_crud(self):
        return ContactoCRUDService()
