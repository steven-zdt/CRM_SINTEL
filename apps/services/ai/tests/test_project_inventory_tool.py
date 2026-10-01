"""
LOOP 1 del MCP Control Plane (docs/mcp/ADR-MCP-001.md): tests de
`project_inventory`. Todos son unit tests puros (sin DB) -- la tool no
usa context.empresa_id (es de dominio `platform`, igual que
`ai_project_map`), censa el registro vivo de Django + filesystem real.
"""

from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.services.ai.context import AIContext
from apps.services.ai.engine import run_tool
from apps.services.ai.tools.platform_audit_tools import ProjectInventoryTool
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase

AI_FLAGS_ON = {"AI_ENABLED": True, "AI_READ_ENABLED": True}
User = get_user_model()


def _fake_context() -> AIContext:
    return AIContext(
        user_id=1,
        empresa_id=1,
        schema_name="test",
        rol="ADMIN",
        alcance="EMPRESA",
    )


def test_app_label_inexistente_es_not_found():
    result = ProjectInventoryTool().run(_fake_context(), app_label="app_que_nunca_existio")
    assert result.status == "NOT_FOUND"


def test_app_label_real_censa_esa_app_solamente():
    result = ProjectInventoryTool().run(_fake_context(), app_label="tenant_clientes")

    assert result.status == "OK"
    assert result.data["source"] == "django_app_registry"
    app = result.data["app"]
    assert app["app_label"] == "tenant_clientes"
    # Cliente es un modelo real de esa app -- confirma que get_models() se
    # ejecuto contra el registro vivo, no una lista inventada a mano.
    assert "Cliente" in app["models"]
    assert app["model_count"] >= 1
    # apps/tenant/clientes/ sigue el FSD documentado en CLAUDE.md.
    assert app["has_services_layer"] is True
    assert app["has_api"] is True
    assert app["has_tests"] is True


def test_sin_argumento_censa_todas_las_apps_y_reporta_ai_tools_y_mcp():
    result = ProjectInventoryTool().run(_fake_context())

    assert result.status == "OK"
    assert result.data["app_count"] > 1
    app_labels = {a["app_label"] for a in result.data["apps"]}
    assert "tenant_clientes" in app_labels
    # El catalogo de AI tools ya registradas debe incluir esta misma tool
    # y las demas -- nunca un catalogo vacio ni inventado aparte.
    tool_names = {t["name"] for t in result.data["ai_tools_registered"]}
    assert "project_inventory" in tool_names
    assert "buscar_cliente" in tool_names
    # MCP sigue bloqueado por AI-07 -- la tool nunca debe fingir tools MCP
    # que no existen.
    assert result.data["mcp_tools_registered"] == []
    assert "BLOCKED" in result.data["mcp_status"]


def test_has_signals_detecta_presencia_real_de_signals_py():
    """No afirma que exista una violacion de negocio -- solo que el
    archivo signals.py existe (senal a revisar manualmente, no un
    veredicto)."""
    result = ProjectInventoryTool().run(_fake_context())
    apps_by_label = {a["app_label"]: a for a in result.data["apps"]}
    # Cada app reporta el campo, sea True o False -- nunca ausente.
    for app in apps_by_label.values():
        assert "has_signals" in app
        assert isinstance(app["has_signals"], bool)


# -- Integracion real via AIEngine.run_tool() -- cierra el gap de negative
# tests que MCP_DOMAIN_MATRIX.md senalaba para el dominio `platform`
# (mismo patron que test_ai_project_map_tool.py::ProjectMapToolEngineIntegrationTests).


class _FakeRequest:
    def __init__(self, user, tenant=None):
        self.user = user
        self.tenant = tenant


class ProjectInventoryToolEngineIntegrationTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.create(
            razon_social="EMPRESA MCP TEST S.A.S.",
            nit="900333555",
            direccion="Calle MCP",
        )
        self.user = User.objects.create_user(email="mcp_user@test.local", password="testpass123")
        TenantProfile.objects.create(user=self.user, empresa=self.empresa)

    @override_settings(**AI_FLAGS_ON)
    def test_project_inventory_via_engine_real(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool("project_inventory", request, app_label="tenant_clientes")

        assert result.status == "OK"
        assert result.data["app"]["app_label"] == "tenant_clientes"

    @override_settings(AI_ENABLED=False)
    def test_project_inventory_bloqueado_si_ai_engine_deshabilitado(self):
        """Hallazgo real (2026-09-25): sin este override explicito, este
        test dependia silenciosamente de que AI_ENABLED sea False por
        default -- en un entorno con AI_ENABLED=true en .env (este mismo,
        usado para pruebas de humo manuales de la sesion), el test fallaba
        (ai_engine.tool_call devolvia status=OK real, no PERMISSION_DENIED).
        Mismo defecto encontrado en varios tests preexistentes del mismo
        directorio (ver docs/mcp/MCP_RELEASE_GATE.md) -- corregido aqui
        forzando el flag explicitamente, nunca confiando en el ambiente."""
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool("project_inventory", request)

        assert result.status == "PERMISSION_DENIED"

    @override_settings(AI_ENABLED=True, AI_READ_ENABLED=False)
    def test_project_inventory_bloqueado_si_solo_ai_enabled_sin_read_enabled(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool("project_inventory", request)

        assert result.status == "PERMISSION_DENIED"
