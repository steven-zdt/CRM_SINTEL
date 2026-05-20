"""
URLs de la API de clientes (DRF Router).
"""
import logging

from rest_framework.routers import DefaultRouter

from .viewsets import ClienteViewSet, ContactoClienteViewSet

logger = logging.getLogger(__name__)

router = DefaultRouter()

# El orden de registro es importante - las rutas mas especificas deben registrarse antes que las genericas.
# Si registramos "" antes que "contactos", DRF intentara interpretar 'contactos' como un UUID.

# Registrar primero la ruta especifica para ContactoCliente.
router.register(r"contactos", ContactoClienteViewSet, basename="contacto")

# Registrar con prefijo vacio despues de las rutas especificas.
router.register(r"", ClienteViewSet, basename="cliente")

urlpatterns = router.urls

if urlpatterns:
    logger.info(f"[OK] ClienteViewSet registrado correctamente. URLs generadas: {len(urlpatterns)}")
    for url_pattern in urlpatterns:
        logger.debug(f"  - {url_pattern.pattern} -> {getattr(url_pattern, 'name', 'N/A')}")
else:
    logger.error("[ERROR] ERROR CRITICO: El router de clientes no genero ninguna URL.")
