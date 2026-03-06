"""
URLs de API para la app facturas.

Arquitectura API-First:
- Todas las rutas están bajo /api/v1/facturas/
- Usa routers de DRF para generar endpoints automáticamente
- Referencia: https://www.django-rest-framework.org/api-guide/routers/

⚠️ IMPORTANTE: El include en config/api_urls.py es `path('facturas/', include(...))`, 
por lo que el router debe registrar con ruta vacía "" para generar /api/v1/facturas/
"""
from django.urls import path
from rest_framework.routers import DefaultRouter
from apps.tenant.facturas.api.viewsets import FacturaViewSet, ItemFacturaViewSet, NotaCreditoViewSet
from apps.tenant.facturas.api.views_mail_ingestion import (
    MailIngestionRunCreateAPIView,
    MailIngestionRunsListAPIView,
    MailIngestionPreviewAPIView,
)
# ⚠️ DEPRECATED v2.40: datatables.py eliminado - usar GET /api/v1/facturas/ con StandardResultsSetPagination

# Router para esta app
router = DefaultRouter()

# Registrar ViewSets
# ⚠️ CRÍTICO: Orden de registro importa - rutas específicas ANTES de ruta vacía ""
# Si r'' está primero, captura todas las rutas (greedy matching) y notas-credito nunca se alcanza
# ⚠️ IMPORTANTE: Registrar con ruta vacía "" porque el include en config/api_urls.py es path('facturas/', ...)
# Esto genera rutas como: /api/v1/facturas/ (list), /api/v1/facturas/{id}/ (detail)
router.register(r'notas-credito', NotaCreditoViewSet, basename='nota-credito')  # ⚠️ ANTES de r''
router.register(r'items-factura', ItemFacturaViewSet, basename='item-factura')  # ⚠️ ANTES de r''
router.register(r'', FacturaViewSet, basename='factura')  # ⚠️ AL FINAL para evitar greedy matching

# URLs generadas por el router
urlpatterns = router.urls

# URLs adicionales para ingesta por correo (Fase 4/5)
# ⚠️ SSoT: Las configuraciones se gestionan en /api/v1/empresa/mailbox/configs/
# Estas rutas se montan bajo /api/v1/facturas/ porque el include es path('facturas/', ...)
urlpatterns += [
    path("ingesta-correo/run/", MailIngestionRunCreateAPIView.as_view(), name="facturas_mail_run"),
    path("ingesta-correo/runs/", MailIngestionRunsListAPIView.as_view(), name="facturas_mail_runs"),
    path("ingesta-correo/preview/", MailIngestionPreviewAPIView.as_view(), name="facturas_mail_preview"),
    # ⚠️ DEPRECATED v2.40: Endpoints DataTables eliminados.
    # Usar GET /api/v1/facturas/ con StandardResultsSetPagination (Tabulator Factory).
    # path("dt/facturas/", facturas_dt, name="facturas_dt"),  # ⚠️ DEPRECATED
    # ⚠️ NOTA: render-offcanvas-pendientes fue eliminado - el offcanvas se carga directamente desde facturas_ui.js
]
