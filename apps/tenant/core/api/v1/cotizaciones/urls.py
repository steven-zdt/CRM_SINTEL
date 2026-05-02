"""Core API v1 - Cotizaciones URLs facade.

# WARNING: POLÍTICA:
- Este módulo expone los endpoints de cotizaciones a través de Core API v1
- Ruta base: /api/v1/core/v1/cotizaciones/
- # WARNING: v2.61: Alineado con patrón de contabilidad
"""

from rest_framework.routers import DefaultRouter

from .viewsets import (
    ConfiguracionCotizacionCoreViewSet,
    CotizacionCoreViewSet,
    CotizacionItemCoreViewSet,
)

# Router para cotizaciones en Core API
router = DefaultRouter(trailing_slash=True)

# Registrar ViewSets
router.register(r'cotizaciones', CotizacionCoreViewSet, basename='core-cotizacion')
router.register(r'items', CotizacionItemCoreViewSet, basename='core-cotizacion-item')
router.register(r'configuracion', ConfiguracionCotizacionCoreViewSet, basename='core-cotizacion-configuracion')

urlpatterns = router.urls
