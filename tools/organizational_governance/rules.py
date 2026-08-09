"""
Motor de reglas (F14.0-F14.12) - Rule/Finding tipados, severidad mapeada a
PASS/WARN/FAIL, y un subconjunto REAL (no fabricado) de reglas de las 8
categorias que pide el prompt maestro. Cada regla se valido contra un caso
conocido de esta misma consolidacion (ver documentacion/F13_F14_FINAL_REPORT.md
"Prueba de corrupcion intencional"/"Prueba de falsos positivos", F14.23/F14.24)
antes de darla por buena - no se implemento ninguna regla que no se pudiera
verificar contra un caso real conocido.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from tools.organizational_governance.extract import PROJECT_ROOT, TENANT_APPS_DIR
from tools.organizational_governance.graph import Graph
from tools.organizational_governance.schema import SCOPE_NONE

CRITICAL = "CRITICAL"
HIGH = "HIGH"
MEDIUM = "MEDIUM"
LOW = "LOW"
INFO = "INFO"

_SEVERITY_TO_STATUS = {
    CRITICAL: "FAIL",
    HIGH: "FAIL",
    MEDIUM: "WARN",
    LOW: "WARN",
    INFO: "PASS",
}

CATEGORY_ARCHITECTURE = "ARCHITECTURE"
CATEGORY_SECURITY = "SECURITY"
CATEGORY_MULTI_TENANT = "MULTI_TENANT"
CATEGORY_ORGANIZATIONAL = "ORGANIZATIONAL"
CATEGORY_INTEGRATIONS = "INTEGRATIONS"
CATEGORY_SERVICE_LAYER = "SERVICE_LAYER"
CATEGORY_DOCUMENTATION = "DOCUMENTATION"
CATEGORY_TEST_COVERAGE = "TEST_COVERAGE"


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    component: str
    file: str
    line: int | None
    symbol: str
    evidence: str
    expected: str
    actual: str
    recommendation: str

    @property
    def status(self) -> str:
        return _SEVERITY_TO_STATUS[self.severity]


@dataclass(frozen=True)
class Rule:
    rule_id: str
    name: str
    severity: str
    category: str
    description: str
    detector: Callable[[Graph], list[Finding]]


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


# ---------------------------------------------------------------------------
# ARCH-001 / ARCH-002 - base de modelo tenant
# ---------------------------------------------------------------------------

def _detect_arch_001_002(graph: Graph) -> list[Finding]:
    findings = []
    tenant_base_like = {"SintelTenantBaseModel", "SedeAwareModel", "TimeStampedModel"}
    for model in graph.nodes_by_label("Model"):
        bases = set(model.props.get("bases", []))
        if bases & tenant_base_like:
            continue
        # SintelTenantBaseModel es la RAIZ del arbol - hereda bare
        # models.Model por definicion (es su unico punto de contacto real
        # con Django), no un consumidor que deberia heredarse a si mismo.
        if model.props.get("class_name") == "SintelTenantBaseModel":
            continue
        # No hereda ninguna base tenant conocida - candidato real a ARCH-002
        # (herencia directa de models.Model, o de una base que este extractor
        # no reconoce - se reporta como FAIL con evidencia, no se asume).
        findings.append(
            Finding(
                rule_id="ARCH-002",
                severity=HIGH,
                component=model.qualified_id,
                file=f"apps/tenant/{model.qualified_id.split('.')[0]}/models.py",
                line=None,
                symbol=model.props.get("class_name", model.qualified_id),
                evidence=f"bases detectadas: {sorted(bases) or ['(ninguna reconocida)']}",
                expected="hereda SintelTenantBaseModel (directo o via SedeAwareModel/TimeStampedModel)",
                actual=f"bases={sorted(bases)}",
                recommendation="Heredar de SintelTenantBaseModel en vez de models.Model directo (AGENTS.md, tabla de prohibiciones).",
            )
        )
    return findings


# ---------------------------------------------------------------------------
# SEC-001 - bypass de DEBUG en autorizacion
# ---------------------------------------------------------------------------

_DEBUG_BYPASS_RE = re.compile(r"if\s+settings\.DEBUG\s*:\s*\n\s*return\s+True")


def _detect_sec_001_debug_bypass(graph: Graph) -> list[Finding]:
    """[F13.6] Verificado limpio en la Remediacion Auditoria Enterprise
    2026-08-06 (C1) - esta regla confirma que sigue limpio, no asume."""
    findings = []
    for path in sorted((PROJECT_ROOT / "apps").rglob("permissions.py")):
        if "/venv/" in path.as_posix() or "\\venv\\" in str(path):
            continue
        text = _read(path)
        if _DEBUG_BYPASS_RE.search(text):
            rel = path.relative_to(PROJECT_ROOT).as_posix()
            findings.append(
                Finding(
                    rule_id="SEC-001",
                    severity=CRITICAL,
                    component=rel,
                    file=rel,
                    line=None,
                    symbol="settings.DEBUG bypass",
                    evidence="patron 'if settings.DEBUG: return True' encontrado",
                    expected="ninguna verificacion de permiso condicionada a DEBUG (AGENTS.md, incidente C1 2026-08-06)",
                    actual="bypass encontrado",
                    recommendation="Eliminar el bypass; DEBUG nunca debe afectar autorizacion.",
                )
            )
    return findings


# ---------------------------------------------------------------------------
# SEC-002 - PermissionDenied convertido en 500 (el bug real de FASE 7)
# ---------------------------------------------------------------------------

def _detect_sec_002_permission_denied_to_500(graph: Graph) -> list[Finding]:
    """Reconstruye la regla que habria detectado el bug real de FASE 7
    (handle_service_error() sin caso para PermissionDenied) - se valida
    contra el estado YA CORREGIDO: debe dar 0 findings hoy (ver
    documentacion/FASE7_AISLAMIENTO_ORGANIZACIONAL.md)."""
    findings = []
    mixins_path = TENANT_APPS_DIR.parent / "api" / "mixins.py"
    if not mixins_path.exists():
        return findings
    text = _read(mixins_path)
    handles_permission_denied = "PermissionDenied" in text and "HTTP_403_FORBIDDEN" in text
    if not handles_permission_denied:
        rel = mixins_path.relative_to(PROJECT_ROOT).as_posix()
        findings.append(
            Finding(
                rule_id="SEC-002",
                severity=HIGH,
                component="apps.tenant.api.mixins.BaseServiceMixin.handle_service_error",
                file=rel,
                line=None,
                symbol="handle_service_error",
                evidence="No se encontro manejo explicito de PermissionDenied -> 403",
                expected="PermissionDenied se mapea a HTTP 403, no al generico 500",
                actual="sin caso explicito para PermissionDenied",
                recommendation="Agregar isinstance(exc, DRFPermissionDenied) -> 403 (ver fix real en commit c63b35e/34fc020).",
            )
        )
    return findings


# ---------------------------------------------------------------------------
# SEC-003 - get_object_or_404 sin check_object_permissions en ViewSets con
# HasOrganizationalScope (el bug HTMX real de FASE 7)
# ---------------------------------------------------------------------------

def _detect_sec_003_object_permission_bypass(graph: Graph) -> list[Finding]:
    findings = []
    viewset_qids_with_scope_perm = set(graph.viewsets_with_has_organizational_scope())
    apps_with_scope_perm = {qid.split(".")[0] for qid in viewset_qids_with_scope_perm}
    for app_label in sorted(apps_with_scope_perm):
        viewsets_file = TENANT_APPS_DIR / app_label / "api" / "viewsets.py"
        text = _read(viewsets_file)
        if not text:
            continue
        try:
            tree = ast.parse(text, filename=str(viewsets_file))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            segment = ast.get_source_segment(text, node) or ""
            if "get_object_or_404(" in segment and "check_object_permissions(" not in segment:
                findings.append(
                    Finding(
                        rule_id="SEC-003",
                        severity=HIGH,
                        component=f"{app_label}.{node.name}",
                        file=str(viewsets_file.relative_to(PROJECT_ROOT)),
                        line=node.lineno,
                        symbol=node.name,
                        evidence="get_object_or_404() sin self.check_object_permissions() en una app con HasOrganizationalScope",
                        expected="self.get_object() o self.check_object_permissions(request, instance) explicito",
                        actual="get_object_or_404() bypasea el permiso de objeto",
                        recommendation="Agregar self.check_object_permissions(request, instance) tras get_object_or_404().",
                    )
                )
    return findings


# ---------------------------------------------------------------------------
# ORG-001 - OrganizationalContext y OrganizationalScope deben permanecer
# separados (nunca uno subclase del otro)
# ---------------------------------------------------------------------------

def _detect_org_001_context_scope_fused(graph: Graph) -> list[Finding]:
    findings = []
    context_file = TENANT_APPS_DIR.parent / "core" / "services" / "organizational_context.py"
    scope_file = TENANT_APPS_DIR.parent / "core" / "services" / "organizational_scope.py"
    for path, other_class in ((context_file, "OrganizationalScope"), (scope_file, "OrganizationalContext")):
        text = _read(path)
        if not text:
            continue
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and other_class in [
                b.id for b in node.bases if isinstance(b, ast.Name)
            ]:
                findings.append(
                    Finding(
                        rule_id="ORG-001",
                        severity=CRITICAL,
                        component=node.name,
                        file=str(path.relative_to(PROJECT_ROOT)),
                        line=node.lineno,
                        symbol=node.name,
                        evidence=f"{node.name} hereda de {other_class}",
                        expected="OrganizationalContext y OrganizationalScope permanecen conceptos independientes (ADR-005)",
                        actual=f"{node.name}({other_class})",
                        recommendation="Revertir la fusion - son conceptos deliberadamente separados.",
                    )
                )
    return findings


# ---------------------------------------------------------------------------
# ORG-002 - segunda fuente de verdad para alcance (TenantProfile.alcance)
# ---------------------------------------------------------------------------

def _detect_org_002_second_scope_source(graph: Graph) -> list[Finding]:
    """Busca clases con 'alcance'/'scope' como campo propio FUERA de
    TenantProfile en apps tenant - candidato a segunda fuente de verdad."""
    findings = []
    for model in graph.nodes_by_label("Model"):
        app_label, class_name = model.qualified_id.split(".", 1)
        if class_name == "TenantProfile":
            continue
        models_file = TENANT_APPS_DIR / app_label / "models.py"
        text = _read(models_file)
        # Busqueda acotada al bloque de la clase (evita falsos positivos de
        # otras clases del mismo archivo con un campo 'alcance' de negocio
        # no relacionado, ej. "alcance del proyecto" en proyectos - se
        # reporta como INFO/WARN, no CRITICAL, precisamente por esa
        # ambiguedad real).
        pattern = rf"class {re.escape(class_name)}\([^)]*\):.*?(?=\nclass |\Z)"
        match = re.search(pattern, text, re.DOTALL)
        if match and re.search(r"\balcance\s*=\s*models\.", match.group(0)):
            findings.append(
                Finding(
                    rule_id="ORG-002",
                    severity=MEDIUM,
                    component=model.qualified_id,
                    file=str((TENANT_APPS_DIR / app_label / "models.py").relative_to(PROJECT_ROOT)),
                    line=None,
                    symbol=class_name,
                    evidence="campo 'alcance' encontrado fuera de TenantProfile",
                    expected="TenantProfile.alcance es la unica fuente de verdad de alcance organizacional (ADR-003)",
                    actual=f"{class_name}.alcance existe",
                    recommendation="Verificar manualmente si es el mismo concepto organizacional o un campo de negocio homonimo no relacionado.",
                )
            )
    return findings


# ---------------------------------------------------------------------------
# ORG-004 - filter_by_scope() estricto en una app sin SedeAwareModel/NOT NULL
# ---------------------------------------------------------------------------

def _detect_org_004_strict_filter_without_hardening(graph: Graph) -> list[Finding]:
    """[Corregido tras falso positivo real durante el smoke-test: la
    version original usaba texto crudo y coincidia con 'filter_by_scope('
    dentro de un DOCSTRING de facturas/services/selectors.py que dice "usa
    filter_by_scope_null_safe() (no filter_by_scope())" - prosa explicando
    lo contrario de lo que detecta. Reescrito con AST (ast.Call real, nunca
    ve comentarios/docstrings como codigo) - ver F14.24 del prompt maestro,
    "precision > cantidad de findings"."""
    from tools.organizational_governance.build import SEDE_AWARE_MODEL_APPS

    findings = []
    for app_label in sorted({m.qualified_id.split(".")[0] for m in graph.nodes_by_label("Model")}):
        if app_label in SEDE_AWARE_MODEL_APPS:
            continue
        selectors_file = TENANT_APPS_DIR / app_label / "services" / "selectors.py"
        text = _read(selectors_file)
        if not text:
            continue
        try:
            tree = ast.parse(text, filename=str(selectors_file))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
                continue
            if node.func.id != "filter_by_scope":
                continue
            findings.append(
                Finding(
                    rule_id="ORG-004",
                    severity=HIGH,
                    component=f"{app_label}.selectors",
                    file=str(selectors_file.relative_to(PROJECT_ROOT)),
                    line=node.lineno,
                    symbol="filter_by_scope",
                    evidence=f"llamada real (AST) a filter_by_scope() en '{app_label}', que no esta en SEDE_AWARE_MODEL_APPS (sede no confirmada NOT NULL)",
                    expected="filter_by_scope_null_safe() para apps sin sede endurecida (ver OSF_TECHNICAL_AUDIT.md §4)",
                    actual="filter_by_scope() estricto",
                    recommendation="Usar filter_by_scope_null_safe() o confirmar que el campo sede de esta app SI es NOT NULL.",
                )
            )
    return findings


# ---------------------------------------------------------------------------
# TEST-001 - app usa OrganizationalScope/Context sin ningun test de adopcion
# ---------------------------------------------------------------------------

def _detect_test_001_scope_usage_without_tests(graph: Graph) -> list[Finding]:
    from tools.organizational_governance.schema import REL_USES_CONTEXT, REL_USES_SCOPE

    findings = []
    for app in graph.nodes_by_label("App"):
        uses_ctx = bool(graph.edges_from(app.key, REL_USES_CONTEXT))
        uses_scope = bool(graph.edges_from(app.key, REL_USES_SCOPE))
        if not (uses_ctx or uses_scope):
            continue
        tests_dir = TENANT_APPS_DIR / app.qualified_id / "tests"
        has_adoption_test = (tests_dir / "test_organizational_context_adoption.py").exists()
        has_scope_test = any(tests_dir.glob("test_scope_*.py")) if tests_dir.exists() else False
        if not has_adoption_test and not has_scope_test:
            findings.append(
                Finding(
                    rule_id="TEST-001",
                    severity=MEDIUM,
                    component=app.qualified_id,
                    file=f"apps/tenant/{app.qualified_id}/tests/",
                    line=None,
                    symbol=app.qualified_id,
                    evidence="app usa OrganizationalContext/Scope pero no tiene test_organizational_context_adoption.py ni test_scope_*.py",
                    expected="cobertura minima de adopcion por app (patron ya establecido en las 13+ apps que si la tienen)",
                    actual="sin test de adopcion encontrado",
                    recommendation="Agregar test_organizational_context_adoption.py siguiendo el patron de las demas apps.",
                )
            )
    return findings


ALL_RULES: tuple[Rule, ...] = (
    Rule("ARCH-002", "Modelo tenant sin base reconocida", HIGH, CATEGORY_ARCHITECTURE,
         "Todo modelo tenant debe heredar SintelTenantBaseModel (directo o via SedeAwareModel/TimeStampedModel).",
         _detect_arch_001_002),
    Rule("SEC-001", "Bypass de DEBUG en autorizacion", CRITICAL, CATEGORY_SECURITY,
         "Ninguna verificacion de permiso puede condicionarse a settings.DEBUG.",
         _detect_sec_001_debug_bypass),
    Rule("SEC-002", "PermissionDenied convertido en 500", HIGH, CATEGORY_SECURITY,
         "handle_service_error() debe mapear PermissionDenied a 403, no al generico 500.",
         _detect_sec_002_permission_denied_to_500),
    Rule("SEC-003", "Bypass de permiso de objeto via get_object_or_404", HIGH, CATEGORY_SECURITY,
         "Toda accion que resuelva un objeto en una app con HasOrganizationalScope debe llamar check_object_permissions().",
         _detect_sec_003_object_permission_bypass),
    Rule("ORG-001", "OrganizationalContext/Scope fusionados", CRITICAL, CATEGORY_ORGANIZATIONAL,
         "OrganizationalContext y OrganizationalScope deben permanecer conceptos independientes (ADR-005).",
         _detect_org_001_context_scope_fused),
    Rule("ORG-002", "Segunda fuente de verdad de alcance", MEDIUM, CATEGORY_ORGANIZATIONAL,
         "TenantProfile.alcance es la unica fuente de verdad de alcance organizacional (ADR-003).",
         _detect_org_002_second_scope_source),
    Rule("ORG-004", "filter_by_scope estricto sin hardening", HIGH, CATEGORY_ORGANIZATIONAL,
         "filter_by_scope() estricto solo es seguro en apps con SedeAwareModel/sede NOT NULL (ADR-005).",
         _detect_org_004_strict_filter_without_hardening),
    Rule("TEST-001", "Uso de scope sin test de adopcion", MEDIUM, CATEGORY_TEST_COVERAGE,
         "Toda app que consuma OrganizationalContext/Scope debe tener al menos un test de adopcion.",
         _detect_test_001_scope_usage_without_tests),
)


def run_all_rules(graph: Graph, rules: Iterable[Rule] = ALL_RULES) -> list[Finding]:
    findings: list[Finding] = []
    for rule in rules:
        findings.extend(rule.detector(graph))
    return findings
