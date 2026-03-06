"""
URL configuration for sintel_project project.

⚠️ IMPORTANTE: django-tenants maneja automáticamente el aislamiento por esquema.
El TenantMainMiddleware establece el esquema antes de procesar cualquier request.

Arquitectura API-First:
- APIs por tenant: /api/v1/ (disponibles cuando se accede a un tenant)
- APIs públicas: /api/public/v1/ (solo en esquema public)
- OpenAPI Schema: /api/schema/ (drf-spectacular)
- Swagger UI: /api/docs/ (documentación interactiva)
- ReDoc: /api/redoc/ (documentación alternativa)
"""
from django.contrib import admin
from django.contrib.auth import logout as auth_logout
from django.urls import path, include, reverse
from django.http import JsonResponse
from django.shortcuts import redirect
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from apps.public.core.api.views import LoggedTokenVerifyView
from config.well_known import chrome_devtools


def root_view(request):
    """
    Vista raíz del proyecto.

    En este proyecto, todo el tráfico que entra por la raíz (http://localhost:8000/)
    se redirige a la consola del tenant público.

    Esto mantiene la arquitectura API-First (las APIs siguen en /api/*),
    pero hace que la experiencia de usuario sea:
      - http://localhost:8000/           -> /console/ (dashboard público)
      - http://sintel.com:8000/         -> /console/ del tenant sintel.com (si está configurado)
    """
    # Redirige siempre a la consola del esquema actual.
    # En el esquema public será el dashboard global; en un esquema tenant_*
    # será el dashboard de ese tenant (misma ruta /console/ pero con otro schema).
    return redirect(reverse("console:dashboard"))


def admin_logout_view(request):
    """
    Logout seguro accesible por GET para el admin.

    El logout por defecto de Django admin requiere POST (para protección CSRF),
    lo que provoca un 405 si se accede directamente por GET a /admin/logout/.

    En este proyecto, preferimos una UX sencilla:
      - /admin/logout/ (GET) cierra la sesión y redirige a /admin/login/
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


urlpatterns = [
    # Health check (para Docker/Kubernetes)
    path('health', health_view, name='health'),
    
    # Ruta raíz
    path('', root_view, name='root'),

    # Override de logout de admin para permitir GET en /admin/logout/
    # (debe ir ANTES de path('admin/', ...))
    path('admin/logout/', admin_logout_view, name='admin-logout-safe'),
    
    # .well-known routes (deben ir antes de otras rutas)
    path('.well-known/appspecific/com.chrome.devtools.json', chrome_devtools, name='chrome-devtools'),
    
    # Login: redirigir al admin login
    path('login/', lambda request: redirect('admin:login'), name='login'),
    path('logout/', lambda request: redirect('admin:logout'), name='logout'),
    
    path('admin/', admin.site.urls),
    
    # Autenticación JWT (disponible en todos los esquemas)
    # Endpoints: /api/token/ (login), /api/token/refresh/ (refresh), /api/token/verify/ (verify)
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', LoggedTokenVerifyView.as_view(), name='token_verify'),
    
    # APIs REST (por tenant)
    # Las rutas de API se registran automáticamente desde cada app/api/urls.py
    path('api/v1/', include(('config.api_urls', 'api'), namespace='v1')),
    
    # APIs REST públicas (solo en esquema public)
    path('api/public/v1/', include('config.public_api_urls')),
    # Consola de administración pública (solo en esquema public, requiere staff)
    path('console/', include('apps.public.console.urls')),
    path('console/impuestos/', include('apps.public.impuestos.dashboard.urls_dashboard')),
    
    # OpenAPI Schema y Documentación (drf-spectacular)
    # Docs: https://drf-spectacular.readthedocs.io/
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
