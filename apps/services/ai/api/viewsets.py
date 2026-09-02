"""
ViewSet HTTP de AI-06 (Form Assistant) -- primer endpoint real del AI
Engine. No hereda `BaseTenantViewSet` (ModelViewSet con lookup UUID)
porque no expone CRUD de un modelo Django -- expone una unica accion
de orquestacion, mismo patron ya aceptado en esta app para
`ReportingViewSet` (`apps/services/reporting/api/viewsets.py`).
Reutiliza autenticacion/permisos existentes en vez de inventar nuevos
(Regla 4).

Feature flags (`AI_ENABLED`/`AI_<KIND>_ENABLED`, `config/settings.py`)
siguen siendo la puerta real -- este ViewSet solo agrega la capa HTTP
(auth + validacion de forma), toda la logica de negocio/permisos vive
en `apps/services/ai/orchestrator/form_assistant.py::ask()` y, debajo,
en `AIEngine.run_tool()`.
"""
from rest_framework import status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.services.ai.api.serializers import AIAskSerializer
from apps.services.ai.orchestrator import ask as orchestrator_ask
from apps.tenant.api.base import RelaxedJWTAuthentication
from apps.tenant.api.permissions import IsTenantMember

_STATUS_TO_HTTP = {
    "OK": status.HTTP_200_OK,
    "NO_TOOL": status.HTTP_200_OK,
    "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
    "PERMISSION_DENIED": status.HTTP_403_FORBIDDEN,
    "NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "CONFLICT": status.HTTP_409_CONFLICT,
    "DOMAIN_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "INTERNAL_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
}


class AIAssistantViewSet(viewsets.ViewSet):
    """
    POST /api/v1/ai/ask/  -> el Form Assistant elige y ejecuta una tool
    ya registrada a partir de lenguaje natural.
    """
    authentication_classes = [RelaxedJWTAuthentication, SessionAuthentication]
    permission_classes = [IsTenantMember]

    @action(detail=False, methods=["post"], url_path="ask")
    def ask(self, request):
        serializer = AIAskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        result = orchestrator_ask(request, data["message"], screen=data.get("screen"))

        http_status = _STATUS_TO_HTTP.get(result["status"], status.HTTP_200_OK)
        return Response(result, status=http_status)
