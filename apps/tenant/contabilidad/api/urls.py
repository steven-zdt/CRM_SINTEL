"""
URLs de API para la app contabilidad.

Arquitectura API-First:
- Todas las rutas están bajo /api/v1/contabilidad/
- Usa routers de DRF para generar endpoints automáticamente
- Referencia: https://www.django-rest-framework.org/api-guide/routers/
"""
from django.urls import path
from rest_framework.routers import DefaultRouter
from apps.tenant.contabilidad.api.viewsets import (
    CuentaContableViewSet,
    AsientoContableViewSet,
    MovimientoContableViewSet,
    CatalogoMaestroNIIFViewSet,
)
# ⚠️ DEPRECATED v2.40: datatables.py está deprecado. Use ViewSet.datatables() actions en su lugar.
# from apps.tenant.contabilidad.api.datatables import (
#     cuentas_contables_dt,
#     asientos_contables_dt,
# )

# Router para esta app
# ⚠️ v2.37: trailing_slash=True unificado (debe coincidir con frontend)
TRAILING_SLASH = True
router = DefaultRouter(trailing_slash=TRAILING_SLASH)

# Registrar ViewSets
router.register(r'cuentas-contables', CuentaContableViewSet, basename='cuenta-contable')
router.register(r'asientos-contables', AsientoContableViewSet, basename='asiento-contable')
router.register(r'movimientos-contables', MovimientoContableViewSet, basename='movimiento-contable')
router.register(r'catalogo-niif', CatalogoMaestroNIIFViewSet, basename='catalogo-niif')

# URLs generadas por el router
urlpatterns = router.urls

# ⚠️ DEPRECATED v2.40: Endpoints DataTables en datatables.py están deprecados.
# Use POST /api/v1/contabilidad/cuentas-contables/dt/cuentas-contables/ y
# POST /api/v1/contabilidad/asientos-contables/dt/asientos-contables/ (actions del ViewSet) en su lugar.
# urlpatterns += [
#     path("dt/cuentas-contables/", cuentas_contables_dt, name="cuentas_contables_dt"),
#     path("dt/asientos-contables/", asientos_contables_dt, name="asientos_contables_dt"),
# ]
