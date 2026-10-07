"""Authenticated MCP endpoint for tenant-scoped SINTEL tools."""
from __future__ import annotations

from djangorestframework_mcp.views import MCPView
from rest_framework_simplejwt.authentication import JWTAuthentication


class SintelTenantMCPView(MCPView):
    """Expose registered tenant ViewSets through MCP with JWT authentication."""

    authentication_classes = [JWTAuthentication]

    def has_mcp_permission(self, request):
        """Require an authenticated active user; tenant membership is enforced by middleware."""
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and user.is_active)
