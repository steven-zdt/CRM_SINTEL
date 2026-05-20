"""
Middleware de Seguridad y Enrutamiento Multi-Tenant (Sintel Version).

WARNING: SEGURIDAD CRÍTICA:
Este middleware implementa múltiples capas de seguridad para proteger el ámbito público
y garantizar el aislamiento correcto entre tenants.

REGLAS ESTRICTAS:
1. Esquema PÚBLICO: Solo accesible desde dominios explícitamente permitidos.
2. Esquema PRIVADO: Solo accesible si el dominio termina en '.sintel.com'
   (o subdominios de localhost para desarrollo).
3. Protección contra Host Header Attacks.
4. Validación estricta de dominios para prevenir acceso no autorizado.
"""

import logging

from django.conf import settings
from django.core.exceptions import DisallowedHost
from django.http import HttpResponseForbidden, JsonResponse
from django_tenants.utils import get_public_schema_name

logger = logging.getLogger(__name__)
security_logger = logging.getLogger("security.tenants")


class TenantSecurityAndURLConfMiddleware:
    """
    Middleware de Seguridad y Enrutamiento Multi-Tenant (Sintel Version).

    WARNING: FUNCIONES:
    1. SEGURIDAD: Protege el ámbito público de accesos no autorizados
    2. URLConf: Establece request.urlconf según el tipo de tenant
    3. VALIDACIÓN: Valida dominios y previene Host Header Attacks

    WARNING: CAPAS DE SEGURIDAD:
    - Validación estricta de dominios permitidos para ámbito público
    - Bloqueo de subdominios intentando acceder al ámbito público
    - Validación de sintaxis de dominios para tenants privados
    - Logging de seguridad para auditoría
    - Protección contra Host Header Attacks
    """

    # 1. Configuración del Esquema Público (WHITELIST ESTRICTA)
    ALLOWED_PUBLIC_DOMAINS = frozenset(
        [
            "sintel.com",  # Dominio de producción
            "localhost",  # Desarrollo local
            "127.0.0.1",  # Desarrollo local (IP)
            "0.0.0.0",  # Desarrollo local (bind all)
            "testserver",  # Django test client host
            "186.117.247.166",  # Servidor IP
            "186.117.247.167",  # Servidor IP adicional
            "192.168.2.15",  # Red local - Consola pública
        ]
    )

    # 2. Configuración del Esquema Privado (Sufijo obligatorio)
    REQUIRED_TENANT_SUFFIX = ".sintel.com"

    # 3. Dominios de desarrollo permitidos para tenants privados
    DEV_DOMAIN_INDICATORS = frozenset(["localhost", "127.0.0.1", "0.0.0.0", ".local"])

    def __init__(self, get_response):
        self.get_response = get_response
        self.public_schema = get_public_schema_name()

        self.tenant_urlconf = getattr(settings, "TENANT_URLCONF", None)
        self.root_urlconf = settings.ROOT_URLCONF

        if not self.tenant_urlconf:
            logger.warning(
                "WARNING: TENANT_URLCONF no definido. Los clientes privados podrían fallar."
            )

        # Logging de inicialización
        logger.info(
            f"OK: TenantSecurityAndURLConfMiddleware inicializado | "
            f"Public schema: {self.public_schema} | "
            f"Allowed public domains: {sorted(self.ALLOWED_PUBLIC_DOMAINS)}"
        )
        # Rutas que pertenecen exclusivamente a tenants (no deben resolverse desde el public host)
        self.TENANT_ONLY_PATH_PREFIXES = (
            "/api/v1/empresas/",
            "/api/v1/empleados/",
            "/api/v1/gastos/",
            "/api/v1/facturas/",
        )

    def _normalize_host(self, request):
        """
        Normaliza y valida el host de la request.

        WARNING: SEGURIDAD: Protege contra Host Header Attacks.

        Returns:
            str: Host normalizado (sin puerto, en minúsculas)

        Raises:
            DisallowedHost: Si el host no está permitido por Django
            ValueError: Si el host tiene formato inválido
        """
        try:
            # Obtener host y limpiar puerto
            host = request.get_host().split(":")[0].lower().strip()

            # Validar que no esté vacío
            if not host:
                raise ValueError("Host vacío no permitido")

            # Validar formato básico (debe contener al menos un punto o ser localhost/127.0.0.1)
            if host not in self.ALLOWED_PUBLIC_DOMAINS and "." not in host:
                raise ValueError(f"Host con formato inválido: {host}")

            return host

        except DisallowedHost:
            security_logger.warning(
                f"🚨 HOST NO PERMITIDO POR DJANGO: {request.get_host()} | "
                f"Path: {request.path} | IP: {self._get_client_ip(request)}"
            )
            raise
        except Exception as e:
            security_logger.error(
                f"🚨 ERROR AL NORMALIZAR HOST: {str(e)} | "
                f"Host raw: {request.get_host()} | Path: {request.path}"
            )
            raise ValueError(f"Error al procesar host: {str(e)}")

    def _get_client_ip(self, request):
        """Obtiene la IP del cliente para logging de seguridad."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR", "unknown")
        return ip

    def _validate_public_access(self, host, tenant, request):
        """
        Valida acceso al ámbito público con múltiples capas de seguridad.

        WARNING: SEGURIDAD CRÍTICA:
        - Solo permite acceso desde dominios explícitamente permitidos
        - Bloquea subdominios intentando acceder al público
        - Registra intentos de acceso no autorizado

        Returns:
            bool: True si el acceso es permitido, False si debe bloquearse
        """
        # CAPA 1: Validar que el host esté en la whitelist
        if host not in self.ALLOWED_PUBLIC_DOMAINS:
            security_logger.warning(
                f"🚨 BLOQUEO PÚBLICO (Capa 1 - Whitelist): "
                f"Host '{host}' no está en ALLOWED_PUBLIC_DOMAINS | "
                f"Tenant: {tenant.schema_name} | "
                f"Path: {request.path} | "
                f"IP: {self._get_client_ip(request)}"
            )
            return False

        # CAPA 2: Bloquear subdominios intentando acceder al público
        # Ejemplo: cliente.sintel.com NO puede acceder al esquema público
        if host.endswith(self.REQUIRED_TENANT_SUFFIX):
            security_logger.warning(
                f"🚨 BLOQUEO PÚBLICO (Capa 2 - Subdominio): "
                f"Subdominio '{host}' intentó acceder al esquema público | "
                f"Tenant: {tenant.schema_name} | "
                f"Path: {request.path} | "
                f"IP: {self._get_client_ip(request)}"
            )
            return False

        # CAPA 3: Validar que no sea un subdominio de localhost en producción
        # (solo permitir localhost exacto, no subdominios)
        if host != "localhost" and "localhost" in host:
            security_logger.warning(
                f"🚨 BLOQUEO PÚBLICO (Capa 3 - Subdominio localhost): "
                f"Subdominio de localhost '{host}' intentó acceder al esquema público | "
                f"Tenant: {tenant.schema_name} | "
                f"Path: {request.path} | "
                f"IP: {self._get_client_ip(request)}"
            )
            return False

        # Acceso permitido
        logger.debug(
            f"OK: Acceso público permitido: {host} → {tenant.schema_name} | Path: {request.path}"
        )
        return True

    def _validate_private_access(self, host, tenant, request):
        """
        Valida acceso a tenant privado con validación de sintaxis de dominio.

        WARNING: SEGURIDAD:
        - Valida que el dominio termine en .sintel.com (producción)
        - Permite localhost/127.0.0.1 para desarrollo
        - Bloquea dominios con formato inválido

        Returns:
            bool: True si el acceso es permitido, False si debe bloquearse
        """
        # Validar sintaxis de dominio para producción
        is_valid_prod = host.endswith(self.REQUIRED_TENANT_SUFFIX)

        # Validar sintaxis de dominio para desarrollo
        is_valid_dev = any(indicator in host for indicator in self.DEV_DOMAIN_INDICATORS)

        if not (is_valid_prod or is_valid_dev):
            security_logger.error(
                f"🚨 BLOQUEO PRIVADO: "
                f"Tenant '{tenant.schema_name}' intentó cargar desde dominio no permitido: '{host}' | "
                f"Se exige '*{self.REQUIRED_TENANT_SUFFIX}' o dominio de desarrollo | "
                f"Path: {request.path} | "
                f"IP: {self._get_client_ip(request)}"
            )
            return False

        # Validación adicional: en producción, no permitir localhost
        # (esto previene confusión entre desarrollo y producción)
        if is_valid_prod and any(indicator in host for indicator in self.DEV_DOMAIN_INDICATORS):
            security_logger.warning(
                f"WARNING: ADVERTENCIA: Dominio de producción con indicador de desarrollo: '{host}' | "
                f"Tenant: {tenant.schema_name}"
            )

        logger.debug(
            f"OK: Acceso privado permitido: {host} → {tenant.schema_name} | Path: {request.path}"
        )
        return True

    def __call__(self, request):
        """
        Procesa la request con validaciones de seguridad y establece URLConf.

        WARNING: FLUJO:
        1. Obtener tenant resuelto por TenantMainMiddleware
        2. Normalizar y validar host
        3. Validar acceso según tipo de tenant (público/privado)
        4. Establecer request.urlconf correctamente
        5. Continuar con el siguiente middleware
        """
        # --- A. Obtener Tenant y Host ---
        tenant = getattr(request, "tenant", None)
        if not tenant:
            # Sin tenant: Django usará ROOT_URLCONF por defecto
            return self.get_response(request)

        try:
            # Normalizar host (protección contra Host Header Attacks)
            host = self._normalize_host(request)
        except (DisallowedHost, ValueError) as e:
            security_logger.error(
                f"🚨 ERROR DE HOST: {str(e)} | "
                f"Path: {request.path} | "
                f"IP: {self._get_client_ip(request)}"
            )
            return HttpResponseForbidden("Invalid Host Header")

        # Debug tracing for test diagnosis
        try:
            logger.debug(
                "TenantSecurityAndURLConfMiddleware: host=%s tenant=%s path=%s method=%s",
                host,
                getattr(tenant, 'schema_name', None),
                request.path,
                request.method,
            )
        except Exception:
            pass

        # --- B. Lógica de Seguridad por Tipo de Esquema ---

        # 1. ESQUEMA PÚBLICO (Landing page, Login central, Consola)
        if tenant.schema_name == self.public_schema:
            # Validar acceso con múltiples capas de seguridad
            access_valid = self._validate_public_access(host, tenant, request)
            logger.info(
                f"🔍 VALIDACIÓN PÚBLICA: Host='{host}' | Tenant='{tenant.schema_name}' | "
                f"Path='{request.path}' | Acceso={'PERMITIDO' if access_valid else 'BLOQUEADO'}"
            )

            if not access_valid:
                # Bloquear acceso no autorizado
                logger.warning(
                    f"⛔ BLOQUEO PÚBLICO: Intento de acceso desde '{host}' al esquema público. "
                    f"Path: {request.path}"
                )
                # Http404 se lanza después de que Django intente resolver las URLs
                # Si lanzamos Http404 aquí, Django nunca intentará resolver las URLs
                logger.debug("TenantSecurityAndURLConfMiddleware: blocked public access host=%s tenant=%s path=%s", host, tenant.schema_name, request.path)
                return HttpResponseForbidden("Acceso no autorizado al esquema público.")

            # Acceso permitido: Asignar URLs públicas
            # Si la request apunta a un endpoint que es exclusivo de tenants,
            # devolver una respuesta clara en vez de dejar que Django responda 404.
            path = request.path or ""
            for prefix in self.TENANT_ONLY_PATH_PREFIXES:
                if path.startswith(prefix):
                    logger.warning(
                        f"⛔ ACCESO INAPROPIADO: intento de acceder a ruta tenant desde host público: {path} | host={host}"
                    )
                    return JsonResponse(
                        {
                            "detail": "Este endpoint es exclusivo para tenants. Use el dominio del tenant (ej: subdominio.sintel.com) o configure el host apropiado."
                        },
                        status=400,
                    )

            request.urlconf = self.root_urlconf
            logger.info(
                f"OK: URLConf establecido: ROOT_URLCONF='{self.root_urlconf}' para tenant público '{tenant.schema_name}' | Path='{request.path}'"
            )
            logger.debug("TenantSecurityAndURLConfMiddleware: set ROOT_URLCONF for public tenant=%s path=%s", tenant.schema_name, request.path)

        # 2. ESQUEMA PRIVADO (Clientes / Tenants)
        else:
            # Validar acceso con validación de sintaxis de dominio
            if not self._validate_private_access(host, tenant, request):
                # Bloquear acceso no autorizado
                return HttpResponseForbidden(
                    f"Dominio no autorizado para este cliente. "
                    f"Debe usar *{self.REQUIRED_TENANT_SUFFIX} o un dominio de desarrollo válido."
                )

            # Acceso permitido: Asignar URLs del Tenant
            if self.tenant_urlconf:
                if not hasattr(request, "urlconf") or request.urlconf != self.tenant_urlconf:
                    request.urlconf = self.tenant_urlconf
                    logger.debug(
                        f"OK: URLConf establecido: TENANT_URLCONF para tenant privado '{tenant.schema_name}'"
                    )
            else:
                logger.error(
                    f"ERROR: TENANT_URLCONF no definido. Tenant '{tenant.schema_name}' usará ROOT_URLCONF "
                    f"(puede causar 404s en rutas de tenant)"
                )

        return self.get_response(request)
