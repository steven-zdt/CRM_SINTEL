"""
Service Layer para Cotizaciones v3.5.

WARNING: v3.5: Service Layer Modular.
"""

# Nuevo Service Layer modular
from apps.tenant.cotizaciones.services.selectors import (
    CotizacionSelector,
    CotizacionItemSelector,
)
from apps.tenant.cotizaciones.services.crud_service import CotizacionCRUDService
from apps.tenant.cotizaciones.services.business_service import CotizacionService
from apps.tenant.cotizaciones.services.api_mixins import (
    CotizacionServiceMixin,
    CotizacionItemServiceMixin,
)

# Legacy compatibilidad (fachada)
from .services import CotizacionService as CotizacionServiceLegacy

__all__ = [
    # Nuevo Service Layer
    'CotizacionSelector',
    'CotizacionItemSelector',
    'CotizacionCRUDService',
    'CotizacionService',
    'CotizacionServiceMixin',
    'CotizacionItemServiceMixin',
    # Legacy
    'CotizacionServiceLegacy',
]
