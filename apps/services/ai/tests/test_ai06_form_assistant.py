"""
Fase AI-06 (Form Assistant): tests reales para
apps/services/ai/orchestrator/form_assistant.py::ask(). Mockea
anthropic.Anthropic (nunca una llamada de red real) pero ejercita el
flujo real completo: parseo de la decision del LLM, ejecucion via
AIEngine.run_tool() (unico punto real de ejecucion), y el enforcement
real de permisos/flags de ese punto.
"""
import json
import os
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.services.ai.orchestrator import ask
from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase

User = get_user_model()

AI_READ_FLAGS_ON = {"AI_ENABLED": True, "AI_READ_ENABLED": True}


class _FakeRequest:
    def __init__(self, user, tenant=None):
        self.user = user
        self.tenant = tenant


def _mock_anthropic_text(payload_dict_or_text):
    text = payload_dict_or_text if isinstance(payload_dict_or_text, str) else json.dumps(payload_dict_or_text)
    fake_message = SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])
    fake_client = SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: fake_message))
    return patch("anthropic.Anthropic", return_value=fake_client)


class FormAssistantTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.create(
            razon_social="EMPRESA AI06 TEST S.A.S.", nit="900999111", direccion="Calle AI06",
        )
        self.user = User.objects.create_user(email="ai06_user@test.local", password="testpass123")
        TenantProfile.objects.create(user=self.user, empresa=self.empresa)
        Cliente.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="900222999", razon_social="Acme AI06 S.A.S.", regimen_tributario="ORDINARIO",
        )

    def test_ai_deshabilitado_no_llama_al_proveedor(self):
        """Nunca debe gastar una llamada al LLM si AI_ENABLED es False."""
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        with patch("anthropic.Anthropic") as mock_anthropic:
            result = ask(request, "busca el cliente Acme")

        assert result["status"] == "PERMISSION_DENIED"
        mock_anthropic.assert_not_called()

    @override_settings(**AI_READ_FLAGS_ON)
    def test_usuario_sin_tenant_profile_no_llama_al_proveedor(self):
        user_sin_perfil = User.objects.create_user(email="ai06_sin_perfil@test.local", password="testpass123")
        request = _FakeRequest(user=user_sin_perfil, tenant=self.tenant)

        with patch("anthropic.Anthropic") as mock_anthropic:
            result = ask(request, "busca el cliente Acme")

        assert result["status"] == "PERMISSION_DENIED"
        mock_anthropic.assert_not_called()

    @override_settings(**AI_READ_FLAGS_ON)
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "fake-key-for-test"})
    def test_llm_elige_tool_real_y_la_ejecuta(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)
        decision = {"tool": "buscar_cliente", "arguments": {"search": "Acme AI06"}}

        with _mock_anthropic_text(decision):
            result = ask(request, "busca el cliente Acme AI06")

        assert result["status"] == "OK"
        assert result["tool_used"] == "buscar_cliente"
        assert len(result["data"]) == 1
        assert result["data"][0]["razon_social"] == "Acme AI06 S.A.S."

    @override_settings(**AI_READ_FLAGS_ON)
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "fake-key-for-test"})
    def test_llm_no_encuentra_tool_aplicable(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)
        decision = {"tool": None, "reason": "Esta pregunta no corresponde a ninguna herramienta disponible."}

        with _mock_anthropic_text(decision):
            result = ask(request, "cual es la capital de Francia?")

        assert result["status"] == "NO_TOOL"

    @override_settings(**AI_READ_FLAGS_ON)
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "fake-key-for-test"})
    def test_llm_alucina_tool_inexistente_es_manejado_por_ai_engine(self):
        """Defensa en profundidad: si el LLM inventa un nombre de tool, el
        orquestador no lo valida el mismo -- confia en que AIEngine.run_tool()
        (el unico punto real de ejecucion) lo rechace con NOT_FOUND."""
        request = _FakeRequest(user=self.user, tenant=self.tenant)
        decision = {"tool": "eliminar_toda_la_base_de_datos", "arguments": {}}

        with _mock_anthropic_text(decision):
            result = ask(request, "haz algo que no deberias poder hacer")

        assert result["status"] == "NOT_FOUND"

    @override_settings(**AI_READ_FLAGS_ON)
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "fake-key-for-test"})
    def test_llm_responde_texto_no_json(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        with _mock_anthropic_text("Lo siento, no puedo ayudarte con eso."):
            result = ask(request, "algo raro")

        assert result["status"] == "INTERNAL_ERROR"
