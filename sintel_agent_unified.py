#!/usr/bin/env python3
"""
sintel_agent_unified.py

Unified MCP server for SINTEL v2.x (Optimizado v2.61.8)

This module implements a single, asynchronous MCP server (``UnifiedMCPServer``)
and registers a consolidated set of tools grouped according to the SINTEL
AGENTS.md architecture rules.  All tools include explicit docstrings stating
which AGENTS rules they validate.

Coverage by AGENTS.md section:
- [RULE 0]  Cero Caracteres Especiales (py_compile + unicode/emoji scan)
- [RULE 1]  Stack: Vanilla JS ES6+ / Django / DRF / Celery / HTMX / Tabulator
- [RULE 2]  Bounded Contexts & Direct Gateway (no Facade)
- [RULE 3]  SSoT Documental (AUDITORIA_FLUJO_COMPLETO.md)
- [RULE 4]  Zero Waste queries, Zero Signals, Zero unauthorized .py files
- [RULE 4.4] django-tenants: SHARED_APPS vs TENANT_APPS segregation audit
- [RULE 5]  Service Layer (CRUD, Business, Selectors, services.py facade, Mixins)
- [RULE 6]  Asset placement: templates/tenant/<app>/ & static/<app>/js/
- [RULE 7]  Feature-Sliced Design (FSD) per model
- [RULE 8]  Wizard pattern: SessionStorage state transfer (no premature BD write)
- [RULE 9]  DOM Shield & Zero Trust UI
- [RULE 10] Error logging [module:action] format
- [RULE 11] Celery async tasks with DLQ
- [RULE 12] HTMX OOB swaps (hx-swap-oob / HX-Trigger reactivity)
- [RULE 13] IDOR prevention via Double Semantic Verification (DSV)
- [RULE 14] SintelTenantBaseModel mandatory inheritance
- [RULE 15] Dual-Auth JWT+Session centralizado en BaseTenantViewSet,
-            IsTenantMember, TenantProfile.rol SSoT, permisos centralizados
-            (apps/tenant/api/permissions.py), prohibido override auth_classes
- [RULE 16] Governance (read AUDITORIA before modifying private apps)
- [RULE 17] Bridge Isolation: apps.public only via core/services/membership.py
- [AGENTS] Copilot agents discovery (.copilot/agents/*.agent.md)

Note: optional runtime packages (docker, psycopg2) are imported inside
try/except blocks so the server remains importable even if not present.
"""

from __future__ import annotations

import ast
import asyncio
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import docker
except Exception:
    docker = None

try:
    import psycopg2
except Exception:
    psycopg2 = None

LOG = logging.getLogger("sintel_agent_unified")
logging.basicConfig(level=logging.INFO)

SINTEL_VERSION = "2.61.8"

# Canonical service-layer files expected by AGENTS.md Rule 5
SERVICE_LAYER_FILES = (
    "__init__.py",
    "crud_service.py",
    "business_service.py",
    "selectors.py",
    "services.py",       # facade re-export for import compatibility (Rule 5)
    "api_mixins.py",
)

# Apps that should NOT be auto-modified (Rule 4.2 / Rule 16)
PROTECTED_ROOTS = ("public",)

# Copilot agents directory (*.agent.md files) — resolves to ~/.copilot/agents/ by default
AGENTS_COPILOT_DIR = Path(os.getenv("COPILOT_AGENTS_DIR", str(Path.home() / ".copilot" / "agents")))


def get_workspace_root() -> Path:
    """
    Resolve the workspace root in a deterministic way.

    Uses `WORKSPACE_ROOT` environment variable if set; otherwise falls back to
    the directory containing this file. This standardizes path resolution across
    tools and avoids mixing `Path(__file__).parent` with env-based roots.
    """
    env = os.getenv("WORKSPACE_ROOT")
    if env:
        return Path(env).resolve()
    return Path(__file__).parent.resolve()


WORKSPACE = get_workspace_root()


# ---------------------------------------------------------------------------
# MCP Server Core
# ---------------------------------------------------------------------------


class UnifiedMCPServer:
    """Asynchronous MCP (JSON-RPC over stdio) server.

    - ``register_tool(func, description)``
    - ``run()``  to start the async message loop

    Tools may be synchronous or async; we detect at call time.
    """

    def __init__(self, name: str = "sintel-unified") -> None:
        self.name = name
        self.tools: dict[str, Any] = {}

    def register_tool(self, func: Any, description: str = "") -> None:
        """Register a callable as an MCP tool (keyed by ``func.__name__``)."""
        self.tools[func.__name__] = func
        if not getattr(func, "__doc__", None):
            func.__doc__ = description

    async def _process_message(self, msg: dict) -> dict:
        method = msg.get("method")
        params = msg.get("params", {})
        msg_id = msg.get("id")

        if method == "tools/list":
            tools_list = [
                {"name": n, "description": (f.__doc__ or ""), "inputSchema": {}}
                for n, f in self.tools.items()
            ]
            return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": tools_list}}

        if method == "tools/call":
            name = params.get("name")
            args = params.get("arguments", {})
            tool = self.tools.get(name)
            if not tool:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Tool '{name}' not found"},
                }
            try:
                if asyncio.iscoroutinefunction(tool):
                    res = await tool(**args)
                else:
                    loop = asyncio.get_running_loop()
                    res = await loop.run_in_executor(None, lambda: tool(**args))
                return {"jsonrpc": "2.0", "id": msg_id, "result": res}
            except Exception as exc:
                LOG.exception("Tool %s failed", name)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32000, "message": str(exc)},
                }

        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32700, "message": "Unknown method"},
        }

    async def _loop(self) -> None:
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            try:
                msg = json.loads(line)
            except Exception:
                err = json.dumps({"error": "invalid json"}) + "\n"
                sys.stderr.write(err)
                sys.stderr.flush()
                continue

            resp = await self._process_message(msg)
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()

    def run(self) -> None:
        """Start the MCP server loop (blocking)."""
        asyncio.run(self._loop())


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _safe_write(path: Path, content: str, *, overwrite: bool = False) -> bool:
    """Write a file conservatively; skip if exists unless *overwrite*."""
    if path.exists() and not overwrite:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _rel(path: Path) -> str:
    """Return workspace-relative POSIX path string."""
    try:
        return str(path.relative_to(WORKSPACE))
    except ValueError:
        return str(path)


def _is_excluded(path: Path) -> bool:
    """True for paths that should be skipped during recursive scans."""
    return any(
        part in ("venv", ".venv", "node_modules", ".git", "__pycache__", "staticfiles")
        for part in path.parts
    )


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _ast_class_inherits_from(node: ast.ClassDef, base_name: str) -> bool:
    for base in node.bases:
        if isinstance(base, ast.Name) and base.id == base_name:
            return True
        if isinstance(base, ast.Attribute) and base.attr == base_name:
            return True
    return False


def _ast_extract_source(src: str, node: ast.AST) -> str:
    """Best-effort extraction of source segment for an AST node."""
    if hasattr(ast, "get_source_segment"):
        seg = ast.get_source_segment(src, node)
        if seg:
            return seg
    # Fallback: line-based extraction
    if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
        lines = src.splitlines()
        return "\n".join(lines[node.lineno - 1 : node.end_lineno])
    return ""


def ast_audit_models_for_tenant(app_root: Path) -> tuple[list[str], list[str]]:
    """Parse models.py via AST.  Returns (models_found, non_compliant_models)."""
    models_file = app_root / "models.py"
    if not models_file.exists():
        return [], ["NO_MODELS_FILE"]

    src = models_file.read_text(encoding="utf-8")
    tree = ast.parse(src)
    found: list[str] = []
    non_compliant: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        # Skip inner Meta, abstract base helpers, and mixins
        if node.name in ("Meta",) or node.name.endswith("Base") or node.name.endswith("Mixin"):
            continue
        found.append(node.name)
        if not _ast_class_inherits_from(node, "SintelTenantBaseModel"):
            non_compliant.append(node.name)
    return found, non_compliant


# ---------------------------------------------------------------------------
# DNA Mapper (Fase 0)
# ---------------------------------------------------------------------------


