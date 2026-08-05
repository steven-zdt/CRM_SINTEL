"""
URLs de la API de proveedores (DRF Router) v3.5.

Alineado con arquitectura API-First.
Se incluye en config/api_urls.py bajo /api/v1/proveedores/
"""
import logging

from rest_framework.routers import DefaultRouter

from .viewsets import ProveedorViewSet, CuentasPagarViewSet, RepresentanteViewSet

logger = logging.getLogger(__name__)

router = DefaultRouter()

# ORDEN CRITICO: los prefijos con nombre ANTES del prefijo vacio ""
# El router de DRF evalua en orden — si "" va primero, "cuentas-por-pagar"
# se interpreta como UUID del ProveedorViewSet y lanza ValidationError.

# Sub-modulo Cuentas por Pagar
router.register(r"cuentas-pagar", CuentasPagarViewSet, basename="cuentas-pagar")

# Sub-modulo Representantes (v3.17.0)
# Endpoint: /api/v1/proveedores/representantes/ + filtro ?proveedor_uuid=...
router.register(r"representantes", RepresentanteViewSet, basename="representante")

# ViewSet principal de proveedores — SIEMPRE AL FINAL con prefijo vacio
router.register(r"", ProveedorViewSet, basename="proveedor")

urlpatterns = router.urls

if urlpatterns:
    logger.info(
        "OK: ProveedorViewSet + CuentasPagarViewSet (CxP) + RepresentanteViewSet (v3.17.0) registrados. URLs: %d",
        len(urlpatterns),
    )
else:
    logger.error("ERROR CRITICO: El router de proveedores no genero URLs. Verifique ViewSets.")