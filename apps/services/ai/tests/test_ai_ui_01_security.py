"""
SINTEL-AI-UI-01 (Fase 7/9): pruebas de seguridad especificas de la mision
de UI del Asistente IA, a traves de la capa HTTP completa (POST
/api/v1/ai/ask/), no solo de build_context()/run_tool() directo.

Complementa (no duplica) los tests ya existentes:
- test_ai_context.py::test_build_context_usuario_a_tenant_a_difiere_de_usuario_b_tenant_b
  ya prueba, con objetos fake, que build_context() nunca mezcla
  empresa_id/schema_name entre 2 contextos. Este archivo prueba una capa
  distinta y complementaria (nunca dos `Empresa` en el mismo schema --
  `Empresa` es singleton por schema, `UniqueConstraint(singleton_key)`,
  ver apps/tenant/empresa/models.py -- crear una segunda ahi haria fallar
  el test, no probaria aislamiento real):
  1. request HTTP real -> AIContext real -> tool real (buscar_cliente) ->
     DB real -> respuesta, dentro del propio schema (empresa_id siempre
     sale de context, nunca del payload -- probado con un empresa_id
     falso inyectado en `arguments`, ver mas abajo).
  2. aislamiento entre 2 SCHEMAS reales (el mecanismo estructural real de
     este proyecto, TEN-01), usando el patron canonico `tenant1`/`tenant2`
     (AGENTS.md 24.5, mismo conftest que ya usan apps/tenant/*/tests/).
- test_buscar_cliente_tool.py::test_write_tools_siguen_bloqueadas_aunque_el_flag_write_este_activo
  ya prueba que AI_WRITE_ENABLED=True no afecta una tool READ real. Este
  archivo agrega la prueba complementaria explicita que pide la Fase 7 de
  esta mision: una tool WRITE registrada (no una real del dominio, una
  fake minima solo para este test) sigue bloqueada por AUTO_APPROVED_KINDS
  aunque el flag este activo -- la garantia estructural de
  apps/services/ai/engine/ai_engine.py, no solo documentada.
"""
from unittest.mock import patch

import pytest
from django.db import connection
from django.core.management import call_command
from django.test import override_settings
from django_tenants.utils import schema_context
from rest_framework import status
from rest_framework.test import APIClient

from apps.public.tenants.models import Client as TenantClient
from apps.public.tenants.models import Domain, TenantMembership
from apps.services.ai.tools.base import BaseTool, ToolKind, ToolResult, ToolRisk
from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase

AI_READ_FLAGS_ON = {"AI_ENABLED": True, "AI_READ_ENABLED": True}
ASK_URL = "/api/v1/ai/ask/"


def _mock_anthropic_tool_decision(tool_name, arguments):
    import json
    from types import SimpleNamespace

    text = json.dumps({"tool": tool_name, "arguments": arguments})
    fake_message = SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])
    fake_client = SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: fake_message))
    return patch("anthropic.Anthropic", return_value=fake_client)


class AIUI01SameSchemaScopeHttpTests(SintelTenantTestCase):
    """`empresa_id` siempre sale de AIContext (derivado del TenantProfile
    real del usuario autenticado), nunca de lo que el LLM/el request
    proponga -- probado a traves del endpoint HTTP real."""

    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.create(
            razon_social="EMPRESA AI-UI-01 S.A.S.", nit="900111001", direccion="Calle A",
        )
        TenantProfile.objects.create(user=self.user, empresa=self.empresa)
        Cliente.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="900333001", razon_social="Cliente Real De Mi Empresa", regimen_tributario="ORDINARIO",
        )

    @override_settings(**AI_READ_FLAGS_ON)
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key-for-test"})
    def test_empresa_id_inyectado_en_arguments_es_ignorado_no_causa_fuga(self):
        """`BuscarClienteTool.run()` no acepta `empresa_id` como parametro
        (unicamente `search`/`limit`, ver clientes_tools.py) -- si el LLM
        alucina uno igual, AIEngine.run_tool() lo captura como excepcion
        generica (nunca un 500 con traceback, Fase 34) en vez de dejarlo
        colar como si fuera un scope valido."""
        decision_con_empresa_id_falso = {"search": "Cliente", "empresa_id": 999999}
        with _mock_anthropic_tool_decision("buscar_cliente", decision_con_empresa_id_falso):
            resp = self.api_client.post(ASK_URL, data={"message": "busca clientes"}, format="json")

        body = resp.json()
        assert body["status"] in ("INTERNAL_ERROR", "VALIDATION_ERROR")
        assert "traceback" not in str(body).lower()

    @override_settings(**AI_READ_FLAGS_ON)
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key-for-test"})
    def test_respuesta_nunca_expone_uuid_de_empresa_ni_schema(self):
        """Fase 3/8: nada tecnico (schema_name, traceback, path interno de
        Python) debe llegar crudo al payload que consume la UI -- excepto
        el uuid del propio registro de negocio (Cliente.uuid), que SI es
        un identificador de negocio legitimo (se usa para abrir el
        registro), no un detalle interno de infraestructura. Nota:
        `Empresa` (a diferencia de `Cliente`/`Cotizacion`/etc.) no declara
        campo `uuid` propio -- verificado leyendo el modelo, no asumido."""
        with _mock_anthropic_tool_decision("buscar_cliente", {"search": "Cliente Real De Mi Empresa"}):
            resp = self.api_client.post(ASK_URL, data={"message": "busca Cliente Real De Mi Empresa"}, format="json")

        body = resp.json()
        crudo = str(body)
        assert self.tenant.schema_name not in crudo
        assert "Traceback" not in crudo
        assert "apps.services.ai" not in crudo