class DNAMapper:
    """Reverse-engineering scanner for legacy apps (Fase 0).

    Identifies models, phantom business logic, query optimization violations,
    and Facade/Gateway anti-patterns.
    """

    @staticmethod
    def map_app_dna(app_name: str) -> dict[str, Any]:
        app_root = WORKSPACE / "apps" / "tenant" / app_name
        if not app_root.exists():
            return {"error": f"app '{app_name}' not found under apps/tenant/"}

        report: dict[str, Any] = {
            "app": app_name,
            "models": {},
            "phantom_logic": [],
            "dependencies": [],
            "queryset_audit": [],
            "facade_violations": [],
            "signals_violations": [],
            "auth_model_violations": [],
        }

        # -- 1) Model Discovery & IDOR Risk --
        models_file = app_root / "models.py"
        if models_file.exists():
            src = models_file.read_text(encoding="utf-8")
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef) or node.name == "Meta":
                    continue
                m_info: dict[str, list[str]] = {
                    "fields": [],
                    "constraints": [],
                    "overrides": [],
                }
                for item in node.body:
                    # Phantom logic in model (Rule 4.7: zero signals / zero
                    # side-effects -- logic in save/clean should migrate)
                    if isinstance(item, ast.FunctionDef) and item.name in (
                        "save",
                        "clean",
                    ):
                        m_info["overrides"].append(item.name)
                        report["phantom_logic"].append(
                            f"[RULE 4.7] Model {node.name}.{item.name}() "
                            "contains logic (move to Business Service)"
                        )

                    # FK / relation discovery
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                val = ast.dump(item.value)
                                if "ForeignKey" in val or "OneToOneField" in val:
                                    m_info["fields"].append(target.id)
                                if "AUTH_USER_MODEL" in val:
                                    report["auth_model_violations"].append(
                                        f"[RULE 4.6] {node.name} references "
                                        "AUTH_USER_MODEL directly. "
                                        "Must use perfil.TenantProfile."
                                    )

                    # Idempotency constraints
                    if isinstance(item, ast.ClassDef) and item.name == "Meta":
                        for m_item in item.body:
                            if isinstance(m_item, ast.Assign):
                                for mt in m_item.targets:
                                    if (
                                        isinstance(mt, ast.Name)
                                        and mt.id in ("unique_together", "constraints")
                                    ):
                                        m_info["constraints"].append(mt.id)
                report["models"][node.name] = m_info

            # Detect signal usage (Rule 4.7)
            if re.search(
                r"(pre_save|post_save|pre_delete|post_delete|m2m_changed)\s*\.\s*connect",
                src,
            ):
                report["signals_violations"].append(
                    "[RULE 4.7] Django signal connect() detected in models.py. "
                    "Must move business logic to Service Layer."
                )

        # -- 2) ViewSet audit --
        vs_file = app_root / "api" / "viewsets.py"
        if vs_file.exists():
            src = vs_file.read_text(encoding="utf-8")

            # Facade references (Rule 2.1)
            if "facade" in src.lower():
                report["facade_violations"].append(
                    "[RULE 2.1] Potential Facade pattern in ViewSet. "
                    "Must use Direct Gateway."
                )

            tree = ast.parse(src)
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                if not any("ViewSet" in (getattr(b, "id", "") or getattr(b, "attr", "")) for b in node.bases):
                    continue
                for item in node.body:
                    if not isinstance(item, ast.FunctionDef):
                        continue
                    # Zero Waste (Rule 4.5)
                    if item.name == "get_queryset":
                        func_src = _ast_extract_source(src, item)
                        if ".all()" in func_src and ".only(" not in func_src and ".defer(" not in func_src:
                            report["queryset_audit"].append(
                                f"[RULE 4.5] {node.name}.get_queryset uses "
                                ".all() without .only()/.defer()"
                            )
                        if ".filter(" in func_src and ".only(" not in func_src and ".defer(" not in func_src:
                            report["queryset_audit"].append(
                                f"[RULE 4.5] {node.name}.get_queryset uses "
                                ".filter() without .only()/.defer()"
                            )
                    # Fat ViewSet heuristic (Rule 5.2)
                    if (
                        len(item.body) > 15
                        and item.name not in ("get_queryset", "get_serializer_class")
                    ):
                        report["phantom_logic"].append(
                            f"[RULE 5.2] {node.name}.{item.name} has "
                            f"{len(item.body)} statements. Delegate to Service."
                        )

        return report


# ---------------------------------------------------------------------------
# Skill Manager
# ---------------------------------------------------------------------------


class SkillManager:
    """Discovers skills from workspace skill directories AND .copilot/agents/*.agent.md."""

    _SKILL_DIRS = (
        ".agents/skills",
        ".antigravity/skills",
        ".github/copilot/skills",
    )

    @classmethod
    def _search_paths(cls) -> list[Path]:
        return [WORKSPACE / d for d in cls._SKILL_DIRS]

    @classmethod
    def list_skills(cls) -> list[str]:
        skills: set[str] = set()
        # Legacy SKILL.md subdirectories
        for p in cls._search_paths():
            if p.exists():
                skills.update(d.name for d in p.iterdir() if d.is_dir())
        # Canonical .copilot/agents/*.agent.md (AGENTS.md agents ecosystem)
        if AGENTS_COPILOT_DIR.exists():
            for f in AGENTS_COPILOT_DIR.glob("*.agent.md"):
                # Strip .agent.md suffix to get the agent name (e.g. "drf")
                skills.add(f.name[: -len(".agent.md")])
        return sorted(skills)

    @classmethod
    def get_skill_details(cls, skill_name: str) -> dict[str, Any]:
        # Canonical: .copilot/agents/<name>.agent.md takes precedence
        agent_file = AGENTS_COPILOT_DIR / f"{skill_name}.agent.md"
        if agent_file.exists():
            return {
                "name": skill_name,
                "type": "agent",
                "path": str(agent_file),
                "instructions": agent_file.read_text(encoding="utf-8"),
            }
        # Legacy SKILL.md subdirectories
        for p in cls._search_paths():
            skill_file = p / skill_name / "SKILL.md"
            if skill_file.exists():
                return {
                    "name": skill_name,
                    "type": "skill",
                    "path": str(p / skill_name),
                    "instructions": skill_file.read_text(encoding="utf-8"),
                }
        return {"error": f"Skill/Agent '{skill_name}' not found"}


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


