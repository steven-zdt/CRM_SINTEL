"""Core API v1 - Landing facade.

Shim de compatibilidad: re-exporta endpoints Core existentes relacionados con landing.

Nota: estos endpoints viven en `apps.tenant.core.api.viewsets`.
"""

from apps.tenant.core.api.viewsets import CoreLandingViewSet  # noqa: F401
