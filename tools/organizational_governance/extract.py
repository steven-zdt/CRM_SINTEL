"""
Extractores reales (F13.3-F13.9) - AST para Python (modelos, ViewSets,
permisos), regex acotado para ADRs (front-matter simple, no vale la pena un
parser Markdown completo para 5 campos), y `git log` real via subprocess
para el historial (F13.9).

Alcance deliberadamente escrito, no oculto (ver documentacion/F13_F14_FINAL_REPORT.md):
- Resuelve herencia DIRECTA de clases (ast, sin resolver imports cross-modulo
  como hace tools/ekg/extract_python.py con su _build_import_map()) - para
  Model/ViewSet de este proyecto la base real casi siempre esta en el mismo
  archivo o se importa con el nombre simple ya usado en el codigo (patron
  verificado: SintelTenantBaseModel, SedeAwareModel, BaseTenantViewSet se
  importan siempre con su nombre simple, nunca calificados por modulo) -
  documentado como limitacion conocida, no oculta.
- Deteccion de OrganizationalContext/OrganizationalScope/HasOrganizationalScope
  por presencia de substring en el codigo fuente de la clase (via
  ast.get_source_segment), no por resolucion de symbol table completa -
  suficiente para las preguntas que F13.14 pide responder, mucho mas barato
  que un resolvedor de tipos real.
"""
from __future__ import annotations

import ast
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TENANT_APPS_DIR = PROJECT_ROOT / "apps" / "tenant"
DOCS_DIR = PROJECT_ROOT / "docs"

TENANT_BASE_NAMES = {"SintelTenantBaseModel", "SedeAwareModel", "TimeStampedModel"}
ORG_CONTEXT_MARKERS = ("OrganizationalContext", "OrganizationalContextMixin")
ORG_SCOPE_MARKERS = ("OrganizationalScope", "filter_by_scope")


@dataclass(frozen=True)
class ModelInfo:
    app_label: str
    class_name: str
    qualified_id: str
    bases: tuple[str, ...]
    is_tenant_model: bool
    has_empresa: bool  # siempre True para SintelTenantBaseModel (heredado); False si no aplica
    has_sede: bool
    has_area: bool
    inherits_sede_aware_model: bool


@dataclass(frozen=True)
class ViewSetInfo:
    app_label: str
    class_name: str
    qualified_id: str
    permission_names: tuple[str, ...]
    uses_organizational_context_mixin: bool
    uses_organizational_scope: bool
    file_path: str
    line: int


@dataclass(frozen=True)
class AdrInfo:
    adr_id: str
    title: str
    estado: str
    file_path: str


@dataclass(frozen=True)
class GitCommitInfo:
    sha: str
    subject: str
    files: tuple[str, ...]


def discover_tenant_apps() -> list[str]:
    """Apps tenant reales = subcarpetas con apps.py (Django app real),
    excluyendo __pycache__/migrations."""
    apps = []
    for p in sorted(TENANT_APPS_DIR.iterdir()):
        if not p.is_dir() or p.name in {"__pycache__", "migrations", "api"}:
            continue
        if (p / "apps.py").exists() or (p / "models.py").exists():
            apps.append(p.name)
    return apps


def _base_names(class_node: ast.ClassDef) -> tuple[str, ...]:
    names = []
    for base in class_node.bases:
        if isinstance(base, ast.Name):
            names.append(base.id)
        elif isinstance(base, ast.Attribute):
            names.append(base.attr)
    return tuple(names)


def _field_names_assigned_in_class(class_node: ast.ClassDef) -> set[str]:
    names = set()
    for stmt in class_node.body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return names


