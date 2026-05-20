"""URLs de API para la app empleados."""
import logging

from rest_framework.routers import DefaultRouter

logger = logging.getLogger(__name__)

# WARNING: CRITICO: Importar ViewSets directamente (sin try/except para ver errores reales)
from .viewsets import ContratoViewSet, DevengoViewSet, EmpleadoViewSet

# Router para esta app
router = DefaultRouter()

# WARNING: CRITICO: Orden de registro es importante
# 1. Primero registrar sub-rutas (contratos, devengos) - rutas especificas primero
# 2. Luego registrar la ruta base (r'') - ruta generica al final para evitar greedy matching
router.register(r'contratos', ContratoViewSet, basename='contrato')
router.register(r'devengos', DevengoViewSet, basename='devengo')
# WARNING: CRITICO: EmpleadoViewSet debe registrarse AL FINAL con r'' para que sea la ruta base
# Esto genera: /api/v1/empleados/ y /api/v1/empleados/summary/
router.register(r'', EmpleadoViewSet, basename='empleado')

# URLs generadas por el router
# WARNING: ESTRUCTURA EXPLICITA: Usar router.urls directamente (patron estandar DRF)
urlpatterns = router.urls

# Log de confirmacion y depuracion
logger.info("OK: URLs de empleados configuradas correctamente")
if urlpatterns:
    logger.info(f"OK: URLs generadas: {len(urlpatterns)} patrones")
    for url_pattern in urlpatterns:
        pattern_name = getattr(url_pattern, 'name', 'N/A')
        pattern_str = str(url_pattern.pattern)
        logger.info(f"   - {pattern_str} -> {pattern_name}")
else:
    logger.error("ERROR: ERROR CRITICO: El router de empleados no genero ninguna URL")
