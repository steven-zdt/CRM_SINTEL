"""
URLs de la API de gastos (DRF Router).

v2.62: FLEXIBILIDAD OPERATIVA - Inmutabilidad deshabilitada.
Se incluye en config/api_urls.py bajo /api/v1/gastos/.
Resoluciones expuestas en /api/v1/gastos/resoluciones/ (v3.7.6).

REGLA DE ORO: El ViewSet se registra como 'gastos' para mantener compatibilidad con el frontend,
aunque el modelo base sea DocumentoSoporte.


"""
import logging

from rest_framework.routers import DefaultRouter

logger = logging.getLogger(__name__)

try:
    from .viewsets import GastoViewSet, ResolucionDIANViewSet
except ImportError as e:
    logger.error(f"ERROR: No se pudo importar ViewSets: {e}", exc_info=True)
    raise

router = DefaultRouter()

# WARNING: Orden critico - rutas especificas ANTES de r'' para evitar greedy matching.
# r'' genera ^(?P<uuid>[^/.]+)/$ que capturaria "resoluciones" como uuid si va primero.
router.register(r'resoluciones', ResolucionDIANViewSet, basename='resoluciones-dian')  # ANTES de r''
router.register(r'', GastoViewSet, basename='gastos')  # AL FINAL

logger.info("OK: GastoViewSet y ResolucionDIANViewSet registrados en el router de gastos")

urlpatterns = router.urls

# Log de URLs generadas (solo en DEBUG)
import django.conf

if django.conf.settings.DEBUG:
    logger.debug(f"LIST URLs de gastos generadas: {[str(url.pattern) for url in router.urls]}")