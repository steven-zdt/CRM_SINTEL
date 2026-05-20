"""
Service Layer para Clientes v3.5.

Exports:
- ClienteSelector: Consultas optimizadas con LIST_FIELDS/DETAIL_FIELDS
- ClienteCRUDService: Persistencia transaccional
- ClienteBusinessService: Logica de negocio
"""
from apps.tenant.clientes.services.selectors import ClienteSelector
from apps.tenant.clientes.services.crud_service import ClienteCRUDService
from apps.tenant.clientes.services.business_service import ClienteBusinessService

# Facade legacy (alias para compatibilidad)
ClienteService = ClienteBusinessService

from apps.tenant.clientes.services.api_mixins import (
    ClienteServiceMixin,
    ContactoClienteServiceMixin,
    ContactoServiceMixin,
)

__all__ = [
    'ClienteSelector',
    'ClienteCRUDService',
    'ClienteBusinessService',
    'ClienteService',
    'ClienteServiceMixin',
    'ContactoClienteServiceMixin',
    'ContactoServiceMixin',
]
