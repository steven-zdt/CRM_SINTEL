"""
URL configuration for sintel_project - Tenants Privados.

WARNING: IMPORTANTE: Este archivo se usa cuando se accede a un tenant privado (ej: cliente.sintel.com).
django-tenants usa este archivo como TENANT_URLCONF para todos los tenants.

ESTE ARCHIVO SOLO CARGA EN DOMINIOS PRIVADOS (TENANTS)

WARNING: ARQUITECTURA API-FIRST (v2.30):
- TODA la lógica de negocio está en apps/tenant/landing/api/
- WARNING: Vistas HTML eliminadas - toda la funcionalidad se maneja mediante APIs REST
- El frontend DEBE consumir las APIs REST para landing, login y activación

Rutas privadas disponibles:
- WARNING: v2.30: Vistas HTML Django eliminadas (/, /login/ ya no existen)
- cliente.sintel.com/activate/?token=... -> Shell estático de activación (HTML/JS que consume la API)
- cliente.sintel.com/dashboard/ -> DashboardIndexView (dashboard con control de roles)
- cliente.sintel.com/api/v1/ -> APIs REST del tenant (facturas, contabilidad, empresa)
- cliente.sintel.com/api/v1/landing/ -> APIs REST de landing/login/activación (API-First)

WARNING: REGLA DE NEGOCIO (v2.30): 
- WARNING: Vistas HTML eliminadas - toda la funcionalidad está en /api/v1/landing/
- El frontend debe consumir las APIs REST para landing, login y activación

WARNING: SEGURIDAD: 
- /admin/ NO está disponible en tenants privados (bloqueado por middleware guard-rail)
- El Admin de Django solo está disponible en el esquema público (ROOT_URLCONF)
- Manejadores de error personalizados (404, 403) para mantener la identidad visual
"""
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.urls import include, path
from django.views.generic import RedirectView, View
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from apps.public.core.api.views import LoggedTokenVerifyView
from apps.tenant.core.api.handlers import custom_page_not_found_view, custom_permission_denied_view

# WARNING: v2.60: Importar ui_urlpatterns de cotizaciones para incluir en urlpatterns
try:
    from apps.tenant.cotizaciones.api.urls import ui_urlpatterns as cotizaciones_ui_urlpatterns
except ImportError:
    # Fallback si ui_urlpatterns no está disponible
    cotizaciones_ui_urlpatterns = []

# Importar ui_urlpatterns de perfil de manera defensiva (puede no existir en algunas instalaciones)
try:
    from apps.tenant.perfil.urls_ui import urlpatterns as perfil_ui_urlpatterns
except ImportError:
    perfil_ui_urlpatterns = []


class TenantRootView(View):
    """
    Vista raíz del tenant (v2.30 - API-First).
    
    WARNING: PÁGINA PRINCIPAL DEL TENANT: "/" SIEMPRE redirige a /static/tenant/landing/index.html
    
    Esta es la página principal para TODOS los tenants (cliente.sintel.com, etc.).
    La página muestra información del tenant y un botón de login.
    
    Redirige según el estado de autenticación:
    - Usuario autenticado → /static/tenant/core/dashboard/index.html (shell estático del dashboard)
    - Usuario anónimo → /static/tenant/landing/index.html (shell estático de landing con botón de login e info del servicio)
    - WARNING: v2.30+: Archivos estáticos de landing ubicados en: apps/tenant/landing/static/tenant/landing/
    
    El shell estático de landing consume /api/v1/landing/info/ para obtener información del tenant.
    """
    def get(self, request):
        # [v2.61] Segmentación Estricta: No servir landing genérica en dominios privados
        # Si el usuario no está autenticado, forzar redirección al shell de login de core
        static_url = settings.STATIC_URL.rstrip('/')
        
        if request.user.is_authenticated:
            # Redirigir al shell estático del dashboard (API-First)
            return redirect(f"{static_url}/tenant/core/dashboard/index.html")
        else:
            # WARNING: SEGURIDAD: Nunca mostrar UI pública en dominios privados
            # Redirigir al shell de login centralizado en Core
            return redirect(f"{static_url}/tenant/core/auth/login.html")


