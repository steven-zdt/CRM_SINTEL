"""
SintelMCPView -- subclase de djangorestframework_mcp.views.MCPView que
cierra los 2 gaps reales encontrados en LOOP 0 (docs/mcp/MCP_BASELINE.md
#2.1) y documentados en ADR-MCP-001/ADR-MCP-002:

1. Autenticacion/autorizacion a nivel de ENDPOINT MCP (initialize/tools/
   list/tools/call) -- el paquete, tal cual se instala, deja
   `authentication_classes = []` y `has_mcp_permission() -> True` por
   defecto: CUALQUIERA puede listar las tools disponibles sin credencial
   (Fase 2 del plan: "Nunca: /mcp/ -> acceso anonimo").
2. AI-07 -- `execute_tool()` construye un `django.http.HttpRequest()` crudo
   para invocar la accion del ViewSet, pero nunca asigna `request.method`.
   `django.http.HttpRequest().method` es `None` (verificado en vivo:
   `None not in SAFE_METHODS`), asi que cualquier permiso que distinga
   lectura/escritura por metodo HTTP (ej. `IsTenantAdminOrReadOnly`, usada
   por los 3 ViewSets piloto) trata TODA llamada MCP -- incluido
   `list`/`retrieve` -- como si fuera una escritura, bloqueando a
   cualquier rol no-ADMIN incluso para lectura.

Version fijada del paquete: `django-rest-framework-mcp==0.1.0a4`
(`requirements.txt`). `execute_tool()` se COPIA integro desde
`djangorestframework_mcp/views.py` de esa version porque el bug esta en
medio del metodo (construccion del `HttpRequest` antes de las
verificaciones de auth/permisos) -- no hay un punto de extension para
inyectar el fix sin duplicar el metodo. Si el paquete sube de version,
diffear este metodo contra el nuevo `views.py` antes de actualizar
`requirements.txt`.
"""

import json
import logging
from http import HTTPStatus
from typing import Any

from django.http import HttpRequest
from djangorestframework_mcp.types import MCPTool
from djangorestframework_mcp.views import MCPView
from rest_framework import exceptions
from rest_framework.authentication import SessionAuthentication
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication

logger = logging.getLogger(__name__)

# AI-07: mapa accion -> metodo HTTP real que esa accion representaria si se
# hubiera invocado por la API REST normal (SSoT: convencion estandar de un
# DRF ModelViewSet). Las acciones custom (`@action`) no registradas en esta
# Wave (solo list/retrieve) caen al fallback "GET" -- revisar esta tabla
# antes de registrar create/update/destroy/acciones custom en una Wave
# futura (Fase 5/6/7/8 del plan).
_ACTION_HTTP_METHOD = {
    "list": "GET",
    "retrieve": "GET",
    "create": "POST",
    "update": "PUT",
    "partial_update": "PATCH",
    "destroy": "DELETE",
}