def extract_models_for_app(app_label: str) -> list[ModelInfo]:
    """[F13.3, F13.5] AST sobre apps/tenant/<app>/models.py."""
    models_file = TENANT_APPS_DIR / app_label / "models.py"
    if not models_file.exists():
        return []
    try:
        tree = ast.parse(models_file.read_text(encoding="utf-8"), filename=str(models_file))
    except SyntaxError:
        return []

    results: list[ModelInfo] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        bases = _base_names(node)
        is_tenant_model = any(b in TENANT_BASE_NAMES or "Model" in b for b in bases)
        if not is_tenant_model:
            continue
        # Excluir enums (TextChoices/IntegerChoices/Choices) - no son modelos.
        if any("Choices" in b for b in bases):
            continue
        # Excluir las propias clases mixin abstractas (SedeAwareModel,
        # TimeStampedModel definidas EN core/inventario) - son la fuente del
        # concepto, no un consumidor con datos reales (mismo criterio que
        # tools/ekg/extract_python.py aplico para TextChoices, ver
        # documentacion/INFORME_FINAL_EKG_GOBERNANZA_2026-08-07.md bug #4).
        if node.name in ("SedeAwareModel", "TimeStampedModel"):
            continue
        field_names = _field_names_assigned_in_class(node)
        inherits_sede_aware = "SedeAwareModel" in bases
        has_sede = inherits_sede_aware or "sede" in field_names
        has_area = "area" in field_names
        # SintelTenantBaseModel inyecta `empresa` automaticamente a TODO
        # modelo tenant real - no hay forma de tener uno sin empresa salvo
        # que el modelo sea abstracto puro sin heredar la base (fuera de
        # alcance: eso ya lo prohibe AGENTS.md/§5.3, no algo que el grafo
        # deba "descubrir", solo confirmar que no ocurre).
        has_empresa = bool(set(bases) & (TENANT_BASE_NAMES | {"SedeAwareModel"})) or "empresa" in field_names
        results.append(
            ModelInfo(
                app_label=app_label,
                class_name=node.name,
                qualified_id=f"{app_label}.{node.name}",
                bases=bases,
                is_tenant_model=True,
                has_empresa=has_empresa,
                has_sede=has_sede,
                has_area=has_area,
                inherits_sede_aware_model=inherits_sede_aware,
            )
        )
    return results


def extract_viewsets_for_app(app_label: str) -> list[ViewSetInfo]:
    """[F13.4, F13.6] AST sobre apps/tenant/<app>/api/viewsets.py - clases
    que terminan en 'ViewSet', su lista de permisos (leida del texto fuente
    de get_permissions()/permission_classes, no resuelta simbolicamente), y
    si el propio texto de la clase menciona OrganizationalContext/Scope."""
    viewsets_file = TENANT_APPS_DIR / app_label / "api" / "viewsets.py"
    if not viewsets_file.exists():
        return []
    source = viewsets_file.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(viewsets_file))
    except SyntaxError:
        return []

    results: list[ViewSetInfo] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or not node.name.endswith("ViewSet"):
            continue
        segment = ast.get_source_segment(source, node) or ""
        permission_names = tuple(sorted(set(re.findall(r"\b([A-Z]\w*Permission\w*|Is\w+|Has\w+)\(\)", segment))))
        results.append(
            ViewSetInfo(
                app_label=app_label,
                class_name=node.name,
                qualified_id=f"{app_label}.{node.name}",
                permission_names=permission_names,
                uses_organizational_context_mixin="OrganizationalContextMixin" in _base_names(node),
                uses_organizational_scope=any(m in segment for m in ORG_SCOPE_MARKERS),
                file_path=str(viewsets_file.relative_to(PROJECT_ROOT)),
                line=node.lineno,
            )
        )
    return results


_ADR_HEADER_RE = re.compile(r"^#\s*(ADR-\d+):\s*(.+)$", re.MULTILINE)
# Algunos ADR usan "Estado:" (espanol), ADR-001 usa "Status:" (ingles) -
# inconsistencia real del proyecto, no un bug de esta regex - se acepta
# ambos en vez de reportar falsamente "UNKNOWN" para ADR-001.
_ADR_ESTADO_RE = re.compile(r"\*\*(?:Estado|Status):\*\*\s*(.+?)\s*$", re.MULTILINE)


