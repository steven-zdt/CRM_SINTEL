import logging

from rest_framework.routers import DefaultRouter

from .viewsets import ResolucionFacturacionViewSet, VentaViewSet

logger = logging.getLogger(__name__)

router = DefaultRouter()
router.register(r"resoluciones", ResolucionFacturacionViewSet, basename="resolucion-facturacion")
router.register(r"", VentaViewSet, basename="venta")

urlpatterns = router.urls

if urlpatterns:
    logger.info("[OK] Ventas URLs registradas: %s", len(urlpatterns))
