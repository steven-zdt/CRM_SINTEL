"""
Service Layer para Core v3.5.

WARNING: POLÍTICA v3.5:
- Service Layer modular: selectors, api_mixins
- Servicios legacy: activation_service, auth_service, orchestration, etc.
- No duplicar lógica de negocio de las apps "dueñas"
- Solo orquestar/componer datos de múltiples apps
"""

# Nuevo Service Layer modular
from apps.tenant.core.services.selectors import CoreSelector
from apps.tenant.core.services.api_mixins import CoreServiceMixin

# Legacy services (mantener compatibilidad)
from .activation_service import ActivationService
from .auth_service import AuthService
from .orchestration import OrchestrationService
from .password_reset import PasswordResetService

__all__ = [
    # Nuevo Service Layer
    'CoreSelector',
    'CoreServiceMixin',
    # Legacy
    'ActivationService',
    'AuthService',
    'OrchestrationService',
    'PasswordResetService',
]