def redirect_to_static_shell(request, filename, subdirectory='landing'):
    """
    Redirige a un archivo estático en STATIC_URL, preservando query parameters.
    
    WARNING: v2.30: Shells estáticos que consumen la API.
    WARNING: REGLA: Los archivos estáticos deben estar en la app de origen: apps/tenant/{app}/static/tenant/{subdirectory}/
    Después de collectstatic, Django los sirve desde STATIC_URL/tenant/{subdirectory}/ mediante WhiteNoise/Nginx.
    
    Args:
        request: HttpRequest
        filename: Nombre del archivo HTML (ej: 'activate.html', 'login.html', 'index.html')
        subdirectory: Subdirectorio dentro de static/tenant/ (default: 'landing')
    
    Returns:
        HttpResponseRedirect a la URL estática con query parameters preservados
    """
    static_url = settings.STATIC_URL.rstrip('/')
    base_url = f"{static_url}/tenant/{subdirectory}/{filename}"
    
    # Preservar query parameters (ej: ?token=... en /activate/)
    query_string = request.META.get('QUERY_STRING', '')
    if query_string:
        redirect_url = f"{base_url}?{query_string}"
    else:
        redirect_url = base_url
    
    return redirect(redirect_url)


# TENANT_URLCONF: servir la landing del tenant (pública) y el login/dash propios
# Cualquier acceso a /admin/ en tenants será bloqueado por un guard-rail a nivel middleware.
# (El Admin solo estará disponible en el URLConf público).
urlpatterns = [
    
    # WARNING: v2.30: Ruta raíz que redirige según autenticación
    path('', TenantRootView.as_view(), name='tenant_root'),

    # WARNING: POLÍTICA: Auth centralizado en Core - todos los shells están en tenant Core
    # Estos shells consumen las APIs REST de /api/v1/core/auth/* (centralizado)
    # WARNING: CRÍTICO: Usar redirect_to_static_shell para preservar query parameters (?token=...)
    path('activate/', lambda request: redirect_to_static_shell(request, 'activate.html', subdirectory='core/auth'), name='tenant_activate_shell'),
    path('login/', RedirectView.as_view(url='/static/tenant/core/auth/login.html', permanent=False), name='tenant_login_shell'),
    path('reset-password/', RedirectView.as_view(url='/static/tenant/core/auth/reset-request.html', permanent=False), name='tenant_reset_request_shell'),
    path('reset-password/confirm/', RedirectView.as_view(url='/static/tenant/core/auth/reset-confirm.html', permanent=False), name='tenant_reset_confirm_shell'),
    path('reset/', RedirectView.as_view(url='/static/tenant/core/auth/reset-confirm.html', permanent=False), name='tenant-reset-shell'),
    path('favicon.ico', RedirectView.as_view(url='/static/tenant/core/favicon.ico', permanent=False), name='tenant-favicon'),
    
    # WARNING: v2.30+: Short routes (UI only via Core static shells)
    # WARNING: REGLA: Solo apps/public/core expone páginas de usuario para landing
    # WARNING: REGLA: Solo apps/tenant/core expone páginas de usuario para otras apps
    # Todas las apps no-core solo exponen APIs JSON bajo /api/v1/<app>/
    # Landing shell: apps/public/core/static/public/core/landing/index.html
    # Otras shells: apps/tenant/core/static/tenant/core/<app>/index.html
    path('dashboard/', RedirectView.as_view(url='/static/tenant/core/dashboard/index.html', permanent=False), name='tenant-dashboard-shell'),
    path('empresa/', RedirectView.as_view(url='/static/tenant/core/empresa/index.html', permanent=False), name='tenant-empresa-shell'),
    path('facturas/', RedirectView.as_view(url='/static/tenant/core/facturas/index.html', permanent=False), name='tenant-facturas-shell'),
    path('contabilidad/', RedirectView.as_view(url='/static/tenant/core/contabilidad/index.html', permanent=False), name='tenant-contabilidad-shell'),
    path('landing/', RedirectView.as_view(url='/workspace/#landing', permanent=False), name='tenant-landing-shell'),
    path('perfil/', RedirectView.as_view(url='/static/tenant/core/perfil/index.html', permanent=False), name='tenant-perfil-shell'),
    
    # Rutas legacy (compatibilidad, redirigen a core shells)
    path('empresas/', RedirectView.as_view(url='/static/tenant/core/empresa/index.html', permanent=False), name='tenant_empresas_shell'),

    # Dashboard Privado (Interfaz Principal)
    # WARNING: v2.30: API-First estricto - Solo API, sin vistas HTML
    # Todas las vistas clásicas han sido eliminadas
    # La UI debe consumir exclusivamente los endpoints API en /api/v1/dashboard/
    # Si se necesita una ruta /dashboard/, debe ser manejada por el frontend (SPA) o shell estático
    # No se expone ninguna ruta server-side que renderice HTML

    # APIs del Tenant (Aisladas)
    # APIs de negocio generales del tenant
    path('api/v1/', include('config.api_urls')),
    # WARNING: DEPRECADO: APIs de landing (se mantienen por compatibilidad, pero se recomienda usar Core API)
    # Nuevos endpoints centralizados: /api/v1/core/auth/* (login, logout, password-reset)
    path('api/v1/landing/', include('apps.tenant.landing.api.urls', namespace='tenant_landing_api')),
    # MCP endpoint (django-rest-framework-mcp): expone ViewSets anotados como herramientas MCP
    # Accesible en: http://<tenant>/mcp/
    # Conectar desde Antigravity via mcp-remote apuntando a esta URL con Bearer token
    path('mcp/', include('djangorestframework_mcp.urls')),
    
    # UI Routes (partials HTML sin datos, API-First)
    # Workspace compositor
    path('', include('apps.tenant.core.urls_ui')),
    # Partials de cada app
    path('ui/landing/', include('apps.tenant.landing.urls_ui')),
    path('ui/dashboard/', include('apps.tenant.dashboard.urls_ui')),
    path('ui/empresa/', include('apps.tenant.empresa.urls_ui')),
    path('ui/empleados/', include('apps.tenant.empleados.urls', namespace='empleados')),
    path('ui/gastos/', include('apps.tenant.gastos.urls', namespace='gastos')),
    path('ui/facturas/', include('apps.tenant.facturas.urls', namespace='facturas')),
    path('ui/contabilidad/', include('apps.tenant.contabilidad.urls', namespace='contabilidad')),
    path('ui/inventario/', include('apps.tenant.inventario.urls', namespace='inventario')),
    path('ui/proveedores/', include('apps.tenant.proveedores.urls', namespace='proveedores')),
    path('ui/proyectos/', include('apps.tenant.proyectos.urls', namespace='proyectos')),
    path('ui/clientes/', include('apps.tenant.clientes.urls', namespace='clientes')),
    path('ui/bancos/', include('apps.tenant.bancos.urls', namespace='bancos')),
    # WARNING: v2.30: Facturas migrado a API-First - UI deprecada
    # path('ui/facturas/', include('apps.tenant.facturas.urls_ui')),
    # WARNING: v2.61: Contabilidad migrado a API-First - URLs migradas a api/urls.py
    # path('ui/contabilidad/', include('apps.tenant.contabilidad.urls_ui')),
    # Perfil UI (incluir solo si existen patrones)
    path('ui/perfil/', include((perfil_ui_urlpatterns, 'perfil'), namespace='perfil_ui')),
    # WARNING: v2.60: Cotizaciones - URLs UI desde api/urls.py (única fuente de verdad)
    # Las rutas UI están en apps/tenant/cotizaciones/api/urls.py (ui_urlpatterns)
    path('cotizaciones/', include((cotizaciones_ui_urlpatterns, 'cotizaciones'), namespace='cotizaciones_ui')),

    # Autenticación JWT (disponible también en tenants)
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', LoggedTokenVerifyView.as_view(), name='token_verify'),
    # --- Core API REST: expone /api/v1/core/landing/info/ y otros endpoints core ---
    path('api/v1/core/', include('apps.tenant.core.api.urls')),
]

# WARNING: SEGURIDAD: Manejadores de error personalizados
# Estos handlers se activan solo en TENANT_URLCONF para mantener
# la identidad visual del tenant incluso en errores.
handler404 = custom_page_not_found_view
handler403 = custom_permission_denied_view

# WARNING: DESARROLLO: Servir archivos media (solo en DEBUG=True)
# En producción, estos archivos deben servirse desde Nginx o el servidor web
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
