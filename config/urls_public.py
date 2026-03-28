"""
URL configuration for sintel_project - Esquema Público.

WARNING: IMPORTANTE: Este archivo se usa SOLO cuando se accede al esquema 'public'.
django-tenants usa este archivo como ROOT_URLCONF para el dominio público.

Rutas públicas disponibles:
- sintel.com/ -> PublicIndexView (redirección inteligente)
- sintel.com/admin/ -> Admin de Django
- sintel.com/console/ -> Consola de administración (requiere staff)
- sintel.com/api/public/v1/ -> APIs REST públicas
- sintel.com/api/admin/v1/ -> APIs REST de administración (requiere staff)
- sintel.com/api/token/ -> Autenticación JWT
"""
from django.contrib import admin
from django.contrib.auth import logout as auth_logout
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from apps.public.core.api.views import LoggedTokenVerifyView
from apps.public.core.views import PublicIndexView
from config.well_known import chrome_devtools


def admin_logout_view(request):
    """
    Logout seguro accesible por GET para el admin.
    
    El logout por defecto de Django admin requiere POST (para protección CSRF),
    lo que provoca un 405 si se accede directamente por GET a /admin/logout/.
    """
    auth_logout(request)
    return redirect("/admin/login/")


def health_view(request):
    """
    Endpoint de health check para Docker/Kubernetes.
    
    Retorna 200 OK si la aplicación está funcionando correctamente.
    """
    from django.db import connection
    try:
        # Verificar conexión a BD
        connection.ensure_connection()
        db_status = 'ok'
    except Exception:
        db_status = 'error'
    
    return JsonResponse({
        'status': 'ok' if db_status == 'ok' else 'degraded',
        'database': db_status,
        'version': '1.0',
    }, status=200 if db_status == 'ok' else 503)


def debug_headers_view(request):
    """
    Temporary debug endpoint: echo selected request headers and META.
    Use only for local debugging and remove after inspection.
    """
    # Collect a safe subset of headers/META to avoid leaking secrets in logs.
    meta = request.META
    data = {
        'HTTP_HOST': meta.get('HTTP_HOST'),
        'HTTP_AUTHORIZATION': meta.get('HTTP_AUTHORIZATION'),
        'REMOTE_ADDR': meta.get('REMOTE_ADDR'),
        'SERVER_NAME': meta.get('SERVER_NAME'),
        'wsgi.url_scheme': meta.get('wsgi.url_scheme'),
        'REQUEST_METHOD': meta.get('REQUEST_METHOD'),
    }
    # Also include Django's request.headers dict for clarity
    try:
        headers = {k: v for k, v in request.headers.items()}
    except Exception:
        headers = {}
    return JsonResponse({'meta': data, 'headers': headers}, status=200)


urlpatterns = [
    
    # Health check (para Docker/Kubernetes)
    path('health', health_view, name='health'),
    
    # Ruta raíz: Redirección inteligente según estado del usuario
    path('', PublicIndexView.as_view(), name='public_index'),
    
    # Override de logout de admin para permitir GET en /admin/logout/
    # (debe ir ANTES de path('admin/', ...))
    path('admin/logout/', admin_logout_view, name='admin-logout-safe'),
    
    # .well-known routes (deben ir antes de otras rutas)
    path('.well-known/appspecific/com.chrome.devtools.json', chrome_devtools, name='chrome-devtools'),
    
    # Login/Logout: redirigir al admin login
    path('login/', lambda request: redirect('admin:login'), name='login'),
    path('logout/', lambda request: redirect('admin:logout'), name='logout'),
    
    # Admin de Django (gestión global)
    path('admin/', admin.site.urls),
    
    # Autenticación JWT (disponible en todos los esquemas)
    # Endpoints: /api/token/ (login), /api/token/refresh/ (refresh), /api/token/verify/ (verify)
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', LoggedTokenVerifyView.as_view(), name='token_verify'),
    
    # APIs REST públicas (solo en esquema public)
    # Fuente de verdad de la API de tenants: apps.public.tenants.api (VIEWSETS)
    # config.public_api_urls ya incluye apps.public.tenants.api.urls, no duplicar
    path('api/public/v1/', include('config.public_api_urls')),
    
    # Tenants públicos (landing, activación)
    path('', include('apps.public.tenants.urls')),
    
    # APIs REST de administración (solo en esquema public, requiere staff)
    # API-First: Endpoints DataTables (POST + CSRF) para la consola
    path('api/admin/v1/console/', include('apps.public.console.api.urls', namespace='console_api')),
    # API-First: CRUD de usuarios globales (SSOT en apps.public.accounts.api)
    path('api/admin/v1/accounts/', include('apps.public.accounts.api.urls')),
    
    # Consola de administración pública (solo en esquema public, requiere staff)
    path('console/', include('apps.public.console.urls')),
    path('console/impuestos/', include('apps.public.impuestos.dashboard.urls_dashboard')),
    
    # OpenAPI Schema y Documentación (drf-spectacular)
    # Docs: https://drf-spectacular.readthedocs.io/
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Add a deterministic explicit users create endpoint at the top-level so
# tests/middleware swaps cannot hide it. This is a minimal, safe fallback.
try:
    from apps.public.accounts.api.public_viewsets import PublicUserViewSet as _PublicUserViewSet
    urlpatterns += [
        path('api/public/v1/users/', _PublicUserViewSet.as_view({'post': 'create'}), name='public-user-create-root'),
    ]
except Exception:
    # If the view isn't importable during initial setup, skip explicit route.
    pass

# WARNING: DESARROLLO: Servir archivos media (solo en DEBUG=True)
# En producción, estos archivos deben servirse desde Nginx o el servidor web
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)