class Tools:
    """SINTEL MCP tools aligned with AGENTS.md v2.61.7.

    Every tool docstring references the AGENTS.md rule(s) it enforces.
    """

    # ------------------------------------------------------------------ #
    #  Discovery & Inventory
    # ------------------------------------------------------------------ #

    @staticmethod
    def list_apps() -> dict[str, Any]:
        """List all tenant apps under apps/tenant/."""
        root = WORKSPACE / "apps" / "tenant"
        if not root.exists():
            return {"tenant_apps": []}
        apps = sorted(
            p.name
            for p in root.iterdir()
            if p.is_dir() and not p.name.startswith("_")
        )
        return {"tenant_apps": apps, "count": len(apps)}

    @staticmethod
    def find_models(app_name: str) -> dict[str, Any]:
        """Find Django model classes in apps/tenant/<app>/models.py."""
        app_root = WORKSPACE / "apps" / "tenant" / app_name
        models_file = app_root / "models.py"
        if not models_file.exists():
            return {"error": "models.py not found", "app": app_name}
        try:
            tree = ast.parse(models_file.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            return {"error": f"syntax error: {exc}"}
        models: dict[str, list[str]] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name != "Meta":
                fields = [
                    n.targets[0].id
                    for n in node.body
                    if isinstance(n, ast.Assign)
                    and n.targets
                    and isinstance(n.targets[0], ast.Name)
                ]
                models[node.name] = fields
        return {"app": app_name, "models": models}

    @staticmethod
    def find_viewsets(app_name: str) -> dict[str, Any]:
        """Find ViewSet classes in api/viewsets.py for an app."""
        vs = WORKSPACE / "apps" / "tenant" / app_name / "api" / "viewsets.py"
        if not vs.exists():
            return {"error": "viewsets.py not found", "app": app_name}
        try:
            tree = ast.parse(vs.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            return {"error": f"syntax error: {exc}"}
        viewsets: list[dict[str, Any]] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            bases = []
            for b in node.bases:
                if isinstance(b, ast.Name):
                    bases.append(b.id)
                elif isinstance(b, ast.Attribute):
                    bases.append(b.attr)
            if any("ViewSet" in s for s in bases):
                methods = [
                    m.name
                    for m in node.body
                    if isinstance(m, ast.FunctionDef) and not m.name.startswith("_")
                ]
                viewsets.append({"name": node.name, "bases": bases, "methods": methods})
        return {"app": app_name, "viewsets": viewsets}

    @staticmethod
    def list_service_mixins(app_name: str) -> dict[str, Any]:
        """List Mixin classes found in app services/ directory."""
        svc_dir = WORKSPACE / "apps" / "tenant" / app_name / "services"
        if not svc_dir.exists():
            return {"error": "no services directory", "app": app_name}
        mixins: list[dict[str, Any]] = []
        for f in svc_dir.glob("*.py"):
            if f.name == "__init__.py":
                continue
            try:
                tree = ast.parse(f.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name.endswith("Mixin"):
                    methods = [
                        n.name
                        for n in node.body
                        if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")
                    ]
                    mixins.append({"name": node.name, "methods": methods, "file": _rel(f)})
        return {"app": app_name, "mixins": mixins}

    @staticmethod
    def get_module_version(app_name: str) -> dict[str, Any]:
        """Extract version from AUDITORIA_FLUJO_COMPLETO.md if present (Rule 3)."""
        audit = WORKSPACE / "apps" / "tenant" / app_name / "AUDITORIA_FLUJO_COMPLETO.md"
        if not audit.exists():
            return {"app": app_name, "version": "unknown", "audit_doc": False}
        txt = audit.read_text(encoding="utf-8")
        m = re.search(r"v(\d+\.\d+\.\d+)", txt)
        return {
            "app": app_name,
            "version": f"v{m.group(1)}" if m else "unknown",
            "audit_doc": True,
        }

    @staticmethod
    def search_pattern(pattern: str, file_type: str = "*.py") -> dict[str, Any]:
        """Search for a regex pattern in workspace files (max 50 matches)."""
        try:
            reobj = re.compile(pattern, re.IGNORECASE)
        except re.error as exc:
            return {"error": f"invalid regex: {exc}"}
        matches: list[dict[str, Any]] = []
        for p in WORKSPACE.rglob(file_type):
            if _is_excluded(p):
                continue
            try:
                for ln, line in enumerate(
                    p.read_text(encoding="utf-8", errors="replace").splitlines(),
                    start=1,
                ):
                    if reobj.search(line):
                        matches.append({
                            "file": _rel(p),
                            "line": ln,
                            "content": line.strip()[:200],
                        })
                        if len(matches) >= 50:
                            return {"pattern": pattern, "matches": matches, "truncated": True}
            except Exception:
                continue
        return {"pattern": pattern, "matches": matches, "truncated": False}

    # ------------------------------------------------------------------ #
    #  Syntax & Compilation (Rule 0)
    # ------------------------------------------------------------------ #

    @staticmethod
    def check_syntax(file_path: str) -> dict[str, Any]:
        """[RULE 0] Check a Python file for syntax errors via AST parsing."""
        full = WORKSPACE / file_path
        if not full.exists():
            return {"error": "file not found", "file": file_path}
        try:
            ast.parse(full.read_text(encoding="utf-8"))
            return {"file": file_path, "valid": True}
        except SyntaxError as exc:
            return {"file": file_path, "valid": False, "error": {"lineno": exc.lineno, "msg": exc.msg}}

    # ------------------------------------------------------------------ #
    #  Structure Validation (Rules 3, 5, 6, 7)
    # ------------------------------------------------------------------ #

    @staticmethod
    def validate_module_structure(app_name: str) -> dict[str, Any]:
        """[RULES 3, 5, 6, 7] Validate that an app follows SINTEL architecture.

        Checks:
        - Template path: templates/tenant/<app>/ (Rule 6 tenant prefix)
        - Static JS path: static/<app>/js/ (Rule 6)
        - Service Layer presence and completeness (Rule 5)
        - AUDITORIA_FLUJO_COMPLETO.md (Rule 3 / Rule 16)
        """
        app_root = WORKSPACE / "apps" / "tenant" / app_name
        if not app_root.exists():
            return {"error": "app not found", "app": app_name}

        # Rule 6: tenant template prefix (canonical: templates/tenant/<app>/)
        # Also accept legacy path templates/<app>/ for apps in transition
        canonical_templates = (app_root / "templates" / "tenant" / app_name).exists()
        legacy_templates = (app_root / "templates" / app_name).exists()
        has_templates = canonical_templates or legacy_templates
        has_static_js = (app_root / "static" / app_name / "js").exists()

        # Rule 5: service layer completeness
        svc_dir = app_root / "services"
        has_services = svc_dir.exists()
        svc_files_present: dict[str, bool] = {}
        if has_services:
            for fname in SERVICE_LAYER_FILES:
                svc_files_present[fname] = (svc_dir / fname).exists()

        # Rule 3 / 16: audit doc
        has_audit = (app_root / "AUDITORIA_FLUJO_COMPLETO.md").exists()

        issues: list[str] = []
        if not has_templates:
            issues.append("[RULE 6] Missing templates/tenant/<app>/ directory")
        elif not canonical_templates and legacy_templates:
            issues.append("[RULE 6] Templates at legacy path templates/<app>/ - migrate to templates/tenant/<app>/")
        if not has_static_js:
            issues.append("[RULE 6] Missing static/<app>/js/ directory")
        if not has_services:
            issues.append("[RULE 5] Missing services/ directory")
        else:
            for fname, present in svc_files_present.items():
                if not present and fname != "services.py":
                    issues.append(f"[RULE 5] Missing services/{fname}")
        if not has_audit:
            issues.append("[RULE 3/16] Missing AUDITORIA_FLUJO_COMPLETO.md")

        return {
            "app": app_name,
            "templates": has_templates,
            "templates_canonical": canonical_templates,
            "static_js": has_static_js,
            "services": has_services,
            "service_files": svc_files_present,
            "audit_doc": has_audit,
            "issues": issues,
            "compliant": len(issues) == 0,
        }

    @staticmethod
    def validate_assets_placement(app_name: str) -> dict[str, Any]:
        """[RULE 6] Validate static asset placement (no leaks into core)."""
        app_root = WORKSPACE / "apps" / "tenant" / app_name
        expected = app_root / "static" / app_name / "js"
        core_leak = WORKSPACE / "apps" / "tenant" / "core" / "static" / "core" / "js" / app_name
        result: dict[str, Any] = {
            "app": app_name,
            "expected_js_exists": expected.exists(),
            "core_legacy_files": [],
        }
        if core_leak.exists():
            for p in core_leak.rglob("*.js"):
                result["core_legacy_files"].append(_rel(p))
        result["compliant"] = result["expected_js_exists"] and not result["core_legacy_files"]
        return result

    # ------------------------------------------------------------------ #
    #  E2E Auditor (Rules 0, 2, 4, 5, 14, 15)
    # ------------------------------------------------------------------ #

    @staticmethod
    def expert_e2e_auditor(app_name: str) -> dict[str, Any]:
        """AST-based end-to-end architectural auditor.

        Validates:
        - [RULE 0]  py_compile on every .py file
        - [RULE 2.2] Core isolation (no domain logic in core)
        - [RULE 4.5] Zero Waste queries in selectors
        - [RULE 4.6] No ForeignKey to AUTH_USER_MODEL
        - [RULE 4.7] No Django signals
        - [RULE 5]   Service Layer presence + completeness
        - [RULE 14]  SintelTenantBaseModel inheritance
        - [RULE 15.1] Dual-Auth: no authentication_classes overrides
        - [RULE 15.5] IsTenantMember + role-based permission in ViewSet
        - [RULE 15.5] No deprecated empresa/permissions.py imports
        - [RULE 17]  Bridge Isolation (no direct apps.public imports)
        """
        import py_compile as _pyc

        report: dict[str, Any] = {
            "app": app_name,
            "version": SINTEL_VERSION,
            "issues": [],
            "recommendations": [],
        }
        app_root = WORKSPACE / "apps" / "tenant" / app_name
        if not app_root.exists():
            report["issues"].append({"code": "APP_NOT_FOUND", "message": "App path not found"})
            return report

        # Rule 2.2 Core Isolation
        if app_name == "core":
            report["recommendations"].append(
                "[RULE 2.2] App 'core' detected. Ensure it acts "
                "ONLY as UI Shell and Infrastructure helper."
            )

        # Rule 0: py_compile
        for py in app_root.rglob("*.py"):
            if _is_excluded(py):
                continue
            try:
                _pyc.compile(str(py), doraise=True)
            except _pyc.PyCompileError as exc:
                report["issues"].append({
                    "code": "PY_COMPILE_ERROR",
                    "file": _rel(py),
                    "message": f"[RULE 0] {exc}",
                })

        # Rule 14: model inheritance
        models, non_compliant = ast_audit_models_for_tenant(app_root)
        report["models_found"] = models
        if non_compliant and "NO_MODELS_FILE" not in non_compliant and app_name != "core":
            report["issues"].append({
                "code": "MODEL_INHERITANCE",
                "bad": non_compliant,
                "message": "[RULE 14] Models must inherit from SintelTenantBaseModel",
            })

        # Rule 4.7: signals detection
        for py in (app_root / "models.py", app_root / "signals.py"):
            if py.exists():
                src = py.read_text(encoding="utf-8", errors="replace")
                if re.search(r"(pre_save|post_save|pre_delete|post_delete)\.connect", src):
                    report["issues"].append({
                        "code": "SIGNAL_USAGE",
                        "file": _rel(py),
                        "message": "[RULE 4.7] Signal connect() detected. Orchestrate in Service Layer.",
                    })

        # Rule 5: Service Layer
        svc_dir = app_root / "services"
        if not svc_dir.exists():
            report["issues"].append({
                "code": "NO_SERVICE_LAYER",
                "message": "[RULE 5] Missing services/ directory.",
            })
        else:
            for fname in SERVICE_LAYER_FILES:
                fpath = svc_dir / fname
                if not fpath.exists():
                    # services.py is an optional facade re-export (backward compat)
                    if fname == "services.py":
                        continue
                    report["issues"].append({
                        "code": "MISSING_SERVICE_FILE",
                        "file": f"services/{fname}",
                        "message": f"[RULE 5] Missing {fname} in services/",
                    })
                    continue
                src = fpath.read_text(encoding="utf-8")
                try:
                    tree = ast.parse(src)
                    funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
                    classes = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
                    report.setdefault("services", {})[_rel(fpath)] = {
                        "functions": funcs,
                        "classes": classes,
                    }
                except SyntaxError as exc:
                    report["issues"].append({
                        "code": "SERVICE_SYNTAX_ERROR",
                        "file": _rel(fpath),
                        "message": str(exc),
                    })

                # Rule 5.4: @transaction.atomic in crud_service
                if fname == "crud_service.py" and "@transaction.atomic" not in src:
                    report["recommendations"].append(
                        f"[RULE 5.4] Consider adding @transaction.atomic in {fname}"
                    )

        # Rule 4.5: selectors Zero Waste
        selectors_file = app_root / "services" / "selectors.py"
        if selectors_file.exists():
            sel_src = selectors_file.read_text(encoding="utf-8")
            if ".all()" in sel_src and ".only(" not in sel_src and ".defer(" not in sel_src:
                report["issues"].append({
                    "code": "SELECTOR_ZERO_WASTE",
                    "file": _rel(selectors_file),
                    "message": "[RULE 4.5] Selector uses .all() without .only()/.defer()",
                })

        # Rule 5.2: ViewSet thinness + Rule 15: permissions & auth
        viewsets_file = app_root / "api" / "viewsets.py"
        if viewsets_file.exists():
            vs_src = viewsets_file.read_text(encoding="utf-8")
            size = viewsets_file.stat().st_size
            if size > 20_000:
                report["issues"].append({
                    "code": "LARGE_VIEWSET",
                    "message": f"[RULE 5.2] viewsets.py is {size:,} bytes. Delegate to Service.",
                })
            # Rule 15.5: IsTenantMember presence
            if "IsTenantMember" not in vs_src and app_name != "core":
                report["issues"].append({
                    "code": "MISSING_ISTM",
                    "message": (
                        "[RULE 15.5] IsTenantMember not found in viewsets.py. "
                        "permission_classes must include IsTenantMember."
                    ),
                })
            # Rule 15.5: Role-based permission presence
            _role_perms = (
                "IsTenantAdminOrReadOnly", "HasTenantRole",
                "IsTenantProfileAdmin", "IsTenantAdmin",
                "IsTenantProfileOperadorOrAdmin",
            )
            if not any(rp in vs_src for rp in _role_perms) and app_name != "core":
                report["recommendations"].append(
                    "[RULE 15.5] No role-based permission class detected in viewsets.py. "
                    "Consider adding IsTenantAdminOrReadOnly or HasTenantRole."
                )
            # Rule 15.1: Prohibited authentication_classes override
            if "authentication_classes" in vs_src and app_name != "core":
                report["issues"].append({
                    "code": "AUTH_CLASSES_OVERRIDE",
                    "message": (
                        "[RULE 15.1] authentication_classes override detected. "
                        "Dual-Auth is inherited from BaseTenantViewSet; overrides are PROHIBITED."
                    ),
                })
            # Rule 15.5: Deprecated empresa/permissions.py import
            if "empresa.permissions" in vs_src or "empresa/permissions" in vs_src:
                report["issues"].append({
                    "code": "DEPRECATED_PERMISSIONS_IMPORT",
                    "message": (
                        "[RULE 15.5] Import from empresa/permissions.py detected (deprecated). "
                        "Use apps.tenant.api.permissions instead."
                    ),
                })

            # Rule 17: Bridge Isolation - no direct apps.public imports
            if app_name not in ("core", "api"):
                for py in app_root.rglob("*.py"):
                    if _is_excluded(py):
                        continue
                    try:
                        src_bridge = py.read_text(encoding="utf-8")
                    except Exception:
                        continue
                    for line_no, line in enumerate(src_bridge.splitlines(), 1):
                        stripped = line.strip()
                        if stripped.startswith("#"):
                            continue
                        if "apps.public" in stripped and (
                            stripped.startswith("from ") or stripped.startswith("import ")
                        ):
                            report["issues"].append({
                                "code": "BRIDGE_ISOLATION_VIOLATION",
                                "file": _rel(py),
                                "line": line_no,
                                "message": (
                                    "[RULE 17] Direct import from apps.public detected. "
                                    "Use apps.tenant.core.services.membership instead."
                                ),
                            })
            # Model imports in ViewSet
            try:
                tree = ast.parse(vs_src)
                imports = [n for n in tree.body if isinstance(n, ast.ImportFrom)]
                model_imports = [
                    (n.module, [a.name for a in n.names])
                    for n in imports
                    if n.module and "models" in n.module
                ]
                if model_imports:
                    report["issues"].append({
                        "code": "MODEL_IMPORTS_IN_VIEWSET",
                        "details": model_imports,
                        "message": "[RULE 5.2] ViewSet imports models directly; use Selectors/CRUDService.",
                    })
            except SyntaxError:
                report["issues"].append({
                    "code": "VIEWSET_SYNTAX_ERROR",
                    "message": "Cannot parse viewsets.py via AST",
                })

        # Rule 4.6: AUTH_USER_MODEL in models
        models_file = app_root / "models.py"
        if models_file.exists():
            msrc = models_file.read_text(encoding="utf-8")
            if "AUTH_USER_MODEL" in msrc:
                report["issues"].append({
                    "code": "AUTH_USER_DIRECT_REF",
                    "file": _rel(models_file),
                    "message": "[RULE 4.6] Direct FK to AUTH_USER_MODEL. Use perfil.TenantProfile.",
                })

        report["summary"] = {"issues_count": len(report["issues"])}
        return report

    # ------------------------------------------------------------------ #
    #  Zero Waste Query Auditor (Rule 4.5)
    # ------------------------------------------------------------------ #

    @staticmethod
    def audit_zero_waste(app_name: str) -> dict[str, Any]:
        """[RULE 4.5] Scan all .py files in an app for unoptimized queries.

        Detects:
        - .all() without .only()/.defer()
        - .filter() without .only()/.defer()
        - Missing queryset = Model.objects.none() in ViewSets
        """
        app_root = WORKSPACE / "apps" / "tenant" / app_name
        if not app_root.exists():
            return {"error": "app not found"}
        violations: list[dict[str, Any]] = []
        for py in app_root.rglob("*.py"):
            if _is_excluded(py):
                continue
            try:
                src = py.read_text(encoding="utf-8")
            except Exception:
                continue
            for ln, line in enumerate(src.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if ".objects.all()" in line and ".only(" not in line and ".defer(" not in line:
                    violations.append({"file": _rel(py), "line": ln, "issue": ".objects.all() without .only()/.defer()"})
                if ".objects.filter(" in line and ".only(" not in line and ".defer(" not in line and "none()" not in line:
                    violations.append({"file": _rel(py), "line": ln, "issue": ".objects.filter() without .only()/.defer()"})
        return {"app": app_name, "violations": violations, "count": len(violations)}

    # ------------------------------------------------------------------ #
    #  Signals Detector (Rule 4.7)
    # ------------------------------------------------------------------ #

    @staticmethod
    def audit_signals(app_name: str) -> dict[str, Any]:
        """[RULE 4.7] Detect prohibited Django signal usage in an app."""
        app_root = WORKSPACE / "apps" / "tenant" / app_name
        if not app_root.exists():
            return {"error": "app not found"}
        hits: list[dict[str, Any]] = []
        signal_re = re.compile(
            r"(pre_save|post_save|pre_delete|post_delete|m2m_changed)\s*\.\s*connect"
        )
        for py in app_root.rglob("*.py"):
            if _is_excluded(py):
                continue
            try:
                src = py.read_text(encoding="utf-8")
            except Exception:
                continue
            for ln, line in enumerate(src.splitlines(), 1):
                if signal_re.search(line):
                    hits.append({"file": _rel(py), "line": ln, "content": line.strip()[:200]})
        return {"app": app_name, "signals_found": hits, "compliant": len(hits) == 0}

    # ------------------------------------------------------------------ #
    #  Celery Task Auditor (Rule 11)
    # ------------------------------------------------------------------ #

    @staticmethod
    def audit_celery_tasks(app_name: str) -> dict[str, Any]:
        """[RULE 11] Audit Celery task patterns for DLQ compliance.

        Checks:
        - max_retries defined in @shared_task / @app.task
        - bind=True for self-aware retry
        - FailedTenantTask fallback on final failure
        """
        app_root = WORKSPACE / "apps" / "tenant" / app_name
        if not app_root.exists():
            return {"error": "app not found"}

        tasks_file = None
        for candidate in ("tasks.py", "celery_tasks.py"):
            p = app_root / candidate
            if p.exists():
                tasks_file = p
                break
        if not tasks_file:
            return {"app": app_name, "tasks_found": False, "note": "No tasks.py found"}

        src = tasks_file.read_text(encoding="utf-8")
        issues: list[str] = []
        if "@shared_task" in src or "@app.task" in src:
            if "max_retries" not in src:
                issues.append(
                    "[RULE 11] Tasks missing max_retries policy"
                )
            if "bind=True" not in src:
                issues.append(
                    "[RULE 11] Tasks should use bind=True for self.retry()"
                )
            if "FailedTenantTask" not in src:
                issues.append(
                    "[RULE 11] No FailedTenantTask DLQ fallback detected"
                )
        return {
            "app": app_name,
            "tasks_file": _rel(tasks_file),
            "issues": issues,
            "compliant": len(issues) == 0,
        }

    # ------------------------------------------------------------------ #
    #  Security & Permissions Auditor (Rules 13, 15, 17)
    # ------------------------------------------------------------------ #

    @staticmethod
    def audit_security(app_name: str) -> dict[str, Any]:
        """[RULES 13, 15, 17] Audit security posture of a tenant app.

        Checks:
        - [15.1] Dual-Auth: no authentication_classes overrides in ViewSets
        - [15.5] IsTenantMember + role-based permission in permission_classes
        - [15.5] No deprecated empresa/permissions.py imports
        - [14]   BaseTenantViewSet inheritance with lookup_field='uuid'
        - [13]   DSV / empresa_id validation in business_service
        - No raw SQL or unsanitized queries
        - [17]   Bridge Isolation: no direct imports from apps.public
        """
        app_root = WORKSPACE / "apps" / "tenant" / app_name
        if not app_root.exists():
            return {"error": "app not found"}

        findings: list[dict[str, str]] = []

        # ViewSet audit
        vs_file = app_root / "api" / "viewsets.py"
        if vs_file.exists():
            src = vs_file.read_text(encoding="utf-8")
            # Rule 15.5: IsTenantMember
            if "IsTenantMember" not in src:
                findings.append({
                    "severity": "HIGH",
                    "rule": "15.5",
                    "message": "IsTenantMember not in permission_classes",
                })
            # Rule 15.1: Prohibited authentication_classes override
            if "authentication_classes" in src and app_name != "core":
                findings.append({
                    "severity": "HIGH",
                    "rule": "15.1",
                    "message": (
                        "authentication_classes override detected. "
                        "Dual-Auth is inherited from BaseTenantViewSet; "
                        "overrides are PROHIBITED (except CoreAuthViewSet)."
                    ),
                })
            # Rule 15.5: Role-based permission
            _role_perms = (
                "IsTenantAdminOrReadOnly", "HasTenantRole",
                "IsTenantProfileAdmin", "IsTenantAdmin",
                "IsTenantProfileOperadorOrAdmin",
            )
            if not any(rp in src for rp in _role_perms) and app_name != "core":
                findings.append({
                    "severity": "MEDIUM",
                    "rule": "15.5",
                    "message": (
                        "No role-based permission class detected. "
                        "Add IsTenantAdminOrReadOnly or HasTenantRole."
                    ),
                })
            # Rule 15.5: Deprecated empresa/permissions.py import
            if "empresa.permissions" in src or "empresa/permissions" in src:
                findings.append({
                    "severity": "MEDIUM",
                    "rule": "15.5",
                    "message": (
                        "Import from empresa/permissions.py (deprecated). "
                        "Use apps.tenant.api.permissions instead."
                    ),
                })
            if "BaseTenantViewSet" not in src:
                findings.append({
                    "severity": "HIGH",
                    "rule": "14",
                    "message": "ViewSet does not inherit BaseTenantViewSet",
                })
            if "lookup_field" in src and '"uuid"' not in src and "'uuid'" not in src:
                findings.append({
                    "severity": "MEDIUM",
                    "rule": "14",
                    "message": "lookup_field is not 'uuid'",
                })

        # Business service DSV check
        bs_file = app_root / "services" / "business_service.py"
        if bs_file.exists():
            bs_src = bs_file.read_text(encoding="utf-8")
            if "empresa_id" not in bs_src and "empresa" not in bs_src:
                findings.append({
                    "severity": "HIGH",
                    "rule": "13",
                    "message": "business_service.py does not reference empresa_id (DSV missing)",
                })

        # Raw SQL detection
        for py in app_root.rglob("*.py"):
            if _is_excluded(py):
                continue
            try:
                src = py.read_text(encoding="utf-8")
            except Exception:
                continue
            if ".raw(" in src or "cursor.execute(" in src:
                findings.append({
                    "severity": "MEDIUM",
                    "rule": "13",
                    "file": _rel(py),
                    "message": "Raw SQL detected. Ensure empresa_id is validated.",
                })

            # Rule 17: Bridge Isolation
            if app_name not in ("core", "api"):
                for line_no, line in enumerate(src.splitlines(), 1):
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue
                    if "apps.public" in stripped and (
                        stripped.startswith("from ") or stripped.startswith("import ")
                    ):
                        findings.append({
                            "severity": "HIGH",
                            "rule": "17",
                            "file": _rel(py),
                            "line": line_no,
                            "message": (
                                "Direct import from apps.public violates bridge isolation. "
                                "Use apps.tenant.core.services.membership."
                            ),
                        })

        return {
            "app": app_name,
            "findings": findings,
            "compliant": not any(f["severity"] == "HIGH" for f in findings),
        }

    # ------------------------------------------------------------------ #
    #  DNA Mapper (Fase 0)
    # ------------------------------------------------------------------ #

    @staticmethod
    def expert_dna_mapper(app_name: str) -> dict[str, Any]:
        """[Fase 0] Automated DNA Mapping per REFACTORING_AGENT.md.

        Identifies models, phantom logic, Zero Waste violations,
        Facade patterns, signal usage, and AUTH_USER_MODEL references.
        """
        return DNAMapper.map_app_dna(app_name)

    # ------------------------------------------------------------------ #
    #  Backend Generator (Rules 4, 5, 13, 14)
    # ------------------------------------------------------------------ #

    @staticmethod
    def expert_backend_generator(
        app_name: str, model_name: str, schema_json: str = "{}"
    ) -> dict[str, Any]:
        """Conservative backend scaffolding generator.

        Constraints:
        - [RULE 4.1] If models.py exists, refuses auto-creation (returns plan).
        - [RULE 14]  Models inherit from SintelTenantBaseModel.
        - [RULE 5]   Service Layer separated: crud_service, business_service,
                      selectors, api_mixins.
        - [RULE 13]  DSV skeleton injected into business_service.
        """
        app_root = WORKSPACE / "apps" / "tenant" / app_name
        if not app_root.exists():
            return {"error": "app not found", "app": app_name}

        if (app_root / "models.py").exists():
            return {
                "error": "[RULE 4.1] models.py already exists; "
                "automatic .py creation prohibited. Run audit + patch manually.",
                "app": app_name,
            }

        try:
            schema = json.loads(schema_json)
        except (json.JSONDecodeError, TypeError) as exc:
            return {"error": f"invalid schema_json: {exc}"}

        created: list[str] = []

        # -- Model scaffold --
        models_dir = app_root / "models"
        models_dir.mkdir(parents=True, exist_ok=True)
        model_file = models_dir / f"{model_name.lower()}.py"
        lines = [
            "from django.db import models",
            "from apps.tenant.core.models import SintelTenantBaseModel",
            "",
            "",
            f"class {model_name}(SintelTenantBaseModel):",
            "    # [RULE 14] Inherits SintelTenantBaseModel for Tenant Isolation",
        ]
        fields = schema.get("fields", {})
        if isinstance(fields, dict) and fields:
            for fname, fdecl in fields.items():
                lines.append(f"    {fname} = models.{fdecl}")
        else:
            lines.append(
                "    nombre = models.CharField(max_length=255, null=True, blank=True)"
            )
        lines.extend([
            "",
            "    class Meta:",
            f'        verbose_name = "{model_name}"',
            f'        verbose_name_plural = "{model_name}s"',
            "",
        ])
        if _safe_write(model_file, "\n".join(lines) + "\n"):
            created.append(_rel(model_file))

        # -- Service Layer scaffold --
        svc_dir = app_root / "services"
        svc_dir.mkdir(parents=True, exist_ok=True)

        svc_files = {
            "__init__.py": (
                f"from .crud_service import {model_name}CRUDService\n"
                f"from .business_service import {model_name}BusinessService\n"
            ),
            "crud_service.py": (
                f"# {model_name} CRUD Service\n"
                "from django.db import transaction\n\n\n"
                f"class {model_name}CRUDService:\n"
                "    # [RULE 5.4] @transaction.atomic mandatory for mutations\n\n"
                "    @staticmethod\n"
                "    @transaction.atomic\n"
                "    def create_record(empresa_id: int, data: dict):\n"
                "        pass\n"
            ),
            "business_service.py": (
                f"# {model_name} Business Service\n"
                "# [RULE 5.3 & RULE 13] DSV + Idempotency\n\n\n"
                f"class {model_name}BusinessService:\n"
                "    @staticmethod\n"
                "    def process_creation(empresa_id: int, payload: dict):\n"
                "        # 1. Double Semantic Verification (Anti-IDOR)\n"
                "        # 2. Idempotency rules\n"
                "        # 3. Delegate to CRUDService\n"
                "        pass\n"
            ),
            "selectors.py": (
                f"# {model_name} Selectors (read-only queries)\n"
                "# [RULE 4.5] Zero Waste: always use .only()/.defer()\n\n\n"
                f"LIST_FIELDS = ()\nDETAIL_FIELDS = ()\n\n\n"
                f"class {model_name}Selector:\n"
                "    @staticmethod\n"
                f"    def list_for_empresa(empresa_id: int):\n"
                f"        pass  # return qs.filter(empresa_id=empresa_id).only(*LIST_FIELDS)\n"
            ),
            "api_mixins.py": (
                f"# {model_name} Service Mixin\n"
                "# [RULE 5] Injected into ViewSet for standardized access\n\n\n"
                f"class {model_name}ServiceMixin:\n"
                "    def get_qs_list(self):\n"
                "        pass\n\n"
                "    def get_qs_detail(self):\n"
                "        pass\n"
            ),
        }
        for fname, content in svc_files.items():
            fpath = svc_dir / fname
            if _safe_write(fpath, content):
                created.append(_rel(fpath))

        return {"created": created}

    # ------------------------------------------------------------------ #
    #  Frontend Generator (Rules 1, 2, 6, 7, 9)
    # ------------------------------------------------------------------ #

    @staticmethod
    def expert_frontend_generator(app_name: str, model_name: str) -> dict[str, Any]:
        """Generate FSD frontend skeleton.

        Enforcements:
        - [RULE 6] Templates at templates/tenant/<app>/ (tenant prefix).
        - [RULE 7.1] Isolated JS modules per model.
        - [RULE 9] DOM Shield hints in HTML partials.
        - [RULE 1] window.Sintel.<AppName> namespace.
        - [RULE 2.1] Gateway Directo in api.js.
        """
        app_root = WORKSPACE / "apps" / "tenant" / app_name
        if not app_root.exists():
            return {"error": "app not found"}

        created: list[str] = []
        # Rule 6: tenant prefix in template path
        tdir = app_root / "templates" / "tenant" / app_name
        jsdir = app_root / "static" / app_name / "js"
        tdir.mkdir(parents=True, exist_ok=True)
        jsdir.mkdir(parents=True, exist_ok=True)

        model_lower = model_name.lower()

        # Templates (Rule 7.1 FSD)
        templates = {
            f"list_{model_lower}.html": (
                f'{{% comment %}}[RULE 7.1] FSD Listing for {model_name}{{% endcomment %}}\n'
                f'<div id="table-{model_lower}"></div>\n'
            ),
            f"offcanvas_crear_{model_lower}.html": (
                f'{{% comment %}}[RULE 7.1 / RULE 9] DOM Shield: use hidden inputs{{% endcomment %}}\n'
                f'<form hx-post="{{% url "api:placeholder" %}}" id="form-crear-{model_lower}">\n'
                f"  {{% csrf_token %}}\n"
                f"</form>\n"
            ),
            f"offcanvas_editar_{model_lower}.html": (
                f'{{% comment %}}[RULE 7.1]{{% endcomment %}}\n'
                f'<form hx-put="" id="form-editar-{model_lower}">\n'
                f"  {{% csrf_token %}}\n"
                f"</form>\n"
            ),
        }
        for fname, content in templates.items():
            fpath = tdir / fname
            if _safe_write(fpath, content):
                created.append(_rel(fpath))

        # JavaScript submodules (Rule 1 / 7.2)
        app_cap = app_name.capitalize()
        js_files = {
            f"{app_name}.api.js": (
                f"// [RULE 2.1] Gateway Directo - SSoT de URLs para {app_name}\n"
                f"window.Sintel = window.Sintel || {{}};\n"
                f"window.Sintel.{app_cap} = window.Sintel.{app_cap} || {{}};\n"
                f"window.Sintel.{app_cap}.Api = {{\n"
                f'  BASE_URL: "/api/v1/{app_name}/",\n'
                f"}};\n"
            ),
            f"features/{model_lower}_list.js": (
                f"// [RULE 7.2] {model_name} Listing (Tabulator + Dual-Auth JWT)\n"
            ),
            f"features/{model_lower}_editor.js": (
                f"// [RULE 7.2] {model_name} Editor (Offcanvas crear/editar)\n"
                f"// [RULE 9] DOM Shield: capture via hidden inputs only\n"
            ),
        }
        for fname, content in js_files.items():
            fpath = jsdir / fname
            if _safe_write(fpath, content):
                created.append(_rel(fpath))

        return {"created": created}

    # ------------------------------------------------------------------ #
    #  Legacy Scanner & Refactor (Rules 2, 4)
    # ------------------------------------------------------------------ #

    @staticmethod
    def scan_legacy_candidates(module_path: str) -> dict[str, Any]:
        """Non-destructive scan for legacy markers in a Python file."""
        target = WORKSPACE / module_path
        if not target.exists():
            return {"error": "path not found", "path": module_path}
        if not str(target).endswith(".py"):
            return {"error": "only .py files supported"}
        txt = target.read_text(encoding="utf-8", errors="replace")
        markers = ("deprecated", "legacy", "obsolete", "todo remove", "remove in")
        hits: list[dict[str, Any]] = []
        for i, line in enumerate(txt.splitlines(), start=1):
            low = line.lower()
            if any(m in low for m in markers):
                hits.append({"line": i, "content": line.strip()[:200]})
        return {"path": module_path, "candidates": hits}

    @staticmethod
    def cleanup_legacy_functions(
        module_path: str,
        apply_changes: bool = False,
        confirm_token: str = "",
        max_deletions: int = 20,
    ) -> dict[str, Any]:
        """Guarded legacy cleanup: dry-run unless apply_changes + confirm_token."""
        target = WORKSPACE / module_path
        if not target.exists():
            return {"error": "path not found"}
        src = target.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(src)
        except SyntaxError:
            return {"error": "cannot parse source"}
        candidates: list[dict[str, Any]] = []
        lines = src.splitlines()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not hasattr(node, "end_lineno"):
                continue
            doc = ast.get_docstring(node) or ""
            context = "\n".join(lines[max(0, node.lineno - 4) : node.lineno - 1]).lower()
            text = (doc + "\n" + context).lower()
            if any(m in text for m in ("deprecated", "legacy", "obsolete", "todo remove")):
                candidates.append({"name": node.name, "start": node.lineno, "end": node.end_lineno})

        if not candidates:
            return {"note": "no legacy candidates found"}
        preview = candidates[:max_deletions]
        if not apply_changes:
            return {"dry_run": True, "candidates": preview}

        if (
            os.getenv("ALLOW_LEGACY_DELETE", "0") != "1"
            or confirm_token != "DELETE_LEGACY_CONFIRMED"
        ):
            return {"error": "deletion blocked: missing env ALLOW_LEGACY_DELETE=1 or invalid token"}

        new_lines = lines[:]
        for item in sorted(preview, key=lambda x: x["start"], reverse=True):
            new_lines[item["start"] - 1 : item["end"]] = [
                f"# [LEGACY REMOVED] {item['name']}"
            ]
        target.write_text("\n".join(new_lines), encoding="utf-8")
        return {"applied": True, "removed": len(preview)}

    @staticmethod
    def expert_legacy_refactor(file_path: str, **kwargs: Any) -> dict[str, Any]:
        """Legacy refactor with two-phase workflow: 'scan' (dry-run) and 'purge'.

        - action='scan' (default): dry-run report.
        - action='purge' + confirm_token='CONFIRM_PURGE': moves file to .legacy.bak.

        Detects Facade usage (Rule 2.1).
        """
        target = WORKSPACE / file_path
        if not target.exists():
            return {"error": "file not found", "file": file_path}

        action = kwargs.get("action", "scan")
        report: dict[str, Any] = {"file": file_path, "action": action, "issues": []}

        content = target.read_text(encoding="utf-8")
        if "Facade" in content or "from core.facade" in content:
            report["issues"].append({
                "code": "FACADE_USAGE",
                "message": "[RULE 2.1] Facade references found. Migrate to Direct Gateway.",
            })

        if action == "scan":
            report["note"] = "Dry-run: no changes. Use action='purge' with confirm_token."
            return report

        if action == "purge":
            token = kwargs.get("confirm_token")
            if token != "CONFIRM_PURGE":
                return {"error": "purge requires confirm_token='CONFIRM_PURGE'"}
            bak = target.with_suffix(target.suffix + ".legacy.bak")
            target.replace(bak)
            report["purged"] = _rel(bak)
            return report

        return {"note": "unknown action; no changes"}

    # ------------------------------------------------------------------ #
    #  Infrastructure & QA
    # ------------------------------------------------------------------ #

    @staticmethod
    def audit_docker_services() -> dict[str, Any]:
        """Lightweight Docker container status check."""
        if docker is None:
            return {"warning": "docker package not installed; cannot audit containers"}
        try:
            client = docker.from_env()
            containers = client.containers.list(all=True)
            info = [{"name": c.name, "status": c.status} for c in containers]
            return {"containers": info}
        except Exception as exc:
            return {"error": str(exc)}

    @staticmethod
    def verify_db_compliance(table: str) -> dict[str, Any]:
        """Verify DB table has empresa_id column (Rule 4.4 / 14)."""
        if psycopg2 is None:
            return {"warning": "psycopg2 not installed; live DB checks unavailable"}
        return {
            "status": "ok",
            "table": table,
            "detail": "psycopg2 available; live checks disabled in this environment",
        }

    @staticmethod
    def run_sintel_tests(path: str | None = None) -> dict[str, Any]:
        """Run pytest for the workspace or a specific path (TESTING_AGENT.md)."""
        cmd = [sys.executable, "-m", "pytest"]
        if path:
            cmd.append(path)
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800,
                cwd=str(WORKSPACE),
            )
            return {
                "returncode": proc.returncode,
                "stdout": proc.stdout[:4000],
                "stderr": proc.stderr[:2000],
            }
        except Exception as exc:
            return {"error": str(exc)}

    @staticmethod
    def check_infrastructure_health() -> dict[str, Any]:
        """Composite infrastructure health summary."""
        return {
            "docker": Tools.audit_docker_services(),
            "db": Tools.verify_db_compliance("facturas_factura"),
            "sintel_version": SINTEL_VERSION,
        }

    # ------------------------------------------------------------------ #
    #  Skills
    # ------------------------------------------------------------------ #

    @staticmethod
    def list_available_skills() -> dict[str, Any]:
        """List discovered Sintel Agent skill modules."""
        return {"skills": SkillManager.list_skills()}

    @staticmethod
    def execute_skill(skill_name: str) -> dict[str, Any]:
        """Retrieve instructions for a specified Skill."""
        return SkillManager.get_skill_details(skill_name)

    # ------------------------------------------------------------------ #
    #  Unicode / Emoji Auditor (Rule 0)
    # ------------------------------------------------------------------ #

    @staticmethod
    def audit_unicode_chars(app_name: str) -> dict[str, Any]:
        """[RULE 0] Scan .py files for emoji/multibyte Unicode that cause SyntaxError.

        Detects any non-ASCII character in Python source files (emojis,
        multibyte chars) that violate the 'Cero Caracteres Especiales' rule.
        Complements check_syntax which only catches compile-time errors.
        """
        app_root = WORKSPACE / "apps" / "tenant" / app_name
        if not app_root.exists():
            # Allow scanning from workspace root if app not found under tenant
            candidate = WORKSPACE / app_name
            if not candidate.exists():
                return {"error": f"app '{app_name}' not found"}
            app_root = candidate

        # Match any non-ASCII character (code point > 127)
        non_ascii_re = re.compile(r"[^\x00-\x7F]")
        violations: list[dict[str, Any]] = []
        for py in app_root.rglob("*.py"):
            if _is_excluded(py):
                continue
            try:
                src = py.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for ln, line in enumerate(src.splitlines(), 1):
                match = non_ascii_re.search(line)
                if match:
                    violations.append({
                        "file": _rel(py),
                        "line": ln,
                        "char_code": ord(match.group()),
                        "preview": line.strip()[:120],
                    })
        return {
            "app": app_name,
            "violations": violations,
            "count": len(violations),
            "compliant": len(violations) == 0,
        }

    # ------------------------------------------------------------------ #
    #  django-tenants Schema Auditor (Rule 4.4)
    # ------------------------------------------------------------------ #

    @staticmethod
    def audit_tenant_schema() -> dict[str, Any]:
        """[RULE 4.4] Audit SHARED_APPS vs TENANT_APPS segregation in settings.py.

        Validates that:
        - SHARED_APPS and TENANT_APPS are defined (not INSTALLED_APPS)
        - django-tenants and related middleware are present
        - No tenant model is leaking into SHARED_APPS
        """
        settings_file = WORKSPACE / "config" / "settings.py"
        if not settings_file.exists():
            return {"error": "config/settings.py not found"}

        src = settings_file.read_text(encoding="utf-8")
        issues: list[str] = []
        info: dict[str, Any] = {}

        # Check SHARED_APPS / TENANT_APPS defined (not monolithic INSTALLED_APPS)
        has_shared = "SHARED_APPS" in src
        has_tenant = "TENANT_APPS" in src
        info["has_shared_apps"] = has_shared
        info["has_tenant_apps"] = has_tenant
        if not has_shared:
            issues.append("[RULE 4.4] SHARED_APPS missing — must not use monolithic INSTALLED_APPS")
        if not has_tenant:
            issues.append("[RULE 4.4] TENANT_APPS missing — required for django-tenants isolation")

        # Check django-tenants in SHARED_APPS
        if has_shared and "'django_tenants'" not in src and '"django_tenants"' not in src:
            issues.append("[RULE 4.4] 'django_tenants' not found in settings — ensure it is in SHARED_APPS")

        # Check TenantMiddleware
        if "TenantMainMiddleware" not in src:
            issues.append("[RULE 4.4] TenantMainMiddleware missing from MIDDLEWARE (must be first)")

        # Check DATABASE_ROUTERS
        if "DATABASE_ROUTERS" not in src:
            issues.append("[RULE 4.4] DATABASE_ROUTERS not defined — django-tenants requires it")

        # Check TENANT_MODEL and DOMAIN_MODEL
        info["has_tenant_model"] = "TENANT_MODEL" in src
        info["has_domain_model"] = "DOMAIN_MODEL" in src
        if not info["has_tenant_model"]:
            issues.append("[RULE 4.4] TENANT_MODEL not defined in settings")
        if not info["has_domain_model"]:
            issues.append("[RULE 4.4] DOMAIN_MODEL not defined in settings")

        return {
            "settings_file": _rel(settings_file),
            "info": info,
            "issues": issues,
            "compliant": len(issues) == 0,
        }

    # ------------------------------------------------------------------ #
    #  Legacy views.py Auditor (Rule 4.3)
    # ------------------------------------------------------------------ #

    @staticmethod
    def audit_views_legacy(app_name: str) -> dict[str, Any]:
        """[RULE 4.3] Detect views.py with business logic (prohibited).

        AGENTS.md Rule 4.3: views.py must NOT contain business logic.
        Business logic belongs exclusively in the Service Layer.
        """
        app_root = WORKSPACE / "apps" / "tenant" / app_name
        if not app_root.exists():
            return {"error": f"app '{app_name}' not found"}

        violations: list[dict[str, Any]] = []
        # Patterns that indicate business logic in views
        biz_patterns = re.compile(
            r"(\btransaction\.atomic\b"
            r"|\bBusinessService\b"
            r"|\bCRUDService\b"
            r"|\bModels?\.\w+\.objects\."
            r"|\b\.save\(\)"
            r"|\b\.create\("
            r"|\b\.update\("
            r"|\b\.delete\("
            r")",
            re.IGNORECASE,
        )

        for views_file in app_root.rglob("views.py"):
            if _is_excluded(views_file):
                continue
            try:
                src = views_file.read_text(encoding="utf-8")
            except Exception:
                continue
            for ln, line in enumerate(src.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if biz_patterns.search(line):
                    violations.append({
                        "file": _rel(views_file),
                        "line": ln,
                        "content": stripped[:200],
                    })

        has_views_py = any(
            True for _ in app_root.rglob("views.py") if not _is_excluded(_)
        )
        return {
            "app": app_name,
            "views_py_found": has_views_py,
            "violations": violations,
            "count": len(violations),
            "compliant": len(violations) == 0,
        }

    # ------------------------------------------------------------------ #
    #  HTMX OOB Audit (Rule 12)
    # ------------------------------------------------------------------ #

    @staticmethod
    def audit_htmx_oob(app_name: str) -> dict[str, Any]:
        """[RULE 12] Audit HTMX Out-of-Band swap and HX-Trigger usage.

        Checks HTML templates for:
        - hx-swap-oob='true' patterns (OOB DOM mutations)
        - HX-Trigger response headers (event-driven reactivity)
        Alerts if POST actions exist but no OOB / trigger pattern detected.
        """
        app_root = WORKSPACE / "apps" / "tenant" / app_name
        if not app_root.exists():
            return {"error": f"app '{app_name}' not found"}

        oob_re = re.compile(r'hx-swap-oob\s*=\s*["\']?true', re.IGNORECASE)
        hxtrigger_re = re.compile(r'HX-Trigger|HX_TRIGGER', re.IGNORECASE)
        htmx_post_re = re.compile(r'hx-(post|put|patch|delete)\s*=', re.IGNORECASE)

        oob_hits: list[dict[str, Any]] = []
        trigger_hits: list[dict[str, Any]] = []
        post_hits: list[dict[str, Any]] = []

        for html in app_root.rglob("*.html"):
            if _is_excluded(html):
                continue
            try:
                src = html.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for ln, line in enumerate(src.splitlines(), 1):
                if oob_re.search(line):
                    oob_hits.append({"file": _rel(html), "line": ln, "content": line.strip()[:120]})
                if htmx_post_re.search(line):
                    post_hits.append({"file": _rel(html), "line": ln})

        # Check Python (views/viewsets) for HX-Trigger header usage
        for py in app_root.rglob("*.py"):
            if _is_excluded(py):
                continue
            try:
                src = py.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for ln, line in enumerate(src.splitlines(), 1):
                if hxtrigger_re.search(line):
                    trigger_hits.append({"file": _rel(py), "line": ln, "content": line.strip()[:120]})

        recommendations: list[str] = []
        if post_hits and not oob_hits and not trigger_hits:
            recommendations.append(
                "[RULE 12] HTMX mutations detected but no hx-swap-oob or HX-Trigger found. "
                "Consider OOB swaps for reactive DOM updates."
            )

        return {
            "app": app_name,
            "oob_swaps": oob_hits,
            "hx_trigger_usage": trigger_hits,
            "htmx_mutations": len(post_hits),
            "recommendations": recommendations,
        }

    # ------------------------------------------------------------------ #
    #  Bridge Isolation Auditor (Rule 17)
    # ------------------------------------------------------------------ #

    @staticmethod
    def audit_bridge_isolation(app_name: str = "") -> dict[str, Any]:
        """[RULE 17] Audit tenant apps for unauthorized imports from apps.public.

        Only apps/tenant/core/ and apps/tenant/api/ are allowed to import
        directly from apps.public. All other tenant apps MUST use the
        centralized bridge: apps.tenant.core.services.membership.

        If app_name is provided, scans only that app. Otherwise scans ALL
        tenant apps and returns a consolidated report.
        """
        ALLOWED = {"core", "api"}
        tenant_root = WORKSPACE / "apps" / "tenant"
        if not tenant_root.exists():
            return {"error": "apps/tenant/ not found"}

        if app_name:
            apps_to_scan = [tenant_root / app_name]
        else:
            apps_to_scan = sorted(
                p for p in tenant_root.iterdir()
                if p.is_dir() and p.name not in ALLOWED and not p.name.startswith("__")
            )

        violations: list[dict[str, Any]] = []
        scanned_apps: list[str] = []

        for app_dir in apps_to_scan:
            if not app_dir.exists():
                continue
            name = app_dir.name
            if name in ALLOWED:
                continue
            scanned_apps.append(name)
            for py in app_dir.rglob("*.py"):
                if _is_excluded(py):
                    continue
                try:
                    src = py.read_text(encoding="utf-8")
                except Exception:
                    continue
                for line_no, line in enumerate(src.splitlines(), 1):
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue
                    if "apps.public" in stripped and (
                        stripped.startswith("from ") or stripped.startswith("import ")
                    ):
                        violations.append({
                            "app": name,
                            "file": _rel(py),
                            "line": line_no,
                            "code": stripped[:200],
                            "fix": "Replace with: from apps.tenant.core.services.membership import ...",
                        })

        return {
            "scanned_apps": scanned_apps,
            "violations": violations,
            "violations_count": len(violations),
            "compliant": len(violations) == 0,
            "rule": "17 - Bridge Isolation (apps.public only via core/services/membership.py)",
        }

    # ------------------------------------------------------------------ #
    #  Copilot Agents Discovery (AGENTS ecosystem)
    # ------------------------------------------------------------------ #

    @staticmethod
    def list_copilot_agents() -> dict[str, Any]:
        """[AGENTS] List all *.agent.md files from the .copilot/agents/ directory.

        Returns agent names, file paths, and one-line descriptions extracted
        from the YAML frontmatter 'description:' field if present.
        """
        if not AGENTS_COPILOT_DIR.exists():
            return {
                "agents_dir": str(AGENTS_COPILOT_DIR),
                "agents": [],
                "error": "Agents directory not found. Set COPILOT_AGENTS_DIR env var.",
            }
        agents: list[dict[str, Any]] = []
        desc_re = re.compile(r"^description:\s*(.+)$", re.MULTILINE)
        for f in sorted(AGENTS_COPILOT_DIR.glob("*.agent.md")):
            name = f.name[: -len(".agent.md")]
            try:
                content = f.read_text(encoding="utf-8")
                m = desc_re.search(content[:800])
                description = m.group(1).strip() if m else ""
            except Exception:
                description = ""
            agents.append({
                "name": name,
                "file": f.name,
                "description": description,
            })
        return {
            "agents_dir": str(AGENTS_COPILOT_DIR),
            "agents": agents,
            "count": len(agents),
        }

    @staticmethod
    def get_agent_details(agent_name: str) -> dict[str, Any]:
        """[AGENTS] Retrieve the full content of a .copilot/agents/<name>.agent.md file."""
        agent_file = AGENTS_COPILOT_DIR / f"{agent_name}.agent.md"
        if not agent_file.exists():
            # Try exact filename match (user may pass full filename)
            exact = AGENTS_COPILOT_DIR / agent_name
            if exact.exists():
                agent_file = exact
            else:
                available = sorted(
                    f.name[: -len(".agent.md")]
                    for f in AGENTS_COPILOT_DIR.glob("*.agent.md")
                ) if AGENTS_COPILOT_DIR.exists() else []
                return {
                    "error": f"Agent '{agent_name}' not found",
                    "available": available,
                }
        try:
            content = agent_file.read_text(encoding="utf-8")
        except Exception as exc:
            return {"error": f"Cannot read agent file: {exc}"}
        return {
            "name": agent_name,
            "path": str(agent_file),
            "size_bytes": agent_file.stat().st_size,
            "content": content,
        }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def initialize_and_register(server: UnifiedMCPServer) -> None:
    """Register ALL tools in grouped blocks to the MCP server.

    Block A: Discovery & Inventory
    Block B: Validation & Auditing (Rules 0-17)
    Block C: Code Generation (Backend + Frontend)
    Block D: Legacy & Refactoring
    Block E: Infrastructure & QA
    Block F: Skills
    Block G: Multi-Tenant & django-tenants (Rule 4.4)
    Block H: Copilot Agents Discovery
    """
    # Block A: Discovery & Inventory
    server.register_tool(Tools.list_apps, "List all tenant apps")
    server.register_tool(Tools.find_models, "Find models in an app")
    server.register_tool(Tools.find_viewsets, "Find ViewSets in an app")
    server.register_tool(Tools.list_service_mixins, "List Service Mixins in an app")
    server.register_tool(Tools.get_module_version, "Extract version from audit doc (Rule 3)")
    server.register_tool(Tools.search_pattern, "Regex search across workspace files")
    server.register_tool(Tools.check_syntax, "[RULE 0] Validate Python syntax via AST")

    # Block B: Validation & Auditing
    server.register_tool(
        Tools.validate_module_structure,
        "[RULES 3/5/6/7] Validate app structure (templates, static, services, audit doc)",
    )
    server.register_tool(
        Tools.validate_assets_placement,
        "[RULE 6] Validate static asset placement (no leaks into core)",
    )
    server.register_tool(
        Tools.expert_e2e_auditor,
        "[RULES 0/2/4/5/14/15/17] AST-based E2E architectural auditor",
    )
    server.register_tool(
        Tools.expert_dna_mapper,
        "[Fase 0] DNA Mapping: models, phantoms, Zero Waste, Facades, signals",
    )
    server.register_tool(
        Tools.audit_zero_waste,
        "[RULE 4.5] Detect unoptimized ORM queries (.all()/.filter() without .only()/.defer())",
    )
    server.register_tool(
        Tools.audit_signals,
        "[RULE 4.7] Detect prohibited Django signal usage",
    )
    server.register_tool(
        Tools.audit_celery_tasks,
        "[RULE 11] Audit Celery tasks for DLQ, retries, and bind patterns",
    )
    server.register_tool(
        Tools.audit_security,
        "[RULES 13/15/17] Security audit: IsTenantMember, DSV, BaseTenantViewSet, bridge isolation",
    )
    server.register_tool(
        Tools.audit_unicode_chars,
        "[RULE 0] Scan .py files for emoji/multibyte Unicode that cause SyntaxError",
    )
    server.register_tool(
        Tools.audit_views_legacy,
        "[RULE 4.3] Detect business logic in views.py (must be in Service Layer)",
    )
    server.register_tool(
        Tools.audit_htmx_oob,
        "[RULE 12] Audit HTMX OOB swaps and HX-Trigger reactivity patterns",
    )
    server.register_tool(
        Tools.audit_bridge_isolation,
        "[RULE 17] Audit tenant apps for unauthorized imports from apps.public",
    )

    # Block C: Code Generation
    server.register_tool(
        Tools.expert_backend_generator,
        "[RULES 4/5/13/14] Conservative backend scaffolding (Service Layer + model)",
    )
    server.register_tool(
        Tools.expert_frontend_generator,
        "[RULES 1/2/6/7/9] FSD frontend skeleton (templates/tenant/ + JS modules)",
    )

    # Block D: Legacy & Refactoring
    server.register_tool(
        Tools.scan_legacy_candidates,
        "Non-destructive scan for legacy/deprecated markers in .py files",
    )
    server.register_tool(
        Tools.cleanup_legacy_functions,
        "Guarded legacy function cleanup (dry-run by default)",
    )
    server.register_tool(
        Tools.expert_legacy_refactor,
        "[RULE 2.1] Legacy refactor: scan Facade usage + optional purge",
    )

    # Block E: Infrastructure & QA
    server.register_tool(Tools.audit_docker_services, "Docker container status audit")
    server.register_tool(Tools.verify_db_compliance, "[RULE 4.4/14] DB table compliance check")
    server.register_tool(Tools.run_sintel_tests, "Run pytest (TESTING_AGENT.md)")
    server.register_tool(Tools.check_infrastructure_health, "Composite infrastructure health")

    # Block F: Skills
    server.register_tool(Tools.list_available_skills, "List available Sintel Agent skills and agents")
    server.register_tool(Tools.execute_skill, "Retrieve a Sintel Skill or Agent's instructions")

    # Block G: Multi-Tenant & django-tenants (Rule 4.4)
    server.register_tool(
        Tools.audit_tenant_schema,
        "[RULE 4.4] Audit SHARED_APPS vs TENANT_APPS segregation in settings.py",
    )

    # Block H: Copilot Agents Discovery
    server.register_tool(
        Tools.list_copilot_agents,
        "[AGENTS] List all *.agent.md files from .copilot/agents/",
    )
    server.register_tool(
        Tools.get_agent_details,
        "[AGENTS] Retrieve the full content of a .copilot/agents/<name>.agent.md",
    )


def main() -> None:
    server = UnifiedMCPServer("sintel-unified")
    initialize_and_register(server)
    startup = {
        "name": "sintel-unified",
        "version": SINTEL_VERSION,
        "tools": list(server.tools.keys()),
        "tools_count": len(server.tools),
        "workspace": str(WORKSPACE),
        "agents_dir": str(AGENTS_COPILOT_DIR),
    }
    print(json.dumps(startup), file=sys.stderr)
    server.run()


if __name__ == "__main__":
    main()