def _crear_tenant_de_prueba(schema, empresa_nit, empresa_nombre):
    """Mismo patron canonico (AGENTS.md 24.5) que apps/tenant/ventas/tests/conftest.py
    tenant1/tenant2 -- reimplementado aqui (no pytest fixture) porque
    apps/services/ai/tests/ usa Django TestCase (SintelTenantTestCase), no
    el estilo pytest-fixture de los tests de apps/tenant/*/tests/."""
    tenant_obj = TenantClient.objects.filter(schema_name=schema).first()
    if not tenant_obj:
        with schema_context('public'):
            tenant_obj = TenantClient.objects.create(schema_name=schema, nombre=f'Tenant {schema}')
            Domain.objects.create(tenant=tenant_obj, domain=f'{schema}.sintel.net.co', is_primary=True)

    with connection.cursor() as cur:
        cur.execute(f'CREATE SCHEMA IF NOT EXISTS {schema}')
    call_command('migrate_schemas', '--tenant', '-s', schema, '--noinput', verbosity=0)

    with schema_context(schema):
        empresa = Empresa.objects.first()
        if not empresa:
            empresa = Empresa.objects.create(nit=empresa_nit, razon_social=empresa_nombre, direccion="Calle X")
    return tenant_obj, empresa


@pytest.mark.django_db
def test_cross_schema_usuario_de_tenant1_no_recupera_clientes_de_tenant2():
    """Fase 7 (Seguridad) de SINTEL-AI-UI-01, aislamiento real entre 2
    esquemas de PostgreSQL (TEN-01) -- no solo dentro de un mismo schema.
    'Usuario Tenant A puede consultar A, no puede recuperar informacion de
    B', probado a traves del endpoint HTTP real."""
    from django.contrib.auth import get_user_model

    User = get_user_model()

    tenant1, empresa1 = _crear_tenant_de_prueba('tenant1', '111', 'Tenant 1 SAS')
    tenant2, empresa2 = _crear_tenant_de_prueba('tenant2', '222', 'Tenant 2 SAS')

    with schema_context(tenant1.schema_name):
        Cliente.objects.get_or_create(
            empresa=empresa1, numero_documento="900444001", defaults={
                "tipo_persona": "JURIDICA", "tipo_documento": "NIT",
                "razon_social": "Cliente Solo De Tenant1", "regimen_tributario": "ORDINARIO",
            },
        )
    with schema_context(tenant2.schema_name):
        Cliente.objects.get_or_create(
            empresa=empresa2, numero_documento="900444002", defaults={
                "tipo_persona": "JURIDICA", "tipo_documento": "NIT",
                "razon_social": "Cliente Solo De Tenant2", "regimen_tributario": "ORDINARIO",
            },
        )

    connection.set_schema_to_public()
    user, _ = User.objects.get_or_create(
        email="ai-ui-01-cross-schema@sintel.local", defaults={"username": "ai_ui_01_cross_schema"},
    )
    TenantMembership.objects.get_or_create(client=tenant1, user=user, defaults={"rol": "ADMIN"})
    with schema_context(tenant1.schema_name):
        TenantProfile.objects.get_or_create(user=user, empresa=empresa1, defaults={"rol": "ADMIN"})

    client = APIClient(HTTP_HOST=f'{tenant1.schema_name}.sintel.net.co')
    client.force_authenticate(user=user)

    # Mismo motivo que tests/tenant/base_test.py::SintelTenantTestCase.setUp():
    # el test no pasa por el arranque WSGI real que resuelve TENANT_URLCONF
    # dinamicamente por host, asi que hay que forzarlo aqui tambien.
    from django.conf import settings as dj_settings
    from django.urls import clear_url_caches, set_urlconf

    with override_settings(ROOT_URLCONF=dj_settings.TENANT_URLCONF):
        clear_url_caches()
        set_urlconf(dj_settings.TENANT_URLCONF)
        with override_settings(**AI_READ_FLAGS_ON), patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key-for-test"}):
            with _mock_anthropic_tool_decision("buscar_cliente", {"search": "Cliente Solo"}):
                resp = client.post(ASK_URL, data={"message": "busca clientes 'Cliente Solo'"}, format="json")
        clear_url_caches()
        set_urlconf(None)

    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert body["status"] == "OK"
    nombres = [c["razon_social"] for c in body["data"]]
    assert "Cliente Solo De Tenant1" in nombres
    assert "Cliente Solo De Tenant2" not in nombres


