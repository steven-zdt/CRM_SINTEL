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
