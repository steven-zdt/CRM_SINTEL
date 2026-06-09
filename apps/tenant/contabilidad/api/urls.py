"""
URLs de API para la app contabilidad.

Arquitectura API-First:
- Todas las rutas están bajo /api/v1/contabilidad/
- Usa routers de DRF para generar endpoints automáticamente
- Referencia: https://www.django-rest-framework.org/api-guide/routers/

WARNING: v2.61: Alineado con sistema de rutas de Core API
- Rutas directas: /api/v1/contabilidad/ (desde config/api_urls.py)
- Gateway Core: /api/v1/core/_apps/contabilidad/ (desde apps/tenant/core/api/urls.py)
- Facades Core v1: /api/v1/core/v1/contabilidad/ (desde apps/tenant/core/api/v1/contabilidad/urls.py)
  - Facades heredan de ViewSets originales y usan serializers Workspace
  - Incluye: cuentas, asientos, movimientos, periodos-contables, catalogo-niif
"""
from django.http import HttpResponseNotFound
from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.tenant.contabilidad.api.viewsets import (
    AsientoContableViewSet,
    CatalogoMaestroNIIFViewSet,
    CuentaContableViewSet,
    DocumentosPendientesViewSet,
    MovimientoContableViewSet,
    PeriodoContableViewSet,
    PlantillaContableViewSet,
    TipoComprobanteViewSet,
    LibroDiarioViewSet,
    RetencionViewSet,
    ConfiguracionRetencionesViewSet,
)

# WARNING: ELIMINADO v2.61: datatables.py y métodos datatables() fueron eliminados.
# La lógica de DataTables fue migrada completamente a Tabulator.
# from apps.tenant.contabilidad.api.datatables import (
#     cuentas_contables_dt,
#     asientos_contables_dt,
# )

# Router para esta app
# WARNING: v2.37: trailing_slash=True unificado (debe coincidir con frontend)
router = DefaultRouter(trailing_slash=True)

# Registrar ViewSets
router.register(r'cuentas-contables', CuentaContableViewSet, basename='cuenta-contable')
router.register(r'asientos-contables', AsientoContableViewSet, basename='asiento-contable')
router.register(r'movimientos-contables', MovimientoContableViewSet, basename='movimiento-contable')
router.register(r'periodos-contables', PeriodoContableViewSet, basename='periodo-contable')
router.register(r'catalogo-niif', CatalogoMaestroNIIFViewSet, basename='catalogo-niif')
router.register(r'tipos-comprobante', TipoComprobanteViewSet, basename='tipo-comprobante')
router.register(r'pendientes', DocumentosPendientesViewSet, basename='pendientes')
router.register(r'libro-diario', LibroDiarioViewSet, basename='libro-diario')
router.register(r'retenciones', RetencionViewSet, basename='retenciones')
router.register(r'configuraciones-retenciones', ConfiguracionRetencionesViewSet, basename='configuraciones-retenciones')
router.register(r'plantillas-contables', PlantillaContableViewSet, basename='plantilla-contable')


# URLs generadas por el router
urlpatterns = router.urls

# WARNING: ELIMINADO v2.61: Endpoints DataTables fueron eliminados completamente.
# La lógica de DataTables fue migrada a Tabulator.
# Los métodos datatables() en ViewSets fueron eliminados.
# urlpatterns += [
#     path("dt/cuentas-contables/", cuentas_contables_dt, name="cuentas_contables_dt"),
#     path("dt/asientos-contables/", asientos_contables_dt, name="asientos_contables_dt"),
# ]

# WARNING: DEPRECATED: Ruta migrada desde urls_ui.py
# Esta ruta está deprecada y retorna 404. La UI se movió a Core.
def deprecated_summary_view(request):
    """Vista deprecada que retorna 404."""
    return HttpResponseNotFound(
        '<h1>404 - Vista deprecada</h1>'
        '<p>Esta ruta ha sido movida a Core. Use /static/tenant/core/contabilidad/index.html</p>'
    )

urlpatterns += [
    # WARNING: DEPRECADO: Ruta migrada desde urls_ui.py - Retorna 404
    path('partials/summary/', deprecated_summary_view, name='contabilidad-summary-partial'),
]
