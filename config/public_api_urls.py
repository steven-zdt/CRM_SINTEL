"""
URLs de APIs REST públicas (solo en esquema public).

WARNING: IMPORTANTE: 
- Estas URLs están disponibles SOLO cuando se accede al esquema 'public'
- Requieren permisos de administrador para la mayoría de las operaciones

Arquitectura API-First:
- Cada app pública tiene su carpeta api/ con serializers, viewsets, urls
- Los routers se registran automáticamente desde cada app
"""
import logging

from django.urls import include, path
from rest_framework.routers import DefaultRouter

logger = logging.getLogger(__name__)
from django.utils.module_loading import import_string

# Ensure PublicUserViewSet is always available under /users/ even if dynamic imports fail
try:
    PublicUserViewSet = import_string('apps.public.accounts.api.public_viewsets.PublicUserViewSet')
    _router_users = DefaultRouter()
    _router_users.register(r'users', PublicUserViewSet, basename='user')
    _users_urlpatterns = _router_users.urls
    logger.info('config.public_api_urls: Registered PublicUserViewSet fallback router with users endpoints')
except Exception:
    _users_urlpatterns = []

# Router principal para APIs REST públicas (por ahora no registra nada directamente)
public_router = DefaultRouter()

# Rutas base: tenants y accounts SON OBLIGATORIAS en cualquier entorno
from apps.public.tenants.api.urls import urlpatterns as tenants_urls

# Prefer the public-facing accounts URLs (registration, me, public user endpoints).
# Fall back to the generic accounts router if public-specific urls are not present.
accounts_module = None
try:
    # Prefer module string include to avoid import-time side-effects during test DB setup
    import importlib
    importlib.import_module('apps.public.accounts.api.public_urls')
    accounts_module = 'apps.public.accounts.api.public_urls'
except Exception:
    accounts_module = 'apps.public.accounts.api.urls'

logger.info("config.public_api_urls: including accounts urls module %s", accounts_module)
try:
    mod = __import__(accounts_module, fromlist=['urlpatterns'])
    ups = getattr(mod, 'urlpatterns', None)
    if ups is not None:
        logger.info("config.public_api_urls: accounts urlpatterns count=%s", len(ups))
        for p in ups:
            try:
                logger.debug("accounts url pattern: %s", p.pattern)
            except Exception:
                logger.debug("accounts url pattern: %s", repr(p))
    else:
        logger.info('config.public_api_urls: accounts module has no urlpatterns')
except Exception as e:
    logger.exception('config.public_api_urls: failed to inspect accounts module %s -> %s', accounts_module, e)

urlpatterns = [
    # Tenants (CRUD completo para staff, exclusivo para administradores)
    path('', include(tenants_urls)),
    # Usuarios globales (Accounts)
    path('', include(accounts_module)),
]

# Rutas opcionales de impuestos (pueden no estar disponibles en algunos contextos como migraciones)
try:
    # API de Ingesta (impuestos) - privada, requiere autenticación
    from apps.public.impuestos.api.ingesta.urls import urlpatterns as ingesta_urls

    # API de Catálogos y Búsqueda (impuestos) - pública, AllowAny
    from apps.public.impuestos.api.urls import urlpatterns as impuestos_urls

    urlpatterns += [
        path('impuestos/', include(ingesta_urls)),  # Ingesta (privada)
        path('', include(impuestos_urls)),  # Catálogos y búsqueda (pública)
    ]
except ImportError:
    # Si las APIs de impuestos no están disponibles, las omitimos sin afectar a tenants/accounts
    pass

# Incluir también el router principal para API Root (actualmente vacío, reservado para futuras extensiones)
urlpatterns += [
    path('', include(public_router.urls)),
    # Fallback explicit users routes to guarantee availability in test environments
    path('', include((list(_users_urlpatterns), 'users'))),
]

# Add an explicit, minimal POST-only route for creating public users to
# make the endpoint deterministic in test environments where import/order
# or router includes may not expose the full router. This points directly
# to the viewset `create` action and is safe (AllowAny handled by the view).
try:
    from apps.public.accounts.api.public_viewsets import PublicUserViewSet as _PublicUserViewSet
    urlpatterns += [
        path('users/', _PublicUserViewSet.as_view({'post': 'create'}), name='public-user-create'),
    ]
    logger.info("config.public_api_urls: added explicit path 'users/' -> PublicUserViewSet.create")
except Exception:
    logger.exception("config.public_api_urls: failed to add explicit PublicUserViewSet path")
