"""
Service Layer para Perfil v3.5.

WARNING: v3.5: Service Layer Modular - Lógica de negocio del dominio Perfil.
- Sin signals: Toda la lógica es explícita
- Sin HTTP: Funciones puras que operan sobre modelos
- Multi-tenant: Transparente (django-tenants maneja el aislamiento por esquema)
"""

# Nuevo Service Layer modular
from apps.tenant.perfil.services.selectors import PerfilSelector, DepartamentoSelector
from apps.tenant.perfil.services.crud_service import PerfilCRUDService, DepartamentoCRUDService
from apps.tenant.perfil.services.business_service import PerfilBusinessService
from apps.tenant.perfil.models import RolTenant
# NOTE: PerfilServiceMixin belongs to api layer (api/mixins.py), not here.
# Import it from apps.tenant.perfil.api.mixins directly.

# Legacy compatibilidad
from .perfil_service import (
    get_or_create_profile,
    read_profile,
    update_profile,
    update_profile_config,
)

__all__ = [
    # Nuevo Service Layer
    'PerfilSelector',
    'DepartamentoSelector',
    'PerfilCRUDService',
    'DepartamentoCRUDService',
    'PerfilBusinessService',
    # PerfilServiceMixin is in api/mixins.py (api-layer concern, not service-layer)
    'RolTenant',
    # Legacy
    'get_or_create_profile',
    'read_profile',
    'update_profile',
    'update_profile_config',
]
