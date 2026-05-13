"""
URLs de la API de gastos (DRF Router).

v2.62: FLEXIBILIDAD OPERATIVA - Inmutabilidad deshabilitada.
Se incluye en config/api_urls.py bajo /api/v1/gastos/ y /api/v1/resoluciones-dian/.

REGLA DE ORO: El ViewSet se registra como 'gastos' para mantener compatibilidad con el frontend,
aunque el modelo base sea DocumentoSoporte.


"""
import logging

from rest_framework.routers import DefaultRouter

logger = logging.getLogger(__name__)

try:
    from .viewsets import GastoViewSet, ResolucionDIANViewSet
except ImportError as e:
    logger.error(f"ERROR: ERROR: No se pudo importar ViewSets: {e}", exc_info=True)
    raise

# WARNING: RECONSTRUCCION COMPLETA DEL ROUTER (v2.40)
# Router para esta app
router = DefaultRouter()

# WARNING: CRITICO: Registro en la raiz (string vacio) porque el prefijo 'gastos/' ya esta en config/api_urls.py
# El basename 'gastos' es VITAL para que DRF genere las URLs correctamente
try:
    router.register(r'', GastoViewSet, basename='gastos')
    logger.info("OK: GastoViewSet registrado correctamente en router con basename='gastos'")
except Exception as e:
    logger.error(f"ERROR: ERROR registrando GastoViewSet en router: {e}", exc_info=True)
    raise

# URLs generadas por el router
# WARNING: ESTRUCTURA EXPLICITA: Usar router.urls directamente (patron estandar DRF)
# WARNING: CRITICO: No usar include(router.urls) dentro de otro include, usar router.urls directamente
urlpatterns = router.urls

# Log de URLs generadas (solo en DEBUG)
import django.conf

if django.conf.settings.DEBUG:
    logger.debug(f"LIST URLs de gastos generadas: {[str(url.pattern) for url in router.urls]}")