"""
URLs de la API de gastos (DRF Router).

⚠️ v2.40: Sistema de Documento Soporte Inmutable.
Se incluye en config/api_urls.py bajo /api/v1/gastos/ y /api/v1/resoluciones-dian/.

REGLA DE ORO: El ViewSet se registra como 'gastos' para mantener compatibilidad con el frontend,
aunque el modelo base sea DocumentoSoporte.

⚠️ CRÍTICO: El router debe estar correctamente configurado para que DRF genere las rutas:
- GET /api/v1/gastos/ (list)
- POST /api/v1/gastos/ (create) - ⚠️ v2.40: Usa automáticamente resolución vigente
- GET /api/v1/gastos/{id}/ (retrieve)
- DELETE /api/v1/gastos/{id}/ (destroy)
- GET /api/v1/gastos/summary/ (summary action)
- GET /api/v1/gastos/resoluciones/ (resoluciones action - legacy)
- GET /api/v1/gastos/resolucion-activa/ (resolucion_activa action) - ⚠️ DEPRECATED: Usar /api/v1/resoluciones-dian/activa/
- POST /api/v1/gastos/configurar-resolucion/ (configurar_resolucion action) - ⚠️ DEPRECATED: Usar POST /api/v1/resoluciones-dian/
- POST /api/v1/gastos/{id}/anular/ (anular action)

⚠️ v2.40: Nuevo ViewSet independiente para Resoluciones DIAN:
- GET /api/v1/resoluciones-dian/ (list)
- POST /api/v1/resoluciones-dian/ (create)
- GET /api/v1/resoluciones-dian/{id}/ (retrieve)
- DELETE /api/v1/resoluciones-dian/{id}/ (destroy) - Solo si no tiene Documentos de Soporte
- POST /api/v1/resoluciones-dian/{id}/desactivar/ (desactivar action)
- GET /api/v1/resoluciones-dian/activa/ (activa action)
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
import logging

logger = logging.getLogger(__name__)

try:
    from .viewsets import GastoViewSet, ResolucionDIANViewSet
except ImportError as e:
    logger.error(f"❌ ERROR: No se pudo importar ViewSets: {e}", exc_info=True)
    raise

# ⚠️ RECONSTRUCCIÓN COMPLETA DEL ROUTER (v2.40)
# Router para esta app
router = DefaultRouter()

# ⚠️ CRÍTICO: Registro en la raíz (string vacío) porque el prefijo 'gastos/' ya está en config/api_urls.py
# El basename 'gastos' es VITAL para que DRF genere las URLs correctamente
try:
    router.register(r'', GastoViewSet, basename='gastos')
    logger.info("✅ GastoViewSet registrado correctamente en router con basename='gastos'")
except Exception as e:
    logger.error(f"❌ ERROR registrando GastoViewSet en router: {e}", exc_info=True)
    raise

# URLs generadas por el router
# ⚠️ ESTRUCTURA EXPLÍCITA: Usar router.urls directamente (patrón estándar DRF)
# ⚠️ CRÍTICO: No usar include(router.urls) dentro de otro include, usar router.urls directamente
urlpatterns = router.urls

# Log de URLs generadas (solo en DEBUG)
import django.conf
if django.conf.settings.DEBUG:
    logger.debug(f"📋 URLs de gastos generadas: {[str(url.pattern) for url in router.urls]}")