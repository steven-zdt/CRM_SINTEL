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


class RelaxedJWTAuthentication(JWTAuthentication):
    """
    Extensión de JWTAuthentication que no bloquea con 401 en modo DEBUG
    si el token es inválido o ha expirado. Permite que la petición
    continúe como AnonymousUser para ser manejada por los fallbacks de desarrollo.
    """
    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except Exception:
            from django.conf import settings
            if settings.DEBUG:
                return None
            raise


class BaseTenantViewSet(viewsets.ModelViewSet):
    """
    ViewSet base para modelos tenant con lookup por UUID y Dual-Auth.

    WARNING: IMPORTANTE:
    - lookup_field="uuid" garantiza que las URLs usen UUID en lugar de PK
    - RelaxedJWTAuthentication: Permite bypass en DEBUG para facilitar integración.
    - SessionAuthentication: Workspace navegador, HTMX, CSRF.
    """
    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"
    authentication_classes = [RelaxedJWTAuthentication, SessionAuthentication]
