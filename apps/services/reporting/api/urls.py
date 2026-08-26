"""
URLs de API del Reporting Hub -- /api/v1/reporting/

WARNING: prefijo vacio deliberado: GET /api/v1/reporting/ = catalogo
completo (list), GET /api/v1/reporting/<dataset_id>/ = detalle de un
dataset (retrieve), POST /api/v1/reporting/query/ y .../export/ son
@action(detail=False) -- DRF los registra ANTES del patron generico
`<pk>/`, por lo que no colisionan (mismo orden ya usado por otros
ViewSets de este proyecto, ej. AsientoContableViewSet.balance_prueba).
"""
from rest_framework.routers import DefaultRouter

from apps.services.reporting.api.viewsets import ReportingViewSet

router = DefaultRouter()
router.register(r"", ReportingViewSet, basename="reporting")

urlpatterns = router.urls
