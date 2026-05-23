"""
URLs de API para cotizaciones v2.62.0 - SINTEL FSD
"""
from django.urls import path
from rest_framework.routers import DefaultRouter

from ..configuracion.viewsets import ConfiguracionCotizacionViewSet
from .viewsets import (
    CotizacionItemViewSet, 
    CotizacionViewSet, 
    ProductoViewSet, 
    ServicioViewSet
)

# Router DRF (APIs REST)
router = DefaultRouter()
router.register(r'configuracion', ConfiguracionCotizacionViewSet, basename='configuracion-cotizacion')
router.register(r'items', CotizacionItemViewSet, basename='cotizacion-item')
router.register(r'productos', ProductoViewSet, basename='producto')
router.register(r'servicios', ServicioViewSet, basename='servicio')
router.register(r'', CotizacionViewSet, basename='cotizacion')

# URLs API REST
api_urlpatterns = router.urls

# URLs UI HTML (para config/urls_tenant.py)
# NOTA: Las vistas UI se mantienen para compatibilidad con HTMX
from ..ui_views import (
    CotizacionEditorDraftView,
    CotizacionEditorTemplateView,
    ConfiguracionListOffcanvasView,
    ConfiguracionCrearOffcanvasView,
    ConfiguracionEditarOffcanvasView,
    ConfiguracionVerOffcanvasView,
    CotizacionDetalleOffcanvasView,
)

ui_urlpatterns = [
    path('editor/<uuid:uuid>/', CotizacionEditorTemplateView.as_view(), name='ui_editor_cotizacion'),
    path('editor/draft/', CotizacionEditorDraftView.as_view(), name='ui_editor_draft'),
    path('partials/configuracion/lista/', ConfiguracionListOffcanvasView.as_view(), name='ui_list_configuracion'),
    path('partials/configuracion/crear/', ConfiguracionCrearOffcanvasView.as_view(), name='ui_crear_configuracion'),
    path('partials/configuracion/editar/<uuid:uuid>/', ConfiguracionEditarOffcanvasView.as_view(), name='ui_editar_configuracion'),
    path('partials/configuracion/ver/<uuid:uuid>/', ConfiguracionVerOffcanvasView.as_view(), name='ui_ver_configuracion'),
    path('partials/ver/<uuid:uuid>/', CotizacionDetalleOffcanvasView.as_view(), name='ui_detalle_cotizacion'),
]

urlpatterns = api_urlpatterns
