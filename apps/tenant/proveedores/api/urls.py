"""
URLs de la API de proveedores (DRF Router) v2.40.

⚠️ v2.40: Alineado con arquitectura API-First.
Se incluye en config/api_urls.py bajo /api/v1/proveedores/
"""
import logging
from rest_framework.routers import DefaultRouter
from .viewsets import ProveedorViewSet

logger = logging.getLogger(__name__)

router = DefaultRouter()
# ⚠️ IMPORTANTE: No incluir el prefijo aquí porque ya está en config/api_urls.py
# El router se incluye con path('proveedores/', include(...)), así que registramos sin prefijo
router.register(r"", ProveedorViewSet, basename="proveedor")

urlpatterns = router.urls

# ⚠️ DEBUG: Log para verificar que las URLs se generaron correctamente
if urlpatterns:
    logger.info(f"✅ ProveedorViewSet registrado correctamente. URLs generadas: {len(urlpatterns)}")
    for url_pattern in urlpatterns:
        logger.info(f"   - {url_pattern.pattern} -> {getattr(url_pattern, 'name', 'N/A')}")
else:
    logger.error("❌ ERROR CRÍTICO: El router de proveedores no generó ninguna URL. Verifique que ProveedorViewSet esté correctamente configurado.")