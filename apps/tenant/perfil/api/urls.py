"""
URLs para la API de perfil.

Endpoints disponibles:
- GET /api/v1/perfil/me/ - Obtener perfil del usuario actual
- PATCH /api/v1/perfil/me/ - Actualizar perfil del usuario actual
- PATCH /api/v1/perfil/me/configuracion/ - Actualizar configuración de UI
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.tenant.perfil.api.viewsets import PerfilViewSet

router = DefaultRouter()
router.register(r'perfiles', PerfilViewSet, basename='perfil')

urlpatterns = [
    path('', include(router.urls)),
]
