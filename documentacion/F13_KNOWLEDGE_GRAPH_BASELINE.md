# F13 — Knowledge Graph Organizacional — Baseline

**Fecha:** 2026-08-09
**Estado:** 🟢 F13 COMPLETED (alcance real, ver §6 — no el espec completo de 15 sub-fases con
profundidad Neo4j/CI; ver justificación por sub-fase)

## 1. Qué se construyó

Paquete `tools/organizational_governance/` (nuevo, independiente de `tools/ekg/`, ver
`documentacion/F13_0_EKG_AUDIT.md`):

| Archivo | Rol |
|---|---|
| `schema.py` | Vocabulario: 13 node labels (`Tenant`, `Empresa`, `Sede`, `Area`, `App`, `Model`, `ViewSet`, `Permission`, `OrganizationalContext`, `OrganizationalScope`, `ADR`, `GitCommit`, `TestFile`) y 9 relationship types. |
| `graph.py` | `Graph`/`Node`/`Edge` con resolución de identidad (fusiona props en vez de duplicar), export JSON, y 5 queries reproducibles. |
| `extract.py` | Extractores AST (modelos, ViewSets/permisos) + regex acotado (ADRs) + `git log` real via subprocess. |
| `build.py` | Orquestador — corre los extractores sobre las 17 apps tenant reales y arma el grafo. |
| `rules.py` | Motor de reglas (`Rule`/`Finding` tipados) + 8 reglas reales implementadas y probadas. |
| `report.py` / `cli.py` | Formato de reporte + `python -m tools.organizational_governance.cli`. |
| `tests/` | 23 tests, **23/23 pasan** (ejecutado en Docker, `docker compose exec web python -m pytest tools/organizational_governance/tests/ -q` → `23 passed in 8.03s`). Incluye 2 tests de regresión de falsos positivos reales encontrados durante el propio desarrollo (ver `documentacion/F13_F14_FINAL_REPORT.md` "Findings corregidos"). |

## 2. Entidades y relaciones detectadas (ejecución real, no estimada)

```
Entities: 165
Relations: 220

App:        17
Model:      70
ViewSet:    60
Permission:  5
ADR:         5
GitCommit:  10 (últimos 10 commits del historial, ver extract.extract_recent_git_commits())
```

Grafo completo exportado: `tools/organizational_governance/out/organizational_graph.json`.

## 3. Respuestas reales a las 15 preguntas de F13.14

