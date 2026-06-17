"""
URLs de la API de Ventas (DRF Router).
Prefijo: /api/v1/ventas/
"""
import logging

from rest_framework.routers import DefaultRouter

from .viewsets import OrdenVentaViewSet

logger = logging.getLogger(__name__)

router = DefaultRouter()
router.register(r"", OrdenVentaViewSet, basename="orden-venta")

urlpatterns = router.urls

if urlpatterns:
    logger.info("[OK] OrdenVentaViewSet registrado. URLs: %s", len(urlpatterns))
