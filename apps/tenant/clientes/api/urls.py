"""
URLs de la API de clientes (DRF Router) v2.60.

⚠️ API-First: Solo endpoints RESTful para Tabulator
⚠️ IMPORTANTE: El prefijo 'clientes/' ya está en config/api_urls.py
⚠️ v2.60: La acción @action 'offcanvas' del ViewSet genera automáticamente la ruta /api/v1/clientes/offcanvas/
⚠️ v2.60: CRUD independiente para ContactoCliente con Zero Trust
"""
import logging
from rest_framework.routers import DefaultRouter
from .viewsets import ClienteViewSet, ContactoClienteViewSet

logger = logging.getLogger(__name__)

router = DefaultRouter()
# ⚠️ CRÍTICO: El orden de registro es IMPORTANTE - las rutas más específicas deben registrarse ANTES que las genéricas
# Si registramos "" antes que "contactos", DRF intentará interpretar 'contactos' como un ID numérico para ClienteViewSet

# ⚠️ v2.60: CRUD independiente para ContactoCliente - REGISTRAR PRIMERO (ruta específica)
# Genera rutas: /api/v1/clientes/contactos/ (list, create), /api/v1/clientes/contactos/{id}/ (retrieve, update, delete)
# La acción @action 'gestor-offcanvas' genera: /api/v1/clientes/contactos/gestor-offcanvas/
router.register(r"contactos", ContactoClienteViewSet, basename="contacto")

# ⚠️ CRÍTICO: Registrar con prefijo vacío DESPUÉS de las rutas específicas
# Esto genera rutas: /api/v1/clientes/ (list, create), /api/v1/clientes/{id}/ (retrieve, update, partial_update)
# El basename debe ser 'cliente' (singular) para que DRF genere los nombres correctos
# ⚠️ v2.60: La acción @action 'offcanvas' genera automáticamente: /api/v1/clientes/offcanvas/
router.register(r"", ClienteViewSet, basename="cliente")

urlpatterns = router.urls

# ⚠️ DEBUG: Verificar que se generaron URLs
if urlpatterns:
    logger.info(f"✅ ClienteViewSet registrado correctamente. URLs generadas: {len(urlpatterns)}")
    for url_pattern in urlpatterns:
        logger.debug(f"  - {url_pattern.pattern} -> {getattr(url_pattern, 'name', 'N/A')}")
else:
    logger.error("❌ ERROR CRÍTICO: El router de clientes no generó ninguna URL. Verifique que ClienteViewSet esté correctamente configurado.")

# ⚠️ DEPRECATED v2.40: Endpoint DataTables en datatables.py está deprecado.
# Use POST /api/v1/clientes/dt/clientes/ (ClienteViewSet.datatables() action) en su lugar.
# urlpatterns += [
#     path("dt/clientes/", clientes_dt, name="clientes_dt"),  # ⚠️ DEPRECATED
# ]
