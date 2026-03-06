"""
URLs de API para cotizaciones v2.60.

⚠️ API-First: Router DRF para endpoints REST.
Las vistas UI están en apps/tenant/cotizaciones/ui_views.py
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .viewsets import CotizacionViewSet, CotizacionItemViewSet
from ..configuracion.viewsets import ConfiguracionCotizacionViewSet
from ..ui_views import (
    CotizacionEditorTemplateView,
    CotizacionEditorDraftView,
    ConfiguracionCrearOffcanvasView,
    ConfiguracionEditarOffcanvasView,
    ConfiguracionListOffcanvasView,
    ConfiguracionVerOffcanvasView,
)

# Router DRF (APIs REST)
router = DefaultRouter()
router.register(r'configuracion', ConfiguracionCotizacionViewSet, basename='configuracion-cotizacion')
router.register(r'items', CotizacionItemViewSet, basename='cotizacion-item')
router.register(r'', CotizacionViewSet, basename='cotizacion')

# URLs API REST (para config/api_urls.py)
api_urlpatterns = router.urls

# URLs UI HTML (para config/urls_tenant.py)
ui_urlpatterns = [
    path('editor/<uuid:uuid>/', CotizacionEditorTemplateView.as_view(), name='ui_editor_cotizacion'),
    path('editor/draft/', CotizacionEditorDraftView.as_view(), name='ui_editor_draft'),
    # URLs para Configuraciones/Plantillas
    path('partials/configuracion/lista/', ConfiguracionListOffcanvasView.as_view(), name='ui_list_configuracion'),
    path('partials/configuracion/crear/', ConfiguracionCrearOffcanvasView.as_view(), name='ui_crear_configuracion'),
    path('partials/configuracion/editar/<int:id>/', ConfiguracionEditarOffcanvasView.as_view(), name='ui_editar_configuracion'),
    path('partials/configuracion/ver/<int:id>/', ConfiguracionVerOffcanvasView.as_view(), name='ui_ver_configuracion'),
]

# Exportar APIs por defecto (para config/api_urls.py)
urlpatterns = api_urlpatterns
