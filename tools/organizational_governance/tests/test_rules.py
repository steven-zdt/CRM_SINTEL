"""
F14.23 (prueba de corrupcion intencional) y F14.24 (prueba de falsos
positivos) del prompt maestro: cada regla debe demostrarse contra un caso
sintetico MALO (debe producir el finding) y un caso BUENO (no debe producir
nada) - no basta con correrla contra el estado ya limpio del repositorio
real, que solo prueba ausencia de falsos positivos, no capacidad real de
deteccion.
"""
import pytest

from tools.organizational_governance import rules
from tools.organizational_governance.graph import Edge, Graph, Node
from tools.organizational_governance.schema import (
    NODE_APP,
    NODE_MODEL,
    NODE_PERMISSION,
    NODE_VIEWSET,
    REL_OWNS,
    REL_USES_PERMISSION,
    SCOPE_NONE,
)


# --- ARCH-002 -----------------------------------------------------------

def test_arch_002_fires_on_model_without_recognized_base():
    graph = Graph()
    graph.add_node(Node(NODE_MODEL, "demo.Huerfano", {"class_name": "Huerfano", "bases": ["Model"], "scope": SCOPE_NONE}))

    findings = rules._detect_arch_001_002(graph)

    assert any(f.rule_id == "ARCH-002" and f.component == "demo.Huerfano" for f in findings)


def test_arch_002_does_not_fire_on_sede_aware_model_consumer():
    graph = Graph()
    graph.add_node(
        Node(NODE_MODEL, "compras.OrdenCompra", {"class_name": "OrdenCompra", "bases": ["SedeAwareModel"], "scope": "sede_scoped"})
    )

    findings = rules._detect_arch_001_002(graph)

    assert findings == []


def test_arch_002_does_not_fire_on_the_base_class_itself():
    graph = Graph()
    graph.add_node(
        Node(NODE_MODEL, "core.SintelTenantBaseModel", {"class_name": "SintelTenantBaseModel", "bases": ["Model"], "scope": SCOPE_NONE})
    )

    findings = rules._detect_arch_001_002(graph)

    assert findings == [], "la raiz del arbol de herencia no debe marcarse como violacion de si misma"


# --- SEC-001 (DEBUG bypass) ----------------------------------------------

def test_sec_001_fires_on_debug_bypass(tmp_path, monkeypatch):
    monkeypatch.setattr(rules, "PROJECT_ROOT", tmp_path)
    bad_dir = tmp_path / "apps" / "tenant" / "demo" / "api"
    bad_dir.mkdir(parents=True)
    (bad_dir / "permissions.py").write_text(
        "from django.conf import settings\n\n"
        "class HasSomething:\n"
        "    def has_permission(self, request, view):\n"
        "        if settings.DEBUG:\n"
        "            return True\n"
        "        return False\n",
        encoding="utf-8",
    )
    graph = Graph()

    findings = rules._detect_sec_001_debug_bypass(graph)

    assert any(f.rule_id == "SEC-001" for f in findings)


def test_sec_001_does_not_fire_on_clean_permissions(tmp_path, monkeypatch):
    monkeypatch.setattr(rules, "PROJECT_ROOT", tmp_path)
    good_dir = tmp_path / "apps" / "tenant" / "demo" / "api"
    good_dir.mkdir(parents=True)
    (good_dir / "permissions.py").write_text(
        "class HasSomething:\n"
        "    def has_permission(self, request, view):\n"
        "        return request.user.is_authenticated\n",
        encoding="utf-8",
    )
    graph = Graph()

    findings = rules._detect_sec_001_debug_bypass(graph)

    assert findings == []


# --- ORG-004 (filter_by_scope estricto sin hardening) ---------------------

def test_org_004_fires_on_real_ast_call(tmp_path, monkeypatch):
    monkeypatch.setattr(rules, "TENANT_APPS_DIR", tmp_path)
    monkeypatch.setattr(rules, "PROJECT_ROOT", tmp_path)
    graph = Graph()
    graph.add_node(Node(NODE_MODEL, "demo.Cosa", {"scope": SCOPE_NONE}))
    services_dir = tmp_path / "demo" / "services"
    services_dir.mkdir(parents=True)
    (services_dir / "selectors.py").write_text(
        "from tools.organizational_governance.x import filter_by_scope\n\n"
        "def get_list(empresa_id, sede_ids=None):\n"
        "    return filter_by_scope(Model.objects.all(), empresa_id, sede_ids=sede_ids)\n",
        encoding="utf-8",
    )

    findings = rules._detect_org_004_strict_filter_without_hardening(graph)

    assert any(f.rule_id == "ORG-004" and f.component == "demo.selectors" for f in findings)


