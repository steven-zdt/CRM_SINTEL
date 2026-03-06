"""
URLs de API para la app impuestos.

Referencia: https://www.django-rest-framework.org/api-guide/routers/
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.public.impuestos.api.viewsets import VIEWSETS, SearchView
from apps.public.impuestos.api.health import SearchHealthView
from apps.public.impuestos.api.crud_viewsets import (
    TipoImpuestoCRUDViewSet,
    TarifaIVACRUDViewSet,
    ConceptoRetencionCRUDViewSet,
    CodigoTributarioCRUDViewSet,
    ActividadEconomicaCRUDViewSet,
    NormaTributariaCRUDViewSet,
)
from apps.public.impuestos.api.datatables import (
    TipoImpuestoDataTablesView,
    TarifaIVADataTablesView,
    ConceptoRetencionDataTablesView,
    CodigoTributarioDataTablesView,
    ActividadEconomicaDataTablesView,
)

# Router para catálogos ReadOnly (públicos)
router = DefaultRouter()

# Registrar todos los ViewSets automáticamente (catálogos ReadOnly)
for prefix, viewset, basename in VIEWSETS:
    router.register(prefix, viewset, basename=basename)

# Router para CRUD privados (autenticados)
crud_router = DefaultRouter()
crud_router.register(r'impuestos/tipos-crud', TipoImpuestoCRUDViewSet, basename='tipo-impuesto-crud')
crud_router.register(r'impuestos/tarifas-iva-crud', TarifaIVACRUDViewSet, basename='tarifa-iva-crud')
crud_router.register(r'impuestos/conceptos-retencion-crud', ConceptoRetencionCRUDViewSet, basename='concepto-retencion-crud')
crud_router.register(r'impuestos/codigos-tributarios-crud', CodigoTributarioCRUDViewSet, basename='codigo-tributario-crud')
crud_router.register(r'impuestos/actividades-economicas-crud', ActividadEconomicaCRUDViewSet, basename='actividad-economica-crud')
crud_router.register(r'impuestos/normas-crud', NormaTributariaCRUDViewSet, basename='norma-tributaria-crud')

urlpatterns = [
    path('', include(router.urls)),  # ReadOnly públicos
    path('', include(crud_router.urls)),  # CRUD privados
    # Endpoint de búsqueda con OpenSearch
    path('impuestos/search/', SearchView.as_view(), name='impuestos-search'),
    # Endpoint de salud de OpenSearch (solo admin)
    path('impuestos/search/health/', SearchHealthView.as_view(), name='impuestos-search-health'),
    # Endpoints DataTables (server-side)
    path('impuestos/dt/tipos/', TipoImpuestoDataTablesView.as_view(), name='dt-tipos'),
    path('impuestos/dt/tarifas-iva/', TarifaIVADataTablesView.as_view(), name='dt-tarifas-iva'),
    path('impuestos/dt/conceptos-retencion/', ConceptoRetencionDataTablesView.as_view(), name='dt-conceptos-retencion'),
    path('impuestos/dt/codigos-tributarios/', CodigoTributarioDataTablesView.as_view(), name='dt-codigos-tributarios'),
    path('impuestos/dt/actividades-economicas/', ActividadEconomicaDataTablesView.as_view(), name='dt-actividades-economicas'),
]
