"""Core API v1 - Contabilidad URLs facade.

⚠️ POLÍTICA:
- Este módulo expone los endpoints de contabilidad a través de Core API v1
- Ruta base: /api/v1/core/v1/contabilidad/
- ⚠️ v2.61: Incluye catálogo NIIF Colombia
"""

from rest_framework.routers import DefaultRouter
from .viewsets import (
    CuentaContableCoreViewSet,
    AsientoContableCoreViewSet,
    MovimientoContableCoreViewSet,
    CatalogoMaestroNIIFCoreViewSet,
)

# Router para contabilidad en Core API
router = DefaultRouter(trailing_slash=True)

# Registrar ViewSets
router.register(r'cuentas', CuentaContableCoreViewSet, basename='core-cuenta-contable')
router.register(r'asientos', AsientoContableCoreViewSet, basename='core-asiento-contable')
router.register(r'movimientos', MovimientoContableCoreViewSet, basename='core-movimiento-contable')
router.register(r'catalogo-niif', CatalogoMaestroNIIFCoreViewSet, basename='core-catalogo-niif')

urlpatterns = router.urls
