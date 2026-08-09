"""
F15 - Grafo de dependencias inter-app (F15.1-F15.3): descubre imports REALES
entre apps tenant (AST, no grep de texto), clasifica cada arista, y detecta
ciclos. Extiende tools/organizational_governance/ (no un modulo separado
sin relacion - construye sobre extract.py/graph.py ya existentes).
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from tools.organizational_governance.extract import TENANT_APPS_DIR, discover_tenant_apps

# Clasificacion (F15.2) - alineada al vocabulario pedido por el prompt maestro.
ALLOWED = "ALLOWED"
CONTROLLED = "CONTROLLED"
SOFT_REFERENCE = "SOFT_REFERENCE"
BRIDGE = "BRIDGE"
DTO = "DTO"
PULL = "PULL"
PUSH_CONTROLLED = "PUSH_CONTROLLED"
FORBIDDEN = "FORBIDDEN"
CIRCULAR = "CIRCULAR"
UNKNOWN = "UNKNOWN"

# Simbolos conocidos, documentados por auditorias reales de esta misma
# consolidacion - no una lista inventada aqui. Ver documentacion/FACTURAS_AUDIT.md,
# VENTAS_FACTURAS_AUDIT.md.
KNOWN_INTERAPP_API_SYMBOLS = frozenset({"FacturaInterAppAPI"})

# Apps de infraestructura - importarlas desde cualquier app de negocio es
# ALLOWED por diseño (AGENTS.md): no son "otra app de negocio".
INFRASTRUCTURE_APPS = frozenset({"core", "api"})


@dataclass(frozen=True)
class DependencyEdge:
    source_app: str
    target_app: str
    source_file: str
    line: int
    imported_symbol: str
    classification: str
    evidence: str


def _iter_python_files(app_dir: Path):
    for pattern in ("models.py", "services/*.py", "services/**/*.py", "api/*.py", "views.py", "tables.py", "ui_views.py"):
        yield from app_dir.glob(pattern)


def _classify_import(source_app: str, target_app: str, module: str, names: list[str], source_text: str) -> tuple[str, str]:
    """Heuristica basada en las convenciones YA establecidas y auditadas de
    este proyecto (no inventadas aqui) - ver documentacion/FACTURAS_AUDIT.md
    §1/§3, documentacion/VENTAS_FACTURAS_AUDIT.md, y AGENTS.md §17/§18.

    [Corregido tras verificacion manual real - ver documentacion/F15_INTEGRATION_BASELINE.md
    "Correcciones aplicadas al clasificador"] La primera version marcaba
    TODO import de otro *.services.business_service como FORBIDDEN sin
    distinguir un bypass real de un llamado a metodo con `empresa_id`
    explicito (Service Layer real, solo que "empuja" en vez de "solo lee") -
    ej. ventas->facturas.FacturaBusinessService.crear_factura_desde_venta()
    es EXACTAMENTE el contrato ya sancionado en VENTAS_FACTURAS_AUDIT.md, no
    una violacion. Ahora se busca `empresa_id=` como argumento nombrado
    cerca del import (mismo archivo) antes de decidir FORBIDDEN."""
    joined_names = " ".join(names)
    if target_app in INFRASTRUCTURE_APPS:
        return ALLOWED, "app de infraestructura (core/api), permitido por AGENTS.md"
    if source_app in INFRASTRUCTURE_APPS:
        # core/ orquesta flujos cross-cutting reales (auth, onboarding,
        # bridge) - ver apps/services/onboarding/empresa_service.py, ya
        # auditado en OCF_OSF_BASELINE.md como patron legitimo. Se marca
        # PUSH_CONTROLLED con nota de revision, no FORBIDDEN a ciegas.
        return PUSH_CONTROLLED, f"core/api orquesta {joined_names} de '{target_app}' (patron cross-cutting ya establecido - onboarding/auth) - verificar manualmente que la instancia Empresa/objeto se resuelve server-side, no de input de usuario"
    if any(n in KNOWN_INTERAPP_API_SYMBOLS for n in names):
        return PULL, f"API inter-app documentada explicitamente como [ABIERTO]/Pull: {joined_names} (ver FACTURAS_AUDIT.md §2)"
    if "Bridge" in joined_names or "Bridge" in module:
        return BRIDGE, f"importa simbolo con forma de Bridge: {joined_names}"
    if "extractor" in module.lower() or "Extractor" in joined_names:
        return PULL, f"importa modulo/simbolo de extractor (Pull Model): {module}.{joined_names}"
    if "RetencionesService" in joined_names:
        return PULL, "RetencionesService es el punto de lectura sancionado del Pull Model de retenciones (ADR-001, arquitectura_general.md §6.7)"
    if module.endswith(".services.selectors") and any(n.endswith("Selector") for n in names):
        return CONTROLLED, f"importa un Selector de otra app ({joined_names}) - mismo patron Bounded Context que import directo de modelo, pero ya encapsula .only()/empresa_id internamente"
    if target_app == "empresa" and "Empresa" in names and module.endswith(".models"):
        return CONTROLLED, "Empresa es el singleton del tenant (no tiene su propio empresa_id) - resolverlo desde otra app es el patron establecido en las 17 apps (SintelDSVMixin._get_empresa())"
    if module.endswith(".models") and "empresa_id" in source_text:
        return CONTROLLED, "import directo de modelo + filtro empresa_id detectado en el mismo archivo (patron Bounded Context, AGENTS.md §18)"
    if module.endswith(".models"):
        return UNKNOWN, "import directo de modelo sin evidencia de filtro empresa_id cercano - requiere revision manual"
    if ".services.business_service" in module or ".services.crud_service" in module:
        if "empresa_id=" in source_text or "empresa_id =" in source_text:
            return PUSH_CONTROLLED, f"llama a {joined_names} de otra app con empresa_id explicito (Service Layer real, no bypass ORM)"
        return FORBIDDEN, f"import directo de Business/CRUDService de otra app ({module}) sin empresa_id explicito detectado - posible bypass del patron Bridge/Soft Reference"
    if "DTO" in joined_names or module.endswith(".dtos"):
        return DTO, f"importa un DTO: {joined_names}"
    return UNKNOWN, f"import de {module} sin patron reconocido - requiere revision manual"


def discover_dependency_edges() -> list[DependencyEdge]:
    apps = discover_tenant_apps()
    edges: list[DependencyEdge] = []
    for source_app in apps:
        app_dir = TENANT_APPS_DIR / source_app
        seen_files = set()
        for path in _iter_python_files(app_dir):
            if path in seen_files or not path.is_file():
                continue
            seen_files.add(path)
            text = path.read_text(encoding="utf-8")
            try:
                tree = ast.parse(text, filename=str(path))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom) or not node.module:
                    continue
                if not node.module.startswith("apps.tenant."):
                    continue
                parts = node.module.split(".")
                if len(parts) < 3:
                    continue
                target_app = parts[2]
                if target_app == source_app:
                    continue
                names = [alias.name for alias in node.names]
                classification, evidence = _classify_import(source_app, target_app, node.module, names, text)
                edges.append(
                    DependencyEdge(
                        source_app=source_app,
                        target_app=target_app,
                        source_file=str(path.relative_to(TENANT_APPS_DIR.parent.parent)),
                        line=node.lineno,
                        imported_symbol=", ".join(names),
                        classification=classification,
                        evidence=evidence,
                    )
                )
    return edges


def detect_cycles(edges: list[DependencyEdge]) -> list[list[str]]:
    """[F15.3] DFS estandar sobre el grafo App->App (ignorando ALLOWED hacia
    infraestructura, que no participa en ciclos de negocio)."""
    adjacency: dict[str, set[str]] = {}
    for e in edges:
        if e.classification == ALLOWED:
            continue
        adjacency.setdefault(e.source_app, set()).add(e.target_app)

    cycles: list[list[str]] = []
    visited: set[str] = set()

    def dfs(node: str, stack: list[str]) -> None:
        if node in stack:
            cycle = stack[stack.index(node):] + [node]
            normalized = tuple(sorted(set(cycle)))
            if not any(tuple(sorted(set(c))) == normalized for c in cycles):
                cycles.append(cycle)
            return
        if node in visited:
            return
        visited.add(node)
        for neighbor in sorted(adjacency.get(node, ())):
            dfs(neighbor, stack + [node])

    for app in sorted(adjacency):
        dfs(app, [])
    return cycles
