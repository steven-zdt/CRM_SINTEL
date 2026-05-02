"""
URLs de API para la app facturas v2.61.2.

# WARNING: API-First: Router DRF para endpoints REST.
Las vistas UI están en apps/tenant/facturas/ui_views.py (si existen).

Arquitectura:
- Todas las rutas están bajo /api/v1/facturas/ (app directa)
- Gateway Core API: /api/v1/core/_apps/facturas/ (acceso directo)
- Facade Core API: /api/v1/core/v1/facturas/ (workspace facade)
- Usa routers de DRF para generar endpoints automáticamente
- Referencia: https://www.django-rest-framework.org/api-guide/routers/

# WARNING: IMPORTANTE: El include en config/api_urls.py es `path('facturas/', include(...))`, 
por lo que el router debe registrar con ruta vacía "" para generar /api/v1/facturas/

# WARNING: v2.61.2: OPTIMIZACIONES:
- Pre-validación de idempotencia (CUFE/CUDE) antes del parsing completo
- Batch processing: soporte para files[] (múltiples archivos)
- Silent Success: actualización automática de FacturaAnexos si XML es más completo
"""
from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.tenant.facturas.api.views_mail_ingestion import (
    MailIngestionPreviewAPIView,
    MailIngestionRunCreateAPIView,
    MailIngestionRunsListAPIView,
)
from apps.tenant.facturas.api.viewsets import FacturaViewSet, ItemFacturaViewSet, NotaCreditoViewSet

# # WARNING: DEPRECATED v2.40: datatables.py eliminado - usar GET /api/v1/facturas/ con StandardResultsSetPagination

# Router para esta app
router = DefaultRouter(trailing_slash=True)

# Registrar ViewSets
# # WARNING: CRÍTICO: Orden de registro importa - rutas específicas ANTES de ruta vacía ""
# Si r'' está primero, captura todas las rutas (greedy matching) y notas-credito nunca se alcanza
# # WARNING: IMPORTANTE: Registrar con ruta vacía "" porque el include en config/api_urls.py es path('facturas/', ...)
# Esto genera rutas como: /api/v1/facturas/ (list), /api/v1/facturas/{id}/ (detail)
router.register(r'notas-credito', NotaCreditoViewSet, basename='nota-credito')  # # WARNING: ANTES de r''
router.register(r'items-factura', ItemFacturaViewSet, basename='item-factura')  # # WARNING: ANTES de r''
router.register(r'', FacturaViewSet, basename='factura')  # # WARNING: AL FINAL para evitar greedy matching

# URLs generadas por el router
# Endpoints disponibles:
# - GET /api/v1/facturas/ (list facturas con paginación)
# - GET /api/v1/facturas/{id}/ (retrieve factura)
# - DELETE /api/v1/facturas/{id}/ (delete factura)
# - POST /api/v1/facturas/importar-ubl/ (importar UBL desde texto)
# - GET /api/v1/facturas/summary/ (resumen de facturación neta)
# - POST /api/v1/facturas/upload-ubl/ (upload UBL file - single o batch)
#   # WARNING: v2.61.2: Soporta batch processing con files[] (múltiples archivos)
#   # WARNING: v2.61.2: Pre-validación de idempotencia (CUFE/CUDE) antes del parsing completo
# - POST /api/v1/facturas/upload-document/ (upload documento universal - XML/PDF/XLS/CSV/TXT)
# - GET /api/v1/facturas/ingest/{task_id}/status/ (estado de ingesta asíncrona)
# - POST /api/v1/facturas/create-from-dto/ (crear factura desde DTO canónico)
# - POST /api/v1/facturas/materialize/ (materializar factura desde resultado de pipeline)
# - GET /api/v1/facturas/{id}/xml/ (obtener XML de factura)
# - GET /api/v1/facturas/{id}/app-response/ (obtener ApplicationResponse XML)
# - POST /api/v1/facturas/update-inbox-state/ (actualizar estado de inbox)
# - GET /api/v1/facturas/gestor-offcanvas/ (renderizar offcanvas de gestor)
# - GET/POST/DELETE /api/v1/facturas/items-factura/ (CRUD items de factura)
# - GET/DELETE /api/v1/facturas/notas-credito/ (CRUD notas de crédito)
# - GET /api/v1/facturas/notas-credito/{id}/xml/ (obtener XML de nota de crédito)
urlpatterns = router.urls

# URLs adicionales para ingesta por correo (Fase 4/5)
# # WARNING: SSoT: Las configuraciones se gestionan en /api/v1/core/v1/empresa/mail-inbox/
# Estas rutas se montan bajo /api/v1/facturas/ porque el include es path('facturas/', ...)
# Endpoints disponibles:
# - POST /api/v1/facturas/ingesta-correo/run/ (ejecutar ingesta de correo)
# - GET /api/v1/facturas/ingesta-correo/runs/ (listar ejecuciones de ingesta)
# - POST /api/v1/facturas/ingesta-correo/preview/ (preview de ingesta sin persistir)
urlpatterns += [
    path("ingesta-correo/run/", MailIngestionRunCreateAPIView.as_view(), name="facturas_mail_run"),
    path("ingesta-correo/runs/", MailIngestionRunsListAPIView.as_view(), name="facturas_mail_runs"),
    path("ingesta-correo/preview/", MailIngestionPreviewAPIView.as_view(), name="facturas_mail_preview"),
    # # WARNING: DEPRECATED v2.40: Endpoints DataTables eliminados.
    # Usar GET /api/v1/facturas/ con StandardResultsSetPagination (Tabulator Factory).
    # path("dt/facturas/", facturas_dt, name="facturas_dt"),  # # WARNING: DEPRECATED
    # # WARNING: NOTA: render-offcanvas-pendientes fue eliminado - el offcanvas se carga directamente desde facturas_ui.js
]

# # WARNING: v2.61.2: DOCUMENTACIÓN DE ENDPOINTS OPTIMIZADOS
# 
# BATCH PROCESSING (upload-ubl):
# POST /api/v1/facturas/upload-ubl/
# Body (multipart/form-data):
#   - file: <archivo.xml> (archivo único)
#   - files[]: <archivo1.xml>, <archivo2.xml>, ... (múltiples archivos - batch)
# Query params:
#   - async=true|false: Modo asíncrono (default: true)
#   - preview=true|false: Modo preview (default: false)
# Returns (single file):
#   - 201 Created: Factura creada
#   - 200 OK: Factura ya existe (idempotente) o duplicado detectado por pre-validación
#   - 202 Accepted: Tarea async encolada (si async=true)
# Returns (batch):
#   - 200 OK: {"creados": X, "duplicados": Y, "errores": Z, "resultados": [...]}
# 
# PRE-VALIDACIÓN DE IDEMPOTENCIA:
# - Extrae CUFE/CUDE usando regex rápida antes del parsing completo
# - Si CUFE ya existe, retorna 200 OK inmediatamente sin parsing
# - Reduce tiempo de respuesta para archivos duplicados
# 
# SILENT SUCCESS:
# - Si factura existe, actualiza FacturaAnexos si el XML nuevo es más completo
# - Compara tamaño del XML y actualiza solo si el nuevo es más largo
# 
# TRANSACTION.ATOMIC OPTIMIZADO:
# - Solo envuelve persistencia, no parsing
# - Mejora rendimiento al no bloquear BD durante parsing
