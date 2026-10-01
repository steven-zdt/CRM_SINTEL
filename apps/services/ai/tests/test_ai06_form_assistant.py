"""
Fase AI-06 (Form Assistant): tests reales para
apps/services/ai/orchestrator/form_assistant.py::ask(). Mockea el
resolver de LLM (nunca una llamada de red real) pero ejercita el flujo
real completo: parseo de la decision del LLM, ejecucion via
AIEngine.run_tool() (unico punto real de ejecucion), y el enforcement
real de permisos/flags de ese punto.

Hallazgo real (2026-09-25): estos tests mockeaban `anthropic.Anthropic`
directo -- correcto cuando se escribieron, pero `ask()` cambio (Fase 10
del plan LLM Provider Hub, 2026-09-24) a resolver el provider real via
`resolve_active_llm()` (DB-aware, puede resolver a Ollama/OpenAI-
compatible, no solo Anthropic). El mock de `anthropic.Anthropic` dejo
de interceptar nada -- la llamada real caia a `resolution.provider.
complete()` de lo que sea que este activo en este entorno (Ollama real,
~90-300s por llamada), lo que explicaba los tests que colgaban minutos
en vez de fallar rapido. Corregido mockeando `resolve_active_llm` en el
modulo `form_assistant` (el punto real de resolucion), no el SDK de un
proveedor especifico -- agnostico a cual provider este activo.
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

# Hallazgo real (2026-09-25): .env de este entorno tiene AI_ADK_ENABLED=true
# -- apps.services.ai.orchestrator.ask() (lo que estos tests importan) es un
# ROUTER que con ese flag despacha a adk_router.ask() (agente ADK real via
# LM Studio/Ollama) en vez de a form_assistant.ask(), la funcion que estos
# tests mockean (_mock_llm_decision_text patchea
# form_assistant.resolve_active_llm, nunca invocado si el router se va por
# ADK). Sin forzar AI_ADK_ENABLED=False, estos tests hacian llamadas reales
# a un LLM (~90-450s cada una) y fallaban por motivos ajenos al mock.
AI_READ_FLAGS_ON = {"AI_ENABLED": True, "AI_READ_ENABLED": True, "AI_ADK_ENABLED": False}


class _FakeRequest:
    def __init__(self, user, tenant=None):
        self.user = user
        self.tenant = tenant


def _mock_llm_decision_text(payload_dict_or_text):
    """Mockea resolve_active_llm() (el punto real de resolucion desde Fase
    10 del plan LLM Provider Hub), no un SDK de proveedor especifico --
    agnostico a si el provider activo real es Anthropic/Ollama/OpenAI-
    compatible."""
    text = (
        payload_dict_or_text
        if isinstance(payload_dict_or_text, str)
        else json.dumps(payload_dict_or_text)
    )
    fake_response = SimpleNamespace(
        text=text,
        model="fake-model",
        provider="fake",
        input_tokens=0,
        output_tokens=0,
        tool_calls=[],
    )
    fake_resolution = SimpleNamespace(
        provider=SimpleNamespace(complete=lambda *a, **kw: fake_response),
        provider_name="fake",
        model="fake-model",
        capabilities=None,
        model_config_id=None,
    )
    return patch(
        "apps.services.ai.orchestrator.form_assistant.resolve_active_llm",
        return_value=fake_resolution,
    )


class FormAssistantTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.create(
            razon_social="EMPRESA AI06 TEST S.A.S.",
            nit="900999111",
            direccion="Calle AI06",
        )
        self.user = User.objects.create_user(email="ai06_user@test.local", password="testpass123")
        TenantProfile.objects.create(user=self.user, empresa=self.empresa)
        Cliente.objects.create(
            empresa=self.empresa,
            tipo_persona="JURIDICA",
            tipo_documento="NIT",
            numero_documento="900222999",
            razon_social="Acme AI06 S.A.S.",
            regimen_tributario="ORDINARIO",
        )

    @override_settings(AI_ENABLED=False)
    def test_ai_deshabilitado_no_llama_al_proveedor(self):
        """Nunca debe gastar una llamada al LLM si AI_ENABLED es False.
        Hallazgo real (2026-09-25): sin este override explicito, el test
        dependia de que AI_ENABLED sea False por defecto -- falla en
        cualquier entorno con AI_ENABLED=true en .env (este mismo)."""
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        with patch(
            "apps.services.ai.orchestrator.form_assistant.resolve_active_llm"
        ) as mock_resolve:
            result = ask(request, "busca el cliente Acme")

        assert result["status"] == "PERMISSION_DENIED"
        mock_resolve.assert_not_called()

    @override_settings(**AI_READ_FLAGS_ON)
    def test_usuario_sin_tenant_profile_no_llama_al_proveedor(self):
        user_sin_perfil = User.objects.create_user(
            email="ai06_sin_perfil@test.local", password="testpass123"
        )
        request = _FakeRequest(user=user_sin_perfil, tenant=self.tenant)

        with patch(
            "apps.services.ai.orchestrator.form_assistant.resolve_active_llm"
        ) as mock_resolve:
            result = ask(request, "busca el cliente Acme")

        assert result["status"] == "PERMISSION_DENIED"
        mock_resolve.assert_not_called()

    @override_settings(**AI_READ_FLAGS_ON)
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "fake-key-for-test"})
    def test_llm_elige_tool_real_y_la_ejecuta(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)
        decision = {"tool": "buscar_cliente", "arguments": {"search": "Acme AI06"}}

        with _mock_llm_decision_text(decision):
            result = ask(request, "busca el cliente Acme AI06")

        assert result["status"] == "OK"
        assert result["tool_used"] == "buscar_cliente"
        assert len(result["data"]) == 1
        assert result["data"][0]["razon_social"] == "Acme AI06 S.A.S."

    @override_settings(**AI_READ_FLAGS_ON)
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "fake-key-for-test"})
    def test_llm_no_encuentra_tool_aplicable(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)
        decision = {
            "tool": None,
            "reason": "Esta pregunta no corresponde a ninguna herramienta disponible.",
        }

        with _mock_llm_decision_text(decision):
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

        with _mock_llm_decision_text(decision):
            result = ask(request, "haz algo que no deberias poder hacer")

        assert result["status"] == "NOT_FOUND"

    @override_settings(**AI_READ_FLAGS_ON)
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "fake-key-for-test"})
    def test_llm_responde_texto_no_json(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        with _mock_llm_decision_text("Lo siento, no puedo ayudarte con eso."):
            result = ask(request, "algo raro")

        assert result["status"] == "INTERNAL_ERROR"
