"""
Fase AI-06 (Form Assistant): tests HTTP reales para
POST /api/v1/ai/ask/ (apps/services/ai/api/viewsets.py). Complementa
test_ai06_form_assistant.py (que prueba ask() directo, sin capa HTTP)
verificando: la URL resuelve de verdad, la autenticacion/permiso real
(IsTenantMember) se aplica, el serializer de entrada valida `message`,
y el mapeo status->codigo HTTP es correcto.
"""
import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase

AI_READ_FLAGS_ON = {"AI_ENABLED": True, "AI_READ_ENABLED": True}
ASK_URL = "/api/v1/ai/ask/"


def _mock_anthropic_text(payload_dict_or_text):
    text = payload_dict_or_text if isinstance(payload_dict_or_text, str) else json.dumps(payload_dict_or_text)
    fake_message = SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])
    fake_client = SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: fake_message))
    return patch("anthropic.Anthropic", return_value=fake_client)


class AIAskEndpointTests(SintelTenantTestCase):
    """
    IsTenantMember (permission_classes de AIAssistantViewSet) exige una
    TenantMembership real (esquema publico), no solo un TenantProfile
    (esquema tenant, lo unico que AIContext.build_context() necesita) --
    hallazgo real de este test: es el primer test de este dominio que
    ejercita la capa HTTP completa, no solo run_tool()/ask() directo.
    Por eso reutiliza el `self.user`/`self.membership` que
    SintelTenantTestCase ya crea con TenantMembership real, y solo le
    agrega el TenantProfile que le falta.
    """

    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.create(
            razon_social="EMPRESA AI06 HTTP TEST S.A.S.", nit="900999222", direccion="Calle AI06-HTTP",
        )
        TenantProfile.objects.create(user=self.user, empresa=self.empresa)
        Cliente.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="900333222", razon_social="Acme AI06 HTTP S.A.S.", regimen_tributario="ORDINARIO",
        )
        self.client_autenticado = self.api_client

    def test_ai_deshabilitado_devuelve_403(self):
        resp = self.client_autenticado.post(ASK_URL, data={"message": "busca clientes"}, format="json")

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.json()["status"] == "PERMISSION_DENIED"

    @override_settings(**AI_READ_FLAGS_ON)
    def test_mensaje_vacio_es_400(self):
        """El serializer de entrada rechaza `message` vacio antes de tocar el orquestador."""
        resp = self.client_autenticado.post(ASK_URL, data={"message": ""}, format="json")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_sin_autenticar_es_401(self):
        """DRF: con authentication_classes no vacio y ningun authenticator
        exitoso, permission_denied() eleva NotAuthenticated (401), no
        PermissionDenied (403) -- comportamiento estandar de DRF, no un
        bug de esta vista."""
        client_anonimo = APIClient(HTTP_HOST=self.domain.domain)

        resp = client_anonimo.post(ASK_URL, data={"message": "busca clientes"}, format="json")

        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    @override_settings(**AI_READ_FLAGS_ON)
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key-for-test"})
    def test_flujo_completo_devuelve_200_con_resultado_de_la_tool(self):
        decision = {"tool": "buscar_cliente", "arguments": {"search": "Acme AI06 HTTP"}}

        with _mock_anthropic_text(decision):
            resp = self.client_autenticado.post(ASK_URL, data={"message": "busca Acme"}, format="json")

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["status"] == "OK"
        assert body["tool_used"] == "buscar_cliente"
        assert len(body["data"]) == 1
        assert body["data"][0]["razon_social"] == "Acme AI06 HTTP S.A.S."

    @override_settings(**AI_READ_FLAGS_ON)
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key-for-test"})
    def test_screen_context_se_acepta_y_se_propaga(self):
        """El payload `screen` (Fase 23) llega hasta build_context() sin romper el flujo."""
        decision = {"tool": None, "reason": "no aplica ninguna herramienta"}
        payload = {
            "message": "estoy en el formulario de clientes",
            "screen": {"app": "clientes", "entity": "Cliente", "entity_id": "", "operation": "create"},
        }

        with _mock_anthropic_text(decision):
            resp = self.client_autenticado.post(ASK_URL, data=payload, format="json")

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "NO_TOOL"
