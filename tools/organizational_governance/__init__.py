"""
Organizational Governance (F13/F14, consolidacion OCF/OSF).

Modulo NUEVO y separado de tools/ekg/ - decision explicita documentada en
documentacion/F13_F14_BASELINE.md ("Resolucion del conflicto entre F13.0 y
Seccion 8"): tools/ekg/ pertenece a una linea de trabajo sin commitear que
no debe tocarse. Este paquete lee el codigo fuente de forma independiente
(no importa ningun modulo de tools/ekg/) y, donde es util, reutiliza los
dumps JSON ya generados en tools/ekg/out/*.json como dato de solo lectura
(nunca como import de codigo Python).

Alcance real (no el espec completo de 39 sub-fases del prompt maestro F13+F14
- ver documentacion/F13_F14_FINAL_REPORT.md para el detalle honesto de que
se implemento con profundidad real y que se dejo fuera, y por que):
  - schema.py   - vocabulario de nodos/relaciones organizacionales
  - extract.py  - extractores AST/regex reales (modelos, ViewSets/permisos,
                  ADRs, git log)
  - graph.py    - grafo en memoria + queries reproducibles + export JSON
  - rules.py    - motor de reglas (Rule/Finding) + subconjunto real de
                  reglas ARCH/ZT/SEC/ORG implementadas y probadas
  - report.py   - formato de reporte legible (CLI)
  - cli.py      - punto de entrada `python -m tools.organizational_governance.cli`
"""
