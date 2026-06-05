"""
URLs para la API de perfil.

Endpoints disponibles:
- GET /api/v1/perfil/me/ - Obtener perfil del usuario actual
- PATCH /api/v1/perfil/me/ - Actualizar perfil del usuario actual
- PATCH /api/v1/perfil/me/configuracion/ - Actualizar configuración de UI
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.tenant.perfil.api.viewsets import PerfilViewSet, DepartamentoViewSet

router = DefaultRouter()
router.register(r'perfiles', PerfilViewSet, basename='perfil')
router.register(r'departamentos', DepartamentoViewSet, basename='departamento')

urlpatterns = [
    path('', include(router.urls)),
]
