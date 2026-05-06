"""
ViewSet base para modelos tenant con lookup por UUID.

WARNING: v2.37: Unificacion de convenciones API-First
- lookup_field="uuid" para todos los ViewSets publicos
- Evita exposicion de PK interno
- Consistente con arquitectura multitenant

WARNING: v2.61.8: Dual-Auth Pattern (JWT + Session)
- JWTAuthentication: Clientes API, Tabulator, integraciones externas
- SessionAuthentication: Workspace navegador, HTMX, CSRF
"""
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication


class BaseTenantViewSet(viewsets.ModelViewSet):
    """
    ViewSet base para modelos tenant con lookup por UUID y Dual-Auth.
    """
    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"
    authentication_classes = [JWTAuthentication, SessionAuthentication]


class BaseTenantGenericViewSet(viewsets.GenericViewSet):
    """
    ViewSet genérico base para modelos tenant con lookup por UUID y Dual-Auth.
    Útil para ViewSets que solo implementan algunos mixins.
    """
    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"
    authentication_classes = [JWTAuthentication, SessionAuthentication]
