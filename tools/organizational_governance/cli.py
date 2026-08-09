"""
Punto de entrada (F14.20/F14.21). No se creo un management command Django
(`python manage.py governance_check`) como pedia literalmente el prompt
maestro - decision documentada, no un olvido: AGENTS.md exige RFC +
etiqueta 'needs-admin-approval' para tocar apps/public/, y ningun app
tenant es un lugar semanticamente correcto para un comando de gobernanza
de todo el repositorio (no es logica de tenant). Se sigue el mismo patron
ya establecido por tools/ekg/ (`python -m tools.ekg.governance`, ver
Makefile `ekg-governance`) por consistencia con el proyecto:

    python -m tools.organizational_governance.cli            # exit code
    python -m tools.organizational_governance.cli --report   # texto legible
    python -m tools.organizational_governance.cli --json out.json

Exit code: 0 = PASS, 1 = WARN, 2 = FAIL (F14.20).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tools.organizational_governance.build import build_organizational_graph
from tools.organizational_governance.report import render_findings_detail, render_report
from tools.organizational_governance.rules import run_all_rules


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="organizational_governance")
    parser.add_argument("--report", action="store_true", help="Imprime el reporte legible completo")
    parser.add_argument("--findings", action="store_true", help="Imprime el detalle de cada finding")
    parser.add_argument("--json", type=str, default=None, help="Escribe el grafo como JSON en la ruta indicada")
    args = parser.parse_args(argv)

    graph = build_organizational_graph()
    findings = run_all_rules(graph)

    if args.json:
        graph.write_json(Path(args.json))

    if args.report or not (args.findings or args.json):
        print(render_report(graph, findings))

    if args.findings:
        print(render_findings_detail(findings))

    fail_count = sum(1 for f in findings if f.status == "FAIL")
    warn_count = sum(1 for f in findings if f.status == "WARN")
    if fail_count:
        return 2
    if warn_count:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
