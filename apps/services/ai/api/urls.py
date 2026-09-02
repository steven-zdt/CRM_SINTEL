"""
URLs del AI Engine -- /api/v1/ai/

Prefijo vacio deliberado en el router (mismo patron que
`apps/services/reporting/api/urls.py`): la unica ruta real hoy es la
`@action` `ask/` (`AIAssistantViewSet`), no hay `list`/`retrieve` de un
recurso CRUD.
"""
from rest_framework.routers import DefaultRouter

from apps.services.ai.api.viewsets import AIAssistantViewSet

router = DefaultRouter()
router.register(r"", AIAssistantViewSet, basename="ai-assistant")

urlpatterns = router.urls
