"""
Service Layer para landing (tenant) v3.5.

⚠️ POLÍTICA v3.5:
- Service Layer modular con selectors, crud_service, business_service, api_mixins
- Auth (login, logout, password-reset) está en Core: apps/tenant/core/services/auth_service.py
"""

# Nuevo Service Layer modular
from apps.tenant.landing.services.selectors import LandingSelector
from apps.tenant.landing.services.crud_service import LandingCRUDService
from apps.tenant.landing.services.business_service import LandingBusinessService
from apps.tenant.landing.services.api_mixins import LandingServiceMixin

# Compatibilidad legacy
from .landing_info_service import get_public_info

__all__ = [
    # Nuevo Service Layer
    'LandingSelector',
    'LandingCRUDService',
    'LandingBusinessService',
    'LandingServiceMixin',
    # Legacy
    'get_public_info',
]
