"""
Permisos personalizados para la app facturas (API-First).

# WARNING: v2.61: CONSOLIDADO - Re-exporta IsTenantAdminOrReadOnly desde core SSoT.
# La implementacion local fue eliminada para evitar duplicacion.
# Toda la logica de permisos vive en apps.tenant.api.permissions (SSoT).
"""

from apps.tenant.api.permissions import IsTenantAdminOrReadOnly  # noqa: F401
