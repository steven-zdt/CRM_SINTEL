"""Core API v1 - Facturas URLs facade.

# WARNING: POLÍTICA:
- Este módulo expone los endpoints de facturas a través de Core API v1
- Ruta base: /api/v1/core/v1/facturas/
- # WARNING: v2.61.1: Alineado con patrón de cotizaciones y contabilidad
"""

from rest_framework.routers import DefaultRouter

from .viewsets import (
    FacturaCoreViewSet,
    ItemFacturaCoreViewSet,
    NotaCreditoCoreViewSet,
)

# Router para facturas en Core API
router = DefaultRouter(trailing_slash=True)

# Registrar ViewSets
# # WARNING: CRÍTICO: Orden de registro importa - rutas específicas ANTES de ruta vacía ""
router.register(r'notas-credito', NotaCreditoCoreViewSet, basename='core-factura-nota-credito')
router.register(r'items-factura', ItemFacturaCoreViewSet, basename='core-factura-item')
router.register(r'facturas', FacturaCoreViewSet, basename='core-factura')  # # WARNING: AL FINAL para evitar greedy matching

urlpatterns = router.urls
