"""
EKG extractor: AGENTS.md sections, MEMORY.md ADRs, docs/ADR-*.md,
.agents/skills/**/*.md, and an app's own .agent/AUDITORIA_*.md.

AGENTS.md/MEMORY.md/skills use a plain, fixed heading convention
(`## [TAG] N. Title`) - splitting on it is markdown structure parsing, the
same kind of narrow scoped exception documented in extract_templates.py, not
a stand-in for AST analysis of code.

Linking a Rule/Document to an Application is deliberately conservative so
the graph does not invent relationships the source text does not support:
  - A section is linked to every tenant app ONLY if AGENTS.md itself
    declares it universally binding (UNIVERSAL_RULE_TAGS below, each one
    checked against the section actually saying "todos los ViewSets" /
    "todo modelo tenant" / equivalent - see tools/ekg/PILOT_REPORT.md).
  - Otherwise a section/document is linked to an app only when that app's
    name is mentioned in its text (e.g. a skill doc naming "compras"
    explicitly), or when the document is the app's own `.agent/` audit doc.
  - This is why .agents/skills/frontend/tabulator.md is extracted as a Rule
    node but NOT linked to `compras`: compras migrated off Tabulator
    (MEMORY.md ADR-006) and tabulator.md's text does not mention compras -
    the graph correctly stays silent instead of asserting a stale relation.
"""

from __future__ import annotations

import re
from pathlib import Path

from tools.ekg import schema

SECTION_RE = re.compile(r"^## \[([A-Z0-9_-]+)\] (\d+)\.\s+(.+)$", re.MULTILINE)

# Sections AGENTS.md itself declares binding on every tenant app (verified
# against the quoted text in tools/ekg/PILOT_REPORT.md's research notes -
# not an assumption made by this extractor).
UNIVERSAL_RULE_TAGS = frozenset(
    {
        "CRITICAL",       # 0. no special chars in .py - applies to all python files
        "CORE-DB",        # 14. every tenant model must inherit SintelTenantBaseModel
        "CRUD-E2E",       # 5. Service Layer flow - all apps
        "ARCHITECTURE",   # 7. FSD - "cada modelo... su propio ecosistema"
        "SECURITY",       # 15. dual-auth - "BaseTenantViewSet... nunca override"
        "BRIDGE",         # 17. cross-schema bridge - all tenant apps except core
        "HTMX-OFFCANVAS", # 26. offcanvas anti-backdrop pattern - all apps
        "JS-ISOLATION",   # 23. CSS/JS isolation per app
        "CSS-ISOLATION",  # 22.
        "UUID-FORMS",     # 27. no parseInt on UUID selects
        "ORM-SELECTORS",  # 30. selector/serializer constants pattern
        "TESTING",        # 24. multi-tenant test patterns
    }
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _split_sections(text: str) -> list[tuple[str, str, str, int, str]]:
    """Return (tag, number, title, line, body) for each `## [TAG] N. Title`
    section, body running until the next same-level heading."""
    matches = list(SECTION_RE.finditer(text))
    sections = []
    for i, m in enumerate(matches):
        tag, number, title = m.group(1), m.group(2), m.group(3).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        line = text.count("\n", 0, m.start()) + 1
        sections.append((tag, number, title, line, body[:4000]))
    return sections


def extract_agents_md(project_root: Path, app_names: list[str]) -> schema.Graph:
    graph = schema.Graph()
    path = project_root / "AGENTS.md"
    if not path.exists():
        return graph
    text = _read(path)
    rel_path = path.relative_to(project_root).as_posix()

    for tag, number, title, line, body in _split_sections(text):
        rule_node_id = schema.rule_id(rel_path, f"{number}-{tag}")
        graph.add_node(
            schema.Node(
                rule_node_id,
                schema.NODE_RULE,
                {
                    "source": rel_path,
                    "tag": tag,
                    "number": number,
                    "title": title,
                    "line": line,
                    "body": body,
                },
            )
        )
        for app_name in app_names:
            if tag in UNIVERSAL_RULE_TAGS or app_name in body:
                app_node_id = schema.application_id(app_name)
                graph.add_node(schema.Node(app_node_id, schema.NODE_APPLICATION, {"name": app_name}))
                graph.add_edge(schema.Edge(app_node_id, rule_node_id, schema.REL_GOVERNED_BY))

    return graph


def extract_memory_md(project_root: Path, app_names: list[str]) -> schema.Graph:
    graph = schema.Graph()
    path = project_root / "MEMORY.md"
    if not path.exists():
        return graph
    text = _read(path)
    rel_path = path.relative_to(project_root).as_posix()

    adr_re = re.compile(r"^\*\s+\*\*ADR-(\d+):\s*(.+?)\*\*\s*$", re.MULTILINE)
    matches = list(adr_re.finditer(text))
    for i, m in enumerate(matches):
        number, title = m.group(1), m.group(2).strip(" *-")
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end() : end].strip()
        doc_node_id = schema.document_id(rel_path, f"ADR-{number}")
        line = text.count("\n", 0, m.start()) + 1
        graph.add_node(
            schema.Node(
                doc_node_id,
                schema.NODE_DOCUMENT,
                {"source": rel_path, "adr": f"ADR-{number}", "title": title, "line": line, "body": body[:2000]},
            )
        )
        for app_name in app_names:
            if app_name in title or app_name in body:
                app_node_id = schema.application_id(app_name)
                graph.add_node(schema.Node(app_node_id, schema.NODE_APPLICATION, {"name": app_name}))
                graph.add_edge(schema.Edge(app_node_id, doc_node_id, schema.REL_DOCUMENTED_BY))

    return graph