class SintelMCPView(MCPView):
    """Endpoint MCP real de SINTEL -- unico punto del repo que debe
    montarse en `config/urls_tenant.py`/`config/urls_public.py` para
    `/mcp/` (nunca `djangorestframework_mcp.urls` directo)."""

    # Mismos autenticadores que BaseTenantViewSet (apps/tenant/api/base.py)
    # -- Seccion 6.2 del plan: "no construir un RBAC paralelo". JWT estricta
    # (no la variante Relaxed-en-DEBUG de BaseTenantViewSet): un agente MCP
    # nunca debe degradar a AnonymousUser silenciosamente por un token
    # invalido/expirado.
    authentication_classes = [JWTAuthentication, SessionAuthentication]

    def has_mcp_permission(self, request) -> bool:
        """
        Gate obligatorio ANTES de `initialize`/`tools/list`/`tools/call`.
        Reutiliza `IsTenantMember` (apps/tenant/api/permissions.py):
        autenticado + membresia activa en el tenant resuelto por
        `TenantMainMiddleware` via Host header. La autorizacion FINA por
        tool (rol/alcance) la sigue resolviendo cada ViewSet dentro de
        `execute_tool()` -- este gate solo responde "¿puede este usuario
        hablar con el MCP de este tenant?", no "¿puede ejecutar esta tool
        especifica?".
        """
        from apps.tenant.api.permissions import IsTenantMember

        allowed = IsTenantMember().has_permission(request, self)
        if not allowed:
            logger.warning(
                "[SintelMCP] acceso denegado al endpoint MCP: user=%s tenant=%s",
                getattr(getattr(request, "user", None), "id", None),
                getattr(request, "tenant", None),
            )
        return allowed

    def execute_tool(
        self, tool: MCPTool, params: dict[str, Any], original_request: HttpRequest
    ) -> Any:
        """Copia de `MCPView.execute_tool()` (django-rest-framework-mcp
        0.1.0a4) con UNA correccion marcada `[FIX AI-07]`: `request.method`
        se asigna antes de construir el `Request` de DRF, para que los
        permisos del ViewSet (`IsTenantAdminOrReadOnly`, etc.) vean el
        metodo HTTP real que esa accion representa."""
        from djangorestframework_mcp.settings import mcp_settings

        viewset_class = tool.viewset_class
        action = tool.action
        user_id = getattr(getattr(original_request, "user", None), "id", None)

        viewset = viewset_class()

        bypass_viewset_auth = mcp_settings.BYPASS_VIEWSET_AUTHENTICATION
        bypass_viewset_permissions = mcp_settings.BYPASS_VIEWSET_PERMISSIONS

        method_kwargs = params.get("kwargs", {})
        body_data = params.get("body", {})

        body_bytes = json.dumps(body_data).encode("utf-8") if body_data else b"{}"
        request = HttpRequest()

        # [FIX AI-07] Unica linea agregada respecto al original: sin esto,
        # `request.method` es `None` y toda verificacion de SAFE_METHODS
        # falla-closed para no-admins (bloquea list/retrieve) o se comporta
        # de forma no documentada para cualquier otro permiso dependiente
        # del metodo HTTP.
        request.method = _ACTION_HTTP_METHOD.get(action, "GET")

        for key, value in original_request.META.items():
            request.META[key] = value
        if hasattr(original_request, "user"):
            request.user = original_request.user
        if hasattr(original_request, "auth"):
            request.auth = original_request.auth

        request.META["HTTP_CONTENT_TYPE"] = "application/json"
        request.META["HTTP_CONTENT_LENGTH"] = str(len(body_bytes))
        request._body = body_bytes
        request._read_started = True

        authenticators = [] if bypass_viewset_auth else viewset.get_authenticators()
        drf_request = Request(
            request,
            parsers=[JSONParser()],
            authenticators=authenticators,
        )

        if bypass_viewset_auth:
            if hasattr(request, "user"):
                drf_request.user = request.user
            if hasattr(request, "auth"):
                drf_request.auth = request.auth

        viewset.action = action
        drf_request.is_mcp_request = True

        viewset.args = ()
        viewset.kwargs = method_kwargs.copy()
        viewset.headers = {}
        viewset.request = drf_request
        viewset.format_kwarg = None

        try:
            if not bypass_viewset_auth:
                viewset.perform_authentication(drf_request)

            if not bypass_viewset_permissions:
                viewset.check_permissions(drf_request)
        except (
            exceptions.AuthenticationFailed,
            exceptions.NotAuthenticated,
            exceptions.PermissionDenied,
        ) as exc:
            if isinstance(
                exc, exceptions.AuthenticationFailed | exceptions.NotAuthenticated
            ):
                authenticators = viewset.get_authenticators()
                if authenticators:
                    exc.auth_header = authenticators[0].authenticate_header(drf_request)
            logger.warning(
                "[SintelMCP] tool denegada tool=%s action=%s user_id=%s error=%s",
                tool.name,
                action,
                user_id,
                exc,
            )
            raise

        viewset.check_throttles(drf_request)

        version, scheme = viewset.determine_version(
            drf_request, *viewset.args, **viewset.kwargs
        )
        drf_request.version, drf_request.versioning_scheme = version, scheme

        if not hasattr(viewset, action):
            raise ValueError(f"ViewSet does not support action: {action}")

        action_method = getattr(viewset, action)
        response = action_method(drf_request, **method_kwargs)

        logger.info(
            "[SintelMCP] tool ejecutada tool=%s action=%s viewset=%s user_id=%s",
            tool.name,
            action,
            viewset_class.__name__,
            user_id,
        )

        if hasattr(response, "data"):
            if response.status_code >= HTTPStatus.BAD_REQUEST.value:
                raise ValueError(f"ViewSet returned error: {response.data}")

            if response.data is not None:
                return response.data
            else:
                return {"message": "Operation completed successfully"}

        return response