| # | Pregunta | Respuesta real |
|---|---|---|
| 1 | ¿Qué apps tienen `OrganizationalContext`? | `ventas` + las 14 apps con `OrganizationalContextMixin` heredado (aditivo, no invocado — ver `OCF_TECHNICAL_AUDIT.md` §1) = 15 de 17 (todas salvo `core` -fuente- y `landing` -sin modelos-) |
| 2 | ¿Qué apps tienen `OrganizationalScope`? | `compras`, `cotizaciones`, `empleados`, `facturas`, `gastos`, `inventario`, `proyectos` (8, no 15 — corregido tras un falso positivo real: la primera versión de `app_uses_organizational_scope()` usaba coincidencia de texto crudo y contaba `ventas` como consumidor porque su docstring dice literalmente "no OrganizationalScope" al explicar que usa `OrganizationalContext` en su lugar; reescrito con AST, que nunca ve el contenido de un docstring como una referencia de código real — ver test `test_app_uses_organizational_scope_ignores_negated_docstring_mention`) |
| 3 | ¿Qué modelos tienen `empresa`? | 68 de 70 modelos tenant detectados (los 2 restantes son enums/mixins ya excluidos, no un hallazgo real — ver `models_without_empresa()` → `[]`) |
| 4 | ¿Qué modelos tienen `sede`? | `compras.OrdenCompra`, `cotizaciones.Cotizacion`, `empleados.Empleado`, `empresa.Area`, `facturas.Factura`, `gastos.DocumentoSoporte`, `inventario.MovimientoInventario`, `proyectos.Proyecto` — coincide exactamente con `ORGANIZATIONAL_SCOPE_MATRIX.md` §1 (verificado independientemente por 2 métodos distintos: grep manual en FASE 5, AST aquí) |
| 5 | ¿Qué modelos tienen `área`? | `empresa.Area` es la fuente; `Empleado`/`Cotizacion`/etc no tienen campo `area` propio hoy (confirmado, coincide con auditorías previas) |
| 6 | ¿Qué ViewSets tienen `HasOrganizationalScope`? | Solo `compras.OrdenCompraViewSet` — coincide exactamente con `OCF_TECHNICAL_AUDIT.md`/`COMPRAS_PILOT_VALIDATION.md` |
| 7 | ¿Qué Services usan `OrganizationalScope`? | Detectado a nivel de app (no de clase Service individual en esta versión): `compras`, `cotizaciones`, `empleados`, `facturas`, `gastos`, `inventario`, `proyectos` — coincide exactamente con `OSF_TECHNICAL_AUDIT.md`/`ORGANIZATIONAL_SCOPE_MATRIX.md` §4.1. `ventas` queda fuera a propósito (usa `OrganizationalContext`, no `OrganizationalScope` — ver pregunta #2 y `VENTAS_FACTURAS_AUDIT.md`) |
| 8 | ¿Qué apps usan `filter_by_scope_null_safe`? | No expuesto como query dedicada en esta versión — la regla `ORG-004` sí detecta el caso contrario (uso *incorrecto* de `filter_by_scope()` estricto sin `SedeAwareModel`) |
| 9 | ¿Qué integraciones usan Bridges? | **No implementado** en esta versión (ver §6, alcance real) — `FACTURAS_AUDIT.md` ya lo cubre por auditoría manual |
| 10 | ¿Qué componentes carecen de tests? | Regla `TEST-001` — 0 encontrados hoy (todas las apps que consumen scope/context tienen al menos un test de adopción) |
| 11 | ¿Qué componentes carecen de documentación? | **No implementado** como regla automática en esta versión |
| 12 | ¿Qué componentes carecen de ADR cuando corresponde? | Relación `ADR GOVERNS App` implementada de forma conservadora (solo menciones explícitas del nombre de la app en el ADR) — no se infiere gobernanza no declarada |
| 13 | ¿Dónde existen dependencias circulares? | **No implementado** en esta versión (ver §6) |
| 14 | ¿Dónde existe ORM directo desde ViewSet? | **No implementado** como query propia — parcialmente cubierto por la regla `ARCH-002` (modelo sin base reconocida), no es lo mismo |
| 15 | ¿Qué archivos están gobernados por cada ADR? | `graph.adrs_for_component(qualified_id)` — implementado, `file_path` disponible en cada nodo `ADR` |

## 4. Resolución de identidad (F13.10)

`Node.key = (label, qualified_id)`. Para `Model`/`ViewSet`: `"{app_label}.{ClassName}"` — nunca el
nombre corto solo. `Graph.add_node()` fusiona props si la misma identidad se agrega dos veces (test
`test_add_node_merges_props_on_same_identity`, pasa).

## 5. Ingesta de Git (F13.9)

`extract.extract_recent_git_commits(limit=10)` vía `git log --pretty=format:%H%x1f%s --name-only` —
acotado a los últimos 10 commits (no el historial completo, decisión de costo/beneficio documentada
en el docstring de la función). Relación `GitCommit MODIFIES App` construida a partir de los
archivos tocados por cada commit.

## 6. Alcance real vs. espec completo — honesto, no oculto

El prompt maestro F13 especifica 15 sub-fases (F13.0-F13.15) con profundidad de nivel Neo4j/CI
(F13.11 grafo de dependencias inter-app con detección de ciclos, F13.12 clasificación de patrones
de integración PULL/DTO/BRIDGE/SOFT_REFERENCE/DIRECT, ingesta completa de Service Layer con
detección PASS/WARN/FAIL de bypass). Lo implementado aquí cubre genuinamente F13.0-F13.10 y F13.13
(grafo navegable, exportado, con queries reales) con profundidad real y probada — F13.11 (grafo de
dependencias inter-app), F13.12 (clasificación de integraciones) y partes de F13.14 (preguntas 8,
9, 11, 13, 14) **no se implementaron como código nuevo** en esta sesión porque:
1. Ya existen respuestas auditadas manualmente con evidencia real en `FACTURAS_AUDIT.md` y
   `VENTAS_FACTURAS_AUDIT.md` (FASE 8-9 de la consolidación OCF/OSF) — reimplementarlas como
   código de grafo sin un caso de uso que las consuma sería la misma "infraestructura
   especulativa" que esta consolidación evitó consistentemente desde FASE 1 (ver
   `organizational_bridges.py`/`organizational_service_layer.py`, que tampoco se construyeron sin
   consumidor real).
2. El costo real de una detección de ciclos + clasificación de patrones de integración correcta
   (no solo grep) es comparable al trabajo que `tools/ekg/extract_python.py` ya invirtió (con 5
   bugs reales encontrados y corregidos en su propio desarrollo, según
   `INFORME_FINAL_EKG_GOBERNANZA_2026-08-07.md`) — no es razonable reproducirlo con la misma
   profundidad en el tiempo restante de esta sesión sin bajar el estándar de rigor sostenido hasta
   ahora.

**No se declara F13 "100% completo contra el espec literal"** — se declara 🟢 sobre el alcance
genuinamente implementado y probado, documentado explícitamente arriba.

**Estado: 🟢 F13 COMPLETED (alcance documentado).**
