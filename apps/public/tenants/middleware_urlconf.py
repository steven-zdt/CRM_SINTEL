"""
Middleware de Seguridad y Enrutamiento Multi-Tenant (Sintel Version).

⚠️ SEGURIDAD CRÍTICA:
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
from django.http import HttpResponseForbidden, Http404
from django.core.exceptions import DisallowedHost
from django_tenants.utils import get_public_schema_name

logger = logging.getLogger(__name__)
security_logger = logging.getLogger('security.tenants')


class TenantSecurityAndURLConfMiddleware:
    """
    Middleware de Seguridad y Enrutamiento Multi-Tenant (Sintel Version).
    
    ⚠️ FUNCIONES:
    1. SEGURIDAD: Protege el ámbito público de accesos no autorizados
    2. URLConf: Establece request.urlconf según el tipo de tenant
    3. VALIDACIÓN: Valida dominios y previene Host Header Attacks
    
    ⚠️ CAPAS DE SEGURIDAD:
    - Validación estricta de dominios permitidos para ámbito público
    - Bloqueo de subdominios intentando acceder al ámbito público
    - Validación de sintaxis de dominios para tenants privados
    - Logging de seguridad para auditoría
    - Protección contra Host Header Attacks
    """

    # 1. Configuración del Esquema Público (WHITELIST ESTRICTA)
    ALLOWED_PUBLIC_DOMAINS = frozenset([
        'sintel.com',      # Dominio de producción
        'localhost',       # Desarrollo local
        '127.0.0.1',       # Desarrollo local (IP)
        '0.0.0.0',         # Desarrollo local (bind all)
    ])
    
    # 2. Configuración del Esquema Privado (Sufijo obligatorio)
    REQUIRED_TENANT_SUFFIX = '.sintel.com'
    
    # 3. Dominios de desarrollo permitidos para tenants privados
    DEV_DOMAIN_INDICATORS = frozenset(['localhost', '127.0.0.1', '0.0.0.0'])

    def __init__(self, get_response):
        self.get_response = get_response
        self.public_schema = get_public_schema_name()
        
        self.tenant_urlconf = getattr(settings, 'TENANT_URLCONF', None)
        self.root_urlconf = settings.ROOT_URLCONF

        if not self.tenant_urlconf:
            logger.warning("⚠️ TENANT_URLCONF no definido. Los clientes privados podrían fallar.")
        
        # Logging de inicialización
        logger.info(
            f"✅ TenantSecurityAndURLConfMiddleware inicializado | "
            f"Public schema: {self.public_schema} | "
            f"Allowed public domains: {sorted(self.ALLOWED_PUBLIC_DOMAINS)}"
        )

    def _normalize_host(self, request):
        """
        Normaliza y valida el host de la request.
        
        ⚠️ SEGURIDAD: Protege contra Host Header Attacks.
        
        Returns:
            str: Host normalizado (sin puerto, en minúsculas)
        
        Raises:
            DisallowedHost: Si el host no está permitido por Django
            ValueError: Si el host tiene formato inválido
        """
        try:
            # Obtener host y limpiar puerto
            host = request.get_host().split(':')[0].lower().strip()
            
            # Validar que no esté vacío
            if not host:
                raise ValueError("Host vacío no permitido")
            
            # Validar formato básico (debe contener al menos un punto o ser localhost/127.0.0.1)
            if host not in self.ALLOWED_PUBLIC_DOMAINS and '.' not in host:
                raise ValueError(f"Host con formato inválido: {host}")
            
            return host
            
        except DisallowedHost as e:
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
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip

    def _validate_public_access(self, host, tenant, request):
        """
        Valida acceso al ámbito público con múltiples capas de seguridad.
        
        ⚠️ SEGURIDAD CRÍTICA:
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
        if host != 'localhost' and 'localhost' in host:
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
            f"✅ Acceso público permitido: {host} → {tenant.schema_name} | Path: {request.path}"
        )
        return True

    def _validate_private_access(self, host, tenant, request):
        """
        Valida acceso a tenant privado con validación de sintaxis de dominio.
        
        ⚠️ SEGURIDAD:
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
                f"⚠️ ADVERTENCIA: Dominio de producción con indicador de desarrollo: '{host}' | "
                f"Tenant: {tenant.schema_name}"
            )
        
        logger.debug(
            f"✅ Acceso privado permitido: {host} → {tenant.schema_name} | Path: {request.path}"
        )
        return True

    def __call__(self, request):
        """
        Procesa la request con validaciones de seguridad y establece URLConf.
        
        ⚠️ FLUJO:
        1. Obtener tenant resuelto por TenantMainMiddleware
        2. Normalizar y validar host
        3. Validar acceso según tipo de tenant (público/privado)
        4. Establecer request.urlconf correctamente
        5. Continuar con el siguiente middleware
        """
        # --- A. Obtener Tenant y Host ---
        tenant = getattr(request, 'tenant', None)
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

        # --- B. Lógica de Seguridad por Tipo de Esquema ---
        
        # 1. ESQUEMA PÚBLICO (Landing page, Login central, Consola)
        if tenant.schema_name == self.public_schema:
            # Validar acceso con múltiples capas de seguridad
            if not self._validate_public_access(host, tenant, request):
                # Bloquear acceso no autorizado
                logger.warning(
                    f"⛔ BLOQUEO PÚBLICO: Intento de acceso desde '{host}' al esquema público. "
                    f"Path: {request.path}"
                )
                raise Http404("Recurso no encontrado.")
            
            # Acceso permitido: Asignar URLs públicas
            request.urlconf = self.root_urlconf
            logger.debug(f"✅ URLConf establecido: ROOT_URLCONF para tenant público '{tenant.schema_name}'")

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
                if not hasattr(request, 'urlconf') or request.urlconf != self.tenant_urlconf:
                    request.urlconf = self.tenant_urlconf
                    logger.debug(
                        f"✅ URLConf establecido: TENANT_URLCONF para tenant privado '{tenant.schema_name}'"
                    )
            else:
                logger.error(
                    f"❌ TENANT_URLCONF no definido. Tenant '{tenant.schema_name}' usará ROOT_URLCONF "
                    f"(puede causar 404s en rutas de tenant)"
                )

        return self.get_response(request)
