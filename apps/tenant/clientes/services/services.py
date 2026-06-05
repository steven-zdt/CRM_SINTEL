"""
Backward-compatibility layer for Clientes services.
[ARCHITECTURE v3.5] Direct usage of specialized services is preferred:
- selectors.py: For read-only queries
- crud_service.py: For atomic DB mutations
- business_service.py: For business logic and orchestration
"""
from .selectors import ClienteSelector, ContactoSelector
from .crud_service import ClienteCRUDService, ContactoCRUDService
from .business_service import ClienteBusinessService
from ..models import Cliente, ContactoCliente

class ClienteBusinessService(ClienteBusinessService):
    """Deprecated: Use business_service.ClienteBusinessService directly."""
    def qs_list(self, empresa_id, search=None):
        return ClienteSelector.get_cliente_list(empresa_id, search)
    
    def qs_detail(self, empresa_id, pk):
        return ClienteSelector.get_cliente_detail(empresa_id, pk)

class ContactoClienteService:
    """Deprecated: Use specialized services."""
    def qs_list(self, empresa_id, cliente_id=None):
        return ContactoSelector.get_contacto_list(empresa_id, cliente_id)
    
    def eliminar_contacto(self, pk, empresa_id):
        c = ContactoCliente.objects.filter(pk=pk, empresa_id=empresa_id).first()
        if c:
            ContactoCRUDService.delete_contacto(c)

class ClienteServiceMixin:
    @property
    def service(self):
        return ClienteBusinessService()

class ContactoClienteServiceMixin:
    @property
    def service(self):
        return ContactoClienteService()


def crear_cliente(empresa, data):
    """
    Deprecated backward-compatibility function for testing.
    Uses ClienteBusinessService to create or update a client.
    """
    tipo_doc = data.get("tipo_documento")
    num_doc = data.get("numero_documento")

    existing = Cliente.objects.filter(
        empresa_id=empresa.id,
        tipo_documento=tipo_doc,
        numero_documento=num_doc
    ).exists()

    creado = not existing
    service = ClienteBusinessService()
    cliente, _ = service.registrar_cliente_completo(empresa.id, data)
    return cliente, creado

