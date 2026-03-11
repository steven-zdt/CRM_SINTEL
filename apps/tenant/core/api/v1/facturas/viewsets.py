"""Core API v1 - Facturas facade.

Shim de compatibilidad: re-exporta endpoints Core existentes relacionados con facturas.
La migración real a módulos v1 se hará incrementalmente.
"""

from apps.tenant.core.api.viewsets import CoreFacturasViewSet  # noqa: F401
