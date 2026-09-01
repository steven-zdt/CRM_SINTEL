"""
Fase AI-02: tests de `ai_project_map`. La mayoria son unit tests puros
(sin DB) -- ProjectMapTool.run() no usa context.empresa_id (es una
tool de dominio `platform`, no de un tenant), asi que un AIContext
minimo de prueba basta; solo el ultimo test pasa por el AIEngine real
completo (con DB) para probar la integracion end-to-end una vez.
"""
import pytest
from django.test import override_settings

from apps.services.ai.context import AIContext
from apps.services.ai.tools.ekg_tools import ProjectMapTool

AI_FLAGS_ON = {"AI_ENABLED": True, "AI_READ_ENABLED": True}


def _fake_context() -> AIContext:
    return AIContext(
        user_id=1, empresa_id=1, schema_name="test", rol="ADMIN", alcance="EMPRESA",
    )


def test_question_invalida_es_validation_error():
    result = ProjectMapTool().run(_fake_context(), question="borrar_todo", name="Cliente")
    assert result.status == "VALIDATION_ERROR"


def test_name_vacio_es_validation_error():
    result = ProjectMapTool().run(_fake_context(), question="owner", name="")
    assert result.status == "VALIDATION_ERROR"


def test_owner_resuelve_modelo_real_via_registro_de_django():
    """AI-02.3: '¿quien posee X?' debe responder la app real, no 'AI Engine'.

    Nota (DOCUMENTATION_DRIFT real, encontrado al escribir este test):
    el app_label REAL de Django para `apps/tenant/clientes/` es
    'tenant_clientes' (ver apps/tenant/clientes/apps.py), no 'clientes'
    -- documentacion/arquitectura_general.md §2.2 lo documenta sin el
    prefijo 'tenant_' para varias apps, desactualizado. No corregido en
    esta pasada (fuera del alcance minimo de esta tool); se prueba el
    valor real, no el documentado."""
    result = ProjectMapTool().run(_fake_context(), question="owner", name="Cliente")

    assert result.status == "OK"
    assert result.data["source"] == "django_app_registry"
    apps_encontradas = {m["app_label"] for m in result.data["matches"]}
    assert "tenant_clientes" in apps_encontradas
    # Nunca debe "poseer" el propio AI Engine un modelo de negocio real.
    assert "ai" not in apps_encontradas
    # El nombre de snapshot EKG (carpeta) es distinto del app_label real.
    snapshot_names = {m["ekg_snapshot_name"] for m in result.data["matches"]}
    assert "clientes" in snapshot_names


def test_owner_modelo_inexistente_es_not_found():
    result = ProjectMapTool().run(_fake_context(), question="owner", name="ModeloQueNoExisteJamas")
    assert result.status == "NOT_FOUND"


def test_owner_es_case_insensitive():
    result = ProjectMapTool().run(_fake_context(), question="owner", name="cliente")
    assert result.status == "OK"


def test_rules_for_app_usa_snapshot_real_y_reporta_fecha():
    result = ProjectMapTool().run(_fake_context(), question="rules_for_app", name="clientes")

    assert result.status == "OK"
    assert result.data["source"] == "ekg_snapshot"
    assert result.data["app_name"] == "clientes"
    # Nunca oculta que es un snapshot -- siempre reporta cuando se genero.
    assert result.data["snapshot_generated_at"]
    assert isinstance(result.data["results"], list)


def test_rules_for_app_sin_snapshot_es_not_found():
    result = ProjectMapTool().run(
        _fake_context(), question="rules_for_app", name="app_que_nunca_tuvo_ekg_build",
    )
    assert result.status == "NOT_FOUND"


def test_fk_relationships_resuelve_app_por_nombre_de_modelo():
    """No requiere que el caller sepa a que app pertenece 'Cliente' de antemano."""
    result = ProjectMapTool().run(_fake_context(), question="fk_relationships", name="Cliente")

    assert result.status == "OK"
    assert result.data["app_name"] == "clientes"
    assert isinstance(result.data["results"], list)


from django.contrib.auth import get_user_model

from apps.services.ai.engine import run_tool
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase

User = get_user_model()


class _FakeRequest:
    def __init__(self, user, tenant=None):
        self.user = user
        self.tenant = tenant


class ProjectMapToolEngineIntegrationTests(SintelTenantTestCase):
    """Integracion end-to-end real: AIEngine.run_tool -> ProjectMapTool,
    con un AIContext construido de verdad desde un usuario/perfil real
    (mismo patron que test_buscar_cliente_tool.py)."""

    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.create(
            razon_social="EMPRESA EKG TEST S.A.S.", nit="900333444", direccion="Calle EKG",
        )
        self.user = User.objects.create_user(email="ekg_user@test.local", password="testpass123")
        TenantProfile.objects.create(user=self.user, empresa=self.empresa)

    @override_settings(**AI_FLAGS_ON)
    def test_ai_project_map_via_engine_real(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool("ai_project_map", request, question="owner", name="Cliente")

        assert result.status == "OK"
        assert "tenant_clientes" in {m["app_label"] for m in result.data["matches"]}

    def test_ai_project_map_bloqueado_si_ai_engine_deshabilitado(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool("ai_project_map", request, question="owner", name="Cliente")

        assert result.status == "PERMISSION_DENIED"
