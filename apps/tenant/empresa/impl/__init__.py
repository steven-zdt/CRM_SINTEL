"""
Servicios internos del dominio Empresa.

⚠️ v2.30: Service Layer Pattern - Lógica de negocio del dominio Empresa.
- Sin signals: Toda la lógica es explícita
- Sin HTTP: Funciones puras que operan sobre modelos
- Multi-tenant: Transparente (django-tenants maneja el aislamiento por esquema)
"""
from .empresa_service import (
    get_empresa,
    get_or_create_empresa,
    update_empresa,
)
from .mailbox_service import (
    list_mailbox_configs,
    create_mailbox_config,
    update_mailbox_config,
    delete_mailbox_config,
)

__all__ = [
    'get_empresa',
    'get_or_create_empresa',
    'update_empresa',
    'list_mailbox_configs',
    'create_mailbox_config',
    'update_mailbox_config',
    'delete_mailbox_config',
]
