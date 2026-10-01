"""
Service Layer para Clientes v3.5.

Exports:
- ClienteSelector: Consultas optimizadas con LIST_FIELDS/DETAIL_FIELDS
- ClienteCRUDService: Persistencia transaccional
- ClienteBusinessService: Logica de negocio
"""

from apps.tenant.clientes.services.api_mixins import (
    CarteraServiceMixin,
    ClienteServiceMixin,
    ContactoClienteServiceMixin,
    ContactoServiceMixin,
)
from apps.tenant.clientes.services.business_service import (
    CarteraBusinessService,
    ClienteBusinessService,
)
from apps.tenant.clientes.services.crud_service import CarteraCRUDService, ClienteCRUDService
from apps.tenant.clientes.services.selectors import CarteraSelector, ClienteSelector

# Facade legacy (alias para compatibilidad)
ClienteService = ClienteBusinessService

__all__ = [
    "ClienteSelector",
    "ClienteCRUDService",
    "ClienteBusinessService",
    "ClienteService",
    "ClienteServiceMixin",
    "ContactoClienteServiceMixin",
    "ContactoServiceMixin",
    "CarteraSelector",
    "CarteraCRUDService",
    "CarteraBusinessService",
    "CarteraServiceMixin",
]