def test_org_004_does_not_fire_on_docstring_mention_regression_guard(tmp_path, monkeypatch):
    """Regresion directa del falso positivo real encontrado durante el
    desarrollo de esta regla (facturas/services/selectors.py menciona
    'filter_by_scope()' en un docstring explicando que NO lo usa)."""
    monkeypatch.setattr(rules, "TENANT_APPS_DIR", tmp_path)
    graph = Graph()
    graph.add_node(Node(NODE_MODEL, "demo.Cosa", {"scope": SCOPE_NONE}))
    services_dir = tmp_path / "demo" / "services"
    services_dir.mkdir(parents=True)
    (services_dir / "selectors.py").write_text(
        '"""\n'
        "usa filter_by_scope_null_safe()\n"
        "(no filter_by_scope()): el 100%% tiene sede NULL\n"
        '"""\n'
        "from tools.organizational_governance.x import filter_by_scope_null_safe\n\n"
        "def get_list(empresa_id, sede_ids=None):\n"
        "    return filter_by_scope_null_safe(Model.objects.all(), empresa_id, sede_ids=sede_ids)\n",
        encoding="utf-8",
    )

    findings = rules._detect_org_004_strict_filter_without_hardening(graph)

    assert findings == []


def test_org_004_does_not_fire_for_sede_aware_model_apps(tmp_path, monkeypatch):
    monkeypatch.setattr(rules, "TENANT_APPS_DIR", tmp_path)
    graph = Graph()
    graph.add_node(Node(NODE_MODEL, "compras.OrdenCompra", {"scope": "sede_scoped"}))
    services_dir = tmp_path / "compras" / "services"
    services_dir.mkdir(parents=True)
    (services_dir / "selectors.py").write_text(
        "def get_list(empresa_id, sede_ids=None):\n"
        "    return filter_by_scope(Model.objects.all(), empresa_id, sede_ids=sede_ids)\n",
        encoding="utf-8",
    )

    findings = rules._detect_org_004_strict_filter_without_hardening(graph)

    assert findings == [], "compras SI tiene SedeAwareModel (sede NOT NULL) - filter_by_scope() estricto es correcto ahi"


# --- SEC-003 (bypass de permiso de objeto) --------------------------------

def _graph_with_scope_viewset() -> Graph:
    graph = Graph()
    graph.add_node(Node(NODE_APP, "demo", {}))
    graph.add_node(Node(NODE_VIEWSET, "demo.DemoViewSet", {}))
    graph.add_node(Node(NODE_PERMISSION, "HasOrganizationalScope", {}))
    graph.add_edge(Edge(REL_OWNS, (NODE_APP, "demo"), (NODE_VIEWSET, "demo.DemoViewSet")))
    graph.add_edge(Edge(REL_USES_PERMISSION, (NODE_VIEWSET, "demo.DemoViewSet"), (NODE_PERMISSION, "HasOrganizationalScope")))
    return graph


def test_sec_003_fires_on_get_object_or_404_without_check(tmp_path, monkeypatch):
    monkeypatch.setattr(rules, "TENANT_APPS_DIR", tmp_path)
    monkeypatch.setattr(rules, "PROJECT_ROOT", tmp_path)
    api_dir = tmp_path / "demo" / "api"
    api_dir.mkdir(parents=True)
    (api_dir / "viewsets.py").write_text(
        "def render_offcanvas_detalle(self, request):\n"
        "    instance = get_object_or_404(Model, uuid=request.GET.get('uuid'))\n"
        "    return Response({'instance': instance})\n",
        encoding="utf-8",
    )

    findings = rules._detect_sec_003_object_permission_bypass(_graph_with_scope_viewset())

    assert any(f.rule_id == "SEC-003" for f in findings)


def test_sec_003_does_not_fire_when_check_object_permissions_present(tmp_path, monkeypatch):
    monkeypatch.setattr(rules, "TENANT_APPS_DIR", tmp_path)
    api_dir = tmp_path / "demo" / "api"
    api_dir.mkdir(parents=True)
    (api_dir / "viewsets.py").write_text(
        "def render_offcanvas_detalle(self, request):\n"
        "    instance = get_object_or_404(Model, uuid=request.GET.get('uuid'))\n"
        "    self.check_object_permissions(request, instance)\n"
        "    return Response({'instance': instance})\n",
        encoding="utf-8",
    )

    findings = rules._detect_sec_003_object_permission_bypass(_graph_with_scope_viewset())

    assert findings == []


# --- Ejecucion real contra el repositorio (regresion, no sintetico) -------

def test_run_all_rules_against_real_repo_is_clean():
    """No sintetico a proposito: confirma que, tras los fixes de FASE 7 ya
    commiteados, el repositorio real produce 0 findings en este subconjunto
    de reglas - es la evidencia real citada en F13_F14_FINAL_REPORT.md."""
    from tools.organizational_governance.build import build_organizational_graph

    graph = build_organizational_graph()
    findings = rules.run_all_rules(graph)

    assert findings == [], f"se esperaba 0 findings en el repo real, se encontraron: {findings}"
