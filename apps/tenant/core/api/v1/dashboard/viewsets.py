"""Core API v1 - Dashboard facade.

Shim de compatibilidad: re-exporta endpoints Core existentes relacionados con dashboard.
"""

from apps.tenant.core.api.viewsets import (  # noqa: F401
    CoreDashboardViewSet,
    DashboardSectionsViewSet,
)
