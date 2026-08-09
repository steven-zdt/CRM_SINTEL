# Governance Baseline Final — F14

**Fecha:** 2026-08-09
**Commit final:** ver `documentacion/F13_F14_FINAL_REPORT.md` §10 (Git) para los hashes exactos tras el commit de este trabajo.

## Cifras reales (ejecución `python -m tools.organizational_governance.cli --report`)

```
KNOWLEDGE GRAPH
Entities: 165
Relations: 220

ARCHITECTURE     PASS: 1  WARN: 0  FAIL: 0
SECURITY         PASS: 3  WARN: 0  FAIL: 0
MULTI_TENANT     PASS: 0  WARN: 0  FAIL: 0   (sin reglas implementadas en esta version)
ORGANIZATIONAL   PASS: 3  WARN: 0  FAIL: 0
INTEGRATIONS     PASS: 0  WARN: 0  FAIL: 0   (sin reglas implementadas en esta version)
SERVICE_LAYER    PASS: 0  WARN: 0  FAIL: 0   (sin reglas implementadas en esta version)
DOCUMENTATION    PASS: 0  WARN: 0  FAIL: 0   (sin reglas implementadas en esta version)
TEST_COVERAGE    PASS: 1  WARN: 0  FAIL: 0

FINAL STATUS: PASS
```

**Reglas implementadas:** 8 (`ARCH-002`, `SEC-001`, `SEC-002`, `SEC-003`, `ORG-001`, `ORG-002`,
`ORG-004`, `TEST-001`) de las ~35 nombradas en el prompt maestro F14.1-F14.10. Categorías
`MULTI_TENANT`, `INTEGRATIONS`, `SERVICE_LAYER`, `DOCUMENTATION` muestran `PASS: 0` porque
**ninguna regla de esas categorías se implementó todavía** — no porque se haya verificado y no
haya nada que reportar. Esta distinción se preserva deliberadamente en el reporte (no se infla
`PASS` a 1 solo para que la categoría "se vea evaluada") — ver `documentacion/F13_F14_FINAL_REPORT.md`
§"Findings pendientes" para el detalle honesto de qué falta.

**Tests del motor:** 23/23 pasan (`tools/organizational_governance/tests/`).

**Autocorrecciones (F14.13/F14.15):** 0 ejecutadas contra el codigo objetivo — no hubo ningún
finding real que autocorregir (el repositorio ya estaba limpio en las 8 reglas implementadas,
gracias a los fixes de FASE 7 de la consolidación OCF/OSF anterior). Sí hubo autocorrección
real durante el *desarrollo del propio motor* — 3 falsos positivos reales encontrados y
corregidos en las propias reglas antes de confiar en su resultado (ver
`documentacion/F13_F14_FINAL_REPORT.md` §"Findings corregidos").

**Findings pendientes:** 0 contra el código real, en las 8 reglas implementadas. Ver
`documentacion/GOVERNANCE_REMEDIATION_PLAN.md`.

**Riesgos:** heredados de la consolidación OCF/OSF anterior (`ORGANIZATIONAL_SCOPE_BASELINE_FINAL.md`
§6) — no resueltos por este motor, solo no re-detectados porque las reglas que los cubrirían
(ej. detección de la asimetría NULL entre `filter_by_scope_null_safe`/`HasOrganizationalScope`)
no se implementaron como regla automática en esta sesión.

**Estado: 🟢 (sobre el alcance real implementado, ver F13_F14_FINAL_REPORT.md para la
declaración completa de qué NO se hizo).**
