"""
Django settings for sintel_project project.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Cargar variables de entorno desde .env si existe
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
# WARNING: v2.30: SECRET_KEY debe ser >= 50 caracteres pseudoaleatorios
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-change-me-in-production')
if len(SECRET_KEY) < 50:
    import warnings
    warnings.warn(
        f"WARNING: SECRET_KEY tiene solo {len(SECRET_KEY)} caracteres. "
        f"Se recomienda >= 50 caracteres para producción. "
        f"Genera uno con: python -c 'import secrets; print(secrets.token_urlsafe(50))'",
        UserWarning
    )

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DJANGO_DEBUG', 'True') == 'True'


# Application definition
# WARNING: ESTRUCTURA CRÍTICA: Separación estricta entre SHARED_APPS y TENANT_APPS
# 
# REGLAS DE ORO:
# 1. SHARED_APPS: Apps que existen SOLO en el esquema 'public' (compartidas por todos los tenants)
# 2. TENANT_APPS: Apps que viven en cada esquema de tenant (específicas de cada empresa)
# 3. WARNING: CRÍTICO: NINGUNA app de apps.tenant.* puede estar en SHARED_APPS
# 4. Django consultará primero el esquema del tenant y luego 'public'
# 5. django-tenants usa estas listas para determinar dónde crear las tablas de cada app

# ============================================================================
# SHARED_APPS: Apps del esquema PUBLIC (compartidas por todos los tenants)
# ============================================================================
# WARNING: CRÍTICO: Estas apps SOLO se instalan en el esquema 'public'
# WARNING: REGLA DE ORO: NINGUNA app que comience con 'apps.tenant.' puede estar aquí
# WARNING: REGLA DE ORO: TODAS las apps que comienzan con 'apps.public.' DEBEN estar aquí
SHARED_APPS = [
    # django-tenants DEBE ir PRIMERO (requisito obligatorio de django-tenants)
    "django_tenants",
    
    # WARNING: APPS PÚBLICAS DEL PROYECTO (SOLO esquema public)
    # Estas apps JAMÁS deben estar en TENANT_APPS
    "apps.public.core",     # Core público (middleware, Server Guard) (SOLO public)
    "apps.public.tenants",   # Gestión de tenants y dominios (SOLO public)
    "apps.public.accounts",  # Usuarios globales (AUTH_USER_MODEL) (SOLO public)
    "apps.public.impuestos", # Catálogo legal/DIAN (compartido) (SOLO public)
    "apps.public.console",   # Consola de administración pública (interfaz web) (SOLO public)
    
    # DRF y herramientas API para esquema public (APIs públicas)
    # WARNING: NOTA: Estas apps también están en TENANT_APPS porque se necesitan en ambos esquemas
    # django-tenants permite que apps estén en ambas listas (se instalan en ambos esquemas)
    "rest_framework",  # DRF para APIs públicas en esquema public
    "rest_framework_simplejwt",  # Autenticación JWT (SimpleJWT)
    "rest_framework_simplejwt.token_blacklist",  # Blacklist de refresh tokens
    "django_filters",  # Filtrado para APIs públicas
    "drf_spectacular",  # OpenAPI schema generation para APIs públicas
    "djangorestframework_mcp",  # MCP server: expone ViewSets como herramientas via /mcp/
    "corsheaders",  # CORS para subdominios dinámicos (sintel.com)
    
    # Django contrib apps (necesarias para admin y funcionalidad base)
    "django.contrib.contenttypes",  # Requerido por admin y relaciones genéricas
    "django.contrib.auth",          # Sistema de autenticación (usuarios globales)
    "django.contrib.admin",         # Admin de Django (en public para gestión global)
    "django.contrib.sessions",      # Sesiones compartidas (usuarios globales)
    "django.contrib.messages",      # Sistema de mensajes
    "django.contrib.staticfiles",   # Archivos estáticos
]

# ============================================================================
# TENANT_APPS: Apps de esquemas PRIVADOS (específicas de cada tenant)
# ============================================================================
# WARNING: CRÍTICO: Estas apps SOLO se instalan en esquemas de tenant (NO en public)
# WARNING: REGLA DE ORO: NINGUNA app que comience con 'apps.public.' puede estar aquí
# WARNING: REGLA DE ORO: TODAS las apps que comienzan con 'apps.tenant.' DEBEN estar aquí
TENANT_APPS = [
    # DRF y herramientas API (disponibles en cada tenant para APIs privadas)
    # WARNING: NOTA: Estas apps también están en SHARED_APPS porque se necesitan en ambos esquemas
    # django-tenants permite que apps estén en ambas listas (se instalan en ambos esquemas)
    "rest_framework",  # DRF para APIs privadas de cada tenant
    "django_filters",  # Filtrado para APIs privadas de cada tenant
    "drf_spectacular",  # OpenAPI schema generation para APIs privadas de cada tenant
    "djangorestframework_mcp",  # MCP server: expone ViewSets como herramientas via /mcp/
    
    # WARNING: APPS PRIVADAS: Aplicaciones de negocio por tenant
    # Estas apps SOLO existen en esquemas de tenant, NUNCA en public
    "apps.tenant.core",         # Vistas core y manejadores de error (404, 403)
    "apps.tenant.empresa",      # Datos de la empresa (por tenant)
    "apps.tenant.facturas",     # Facturación (por tenant)
    "apps.tenant.contabilidad", # Contabilidad (por tenant)
    "apps.tenant.inventario",   # Inventario (por tenant)
    "apps.tenant.empleados",    # Empleados y nómina (por tenant)
    "apps.tenant.gastos",       # Gastos operativos y de personal (por tenant)
    "apps.tenant.cotizaciones", # Cotizaciones y presupuestos (por tenant) v2.40
    "apps.tenant.proveedores",  # Proveedores y compras (por tenant)
    "apps.tenant.clientes",    # Clientas y ventas (por tenant)
    "apps.tenant.proyectos",   # Proyectos (por tenant)
    "apps.tenant.landing",      # Landing page para tenants (accesible anónimamente)
    "apps.tenant.dashboard",    # Dashboard con control de roles
    "apps.tenant.perfil",       # Perfil privado del colaborador (por tenant)
    "apps.tenant.bancos",       # Gestion de estados bancarios y conciliacion (por tenant)
]

# ============================================================================
# INSTALLED_APPS: Lista completa para Django
# ============================================================================
# WARNING: CRÍTICO: Esta fórmula elimina duplicados (apps que están en ambas listas)
# Las apps que están en ambas listas (ej: rest_framework) se instalan en ambos esquemas
# WARNING: VALIDACIÓN: Verificar que ninguna app.tenant.* esté en SHARED_APPS
INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]

# WARNING: VALIDACIÓN DE SEGURIDAD: Verificar segregación estricta de apps
# Estas validaciones previenen la contaminación de esquemas privados con apps públicas

# 1. Verificar que NO haya apps de tenant en SHARED_APPS
_tenant_apps_in_shared = [app for app in SHARED_APPS if app.startswith("apps.tenant.")]
if _tenant_apps_in_shared:
    raise ValueError(
        f"ERROR: ERROR CRÍTICO: Apps de tenant encontradas en SHARED_APPS: {_tenant_apps_in_shared}. "
        f"Las apps de tenant SOLO deben estar en TENANT_APPS."
    )

# 2. Verificar que TODAS las apps públicas NO estén en TENANT_APPS
# WARNING: CRÍTICO: Cualquier app que comience con 'apps.public.' JAMÁS debe estar en TENANT_APPS
_public_apps_in_tenant = [app for app in TENANT_APPS if app.startswith("apps.public.")]
if _public_apps_in_tenant:
    raise ValueError(
        f"ERROR: ERROR CRÍTICO: Apps públicas encontradas en TENANT_APPS: {_public_apps_in_tenant}. "
        f"Las apps públicas (apps.public.*) JAMÁS deben estar en TENANT_APPS. "
        f"SOLO deben estar en SHARED_APPS."
    )

# 3. Verificar que apps públicas obligatorias estén en SHARED_APPS
_required_public_apps = [
    "apps.public.tenants",
    "apps.public.accounts",
    "apps.public.impuestos",
]
_missing_public_apps = [app for app in _required_public_apps if app not in SHARED_APPS]
if _missing_public_apps:
    raise ValueError(
        f"ERROR: ERROR CRÍTICO: Apps públicas obligatorias faltantes en SHARED_APPS: {_missing_public_apps}. "
        f"Estas apps DEBEN estar en SHARED_APPS."
    )

# 4. Verificar que apps privadas obligatorias estén en TENANT_APPS
_required_tenant_apps = [
    "apps.tenant.empresa",
    "apps.tenant.facturas",
    "apps.tenant.contabilidad",
    "apps.tenant.inventario",
    "apps.tenant.landing",
    "apps.tenant.dashboard",
    "apps.tenant.perfil",
]
_missing_tenant_apps = [app for app in _required_tenant_apps if app not in TENANT_APPS]
if _missing_tenant_apps:
    raise ValueError(
        f"ERROR: ERROR CRÍTICO: Apps privadas obligatorias faltantes en TENANT_APPS: {_missing_tenant_apps}. "
        f"Estas apps DEBEN estar en TENANT_APPS."
    )

# WARNING: CONFIGURACIÓN CRÍTICA: Orden de middleware para django-tenants
# WARNING: ESTÁNDAR: Puerto 80 (HTTP) - ForceNoPortMiddleware normaliza HTTP_HOST antes de TenantMainMiddleware
# WARNING: v2.26: Orden optimizado para enrutamiento estable por hostname
# 
# Orden crítico:
# 1. SecurityMiddleware, WhiteNoise, CORS (infraestructura)
# 2. SessionMiddleware (requerido antes de normalización de host)
# 3. ForceNoPortMiddleware (normaliza HTTP_HOST eliminando puerto)
# 4. TenantMainMiddleware (CRÍTICO: resuelve tenant por hostname y selecciona URLConf)
# 5. Middlewares de seguridad y validación (después de resolución de tenant)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # OK: WhiteNoise para servir staticfiles en producción
    'corsheaders.middleware.CorsMiddleware',  # OK: CORS: Debe ir ANTES de CommonMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',  # OK: CRÍTICO: Debe ejecutarse antes de ForceNoPortMiddleware
    'apps.public.core.middleware.ValidateALLOWED_HOSTSMiddleware',  # OK: SEGURIDAD: Valida Host header contra ALLOWED_HOSTS (ANTES de Django URL resolution)
    'apps.public.core.middleware.ForceNoPortMiddleware',  # OK: ESTÁNDAR: Normaliza HTTP_HOST eliminando puerto (ANTES de TenantMainMiddleware)
    'django_tenants.middleware.main.TenantMainMiddleware',  # OK: CRÍTICO: Identifica tenant usando HTTP_HOST normalizado y selecciona URLConf (ROOT_URLCONF o TENANT_URLCONF)
    'apps.tenant.core.middleware.SintelExceptionMiddleware',  # OK: v2.40: Manejo centralizado de excepciones (DESPUÉS de TenantMainMiddleware para tener contexto del esquema)
    'apps.public.tenants.middleware_urlconf.TenantSecurityAndURLConfMiddleware',  # OK: SEGURIDAD + URLConf: Protege ámbito público y establece request.urlconf (después de TenantMainMiddleware)
    'apps.public.tenants.middleware.TenantSecurityMiddleware',  # OK: SEGURIDAD: Bloquea tenants suspendidos (debe ir después de TenantMainMiddleware)
    'apps.public.core.middleware.CSRFTrustedOriginMiddleware',  # OK: DESARROLLO: Permite dominios arbitrarios en CSRF_TRUSTED_ORIGINS
    'django.middleware.common.CommonMiddleware',
    'apps.public.core.middleware.DebugNoCSRFMiddleware',  # OK: DESARROLLO: Desactiva CSRF en DEBUG mode
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # OK: CRÍTICO: Proporciona request.user (requerido para require_tenant_membership)
    'apps.public.tenants.authz.require_tenant_membership',  # OK: SEGURIDAD: Valida membresía del tenant para usuarios autenticados (factory funcional)
    'apps.public.tenants.middleware_admin_guard.block_public_routes_on_tenants',  # OK: GUARD-RAIL: Bloquea /admin/, /console/ y /api/public/ en cualquier esquema ≠ public
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# WARNING: CONFIGURACIÓN CRÍTICA: URLs separadas para público y privado
# django-tenants usa ROOT_URLCONF para el esquema 'public' y TENANT_URLCONF para tenants
ROOT_URLCONF = 'config.urls_public'  # URLs para esquema público (sintel.com)
TENANT_URLCONF = 'config.urls_tenant'  # URLs para tenants privados (cliente.sintel.com)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',  # OK: CRÍTICO: Requerido por django-tenants
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
# WARNING: CONFIGURACIÓN CRÍTICA: ENGINE debe ser django_tenants.postgresql_backend
DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',  # OK: CRÍTICO: Backend especial para multi-tenant
        'NAME': os.getenv('DATABASE_NAME', 'sintel'),
        'USER': os.getenv('DATABASE_USER', 'sintel'),
        'PASSWORD': os.getenv('DATABASE_PASSWORD', 'sintel'),
        'HOST': os.getenv('DATABASE_HOST', 'db'),
        'PORT': os.getenv('DATABASE_PORT', '5432'),
    }
}

# WARNING: CONFIGURACIÓN CRÍTICA: DATABASE_ROUTERS debe ser una tupla con TenantSyncRouter
DATABASE_ROUTERS = (
    'django_tenants.routers.TenantSyncRouter',  # OK: CRÍTICO: Router para enrutar queries al esquema correcto
)

# Tenant Configuration
TENANT_MODEL = "tenants.Client"
TENANT_DOMAIN_MODEL = "tenants.Domain"
AUTH_USER_MODEL = "accounts.User"

# WARNING: CONFIGURACIÓN DE SUBDOMINIOS (v2.17) - POLÍTICA ESTRICTA
# Dominio base del SaaS para construcción automática de subdominios
# 
# REGLA DE ORO:
# - El dominio base se configura desde variable de entorno o usa 'sintel.com' por defecto
# - En DEV: Puede ser 'sintel.localhost' (configurable desde .env)
# - En PROD: 'sintel.com' (configurable desde .env)
# 
# POLÍTICA ESTRICTA:
# - El tenant PÚBLICO siempre responde en {TENANT_DOMAIN_BASE} (ej: sintel.com)
# - Los tenants PRIVADOS siempre usan subdominios: {schema_name}.{TENANT_DOMAIN_BASE} (ej: cliente.sintel.com)
# - NO se permiten dominios arbitrarios o FQDN personalizados
# - Los subdominios se activan automáticamente y son accesibles desde el navegador
# WARNING: DOMINIO PRINCIPAL Y DEFINITIVO: sintel.com
# sintel.com es el dominio principal y definitivo para el tenant público en TODOS los entornos
# Para desarrollo local, añadir sintel.com a /etc/hosts (Linux/Mac) o hosts de Windows
# Los tenants privados usan subdominios: {schema_name}.sintel.com
_default_tenant_domain_base = 'sintel.com'  # WARNING: DOMINIO PRINCIPAL Y DEFINITIVO
TENANT_DOMAIN_BASE = os.getenv('TENANT_DOMAIN_BASE', _default_tenant_domain_base)

# Puerto de la aplicación (solo para referencia, NO se usa en dominios)
# WARNING: ESTÁNDAR: Puerto 80 (HTTP) - Los dominios NO incluyen puerto explícito
# En desarrollo: runserver puede usar 8000, pero los dominios son sin puerto
# En producción: 80 (HTTP) o 443 (HTTPS) - puertos implícitos
APP_PORT = os.getenv('APP_PORT', '8000')  # Solo para referencia, no se usa en construcción de URLs
SITE_PROTOCOL = os.getenv('SITE_PROTOCOL', '')  # 'https' para forzar en todos los URL builders

# Tenant configuration
TENANT_MODEL = "tenants.Client"  # app_label es 'tenants' (último componente de 'apps.public.tenants')
TENANT_DOMAIN_MODEL = "tenants.Domain"

# When True, if no tenant is found for the request hostname, the system
# will serve the public URLConf instead of raising 404. This is useful for
# development and test environments where the Domain table may not contain
# an entry for 'localhost' or ephemeral hosts. Default: True in DEBUG.
SHOW_PUBLIC_IF_NO_TENANT_FOUND = os.getenv('SHOW_PUBLIC_IF_NO_TENANT_FOUND', 'True' if DEBUG else 'False') == 'True'

# Custom User Model
AUTH_USER_MODEL = "accounts.User"  # app_label.ModelName
# IMPORTANTE: Esta configuración debe hacerse ANTES de la primera migración
# Si ya tienes migraciones, necesitarás crear el modelo y luego hacer las migraciones

# WARNING: SEGURIDAD: Backends de autenticación tenant-aware
# El orden es importante: TenantAwareBackend debe ir ANTES de ModelBackend
# para que filtre primero y valide la membresía del tenant
AUTHENTICATION_BACKENDS = [
    'apps.public.tenants.auth_backend.TenantAwareBackend',  # OK: SEGURIDAD: Filtro tenant (debe ir primero)
    'django.contrib.auth.backends.ModelBackend',  # Fallback estándar (opcional, pero recomendado para compatibilidad)
]

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'es-co'
TIME_ZONE = os.getenv('TIME_ZONE', 'America/Bogota')
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'  # Para producción (collectstatic)
STATICFILES_DIRS = [
    BASE_DIR / 'static',  # Directorio global de archivos estáticos (opcional)
]

# Media files (Uploaded files: avatares, logos, etc.)
MEDIA_URL = '/media/'  # URL base para archivos media
MEDIA_ROOT = BASE_DIR / 'media'  # Directorio donde se almacenan los archivos subidos

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# WhiteNoise: servir staticfiles en producción
# Referencia: https://whitenoise.readthedocs.io/
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# WhiteNoise: configuración adicional
WHITENOISE_USE_FINDERS = DEBUG  # Usar finders en desarrollo para recoger cambios sin collectstatic
WHITENOISE_AUTOREFRESH = DEBUG  # Solo en desarrollo

# Test Runner Configuration
# WARNING: CRÍTICO: Requerido para que django-tenants maneje correctamente la creación de esquemas en tests
# TEST_RUNNER: Usar DiscoverRunner estándar de Django (por defecto)
# django-tenants no requiere un test runner especial; usa TenantTestCase y TenantClient
# TEST_RUNNER = 'django.test.runner.DiscoverRunner'  # Por defecto en Django

# Security Settings (Development)
# WARNING: IMPORTANTE: Django's runserver solo soporta HTTP, NO HTTPS
# En desarrollo local, siempre usar HTTP (http://localhost o http://tupapi.com) - puerto 80 implícito
# El middleware HTTPSRedirectMiddleware intenta redirigir HTTPS -> HTTP en DEBUG
# Si el navegador fuerza HTTPS, limpiar HSTS: chrome://net-internals/#hsts
# Para producción, configurar estas opciones en un módulo de settings separado
SECURE_SSL_REDIRECT = False  # No forzar HTTPS en desarrollo
SESSION_COOKIE_SECURE = False  # Cookies de sesión no requieren HTTPS en desarrollo
CSRF_COOKIE_SECURE = False  # Cookies CSRF no requieren HTTPS en desarrollo

# Cross-Origin-Opener-Policy (COOP)
# WARNING: WARNING: El navegador mostrará un warning si usas HTTP en lugar de HTTPS
# Esto es normal en desarrollo y no afecta la funcionalidad
# En producción, configurar HTTPS y agregar este header solo en HTTPS
if DEBUG:
    # En desarrollo, no configurar COOP (evita warnings innecesarios)
    SECURE_CROSS_ORIGIN_OPENER_POLICY = None
else:
    # En producción con HTTPS, usar COOP restrictivo
    SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin-allow-popups'

# --- Configuración Dinámica de Dominios (SINTEL) ---
# Permite tráfico desde cualquier subdominio de sintel.com
# Configuración de seguridad para dominios dinámicos multi-tenant

import re

"""
Seguridad Host Header (prod) y soporte HTTPS detrás de proxy.

