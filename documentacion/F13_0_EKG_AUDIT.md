# F13.0 — Descubrimiento del EKG Existente

**Fecha:** 2026-08-09
**Estado:** 🟢 COMPLETED

## Qué existe

`tools/ekg/` es un pipeline de Knowledge Graph propio del proyecto, con rollout ya hecho a las 17
apps tenant (más `apps/public/`, 22 apps en total según `documentacion/INFORME_FINAL_EKG_GOBERNANZA_2026-08-07.md`).

| Módulo | Responsabilidad |
|---|---|
| `tools/ekg/schema.py` | SSoT del vocabulario: node labels (`Project`, `Application`, `Model`, `Field`, `Service`, `ViewSet`, `Serializer`, `Endpoint`, `Template`, `JS`, `Rule`, `Document`, `Test`, `Setting`, `Docker`) y relationship types (`IMPORTS`, `INHERITS`, `HAS_FIELD`, `REFERENCES`, `EXPOSES`, `USES`, `CALLS`, `CONSUMES`, `RENDERS`, `BELONGS_TO`, `DOCUMENTED_BY`, `GOVERNED_BY`, `TESTED_BY`, `SSOT_OF`, `DEPENDS_ON`). |
| `extract_python.py`, `extract_js.py`, `extract_docs.py`, `extract_templates.py`, `extract_infra.py` | Extractores AST/regex por dominio. |
| `build_graph.py` | Orquestador — construye el grafo por app, exporta JSON a `tools/ekg/out/<app>.json`, opcionalmente carga a Neo4j (`load_neo4j.py`). |
| `governance.py` | 4 reglas ya implementadas: `models_not_inheriting_tenant_base`, `js_outside_own_app_static_path`, `templates_outside_own_app_path`, `viewsets_without_service_layer`. |
| `impact.py` | Motor de impacto ("qué se rompe si cambio esto"). |
| `platform.py`, `export_html.py` | Síntesis (`--summary`/`--dossier`) y explorador HTML offline. |
| `queries.py`, `validate.py` | Queries auxiliares y validación del grafo. |
| `tools/ekg/out/*.json` | 17 dumps por app + varios de auditoría (`audit_*.json`), ya generados en disco. |

**Formato:** JSON (`schema.graph_to_jsonable()`), con carga opcional a Neo4j. No hay un segundo
formato compitiendo — se reutiliza el mismo criterio (JSON como fuente portable) para el grafo
organizacional nuevo.

**Tests:** `tools/ekg/tests/` — 9 archivos (`test_build_graph.py`, `test_export_html.py`,
`test_extract_docs.py`, `test_extract_js.py`, `test_extract_python.py`,
`test_extract_python_nested_layout.py`, `test_extract_templates.py`, `test_governance.py`,
`test_impact.py`, `test_platform.py`).

**Documentación que lo gobierna:** `tools/ekg/PILOT_REPORT.md`,
`documentacion/AUDITORIA_CODIGO_MUERTO_EKG_2026-08-05.md`,
`documentacion/INFORME_FINAL_EKG_GOBERNANZA_2026-08-07.md`.

## Estado en Git

**Sin commitear.** `git status` reporta `tools/ekg/*` como 8 archivos modificados + 8 nuevos —
línea de trabajo separada, sin relación con la consolidación OCF/OSF de esta sesión (confirmado en
`documentacion/OCF_OSF_BASELINE.md` §4, categoría E).

## Decisión: extender vs. crear uno nuevo

El prompt maestro F13.0 exige "NO crear un segundo Knowledge Graph si ya existe uno compatible" y
"Si existe una implementación EKG: EXTENDER, no reemplazar". El EKG existente **es** compatible
conceptualmente (mismo enfoque: extractores → grafo → JSON → reglas de gobernanza) — pero está
sujeto a la regla más estricta y explícita del mismo prompt maestro (§8): los ~78-79 archivos de
líneas de trabajo no relacionadas, incluido `tools/ekg/` completo, **no se tocan ni se commitean**.

**Resolución aplicada** (registrada, no silenciada — ver `documentacion/F13_F14_BASELINE.md`):
el Knowledge Graph organizacional se construye en `tools/organizational_governance/` — un paquete
**nuevo**, que:
- **No importa ningún módulo de `tools/ekg/`** (cero acoplamiento de código, cero riesgo de
  arrastrar cambios ajenos a un commit de F13/F14).
- Reutiliza el mismo *criterio* que `tools/ekg/schema.py` ya estableció (SSoT de vocabulario en un
  módulo `schema.py` propio, grafo con `Node`/`Edge`, export a JSON) — "extiende el concepto", no
  el código.
- Puede, en el futuro (fuera de esta sesión), fusionarse con `tools/ekg/` una vez que esa línea de
  trabajo se commitee por su cuenta — decisión que no le corresponde a esta consolidación tomar
  unilateralmente.

**Fecha de esta decisión:** 2026-08-09. **Estado: 🟢 COMPLETED.**
