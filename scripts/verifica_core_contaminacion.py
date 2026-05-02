#!/usr/bin/env python3
# verifica_core_contaminacion.py
"""
Escaneo de:
  1) Contaminación de Core: tenant/<app>/ dentro de apps/tenant/core/templates/tenant/core/partials
  2) Duplicados legacy en Core (getCookie, setTimeout visibilidad, inicialización DataTables inline, mini-http/mini-csrf fuera de lib oficial)

Salida:
  - auditoria_core_contaminacion.json
  - AUDITORIA_CORE_CONTAMINACION.md
Exit code != 0 si hay infracciones.
"""

import os
import re
import json
import sys
from datetime import datetime

ROOT = os.getcwd()
CORE_PARTIALS_DIR = os.path.join(ROOT, 'apps/tenant/core/templates/tenant/core/partials')
CORE_STATIC_DIR = os.path.join(ROOT, 'apps/tenant/core/static/tenant/core/js')

def walk(dirpath, exts=('.html', '.js', '.ts', '.mjs', '.cjs')):
    """Recorre recursivamente un directorio y retorna archivos con extensiones especificadas."""
    out = []
    if not os.path.exists(dirpath):
        return out
    for r, _, files in os.walk(dirpath):
        for f in files:
            if any(f.lower().endswith(ext) for ext in exts):
                out.append(os.path.join(r, f))
    return out

def read(p):
    """Lee un archivo y retorna su contenido."""
    try:
        with open(p, 'r', encoding='utf-8', errors='ignore') as fh:
            return fh.read()
    except Exception:
        return ''

def rel(p):
    """Retorna la ruta relativa desde ROOT."""
    return os.path.relpath(p, ROOT).replace('\\', '/')

results = {
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "contamination": [],
    "legacy": [],
    "summary": {"contamination_count": 0, "legacy_count": 0}
}

# 1) Contaminación Core (partials)
contam_regex = re.compile(r"tenant/(?!core/)[A-Za-z0-9_\-]+/?")
for f in walk(CORE_PARTIALS_DIR, ('.html',)):
    text = read(f)
    matches = sorted(set(contam_regex.findall(text)))
    if matches:
        results["contamination"].append({
            "file": rel(f),
            "matches": matches
        })

# 2) Legacy duplicado (Core partials + Core static)
legacy_patterns = [
    (re.compile(r"getCookie\(['\"]csrftoken['\"]\)"), "getCookie('csrftoken')"),
    (re.compile(r"setTimeout\s*\("), "setTimeout( (posible visibilidad inline)"),
    (re.compile(r"\.(DataTable|dataTable)\s*\(|new\s+DataTable\s*\(|\$\s*\.fn\s*\.DataTable"), "Inicialización directa DataTables (inline)")
]

core_targets = walk(CORE_PARTIALS_DIR, ('.html',)) + walk(CORE_STATIC_DIR, ('.js', '.mjs', '.cjs', '.ts'))

for f in core_targets:
    text = read(f)
    local = []
    
    for rx, label in legacy_patterns:
        if rx.search(text):
            # Para setTimeout: solo marcamos si está en templates
            if "setTimeout" in label and "/templates/" not in f.replace("\\", "/"):
                continue
            local.append(label)
    
    # fetch(...) sospechoso en Core static fuera de lib oficial
    if f.endswith(('.js', '.mjs', '.cjs', '.ts')) and '/static/tenant/core/js/' in f.replace("\\", "/") and '/static/tenant/core/js/lib/' not in f.replace("\\", "/"):
        if re.search(r"\bfetch\s*\(", text) and not re.search(r"API_HELPERS\s*\.\s*safeFetchJson", text):
            local.append("fetch directo fuera de http.js oficial (sospechoso)")
    
    if local:
        results["legacy"].append({"file": rel(f), "findings": local})

# Resumen
results["summary"]["contamination_count"] = len(results["contamination"])
results["summary"]["legacy_count"] = len(results["legacy"])

# JSON
with open(os.path.join(ROOT, "auditoria_core_contaminacion.json"), "w", encoding="utf-8") as fh:
    json.dump(results, fh, indent=2, ensure_ascii=False)

# MD
lines = []
lines.append("# Auditoría de Contaminación Core y Legacy")
lines.append(f"**Fecha:** {results['timestamp']}\n")
lines.append("## Resumen")
lines.append(f"- Contaminación Core (partials con tenant/<app>/): **{results['summary']['contamination_count']}**")
lines.append(f"- Legacy duplicado (Core): **{results['summary']['legacy_count']}**\n")
lines.append("---\n## Detalle de Contaminación (Core partials)")
if not results["contamination"]:
    lines.append("- [OK] Sin hallazgos")
else:
    for c in results["contamination"]:
        lines.append(f"- **{c['file']}**")
        lines.append(f"  - matches: {', '.join(c['matches'])}")
lines.append("\n---\n## Detalle Legacy en Core (partials/static)")
if not results["legacy"]:
    lines.append("- [OK] Sin hallazgos")
else:
    for l in results["legacy"]:
        lines.append(f"- **{l['file']}**")
        lines.append(f"  - findings: {' | '.join(l['findings'])}")

with open(os.path.join(ROOT, "AUDITORIA_CORE_CONTAMINACION.md"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))

violations = results["summary"]["contamination_count"] + results["summary"]["legacy_count"]
if violations > 0:
    print(f"\n[ERROR] Infracciones detectadas: {violations}. Revisa AUDITORIA_CORE_CONTAMINACION.md\n")
    sys.exit(2)

print("\n[OK] Sin infracciones en Core. Auditoria OK.\n")
sys.exit(0)
