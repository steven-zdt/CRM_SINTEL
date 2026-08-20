"""
Backward-compatibility layer for Clientes services.
[ARCHITECTURE v3.5] Direct usage of specialized services is preferred:
- selectors.py: For read-only queries
- crud_service.py: For atomic DB mutations
- business_service.py: For business logic and orchestration

Only `crear_cliente()` remains here -- used by
tests/test_idempotence_v2614.py y tests/test_clientes_api_and_service.py.
Las clases `ClienteBusinessService`/`ContactoClienteService`/
`ClienteServiceMixin`/`ContactoClienteServiceMixin` que existian antes
en este archivo (sombra sin consumidores de las reales en
api_mixins.py/business_service.py) fueron eliminadas -- confirmado
via grep repo-wide que nada las importaba desde este modulo especifico.
"""
from .business_service import ClienteBusinessService
from ..models import Cliente


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

