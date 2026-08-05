"""
URLs de APIs REST publicas (solo en esquema public).

Arquitectura API-First:
- Cada app publica tiene su carpeta api/ con serializers, viewsets, urls
- Los routers se registran desde cada app
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

public_router = DefaultRouter()

from apps.public.tenants.api.urls import urlpatterns as tenants_urls
from apps.public.accounts.api.public_urls import urlpatterns as accounts_urls

urlpatterns = [
    path('', include(tenants_urls)),
    path('', include(accounts_urls)),
    path('', include(public_router.urls)),
]

# Impuestos (opcional — puede no estar disponible durante migraciones)
try:
    from apps.public.impuestos.api.ingesta.urls import urlpatterns as ingesta_urls
    from apps.public.impuestos.api.urls import urlpatterns as impuestos_urls
    urlpatterns += [
        path('impuestos/', include(ingesta_urls)),
        path('', include(impuestos_urls)),
    ]
except ImportError:
    pass

# Ruta explicita para registro publico de usuarios
from apps.public.accounts.api.public_viewsets import PublicUserViewSet
urlpatterns += [
    path('users/', PublicUserViewSet.as_view({'post': 'create'}), name='public-user-create'),
]

# Activacion y reenvio de codigo (publico, sin auth) — accesible desde home.sintel.net.co
# Mismo handler que en urls_tenant, adaptado para schema publico via deteccion interna.
try:
    from apps.tenant.core.api.viewsets import CoreAuthViewSet as _CoreAuthViewSet
    urlpatterns += [
        path(
            'auth/activate-with-code/',
            _CoreAuthViewSet.as_view({'post': 'activate_with_code'}),
            name='public-activate-with-code',
        ),
        path(
            'auth/resend-activation-code/',
            _CoreAuthViewSet.as_view({'post': 'resend_activation_code'}),
            name='public-resend-activation-code',
        ),
    ]
except Exception:
    pass

# WARNING: [ARQ-A3] Login y password-reset (publico, sin auth) — login.html,
# reset-request.html y reset-confirm.html son paginas estaticas accesibles desde
# home.sintel.net.co (mismo problema que activate.html en ADR-002). Mismo handler
# que en urls_tenant; cada action detecta internamente si esta en schema publico
# (ver apps/tenant/core/api/viewsets.py: login, password_reset_request,
# password_reset_confirm).
try:
    from apps.tenant.core.api.viewsets import CoreAuthViewSet as _CoreAuthViewSetAuth
    urlpatterns += [
        path(
            'auth/login/',
            _CoreAuthViewSetAuth.as_view({'post': 'login'}),
            name='public-login',
        ),
        path(
            'auth/password-reset/request/',
            _CoreAuthViewSetAuth.as_view({'post': 'password_reset_request'}),
            name='public-password-reset-request',
        ),
        path(
            'auth/password-reset/confirm/',
            _CoreAuthViewSetAuth.as_view({'post': 'password_reset_confirm'}),
            name='public-password-reset-confirm',
        ),
    ]
except Exception:
    pass