def extract_adrs() -> list[AdrInfo]:
    """[F13.7] Regex acotado sobre docs/ADR-*.md - un parser Markdown
    completo seria sobre-ingenieria para 2 campos (titulo, estado)."""
    results = []
    for path in sorted(DOCS_DIR.glob("ADR-*.md")):
        text = path.read_text(encoding="utf-8")
        header_match = _ADR_HEADER_RE.search(text)
        estado_match = _ADR_ESTADO_RE.search(text)
        adr_id = header_match.group(1) if header_match else path.stem.split("-organizational")[0].split("-contexto")[0]
        title = header_match.group(2).strip() if header_match else path.stem
        estado = estado_match.group(1).strip() if estado_match else "UNKNOWN"
        results.append(AdrInfo(adr_id=adr_id, title=title, estado=estado, file_path=str(path.relative_to(PROJECT_ROOT))))
    return results


def _file_has_real_reference(path: Path, names: tuple[str, ...]) -> bool:
    """AST, no texto crudo - un docstring que dice 'no usa OrganizationalScope'
    (caso real encontrado: apps/tenant/ventas/services/api_mixins.py:27, ver
    documentacion/F13_KNOWLEDGE_GRAPH_BASELINE.md) contiene el substring pero
    NO es una referencia real de codigo. ast.walk() nunca ve el contenido de
    un docstring/comentario como Name/Attribute/Call - por construccion evita
    esta clase de falso positivo (misma tecnica que ya se aplico a ORG-004)."""
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        candidate = None
        if isinstance(node, ast.Name):
            candidate = node.id
        elif isinstance(node, ast.Attribute):
            candidate = node.attr
        if candidate and any(candidate == n or candidate.startswith(n) for n in names):
            return True
    return False


def app_uses_organizational_scope(app_label: str) -> bool:
    """[Corregido tras falso positivo real] `OrganizationalScope` no
    siempre se usa dentro de una clase *ViewSet (ej. empleados la usa en
    services/api_mixins.py y views.py, no en api/viewsets.py - confirmado
    en documentacion/ORGANIZATIONAL_SCOPE_MATRIX.md §4.1). Revisa 3
    archivos por AST (no texto crudo, ver _file_has_real_reference):
    api/viewsets.py, services/api_mixins.py, views.py."""
    app_dir = TENANT_APPS_DIR / app_label
    candidates = [
        app_dir / "api" / "viewsets.py",
        app_dir / "services" / "api_mixins.py",
        app_dir / "views.py",
    ]
    return any(
        _file_has_real_reference(p, ("OrganizationalScope", "filter_by_scope"))
        for p in candidates
        if p.exists()
    )


def app_uses_organizational_context(app_label: str) -> bool:
    """Analogo a app_uses_organizational_scope() pero para OrganizationalContext
    (incluye el caso `ventas`, que llama OrganizationalContext.resolve()
    directo desde services/api_mixins.py sin heredar el Mixin - ver
    documentacion/VENTAS_FACTURAS_AUDIT.md). AST, no texto crudo (mismo
    motivo que app_uses_organizational_scope())."""
    app_dir = TENANT_APPS_DIR / app_label
    candidates = [
        app_dir / "api" / "viewsets.py",
        app_dir / "services" / "api_mixins.py",
        app_dir / "views.py",
    ]
    return any(
        _file_has_real_reference(p, ("OrganizationalContext", "OrganizationalContextMixin"))
        for p in candidates
        if p.exists()
    )


def extract_recent_git_commits(limit: int = 10) -> list[GitCommitInfo]:
    """[F13.9] git log real via subprocess - no reimplementa un parser de
    .git. Acotado a los ultimos `limit` commits (suficiente para lo que
    F13.14 pide responder: que se toco recientemente); no se ingiere el
    historial completo del repositorio por costo/beneficio."""
    try:
        log_output = subprocess.run(
            ["git", "log", f"-{limit}", "--pretty=format:%H%x1f%s", "--name-only"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return []

    commits: list[GitCommitInfo] = []
    current_sha = None
    current_subject = ""
    current_files: list[str] = []
    for line in log_output.splitlines():
        if "\x1f" in line:
            if current_sha is not None:
                commits.append(GitCommitInfo(sha=current_sha, subject=current_subject, files=tuple(current_files)))
            current_sha, current_subject = line.split("\x1f", 1)
            current_files = []
        elif line.strip():
            current_files.append(line.strip())
    if current_sha is not None:
        commits.append(GitCommitInfo(sha=current_sha, subject=current_subject, files=tuple(current_files)))
    return commits
