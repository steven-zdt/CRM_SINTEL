"""
Middleware para manejar redirecciones HTTPS -> HTTP en desarrollo y headers de seguridad (v3.10.4).

[WARNING] REGLA 0: Cero caracteres especiales o emojis. Solo ASCII.
"""

import logging
import uuid
import fnmatch

from django.conf import settings
from django.http import HttpResponsePermanentRedirect, HttpResponseBadRequest
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)
security_logger = logging.getLogger("security.tenants")


class ValidateALLOWED_HOSTSMiddleware:
    """
    Valida ALLOWED_HOSTS EXPLICITAMENTE sin pasar por request.get_host().

    Si el Host header no coincide con ALLOWED_HOSTS, retorna 400 Bad Request inmediatamente.
    Esto previene que bots/exploradores lleguen a Django URL resolution y generen logs 404 confusos.

    POSICION: Debe ser UNO DE LOS PRIMEROS middleware (despues de SessionMiddleware).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def _host_matches(self, host):
        """Verifica si host coincide con ALLOWED_HOSTS (con soporte para wildcards)."""
        allowed_hosts = set(settings.ALLOWED_HOSTS)
        
        if '*' in allowed_hosts:
            return True

        # Remover puerto si esta presente
        host_only = host.split(":")[0] if ":" in host else host

        for allowed_host in allowed_hosts:
            if allowed_host == '*':
                return True
            if allowed_host.startswith('.'):
                # .sintel.net.co matches sintel.net.co and test.sintel.net.co
                if host_only == allowed_host[1:] or host_only.endswith(allowed_host):
                    return True
            elif '*' in allowed_host:
                if fnmatch.fnmatch(host_only, allowed_host):
                    return True
            else:
                if host_only == allowed_host:
                    return True

        return False

    def __call__(self, request):
        """Valida Host header antes de dejar que llegue a Django."""
        http_host = request.META.get("HTTP_HOST") or request.META.get("SERVER_NAME", "")

        if not http_host:
            # Sin Host header: rechazar
            security_logger.warning(
                "[BLOCKED] No Host header | Path: %s | IP: %s",
                request.path,
                self._get_client_ip(request)
            )
            return HttpResponseBadRequest("Invalid request: missing Host header")

        # Validar contra ALLOWED_HOSTS
        if not self._host_matches(http_host):
            security_logger.warning(
                "[BLOCKED] Invalid Host header '%s' not in ALLOWED_HOSTS | Path: %s | IP: %s",
                http_host,
                request.path,
                self._get_client_ip(request)
            )
            return HttpResponseBadRequest("Invalid Host header")

        return self.get_response(request)

    def _get_client_ip(self, request):
        """Obtiene IP del cliente para logging."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0]
        return request.META.get("REMOTE_ADDR", "unknown")