class AIUI01WriteNeverAutoApprovedTests(SintelTenantTestCase):
    """Fase 7: WRITE nunca se auto-aprueba, ni siquiera con
    AI_WRITE_ENABLED=True -- probado registrando una tool WRITE minima
    (no una real del dominio) contra el AIEngine real, para no depender de
    que exista una tool WRITE de negocio (hoy no hay ninguna, ver
    AI_RELEASE_GATE.md AI-10)."""

    class _FakeWriteTool(BaseTool):
        name = "ai_ui_01_fake_write_tool"
        description = "Tool WRITE ficticia, solo para probar AUTO_APPROVED_KINDS."
        domain = "test"
        kind = ToolKind.WRITE
        risk = ToolRisk.SAFE_WRITE

        def run(self, context, **kwargs):  # pragma: no cover -- nunca deberia ejecutarse
            return ToolResult(status="OK", data={"escrito": True})

    def setUp(self):
        super().setUp()
        # build_context() exige un TenantProfile real (esquema tenant) --
        # SintelTenantTestCase.setUp() solo crea el TenantMembership
        # (esquema public). Sin esto, PERMISSION_DENIED llega antes por
        # falta de contexto, no por el bloqueo de WRITE que este test
        # quiere probar (hallazgo real de la primera corrida de este test).
        empresa = Empresa.objects.create(
            razon_social="EMPRESA WRITE-BLOCK AI-UI-01 S.A.S.", nit="900111099", direccion="Calle W",
        )
        TenantProfile.objects.create(user=self.user, empresa=empresa)

    @override_settings(AI_ENABLED=True, AI_READ_ENABLED=True, AI_WRITE_ENABLED=True)
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key-for-test"})
    def test_tool_write_registrada_sigue_bloqueada_con_flag_write_activo(self):
        """Hallazgo real de la primera corrida de este test: sin mockear
        ANTHROPIC_API_KEY, AnthropicProvider.complete() lanza RuntimeError
        (comportamiento correcto, sin key no hay como llamar al LLM) --
        form_assistant.py::ask() lo captura y devuelve INTERNAL_ERROR (500)
        ANTES de llegar siquiera a AIEngine.run_tool()/AUTO_APPROVED_KINDS,
        dando un falso 500 que no tiene nada que ver con el bloqueo de
        WRITE que este test quiere probar. Mismo mock que los otros 3
        tests de este archivo."""
        from apps.services.ai.tools.registry import _REGISTRY, register_tool

        tool = self._FakeWriteTool()
        assert tool.name not in _REGISTRY, "nombre de tool fake choca con una real -- cambiar el nombre"
        register_tool(tool)
        try:
            with _mock_anthropic_tool_decision(tool.name, {}):
                resp = self.api_client.post(ASK_URL, data={"message": "escribe algo"}, format="json")

            assert resp.status_code == status.HTTP_403_FORBIDDEN
            body = resp.json()
            assert body["status"] == "PERMISSION_DENIED"
            assert "aprobacion" in body["message"].lower()
        finally:
            del _REGISTRY[tool.name]
