"""
URLs de API para la app empleados.

WARNING: v2.40: Arquitectura API-First con Tabulator Factory.
- Todas las rutas están bajo /api/v1/empleados/
- Usa routers de DRF para generar endpoints automáticamente
- Referencia: https://www.django-rest-framework.org/api-guide/routers/
"""
import logging

from rest_framework.routers import DefaultRouter

logger = logging.getLogger(__name__)

# WARNING: CRÍTICO: Importar ViewSets directamente (sin try/except para ver errores reales)
from .viewsets import ContratoViewSet, DevengoViewSet, EmpleadoViewSet

# Router para esta app
router = DefaultRouter()

# WARNING: CRÍTICO: Orden de registro es importante
# 1. Primero registrar sub-rutas (contratos, devengos) - rutas específicas primero
# 2. Luego registrar la ruta base (r'') - ruta genérica al final para evitar greedy matching
router.register(r'contratos', ContratoViewSet, basename='contrato')
router.register(r'devengos', DevengoViewSet, basename='devengo')
# WARNING: CRÍTICO: EmpleadoViewSet debe registrarse AL FINAL con r'' para que sea la ruta base
# Esto genera: /api/v1/empleados/ y /api/v1/empleados/summary/
router.register(r'', EmpleadoViewSet, basename='empleado')

# URLs generadas por el router
# WARNING: ESTRUCTURA EXPLÍCITA: Usar router.urls directamente (patrón estándar DRF)
urlpatterns = router.urls

# Log de confirmación y depuración
logger.info("OK: URLs de empleados configuradas correctamente")
if urlpatterns:
    logger.info(f"📋 URLs generadas: {len(urlpatterns)} patrones")
    for url_pattern in urlpatterns:
        pattern_name = getattr(url_pattern, 'name', 'N/A')
        pattern_str = str(url_pattern.pattern)
        logger.info(f"   - {pattern_str} -> {pattern_name}")
else:
    logger.error("ERROR: ERROR CRÍTICO: El router de empleados no generó ninguna URL")