class ForceNoPortMiddleware:
    """
    Middleware que normaliza el HTTP_HOST eliminando el puerto antes de que
    django-tenants intente resolver el inquilino.

    WARNING: ESTANDAR: Puerto 80 (HTTP) - Sin puertos explicitos
    - Los dominios en la BD NUNCA tienen puerto (ej: {schema}.localhost, {schema}.sintel.net.co)
    - El navegador puede enviar :8000, pero Django lo ignora
    - Este middleware garantiza que django-tenants siempre busque strings limpios

    Posicion critica: Debe ejecutarse DESPUES de SessionMiddleware y
    ANTES de django_tenants.middleware.main.TenantMainMiddleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """
        Normaliza HTTP_HOST eliminando el puerto antes de la resolucion del tenant.

        Ejemplo:
        - Entrada: HTTP_HOST = "{schema}.localhost:8000"
        - Salida: HTTP_HOST = "{schema}.localhost"

        NOTA: Accedemos directamente a META['HTTP_HOST'] para evitar que Django valide
        ALLOWED_HOSTS prematuramente. La validacion ocurrira en TenantSecurityAndURLConfMiddleware.
        """
        # Obtener el host actual del META (puede incluir puerto)
        # NO usar request.get_host() porque activa validacion ALLOWED_HOSTS prematuramente
        host = request.META.get("HTTP_HOST", "")

        # Separar dominio del puerto (split por ':')
        # Si hay puerto, tomar solo la parte del dominio
        if host and ":" in host:
            domain_only = host.split(":")[0]
            # Sobrescribir HTTP_HOST en request.META
            request.META["HTTP_HOST"] = domain_only
            # Tambien actualizar SERVER_NAME si existe
            if "SERVER_NAME" in request.META:
                request.META["SERVER_NAME"] = domain_only

        return self.get_response(request)


class HTTPSRedirectMiddleware:
    """
    Middleware que redirige HTTPS a HTTP en modo desarrollo.

    Solo se activa cuando DEBUG=True para evitar problemas en produccion.

    WARNING: LIMITACION: Si el navegador intenta una conexion SSL/TLS directa,
    el servidor HTTP no puede procesarla y falla antes de que este middleware
    pueda intervenir. En ese caso, el usuario debe:
    1. Usar HTTP explicitamente: http://{schema}.sintel.net.co (NO https://) - puerto 80 implicito
    2. Limpiar HSTS del navegador: chrome://net-internals/#hsts
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Solo en modo desarrollo
        if settings.DEBUG:
            # Verificar si la peticion viene por HTTPS
            # Django detecta HTTPS mediante headers del proxy o request.is_secure()
            is_https = (
                request.is_secure()
                or request.META.get("HTTP_X_FORWARDED_PROTO") == "https"
                or request.META.get("HTTP_X_FORWARDED_SSL") == "on"
            )

            if is_https:
                # Construir URL HTTP equivalente
                http_url = request.build_absolute_uri().replace("https://", "http://", 1)
                return HttpResponsePermanentRedirect(http_url)

        response = self.get_response(request)

        # En desarrollo, agregar headers de seguridad permisivos para evitar advertencias del navegador
        if settings.DEBUG:
            # Cross-Origin-Opener-Policy: Permitir en desarrollo (el navegador requiere HTTPS o localhost)
            # Para desarrollo con dominios arbitrarios, usamos 'unsafe-none' o simplemente no lo configuramos
            # El navegador mostrara una advertencia, pero no bloqueara la funcionalidad
            if "Cross-Origin-Opener-Policy" not in response:
                # Solo establecer si el origen es localhost o 127.0.0.1
                # Acceder directamente a META para evitar validacion ALLOWED_HOSTS prematura
                http_host = request.META.get("HTTP_HOST", "")
                host = http_host.split(":")[0] if http_host else ""
                if host in ["localhost", "127.0.0.1"]:
                    response["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
                # Para otros dominios en desarrollo, no establecer el header para evitar advertencias

        return response


class CSRFTrustedOriginMiddleware:
    """
    Middleware para permitir dominios arbitrarios en desarrollo.

    En desarrollo (DEBUG=True), agrega automaticamente el dominio de la request
    a CSRF_TRUSTED_ORIGINS si no esta ya presente.

    WARNING: IMPORTANTE: Solo funciona en DEBUG=True. En produccion, se requiere
    lista explicita en CSRF_TRUSTED_ORIGINS.

    Este middleware debe ejecutarse ANTES de CsrfViewMiddleware para que
    Django pueda validar correctamente el token CSRF.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.DEBUG:
            # WARNING: v2.30: ForceNoPortMiddleware ya modifico HTTP_HOST, pero HTTP_ORIGIN
            # viene del navegador y puede incluir el puerto. Usar HTTP_ORIGIN si esta presente.
            http_origin = request.META.get("HTTP_ORIGIN")

            if http_origin:
                # El navegador envio HTTP_ORIGIN (puede incluir puerto)
                # Agregar directamente a CSRF_TRUSTED_ORIGINS
                if http_origin not in settings.CSRF_TRUSTED_ORIGINS:
                    settings.CSRF_TRUSTED_ORIGINS.append(http_origin)

                # Tambien agregar variantes sin puerto y con puerto alternativo
                from urllib.parse import urlparse

                parsed = urlparse(http_origin)
                host = parsed.hostname
                port = parsed.port
                scheme = parsed.scheme

                # Sin puerto (puerto 80/443 implicito)
                origin_no_port = f"{scheme}://{host}"
                if origin_no_port not in settings.CSRF_TRUSTED_ORIGINS:
                    settings.CSRF_TRUSTED_ORIGINS.append(origin_no_port)

                # Con puerto si esta presente
                if port:
                    origin_with_port = f"{scheme}://{host}:{port}"
                    if origin_with_port not in settings.CSRF_TRUSTED_ORIGINS:
                        settings.CSRF_TRUSTED_ORIGINS.append(origin_with_port)
            else:
                # Si no hay HTTP_ORIGIN, construir desde HTTP_HOST
                # (ForceNoPortMiddleware ya elimino el puerto, pero podemos inferirlo)
                # Acceder directamente a META para evitar validacion ALLOWED_HOSTS prematura
                http_host = request.META.get("HTTP_HOST", "")
                host = http_host.split(":")[0] if http_host else ""
                scheme = "https" if request.is_secure() else "http"

                # Agregar sin puerto
                origin_no_port = f"{scheme}://{host}"
                if origin_no_port not in settings.CSRF_TRUSTED_ORIGINS:
                    settings.CSRF_TRUSTED_ORIGINS.append(origin_no_port)

                # Intentar inferir puerto desde SERVER_PORT o HTTP_REFERER
                port = None
                if "SERVER_PORT" in request.META:
                    try:
                        port = int(request.META["SERVER_PORT"])
                        # Solo agregar si no es el puerto estandar (80/443)
                        if port not in (80, 443):
                            origin_with_port = f"{scheme}://{host}:{port}"
                            if origin_with_port not in settings.CSRF_TRUSTED_ORIGINS:
                                settings.CSRF_TRUSTED_ORIGINS.append(origin_with_port)
                    except (ValueError, TypeError):
                        pass

                # Establecer HTTP_ORIGIN si no esta presente
                if "HTTP_ORIGIN" not in request.META:
                    if port and port not in (80, 443):
                        request.META["HTTP_ORIGIN"] = f"{scheme}://{host}:{port}"
                    else:
                        request.META["HTTP_ORIGIN"] = origin_no_port

        # If an access token was delivered via HttpOnly cookie (OTT flow),
        # expose it to downstream authentication mechanisms by mapping it
        # into the Authorization header if not already present.
        try:
            if 'HTTP_AUTHORIZATION' not in request.META:
                access_tok = request.COOKIES.get('access_token')
                if access_tok and isinstance(access_tok, str) and access_tok.count('.') >= 2:
                    request.META['HTTP_AUTHORIZATION'] = f'Bearer {access_tok}'
        except Exception:
            # Fail-safe: do not interrupt request processing
            pass

        return self.get_response(request)


# Thread-local storage para contexto de logging
import threading

_logging_context = threading.local()


class RequestContextLogFilter(logging.Filter):
    """
    Filtro de logging que anade request_id y schema_name a los LogRecords.

    WARNING: IMPORTANTE: Este filtro siempre anade los campos (con "-" si no estan disponibles).
    - Compatible con formatters que incluyen %(request_id)s (siempre existe)
    - Compatible con formatters que no los incluyen (no rompe)
    - El formatter por defecto NO usa estos campos (evita errores en arranque/import-time)
    """

    def filter(self, record):
        # Obtener valores del thread-local (si estan disponibles)
        request_id = getattr(_logging_context, "request_id", None)
        schema_name = getattr(_logging_context, "schema_name", None)

        # Siempre anadir al record (con fallback a "-" si no estan disponibles)
        # Esto permite que formatters opcionales como "verbose_with_context" funcionen
        # pero el formatter por defecto ("brief"/"simple") no los usa
        record.request_id = request_id if request_id else "-"
        record.schema_name = schema_name if schema_name else "-"

        return True


class RequestContextMiddleware(MiddlewareMixin):
    """
    Middleware que genera request_id y adjunta schema_name a los logs.

    WARNING: POSICION: Debe ejecutarse despues de TenantMainMiddleware para tener acceso a request.tenant.
    """

    def process_request(self, request):
        """Genera request_id si no existe y lo guarda en thread-local."""
        rid = request.META.get("REQUEST_ID")
        if not rid:
            rid = uuid.uuid4().hex
            request.META["REQUEST_ID"] = rid
        # Guarda en thread-local para acceso desde cualquier logger
        _logging_context.request_id = rid

    def process_view(self, request, view_func, view_args, view_kwargs):
        """Adjunta filtros al root logger y anade schema_name al contexto."""
        # Adjunta filtros al root logger (si no estan)
        root_logger = logging.getLogger()
        for h in root_logger.handlers:
            if not any(isinstance(f, RequestContextLogFilter) for f in h.filters):
                h.addFilter(RequestContextLogFilter())

        # Anade schema_name al contexto si esta disponible
        schema_name = "-"
        if hasattr(request, "tenant") and request.tenant:
            schema_name = getattr(request.tenant, "schema_name", "-")

        # Guarda en thread-local para acceso desde cualquier logger
        _logging_context.schema_name = schema_name
        return None

    def process_response(self, request, response):
        # Limpiar thread-local al finalizar la request
        if hasattr(_logging_context, "request_id"):
            delattr(_logging_context, "request_id")
        if hasattr(_logging_context, "schema_name"):
            delattr(_logging_context, "schema_name")
        return response


class DebugNoCSRFMiddleware:
    """
    En DEBUG mode, desactiva la verificacion CSRF para permitir desarrollo sin
    tener que enviar tokens CSRF en requests DELETE, POST, PUT, PATCH.

    SOLO para desarrollo. En produccion (DEBUG=False), el CSRF middleware
    funciona normalmente.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.conf import settings
        if settings.DEBUG:
            # Marcar request como si ya paso CSRF
            request._dont_enforce_csrf_checks = True
        return self.get_response(request)
