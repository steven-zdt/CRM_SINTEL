"""Authenticated MCP endpoints for SINTEL."""
from __future__ import annotations

from djangorestframework_mcp.views import MCPView
from rest_framework.permissions import IsAdminUser
from rest_framework_simplejwt.authentication import JWTAuthentication


class SintelTenantMCPView(MCPView):
    """Expose registered tenant ViewSets through MCP with JWT authentication."""

    authentication_classes = [JWTAuthentication]

    def has_mcp_permission(self, request):
        """Require an authenticated active user; tenant membership is enforced by middleware."""
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and user.is_active)


class SintelPublicMCPView(MCPView):
    """Expose public/admin ViewSets through MCP only to staff users."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]

    def has_mcp_permission(self, request):
        """Require an authenticated active staff user for public-scope MCP."""
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and user.is_active and user.is_staff)
