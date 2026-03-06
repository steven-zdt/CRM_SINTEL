"""
URLs de APIs REST públicas (solo en esquema public).

⚠️ IMPORTANTE: 
- Estas URLs están disponibles SOLO cuando se accede al esquema 'public'
- Requieren permisos de administrador para la mayoría de las operaciones

Arquitectura API-First:
- Cada app pública tiene su carpeta api/ con serializers, viewsets, urls
- Los routers se registran automáticamente desde cada app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Router principal para APIs REST públicas (por ahora no registra nada directamente)
public_router = DefaultRouter()

# Rutas base: tenants y accounts SON OBLIGATORIAS en cualquier entorno
from apps.public.tenants.api.urls import urlpatterns as tenants_urls
from apps.public.accounts.api.urls import urlpatterns as accounts_urls

urlpatterns = [
    # Tenants (CRUD completo para staff, exclusivo para administradores)
    path('', include(tenants_urls)),
    # Usuarios globales (Accounts)
    path('', include(accounts_urls)),
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
]
