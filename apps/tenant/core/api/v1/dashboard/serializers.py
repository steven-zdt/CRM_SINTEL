"""Core API v1 - Dashboard serializers.

Shim de compatibilidad: los serializers compuestos viven en
`apps.tenant.core.api.serializers`.
"""

from apps.tenant.core.api.serializers import DashboardCompletoSerializer  # noqa: F401
from apps.tenant.core.api.serializers_sections import DashboardSectionSerializer  # noqa: F401