- ALLOWED_HOSTS: lista explícita; en prod NO usar '*'.
- USE_X_FORWARDED_HOST / SECURE_PROXY_SSL_HEADER: forzan https en build_absolute_uri detrás de proxy.
- CSRF_TRUSTED_ORIGINS: desde Django 4/5 debe incluir esquema (http/https).
"""

# 1. ALLOWED HOSTS (Configuración dinámica basada en DEBUG)
# WARNING: POLÍTICA ESTRICTA DE SUBDOMINIOS:
# - El punto inicial (.) actúa como wildcard estándar de Django
# - Acepta cualquier subdominio del dominio base (ej: cliente.sintel.com, ejemplo.sintel.com)
# - El dominio base sin punto es para el tenant público (ej: sintel.com)
# - Los subdominios se activan automáticamente al crear un tenant
# WARNING: SEGURIDAD: En producción, usar lista explícita desde ENV (NO usar '*')
# WARNING: v2.60: Siempre incluir sintel.com y dominios públicos para permitir acceso desde ambos dominios
base_allowed_hosts = (
    os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,192.168.2.15,sintel.com,186.117.247.166,186.117.247.167").split(",")
    if DEBUG
    else os.getenv("ALLOWED_HOSTS", "sintel.com,.sintel.com,186.117.247.166,186.117.247.167").split(",")
)

# Limpiar espacios y filtrar vacíos
ALLOWED_HOSTS = [h.strip() for h in base_allowed_hosts if h.strip()]

# WARNING: v2.60: Asegurar que sintel.com siempre esté incluido (para acceso desde dominio público)
if 'sintel.com' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('sintel.com')

# En desarrollo, agregar hosts adicionales si no están en ENV
if DEBUG:
    _dev_hosts = [
        f".{TENANT_DOMAIN_BASE}",  # .sintel.com o .localhost (acepta cualquier subdominio)
        TENANT_DOMAIN_BASE,  # sintel.com o localhost (dominio base - tenant público)
        "localhost",  # Para desarrollo local estándar
        ".localhost",  # WARNING: CRÍTICO: Permite subdominios locales (cliente.localhost, etc.)
        "127.0.0.1",  # Para desarrollo local estándar
        "sintel.com",  # Dominio de producción (también disponible en desarrollo)
        ".sintel.com",
        "sintel.com.co",
        "testserver",
        "test.sintel.local",  # Soporte para tests
        "192.168.2.15",  # IP local del servidor (acceso desde red interna)
    ]
    for host in _dev_hosts:
        if host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(host)

# HTTPS vía proxy inverso (Nginx/Traefik)
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# 2. CORS (Cross-Origin Resource Sharing)
# Regex para validar origen (más seguro que CORS_ORIGIN_ALLOW_ALL)
CORS_ALLOWED_ORIGIN_REGEXES = [
    rf"^https://.*\.{re.escape(TENANT_DOMAIN_BASE)}$",
    r"^https://.*\.sintel\.com$",  # Cualquier subdominio de sintel.com en HTTPS
]

# En desarrollo, también permitir HTTP
if DEBUG:
    CORS_ALLOWED_ORIGIN_REGEXES.extend([
        rf"^http://.*\.{re.escape(TENANT_DOMAIN_BASE)}$",
        r"^http://.*\.sintel\.com(:\d+)?$",  # Cualquier subdominio de sintel.com en HTTP (con puerto opcional)
        r"^http://sintel\.com(:\d+)?$",  # Dominio sintel.com en HTTP (con puerto opcional)
    ])
    # También permitir localhost e IP local en desarrollo
    CORS_ALLOWED_ORIGIN_REGEXES.extend([
        r"^http://localhost(:\d+)?$",
        r"^http://127\.0\.0\.1(:\d+)?$",
        r"^https?://192\.168\.2\.15(:\d+)?$",  # IP local del servidor
    ])

# WARNING: IMPORTANTE: Permitir credenciales (cookies) en CORS para autenticación por sesión
CORS_ALLOW_CREDENTIALS = True

# 3. CSRF Trusted Origins
# WARNING: IMPORTANTE: Django NO soporta wildcards (*) en CSRF_TRUSTED_ORIGINS
# WARNING: SEGURIDAD: Desde Django 4/5 debe incluir esquema (http/https)
# En producción, se debe usar el middleware CSRFTrustedOriginMiddleware
# que permite dominios dinámicos basados en la validación de django-tenants
# CSRF: orígenes de confianza (con esquema). Separar por comas en ENV.
_csrf_origins = os.getenv(
    "CSRF_TRUSTED_ORIGINS",
    "http://localhost,http://127.0.0.1,http://192.168.2.15,https://192.168.2.15,https://sintel.com,https://.sintel.com,https://186.117.247.166,https://186.117.247.167",
).split(",")
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins if o.strip()]

# En desarrollo, agregar orígenes adicionales si no están en ENV
if DEBUG:
    _dev_csrf_origins = [
        "http://localhost",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:8000",
        f"http://{TENANT_DOMAIN_BASE}",
        "http://sintel.com",  # Dominio de producción (también disponible en desarrollo)
        "http://sintel.com:8000",  # Dominio con puerto 8000 para desarrollo
        "http://*.sintel.com:8000",  # Todos los subdominios tenant en desarrollo
        "http://192.168.2.15",  # IP local del servidor
        "https://192.168.2.15",
        "http://192.168.2.15:8000",
    ]
    for origin in _dev_csrf_origins:
        if origin not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(origin)
else:
    # En producción, agregar orígenes HTTPS explícitos si no están en ENV
    _prod_csrf_origins = [
        "https://sintel.com",         # Dominio público principal
        "https://.sintel.com.co",     # Subdominios de sintel.com
        "https://186.117.247.166",    # IP pública del servidor (acceso directo por IP)
        "https://186.117.247.167",    # IP pública del servidor (acceso directo por IP)
    ]
    for origin in _prod_csrf_origins:
        if origin not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(origin)

# 4. CSRF Cookie Domain y Configuración
# Permitir compartir cookie CSRF entre subdominios (necesario para login global si aplica)
# El punto inicial (.) permite que la cookie sea accesible desde cualquier subdominio
# En desarrollo, no restringir el dominio para permitir dominios arbitrarios (ej: tupapi.com, ejemplo.com)
# WARNING: v2.30: Nombre de cookie debe coincidir con el que lee el frontend
CSRF_COOKIE_NAME = "csrftoken"  # Debe coincidir con getCookie("csrftoken") en workspace.html

if DEBUG:
    CSRF_COOKIE_DOMAIN = None  # En desarrollo, permitir cualquier dominio (incluye subdominios y puertos)
    CSRF_COOKIE_SAMESITE = 'Lax'  # Permitir cookies en requests del mismo sitio
    CSRF_COOKIE_HTTPONLY = False  # Permitir acceso desde JavaScript (necesario para leer desde JS)
    CSRF_COOKIE_SECURE = False  # No requiere HTTPS en desarrollo
    CSRF_USE_SESSIONS = False  # Usar cookies en lugar de sesiones para CSRF
else:
    CSRF_COOKIE_DOMAIN = f".{TENANT_DOMAIN_BASE}"  # En producción, restringir a subdominios
    CSRF_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_HTTPONLY = False
    CSRF_COOKIE_SECURE = True  # Requiere HTTPS en producción
    CSRF_USE_SESSIONS = False

# Authentication URLs
# Configuración de URLs de autenticación
# WARNING: TENANTS PRIVADOS: Usan /login/ (vista personalizada TenantLoginView)
# WARNING: ESQUEMA PÚBLICO: Usa /admin/login/ (admin de Django)
# Para tenants privados, la landing page (/) es la vista principal
# WARNING: CRÍTICO: URL de login para tenants privados (usado por LoginRequiredMixin y decoradores)
# Esta configuración asegura que @login_required nunca redirija a /admin/login/ en tenants privados
# En tenants privados: /login/ -> TenantLoginView
# En esquema público: /login/ -> /admin/login/ (redirección en config/urls.py)
LOGIN_URL = '/login/'  # OK: FORZADO: login del TENANT_URLCONF (no /admin/login/)
# LOGIN_REDIRECT_URL se configura dinámicamente según el contexto (público vs tenant)
# Para tenants privados, redirige al dashboard: /dashboard/ (resuelto en TENANT_URLCONF)
# Para dominio público, redirige a '/console/'
LOGIN_REDIRECT_URL = '/dashboard/'  # OK: URL por defecto para tenants (se resuelve en TENANT_URLCONF)
LOGOUT_REDIRECT_URL = '/'  # OK: URL a la que redirigir después del logout (página principal del tenant - landing)

# Django REST Framework (API-First)
# WARNING: IMPORTANTE: DRF está en TENANT_APPS, por lo que cada tenant tiene sus propias APIs
# django-tenants maneja automáticamente el aislamiento por esquema
# NO es necesario filtrar manualmente por tenant_id
# 
# Referencias:
# - ViewSets & Routers: https://www.django-rest-framework.org/api-guide/viewsets/
# - Pagination: https://www.django-rest-framework.org/api-guide/pagination/
# - Filtering: https://www.django-rest-framework.org/api-guide/filtering/
# - Permissions: https://www.django-rest-framework.org/api-guide/permissions/
# - Throttling: https://www.django-rest-framework.org/api-guide/throttling/
# - Versioning: https://www.django-rest-framework.org/api-guide/versioning/
# ============================================================================
# Django File Upload Limits
# ============================================================================
# Aumentar límites para archivos XML UBL (pueden ser pesados con attachments)
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024  # 20 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024  # 20 MB

# ============================================================================
# Django REST Framework Configuration
# ============================================================================
REST_FRAMEWORK = {
    # OpenAPI Schema (drf-spectacular)
    # DRF deprecó su generador integrado; drf-spectacular es la alternativa recomendada
    # Docs: https://drf-spectacular.readthedocs.io/
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    
    # Autenticación
    # WARNING: JWT GLOBAL: APIs REST usan JWT (Authorization: Bearer) por defecto
    # OK: DEV: SessionAuthentication añadido para workspace (cookies de sesión desde mismo host)
    # Los ViewSets específicos pueden sobrescribir con authentication_classes = [SessionAuthentication]
    # DRF prioriza authentication_classes del ViewSet sobre DEFAULT_AUTHENTICATION_CLASSES
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # OK: JWT para APIs externas
        'rest_framework.authentication.SessionAuthentication',  # OK: DEV: Workspace usa cookies de sesión
        # TokenAuthentication removido - legacy, no se usa
    ],
    
    # Permisos
    # Por defecto, todas las APIs requieren autenticación
    # Se puede sobrescribir por ViewSet con permission_classes
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    
    # Filtrado, búsqueda y ordenación
    # django-filter: https://django-filter.readthedocs.io/
    # DRF Filtering: https://www.django-rest-framework.org/api-guide/filtering/
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    
    # Paginación global
    # Usa StandardResultsSetPagination (page_size=20, max_page_size=200)
    # Se puede sobrescribir por ViewSet con pagination_class
    'DEFAULT_PAGINATION_CLASS': 'apps.config.api.pagination.StandardResultsSetPagination',
    'PAGE_SIZE': 20,
    
    # Throttling (rate limiting)
    # Limita el número de requests por usuario/anónimo
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'apps.public.impuestos.api.ingesta.throttling.IngestaScopedThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '500/day',   # 500 requests por día para usuarios anónimos (catálogos públicos)
        'user': '2000/day',  # 2000 requests por día para usuarios autenticados
        'impuestos_ingesta': '20/hour',  # 20 requests por hora para ingesta
        'impuestos_search': '100/minute',  # 100 requests por minuto para búsqueda
    },
    
    # Versionado de APIs
    # NamespaceVersioning permite versionar por namespace en URLs (/api/v1/, /api/v2/)
    # Docs: https://www.django-rest-framework.org/api-guide/versioning/#namespaceversioning
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.NamespaceVersioning',
    
    # Formato de respuesta
    # Solo JSON: APIs solo devuelven JSON (sin BrowsableAPIRenderer)
    # UI dedicada: Toda presentación HTML pasa por templates en /console/...
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        # NO incluir BrowsableAPIRenderer: APIs solo JSON, UI en templates dedicados
    ],
    
    # Parsers (formato de entrada)
    # MultiPartParser: para subida de archivos en /ingesta (multipart/form-data)
    # FormParser: para formularios POST (application/x-www-form-urlencoded)
    # JSONParser: para JSON en /ingesta y otras APIs (application/json)
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',  # Para form-urlencoded
        'rest_framework.parsers.MultiPartParser',  # Para /ingesta multipart
    ],
    
    # Manejo de excepciones
    # Se puede personalizar con apps.config.api.exceptions.custom_exception_handler
    'EXCEPTION_HANDLER': 'apps.config.api.exceptions.exception_handler',
    
    # Formato de fecha/hora
    'DATETIME_FORMAT': '%Y-%m-%dT%H:%M:%S',
    'DATE_FORMAT': '%Y-%m-%d',
    'TIME_FORMAT': '%H:%M:%S',
}

# ============================================================================
# django-rest-framework-mcp: Configuracion del servidor MCP HTTP
# ============================================================================
# Expone los ViewSets decorados con @mcp_viewset() como herramientas MCP en /mcp/
# Docs: https://github.com/zacharypodbela/django-rest-framework-mcp
# El endpoint /mcp/ es compatible con mcp-remote para STDIO transport
DJANGORESTFRAMEWORK_MCP = {
    # RETURN_200_FOR_ERRORS: requerido para compatibilidad con mcp-remote
    # mcp-remote no maneja correctamente HTTP 401/403 (asume OAuth en 401)
    # Con True, retorna HTTP 200 pero preserva el error en el body JSON-RPC
    'RETURN_200_FOR_ERRORS': True,
    # Preservar autenticacion JWT/Session de cada ViewSet (BaseTenantViewSet)
    # El agente debe enviar: Authorization: Bearer <jwt_token>
    'BYPASS_VIEWSET_AUTHENTICATION': False,
    'BYPASS_VIEWSET_PERMISSIONS': False,
}

# drf-spectacular (OpenAPI Schema)
# Docs: https://drf-spectacular.readthedocs.io/
SPECTACULAR_SETTINGS = {
    'TITLE': 'SINTEL API',
    'DESCRIPTION': 'API REST para sistema multi-tenant de gestión contable y facturación electrónica',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SCHEMA_PATH_PREFIX': '/api/v1/',
}

# JWT Configuration (djangorestframework-simplejwt)
# Docs: https://django-rest-framework-simplejwt.readthedocs.io/
# WARNING: v2.30: Hardening de seguridad JWT
import base64
import secrets
from datetime import timedelta

# WARNING: v2.30: Configuración de SIGNING_KEY fuerte (32+ bytes)
# Opción 1: Usar JWT_SECRET_KEY desde variable de entorno (recomendado para producción)
# Opción 2: Generar una clave fuerte automáticamente si no está configurada (solo DEV)
# Opción 3: Migrar a RS256 (requiere generar par de llaves PRIVATE_KEY/PUBLIC_KEY)
JWT_SECRET_KEY_ENV = os.getenv('JWT_SECRET_KEY', None)

# Para RS256 (recomendado para producción), descomentar y configurar:
# JWT_PRIVATE_KEY_ENV = os.getenv('JWT_PRIVATE_KEY', None)
# JWT_PUBLIC_KEY_ENV = os.getenv('JWT_PUBLIC_KEY', None)

# Por ahora, usar HS256 con clave fuerte (32 bytes mínimo)
if JWT_SECRET_KEY_ENV:
    # Validar que la clave tenga al menos 32 bytes (256 bits)
    try:
        # Si viene en base64, decodificar para verificar longitud
        decoded_key = base64.b64decode(JWT_SECRET_KEY_ENV) if len(JWT_SECRET_KEY_ENV) > 44 else JWT_SECRET_KEY_ENV.encode()
        if len(decoded_key) < 32:
            import warnings
            warnings.warn(
                f"WARNING: JWT_SECRET_KEY tiene solo {len(decoded_key)} bytes. "
                f"Se requieren >= 32 bytes (256 bits) para HS256. "
                f"Genera uno con: python -c 'import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())'",
                UserWarning
            )
        jwt_signing_key = JWT_SECRET_KEY_ENV
    except Exception:
        # Si no es base64, usar directamente (debe ser string de al menos 32 caracteres)
        if len(JWT_SECRET_KEY_ENV) < 32:
            import warnings
            warnings.warn(
                f"WARNING: JWT_SECRET_KEY tiene solo {len(JWT_SECRET_KEY_ENV)} caracteres. "
                f"Se requieren >= 32 caracteres para HS256.",
                UserWarning
            )
        jwt_signing_key = JWT_SECRET_KEY_ENV
else:
    # Fallback: usar SECRET_KEY si JWT_SECRET_KEY no esta configurada
    jwt_signing_key = SECRET_KEY

SIMPLE_JWT = {
    # Duración de los tokens
    # WARNING: RECOMENDADO: Access tokens cortos (10-20 min), refresh tokens medios (7-30 días)
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),   # Token de acceso: 15 minutos (corto para seguridad)
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),       # Token de refresh: 7 días (medio)
    
    # Rotación de refresh tokens
    'ROTATE_REFRESH_TOKENS': True,                     # Generar nuevo refresh token en cada refresh
    'BLACKLIST_AFTER_ROTATION': True,                  # Invalidar refresh token anterior (requiere django-rest-framework-simplejwt[blacklist])
    
    # Algoritmo de firma
    # WARNING: v2.30: HS256 con clave fuerte (32+ bytes) o migrar a RS256 para producción
    'ALGORITHM': 'HS256',                              # Algoritmo de firma (HS256 es el estándar)
    'SIGNING_KEY': jwt_signing_key,                    # Clave secreta fuerte (32+ bytes)
    
    # Headers y claims
    'AUTH_HEADER_TYPES': ('Bearer',),                  # Tipo de header: Authorization: Bearer <token>
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',           # Nombre del header HTTP
    'USER_ID_FIELD': 'id',                             # Campo del modelo User para el claim 'user_id'
    'USER_ID_CLAIM': 'user_id',                        # Claim JWT que contiene el user_id
    
    # Configuración de tokens
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    
    # Configuración de refresh
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

# WARNING: NOTA: Para migrar a RS256 en producción, descomentar y configurar:
# SIMPLE_JWT['ALGORITHM'] = 'RS256'
# SIMPLE_JWT['SIGNING_KEY'] = JWT_PRIVATE_KEY_ENV  # Clave privada RSA
# SIMPLE_JWT['VERIFYING_KEY'] = JWT_PUBLIC_KEY_ENV  # Clave pública RSA
# Generar par de llaves con: openssl genrsa -out private_key.pem 2048 && openssl rsa -in private_key.pem -pubout -out public_key.pem

# ============================================================================
# Email / SMTP Configuration
# ============================================================================
# WARNING: IMPORTANTE: Configuración de email para envío de invitaciones y notificaciones
# Variables de entorno requeridas en .env:
# - EMAIL_BACKEND: Backend de email (default: console en desarrollo)
# - EMAIL_HOST: Servidor SMTP (ej: smtp.gmail.com)
# - EMAIL_PORT: Puerto SMTP (ej: 587 para TLS, 465 para SSL)
# - EMAIL_USE_TLS: Usar TLS (True/False)
# - EMAIL_USE_SSL: Usar SSL (True/False)
# - EMAIL_HOST_USER: Usuario SMTP
# - EMAIL_HOST_PASSWORD: Contraseña SMTP (o App Password para Gmail)
# - DEFAULT_FROM_EMAIL: Email remitente por defecto
# - CONTACT_EMAIL: Email de contacto (opcional)
# - EMAIL_TIMEOUT: Timeout en segundos (opcional, default: 20)

# Backend de email
# En desarrollo: usar console backend para ver emails en consola
# En producción: usar SMTP backend
EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend'
)

# Configuración SMTP (solo se usa si EMAIL_BACKEND es smtp)
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False') == 'True'

# Credenciales SMTP
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

# Email remitente por defecto
# WARNING: IMPORTANTE: Si DEFAULT_FROM_EMAIL en .env es ${EMAIL_HOST_USER} o EMAIL_HOST_USER, usar el valor real
_default_from_email_env = os.getenv('DEFAULT_FROM_EMAIL', '')
if _default_from_email_env and _default_from_email_env not in ('${EMAIL_HOST_USER}', 'EMAIL_HOST_USER'):
    DEFAULT_FROM_EMAIL = _default_from_email_env
else:
    # Usar EMAIL_HOST_USER si está disponible, sino usar un valor por defecto
    DEFAULT_FROM_EMAIL = EMAIL_HOST_USER if EMAIL_HOST_USER else 'no-reply@sintel.local'

# Email de contacto (opcional)
CONTACT_EMAIL = os.getenv('CONTACT_EMAIL', DEFAULT_FROM_EMAIL)

# Email del servidor (para errores del sistema)
# Si no se especifica, usar DEFAULT_FROM_EMAIL
SERVER_EMAIL = os.getenv('SERVER_EMAIL', DEFAULT_FROM_EMAIL)

# Timeout para conexiones SMTP (segundos)
EMAIL_TIMEOUT = int(os.getenv('EMAIL_TIMEOUT', '20'))

# Redis/Celery (configuración básica)
REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')

# Celery Configuration
# WARNING: IMPORTANTE: La cola puede ser compartida, pero el worker debe cambiar
# connection.schema_name usando schema_context en las tareas
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutos
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutos

# WARNING: ROBUSTEZ: Forzar import de módulos de tareas críticos
# Evita que ImportError durante autodiscovery queden silenciados
# Celery puede ignorar ciertos errores de import durante autodiscovery
# Esta configuración fuerza la importación explícita para detectar errores temprano
CELERY_IMPORTS = (
    "apps.public.tenants.tasks",  # Tarea crítica de onboarding
    "apps.services.maildigester.tasks",  # Tarea de ingesta de facturas desde correo
)

# WARNING: CONFIGURACIÓN CRÍTICA: Colas Prioritarias
# Define cola por defecto
CELERY_TASK_DEFAULT_QUEUE = 'default'

# Rutas explícitas de tareas a colas
# IMPORTANTE: El orden importa. Las tareas críticas van a high_priority
CELERY_TASK_ROUTES = {
    # Onboarding de tenants: cola de alta prioridad
    'apps.public.tenants.tasks.onboard_tenant_task':              {'queue': 'high_priority'},
    'apps.public.tenants.tasks.send_activation_email_task':       {'queue': 'high_priority'},
    'apps.public.tenants.tasks.provision_tenant_certificates_task': {'queue': 'high_priority'},

    # Ingesta de facturas desde correo: cola de alta prioridad (critica)
    'apps.services.maildigester.tasks.fetch_and_process_billing_mail': {'queue': 'high_priority'},

    # Todas las demas tareas van a default
    '*': {'queue': 'default'},
}

# Integraciones Externas
# DIAN
DIAN_API_KEY = os.getenv('DIAN_API_KEY', '')
DIAN_API_URL_TEST = os.getenv('DIAN_API_URL_TEST', 'https://api-test.dian.gov.co')
DIAN_API_URL_PRODUCTION = os.getenv('DIAN_API_URL_PRODUCTION', 'https://api.dian.gov.co')
DIAN_AMBIENTE = os.getenv('DIAN_AMBIENTE', 'pruebas')  # 'pruebas' o 'produccion'

# Auditoría y Logging
AUDIT_LOG_DIR = os.getenv('AUDIT_LOG_DIR', 'logs/audit')
AUDIT_LOG_MAX_BYTES = int(os.getenv('AUDIT_LOG_MAX_BYTES', 10 * 1024 * 1024))  # 10MB
AUDIT_LOG_BACKUP_COUNT = int(os.getenv('AUDIT_LOG_BACKUP_COUNT', 5))
AUDIT_LOG_LEVEL = os.getenv('AUDIT_LOG_LEVEL', 'INFO')  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# ============================================================================
# Configuración de Activación de Owners (v2.30)
# ============================================================================
# WARNING: SEGURIDAD: Permite resetear contraseña a unusable para reenvío de tokens
# Solo habilitar en entornos de desarrollo o con flag explícito
ALLOW_RESET_ACTIVATION = os.getenv('ALLOW_RESET_ACTIVATION', 'False') == 'True'

# WARNING: v2.30: Feature flag para migración API-first del dashboard
# Cuando DASHBOARD_API_FIRST=True, las vistas legacy se desactivan y solo funcionan los endpoints API
DASHBOARD_API_FIRST = os.getenv('DASHBOARD_API_FIRST', 'True') == 'True'

# TTL por defecto para tokens de activación (en minutos)
OWNER_ACTIVATION_TOKEN_TTL_MINUTES = int(os.getenv('OWNER_ACTIVATION_TOKEN_TTL_MINUTES', '120'))  # 2 horas por defecto

# Backups
BACKUP_DIR = os.getenv('BACKUP_DIR', 'backups')
BACKUP_RETENTION_DAYS = int(os.getenv('BACKUP_RETENTION_DAYS', 30))  # Días de retención de backups

# ============================================================================
# Feature Flags - Pipeline Universal de Documentos (v2.40)
# ============================================================================
# WARNING: v2.40: Document Ingest Pipeline Universal
# - FEATURE_DOCUMENT_PIPELINE=True: Activa el pipeline universal de documentos
#   (document_ingest + document_parser) para ingesta de XML, PDF, XLS/XLSX, CSV, TXT
# - FEATURE_DOCUMENT_PIPELINE=False: Desactiva el pipeline universal (comportamiento legacy)
# - Requerido para: POST /api/v1/facturas/upload-ubl/ y endpoints de ingesta de documentos
# - Rollout: Activar en staging primero, luego producción
FEATURE_DOCUMENT_PIPELINE = os.getenv("FEATURE_DOCUMENT_PIPELINE", "true").lower() == "true"

# WARNING: v2.36: Feature flag adicional para endpoint universal de documentos
# - FEATURE_UPLOAD_DOCUMENT_ENDPOINT=True: Activa endpoint universal /api/v1/core/documentos/upload/
# - FEATURE_UPLOAD_DOCUMENT_ENDPOINT=False: Mantiene solo endpoints específicos por app
FEATURE_UPLOAD_DOCUMENT_ENDPOINT = os.getenv("FEATURE_UPLOAD_DOCUMENT_ENDPOINT", "false").lower() == "true"

# ============================================================================
# Logging Configuration
# ============================================================================
# WARNING: IMPORTANTE: Configuración de logging para diagnóstico de emails e invitaciones
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
        "brief": {
            "format": "[{levelname}] {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "brief",  # Formato breve para logs forenses
            "level": "INFO",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        # Logger del servicio de invitaciones
        "apps.public.tenants.services.invitations": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        # Logger del servicio de onboarding
        "apps.services.onboarding.empresa_service": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        # Logger de Django mail (para ver intentos de envío SMTP)
        "django.core.mail": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        # Logger de Django en general (reducir ruido)
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        # Reducir ruido de DB backends
        "django.db.backends": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        # Reducir ruido de requests
        "django.request": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        # WARNING: WeasyPrint eliminado - Configuración de logs removida
        # Server logs a INFO (menos ruido que DEBUG)
        "django.server": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        # FORÉNSICA: Logger específico para upload de facturas
        "facturas.upload": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

