import logging
from django.conf import settings
from rest_framework.routers import DefaultRouter

logger = logging.getLogger(__name__)

try:
    from .viewsets import CuentaBancariaViewSet, ExtractoBancarioViewSet, TransaccionBancariaViewSet
except ImportError as e:
    logger.error(f"ERROR: No se pudo importar ViewSets en api/urls.py de bancos: {e}", exc_info=True)
    raise

router = DefaultRouter()
router.register(r"cuentas", CuentaBancariaViewSet, basename="bancos-cuentas")
router.register(r"extractos", ExtractoBancarioViewSet, basename="bancos-extractos")
router.register(r"transacciones", TransaccionBancariaViewSet, basename="bancos-transacciones")

urlpatterns = router.urls

if settings.DEBUG:
    logger.debug(f"URLs de bancos registradas: {[str(url.pattern) for url in router.urls]}")
