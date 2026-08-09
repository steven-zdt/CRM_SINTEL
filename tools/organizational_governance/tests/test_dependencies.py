from tools.organizational_governance import dependencies as deps


def _write(tmp_path, app, rel_path, content):
    path = tmp_path / app / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_classify_bridge_import(tmp_path, monkeypatch):
    monkeypatch.setattr(deps, "TENANT_APPS_DIR", tmp_path)
    monkeypatch.setattr("tools.organizational_governance.extract.TENANT_APPS_DIR", tmp_path)
    _write(tmp_path, "a", "services/business_service.py", "")
    _write(tmp_path, "b", "services/business_service.py",
           "def foo():\n    from apps.tenant.a.services.selectors import ClienteBridge\n    return ClienteBridge\n")
    for app in ("a", "b"):
        (tmp_path / app / "models.py").write_text("", encoding="utf-8")
    edges = deps.discover_dependency_edges()
    bridge_edges = [e for e in edges if e.classification == deps.BRIDGE]
    assert any(e.source_app == "b" and e.target_app == "a" for e in bridge_edges)


def test_classify_forbidden_when_no_empresa_id_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(deps, "TENANT_APPS_DIR", tmp_path)
    monkeypatch.setattr("tools.organizational_governance.extract.TENANT_APPS_DIR", tmp_path)
    _write(tmp_path, "a", "models.py", "")
    _write(tmp_path, "b", "services/business_service.py",
           "def foo():\n    from apps.tenant.a.services.business_service import ABusinessService\n    return ABusinessService.crear(data)\n")
    for app in ("a", "b"):
        (tmp_path / app / "models.py").write_text("", encoding="utf-8")
    edges = deps.discover_dependency_edges()
    matching = [e for e in edges if e.source_app == "b" and e.target_app == "a"]
    assert matching and matching[0].classification == deps.FORBIDDEN


def test_classify_push_controlled_when_empresa_id_present(tmp_path, monkeypatch):
    monkeypatch.setattr(deps, "TENANT_APPS_DIR", tmp_path)
    monkeypatch.setattr("tools.organizational_governance.extract.TENANT_APPS_DIR", tmp_path)
    _write(tmp_path, "a", "models.py", "")
    _write(tmp_path, "b", "services/business_service.py",
           "def foo(empresa_id):\n    from apps.tenant.a.services.business_service import ABusinessService\n"
           "    return ABusinessService.crear(empresa_id=empresa_id)\n")
    for app in ("a", "b"):
        (tmp_path / app / "models.py").write_text("", encoding="utf-8")
    edges = deps.discover_dependency_edges()
    matching = [e for e in edges if e.source_app == "b" and e.target_app == "a"]
    assert matching and matching[0].classification == deps.PUSH_CONTROLLED


def test_known_interapp_api_symbol_classified_as_pull(tmp_path, monkeypatch):
    monkeypatch.setattr(deps, "TENANT_APPS_DIR", tmp_path)
    monkeypatch.setattr("tools.organizational_governance.extract.TENANT_APPS_DIR", tmp_path)
    _write(tmp_path, "a", "models.py", "")
    _write(tmp_path, "b", "services/business_service.py",
           "def foo():\n    from apps.tenant.a.services.business_service import FacturaInterAppAPI\n"
           "    return FacturaInterAppAPI.get_by_id(1)\n")
    for app in ("a", "b"):
        (tmp_path / app / "models.py").write_text("", encoding="utf-8")
    edges = deps.discover_dependency_edges()
    matching = [e for e in edges if e.source_app == "b" and e.target_app == "a"]
    assert matching and matching[0].classification == deps.PULL


def test_detect_cycles_finds_two_node_cycle():
    edges = [
        deps.DependencyEdge("a", "b", "a.py", 1, "X", deps.PUSH_CONTROLLED, "e"),
        deps.DependencyEdge("b", "a", "b.py", 1, "Y", deps.PUSH_CONTROLLED, "e"),
    ]
    cycles = deps.detect_cycles(edges)
    assert any(set(c) == {"a", "b"} for c in cycles)


def test_detect_cycles_ignores_allowed_edges():
    edges = [deps.DependencyEdge("a", "core", "a.py", 1, "X", deps.ALLOWED, "e")]
    assert deps.detect_cycles(edges) == []
