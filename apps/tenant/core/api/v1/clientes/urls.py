"""Core API v1 - Clientes URLs facade.

# WARNING: POLÍTICA:
- Este módulo expone los endpoints de clientes a través de Core API v1
- Ruta base: /api/v1/core/v1/clientes/
- # WARNING: v2.61: Alineado con patrón de cotizaciones y contabilidad
"""

from rest_framework.routers import DefaultRouter

from .viewsets import (
    ClienteCoreViewSet,
    ContactoClienteCoreViewSet,
)

# Router para clientes en Core API
router = DefaultRouter(trailing_slash=True)

# Registrar ViewSets
router.register(r'clientes', ClienteCoreViewSet, basename='core-cliente')
router.register(r'contactos', ContactoClienteCoreViewSet, basename='core-contacto-cliente')

urlpatterns = router.urls
