"""
EKG visualization (Fase 9 of the spec): a single, self-contained, offline
HTML file that lets a human navigate the full merged graph - search any
node by name/path, open it, see its properties, and jump to every node it
points to or is pointed at from, one click at a time ("Todo navegable").

Scope, stated honestly (see tools/ekg/schema.py's NODE_LABELS/REL_TYPES -
the single source of truth for what this graph actually models):
  covered    : Project, Application, Model, Field, Service, ViewSet,
               Serializer, Endpoint, Template, JS, Rule, Document, Test,
               Setting, Docker - i.e. "Arquitectura, Dependencias, Apps,
               Modelos, Servicios, API, Frontend, Documentacion" from the
               original spec's Fase 9 list.
  NOT covered: Celery tasks, domain events/signals, and permission classes
               per endpoint are not extracted as graph data by any
               extractor today (see governance.py's module docstring for
               the same boundary on the rules side) - this explorer does
               not show tabs for them because that data does not exist in
               the graph; inventing placeholder nodes here would be
               exactly the "documentacion ficticia" the spec prohibits.

No new dependency: the page is vanilla HTML/CSS/JS, no CDN, so it opens
directly from disk (file://) with no server and no network access.

CLI: python -m tools.ekg.export_html [--output PATH]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.ekg import schema
from tools.ekg.impact import OUT_DIR, PILOT_APPS, PUBLIC_APPS, load_full_offline_graph

DEFAULT_OUTPUT = OUT_DIR / "graph_explorer.html"

_LABEL_ORDER = [
    schema.NODE_APPLICATION,
    schema.NODE_MODEL,
    schema.NODE_FIELD,
    schema.NODE_SERVICE,
    schema.NODE_VIEWSET,
    schema.NODE_SERIALIZER,
    schema.NODE_ENDPOINT,
    schema.NODE_TEMPLATE,
    schema.NODE_JS,
    schema.NODE_RULE,
    schema.NODE_DOCUMENT,
    schema.NODE_TEST,
    schema.NODE_SETTING,
    schema.NODE_DOCKER,
    schema.NODE_PROJECT,
]


def _display_name(properties: dict) -> str:
    return (
        properties.get("name")
        or properties.get("path")
        or properties.get("route")
        or properties.get("defined_in")
        or ""
    )


def build_export_data(graph: schema.Graph) -> dict:
    raw = schema.graph_to_jsonable(graph)
    nodes = []
    for n in raw["nodes"]:
        nodes.append(
            {
                "id": n["id"],
                "label": n["label"],
                "display": _display_name(n["properties"]) or n["id"],
                "properties": n["properties"],
            }
        )
    nodes.sort(key=lambda n: (n["label"], n["display"].lower()))

    label_counts: dict[str, int] = {}
    for n in nodes:
        label_counts[n["label"]] = label_counts.get(n["label"], 0) + 1

    return {
        "nodes": nodes,
        "edges": raw["edges"],
        "label_order": [l for l in _LABEL_ORDER if l in label_counts],
        "label_counts": label_counts,
        "apps_merged": list(PILOT_APPS + PUBLIC_APPS),
    }


_HTML_TEMPLATE = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>SINTEL EKG - Explorador del Grafo de Conocimiento</title>
<style>
  :root { color-scheme: light dark; }
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: -apple-system, Segoe UI, Roboto, sans-serif;
    display: grid; grid-template-columns: 300px 340px 1fr; height: 100vh;
    background: #0f1115; color: #e6e6e6;
  }
  .panel { overflow-y: auto; border-right: 1px solid #2a2d34; padding: 12px; }
  h1 { font-size: 14px; margin: 0 0 10px; color: #9fd3ff; }
  .meta { font-size: 11px; color: #888; margin-bottom: 12px; line-height: 1.5; }
  input[type=search] {
    width: 100%; padding: 6px 8px; margin-bottom: 10px; border-radius: 6px;
    border: 1px solid #3a3d44; background: #1a1c22; color: #e6e6e6;
  }
  .label-item, .node-item { padding: 5px 8px; border-radius: 5px; cursor: pointer; font-size: 12.5px; }
  .label-item:hover, .node-item:hover { background: #1e2128; }
  .label-item.active { background: #24405c; color: #cde8ff; }
  .count { float: right; color: #777; }
  .node-item .lbl { color: #7fb3e0; font-size: 10.5px; margin-right: 4px; }
  #detail { padding: 16px; overflow-y: auto; }
  .prop-table { width: 100%; border-collapse: collapse; margin: 10px 0 18px; font-size: 12px; }
  .prop-table td { border-bottom: 1px solid #23262d; padding: 4px 6px; vertical-align: top; }
  .prop-table td:first-child { color: #999; width: 160px; white-space: nowrap; }
  .badge { display: inline-block; background: #24405c; color: #cde8ff; padding: 2px 8px;
           border-radius: 10px; font-size: 11px; margin-right: 6px; }
  .section-title { font-size: 12px; text-transform: uppercase; letter-spacing: .04em;
                    color: #888; margin: 18px 0 6px; }
  .edge-row { padding: 4px 0; font-size: 12.5px; border-bottom: 1px solid #1c1e24; cursor: pointer; }
  .edge-row:hover { color: #9fd3ff; }
  .rel { color: #d6a95f; font-size: 10.5px; margin-right: 6px; }
  .empty { color: #666; font-size: 12px; font-style: italic; }
  a, a:visited { color: #9fd3ff; }
</style>
</head>
<body>
  <div class="panel" id="labels"></div>
  <div class="panel">
    <input type="search" id="search" placeholder="Buscar por nombre/ruta...">
    <div id="node-list"></div>
  </div>
  <div id="detail"></div>

<script>
const DATA = __GRAPH_JSON__;

const byId = {};
for (const n of DATA.nodes) byId[n.id] = n;

const outEdges = {}, inEdges = {};
for (const e of DATA.edges) {
  (outEdges[e.source_id] ||= []).push(e);
  (inEdges[e.target_id] ||= []).push(e);
}

let activeLabel = null;

function renderLabels() {
  const el = document.getElementById('labels');
  el.innerHTML = '<h1>SINTEL - Grafo de Conocimiento</h1>' +
    '<div class="meta">' + DATA.nodes.length + ' nodos, ' + DATA.edges.length +
    ' relaciones<br>' + DATA.apps_merged.length + ' apps fusionadas' +
    '<br><br><b>No modelado</b> (sin datos en el grafo): tareas Celery, ' +
    'eventos/signals, permisos por endpoint.</div>';
  const all = document.createElement('div');
  all.className = 'label-item' + (activeLabel === null ? ' active' : '');
  all.textContent = 'Todos';
  all.innerHTML += '<span class="count">' + DATA.nodes.length + '</span>';
  all.onclick = () => { activeLabel = null; renderLabels(); renderList(); };
  el.appendChild(all);
  for (const label of DATA.label_order) {
    const div = document.createElement('div');
    div.className = 'label-item' + (activeLabel === label ? ' active' : '');
    div.innerHTML = label + '<span class="count">' + DATA.label_counts[label] + '</span>';
    div.onclick = () => { activeLabel = label; renderLabels(); renderList(); };
    el.appendChild(div);
  }
}

function renderList() {
  const q = document.getElementById('search').value.trim().toLowerCase();
  const el = document.getElementById('node-list');
  el.innerHTML = '';
  let shown = 0;
  for (const n of DATA.nodes) {
    if (activeLabel && n.label !== activeLabel) continue;
    if (q && !n.display.toLowerCase().includes(q) && !n.id.toLowerCase().includes(q)) continue;
    if (++shown > 500) break;
    const div = document.createElement('div');
    div.className = 'node-item';
    div.innerHTML = '<span class="lbl">' + n.label + '</span>' + escapeHtml(n.display);
    div.onclick = () => { location.hash = '#' + encodeURIComponent(n.id); };
    el.appendChild(div);
  }
  if (shown === 0) el.innerHTML = '<div class="empty">Sin resultados.</div>';
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
}

function renderDetail() {
  const id = decodeURIComponent(location.hash.slice(1));
  const el = document.getElementById('detail');
  if (!id || !byId[id]) {
    el.innerHTML = '<div class="empty">Selecciona un nodo de la lista para ver sus detalles y relaciones.</div>';
    return;
  }
  const n = byId[id];
  let html = '<span class="badge">' + n.label + '</span><h1 style="display:inline;font-size:18px;color:#fff">' +
             escapeHtml(n.display) + '</h1>';
  html += '<table class="prop-table"><tr><td>id</td><td>' + escapeHtml(n.id) + '</td></tr>';
  for (const [k, v] of Object.entries(n.properties)) {
    html += '<tr><td>' + escapeHtml(k) + '</td><td>' + escapeHtml(JSON.stringify(v)) + '</td></tr>';
  }
  html += '</table>';

  html += '<div class="section-title">Relaciones salientes (' + (outEdges[id] || []).length + ')</div>';
  html += renderEdgeList(outEdges[id] || [], 'target_id');

  html += '<div class="section-title">Relaciones entrantes (' + (inEdges[id] || []).length + ')</div>';
  html += renderEdgeList(inEdges[id] || [], 'source_id');

  el.innerHTML = html;
  el.querySelectorAll('.edge-row[data-nav]').forEach(row => {
    row.onclick = () => { location.hash = '#' + encodeURIComponent(row.dataset.nav); };
  });
}

function renderEdgeList(edges, otherKey) {
  if (!edges.length) return '<div class="empty">Ninguna.</div>';
  let html = '';
  for (const e of edges) {
    const other = byId[e[otherKey]];
    const label = other ? (other.label + ': ' + other.display) : e[otherKey];
    html += '<div class="edge-row" data-nav="' + escapeHtml(e[otherKey]) + '">' +
            '<span class="rel">' + e.rel_type + '</span>' + escapeHtml(label) + '</div>';
  }
  return html;
}

document.getElementById('search').addEventListener('input', renderList);
window.addEventListener('hashchange', renderDetail);
renderLabels();
renderList();
renderDetail();
</script>
</body>
</html>
"""


def render_html(data: dict) -> str:
    # Several Rule/Document node "body" properties are raw markdown pulled
    # verbatim from AGENTS.md/.agent docs, which include literal code
    # examples like "<script>" - an HTML parser closes the real <script>
    # block on the first "</script" substring it sees, script tag or not,
    # even inside a JS string literal. Escaping "</" to "<\/" keeps the JSON
    # value byte-identical once JS parses it back, while making it
    # invisible to the HTML tokenizer.
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return _HTML_TEMPLATE.replace("__GRAPH_JSON__", payload)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export the merged EKG graph to a self-contained, offline HTML explorer."
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output HTML file path")
    args = parser.parse_args()

    graph = load_full_offline_graph()
    data = build_export_data(graph)
    html = render_html(data)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"[export_html] {graph.node_count()} nodes, {graph.edge_count()} edges -> {output_path}")


if __name__ == "__main__":
    main()