def extract_adr_docs(project_root: Path, app_names: list[str]) -> schema.Graph:
    graph = schema.Graph()
    docs_dir = project_root / "docs"
    if not docs_dir.exists():
        return graph

    for path in sorted(docs_dir.glob("ADR-*.md")):
        text = _read(path)
        rel_path = path.relative_to(project_root).as_posix()
        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else path.stem
        doc_node_id = schema.document_id(rel_path)
        graph.add_node(
            schema.Node(doc_node_id, schema.NODE_DOCUMENT, {"source": rel_path, "title": title})
        )
        for app_name in app_names:
            if app_name in text:
                app_node_id = schema.application_id(app_name)
                graph.add_node(schema.Node(app_node_id, schema.NODE_APPLICATION, {"name": app_name}))
                graph.add_edge(schema.Edge(app_node_id, doc_node_id, schema.REL_DOCUMENTED_BY))

    return graph


def extract_skills(project_root: Path, app_names: list[str]) -> schema.Graph:
    graph = schema.Graph()
    skills_dir = project_root / ".agents" / "skills"
    if not skills_dir.exists():
        return graph

    for path in sorted(skills_dir.rglob("*.md")):
        if path.name == "README.md":
            continue
        text = _read(path)
        rel_path = path.relative_to(project_root).as_posix()
        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else path.stem
        rule_node_id = schema.rule_id(rel_path, "skill")
        graph.add_node(
            schema.Node(rule_node_id, schema.NODE_RULE, {"source": rel_path, "title": title})
        )
        for app_name in app_names:
            if app_name in text:
                app_node_id = schema.application_id(app_name)
                graph.add_node(schema.Node(app_node_id, schema.NODE_APPLICATION, {"name": app_name}))
                graph.add_edge(schema.Edge(app_node_id, rule_node_id, schema.REL_GOVERNED_BY))

    return graph


def extract_app_audit_doc(
    app_name: str, project_root: Path, schema_root: str = "tenant", folder_name: str | None = None
) -> schema.Graph:
    """`app_name`/`folder_name` split for the same reason as
    extract_python.py's extract_app_python() - see its docstring."""
    graph = schema.Graph()
    agent_dir = project_root / "apps" / schema_root / (folder_name or app_name) / ".agent"
    if not agent_dir.exists():
        return graph

    app_node_id = schema.application_id(app_name)
    graph.add_node(schema.Node(app_node_id, schema.NODE_APPLICATION, {"name": app_name}))

    for path in sorted(agent_dir.glob("*.md")):
        text = _read(path)
        rel_path = path.relative_to(project_root).as_posix()
        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else path.stem
        doc_node_id = schema.document_id(rel_path)
        graph.add_node(
            schema.Node(doc_node_id, schema.NODE_DOCUMENT, {"source": rel_path, "title": title})
        )
        graph.add_edge(schema.Edge(app_node_id, doc_node_id, schema.REL_DOCUMENTED_BY))

    return graph
