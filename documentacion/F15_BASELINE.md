# F15.0 — Baseline (Integración Inter-App)

**Fecha:** 2026-08-09
**Commit base:** `e403232`
**Branch:** `feat/onboarding-cookie`

## Git

`git status --short` → 74 archivos sin commitear, todos categoría E (sin cambios desde el cierre
de F13/F14, ver `documentacion/OCF_OSF_BASELINE.md` §4 / `F13_F14_FINAL_REPORT.md` §11).

## Governance (estado heredado)

```
python -m tools.organizational_governance.cli --report
KNOWLEDGE GRAPH: Entities 165, Relations 218 (varía levemente entre corridas por la ventana de
  los ultimos 10 commits de git log — no es una regresion, ver extract.extract_recent_git_commits())
ARCHITECTURE PASS:1 WARN:0 FAIL:0
SECURITY     PASS:3 WARN:0 FAIL:0
ORGANIZATIONAL PASS:3 WARN:0 FAIL:0
TEST_COVERAGE PASS:1 WARN:0 FAIL:0
FINAL STATUS: PASS
```

## Inventario reutilizado (no re-derivado desde cero)

Este plan pide "descubrir" apps/modelos/services/bridges/DTOs/selectors/APIs/tests — la mayor
parte de esto **ya existe, auditado con evidencia real**, de la consolidación OCF/OSF anterior:

- Apps y modelos: `tools/organizational_governance/out/organizational_graph.json` (165 nodos).
- Qué apps consumen `OrganizationalContext`/`OrganizationalScope`: `ORGANIZATIONAL_SCOPE_MATRIX.md` §4.
- Bridges reales de `facturas` (los únicos 5 Bridges con esa forma en el proyecto):
  `FACTURAS_AUDIT.md` §3.
- Contrato Ventas→Facturas (DTO, Soft Reference): `VENTAS_FACTURAS_AUDIT.md`.
- Matriz de qué app necesita sede/área: `ORGANIZATIONAL_SCOPE_MATRIX.md` §1 (F6 de OSF).

F15 extiende esto con lo que **no** existía: un grafo de dependencias inter-app por import real
(no solo los 5 Bridges de facturas) y clasificación explícita de cada arista.

## Decisión de alcance para F15-F20 (registrada, no oculta)

Ver mensaje de apertura de esta fase en la conversación: F17 (rollout) se ejecuta como
**documentación de estado real**, no como nueva migración de esquema — la matriz de FASE 5/OSF-F6
ya concluyó qué apps necesitan `sede`/`área` y con qué prioridad, y tanto el principio §5 de este
mismo prompt ("NO migración masiva inicial") como la decisión explícita del usuario sobre `ventas`
(2 turnos atrás) respaldan no re-abrir esa decisión sin una necesidad de negocio nueva y
verificada. Los `COL-*` de F20 se implementan como checks estructurales/técnicos (presencia de
CUFE, separación de tipos de documento, trazabilidad), nunca como afirmación de cumplimiento legal
verificado — no se investigó ni se cita legislación colombiana específica (artículos/decretos) sin
la capacidad real de verificarla contra una fuente autoritativa.

**Estado: 🟢 COMPLETED.**
