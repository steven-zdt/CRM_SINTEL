"""
EKG extractor: templates/tenant/<app>/**/*.html.

Django templates are not valid HTML and have no mature Tree-sitter grammar
in this stack, so this extractor uses the stdlib `html.parser.HTMLParser`
for tag/attribute structure, plus one narrow, explicitly-scoped regex for
`{% include "..." %}` tags only (Django template syntax is not tag-based
HTML, so a tree walker cannot see it - this is a deliberate, documented
exception to the "no regex for code structure" rule, not a shortcut around
it: it extracts a single fixed micro-grammar, not general relationships).
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

from tools.ekg import schema

INCLUDE_TAG_RE = re.compile(r"{%\s*include\s+['\"]([^'\"]+)['\"]")
SCRIPT_SRC_STATIC_RE = re.compile(r"static\s+['\"]([^'\"]+\.js)['\"]")


class _TemplateStructure(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.data_attrs: set[str] = set()
        self.script_srcs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name == "id" and value:
                self.ids.add(value)
            elif name.startswith("data-") and value:
                self.data_attrs.add(f"{name}={value}")
            elif tag == "script" and name == "src" and value:
                self.script_srcs.append(value)


def extract_app_templates(app_name: str, project_root: Path) -> schema.Graph:
    graph = schema.Graph()
    templates_dir = project_root / "apps" / "tenant" / app_name / "templates" / "tenant" / app_name
    if not templates_dir.exists():
        return graph

    app_node_id = schema.application_id(app_name)
    graph.add_node(schema.Node(app_node_id, schema.NODE_APPLICATION, {"name": app_name}))

    html_files = sorted(templates_dir.rglob("*.html"))
    for path in html_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        rel_path = path.relative_to(project_root).as_posix()

        parser = _TemplateStructure()
        parser.feed(text)

        template_node_id = schema.template_id(rel_path)
        graph.add_node(
            schema.Node(
                template_node_id,
                schema.NODE_TEMPLATE,
                {
                    "path": rel_path,
                    "ids": sorted(parser.ids),
                    "data_attrs": sorted(parser.data_attrs),
                },
            )
        )
        graph.add_edge(schema.Edge(template_node_id, app_node_id, schema.REL_BELONGS_TO))

        for included in INCLUDE_TAG_RE.findall(text):
            included_rel = _resolve_django_template_ref(included, project_root)
            if included_rel is not None:
                included_id = schema.template_id(included_rel)
                graph.add_node(schema.Node(included_id, schema.NODE_TEMPLATE, {"path": included_rel}))
                graph.add_edge(schema.Edge(template_node_id, included_id, schema.REL_USES))

        for js_src in parser.script_srcs:
            match = SCRIPT_SRC_STATIC_RE.search(js_src) or re.search(r"([\w./-]+\.js)$", js_src)
            if match is None:
                continue
            js_rel = _resolve_static_js_ref(match.group(1), app_name, project_root)
            if js_rel is not None:
                js_node_id = schema.js_id(js_rel)
                graph.add_node(schema.Node(js_node_id, schema.NODE_JS, {"path": js_rel}))
                graph.add_edge(schema.Edge(template_node_id, js_node_id, schema.REL_USES))

    return graph


def _resolve_django_template_ref(ref: str, project_root: Path) -> str | None:
    # Django template loader paths are already app-relative, e.g.
    # "tenant/compras/compras_list.html" -> apps/<tier>/<app>/templates/<ref>
    for tier in ("tenant", "public"):
        for candidate in (project_root / "apps" / tier).glob(f"*/templates/{ref}"):
            if candidate.exists():
                return candidate.relative_to(project_root).as_posix()
    return None


def _resolve_static_js_ref(js_path: str, app_name: str, project_root: Path) -> str | None:
    # {% static 'compras/js/compras.api.js' %} -> apps/tenant/<app>/static/<js_path>
    candidate = project_root / "apps" / "tenant" / app_name / "static" / js_path
    if candidate.exists():
        return candidate.relative_to(project_root).as_posix()
    return None
