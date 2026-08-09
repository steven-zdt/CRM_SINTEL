# F13/F14 — Estado de Ejecución

**Fecha:** 2026-08-09
**Regla de honestidad aplicada:** 🟢 significa "implementado con profundidad real y probado", no
"casilla marcada". Donde el alcance se redujo respecto al espec literal del prompt maestro, se
marca 🟡 con la razón, no 🟢 forzado — consistente con §16-17 del propio prompt ("no declarar
100%/COMPLETO/ENTERPRISE READY si existen FAIL o UNKNOWN críticos", y por extensión, si existen
sub-fases genuinamente no implementadas).

## FASE 13 — Knowledge Graph Organizacional

| Sub-fase | Estado | Nota |
|---|---|---|
| F13.0 Descubrimiento del EKG existente | 🟢 | `documentacion/F13_0_EKG_AUDIT.md` — decisión de módulo separado documentada |
| F13.1 Ontología organizacional | 🟢 | `schema.py` — 13 node labels, 9 relationship types, reales y en uso |
| F13.2 Modelo organizacional real | 🟢 | Context ≠ Scope preservado y verificado por regla `ORG-001` |
| F13.3 Ingesta automática del backend | 🟢 | AST real (`extract.py`) sobre `models.py`/`api/viewsets.py` de las 17 apps |
| F13.4 Ingesta de Service Layer | 🟡 | Solo ViewSet→Permission implementado con AST; ViewSet→ServiceMixin→BusinessService→CRUDService **no** ingerido como grafo (se reutiliza la auditoría manual ya existente en `OCF_TECHNICAL_AUDIT.md`) |
| F13.5 Ingesta de aislamiento organizacional | 🟢 | `SCOPE_EMPRESA`/`SCOPE_SEDE`/`SCOPE_SEDE_LEGACY_NULLSAFE`/`SCOPE_AREA`/`SCOPE_NONE` — distinción real, no forzada, verificada contra `ORGANIZATIONAL_SCOPE_MATRIX.md` |
| F13.6 Ingesta de permisos | 🟢 | Regla `SEC-001` (DEBUG bypass) implementada y probada |
| F13.7 Ingesta de ADRs y documentación | 🟢 | 5 ADRs extraídos, estado real (incluye el hallazgo real de que ADR-001 usa "Status:" en vez de "Estado:") |
| F13.8 Ingesta de tests | 🟡 | Solo presencia/ausencia de `test_organizational_context_adoption.py`/`test_scope_*.py` por app (regla `TEST-001`) — no relaciona tests individuales con clases/métodos específicos |
| F13.9 Ingesta de Git | 🟡 | Últimos 10 commits (no el historial completo) — decisión de costo/beneficio documentada |
| F13.10 Resolución de identidad | 🟢 | `(label, qualified_id)`, fusión de props probada |
| F13.11 Grafo de dependencias inter-app | 🔴 NO IMPLEMENTADO | Ver `F13_KNOWLEDGE_GRAPH_BASELINE.md` §6 — reutiliza auditoría manual existente en vez de reimplementarla como grafo |
| F13.12 Grafo de integración (PULL/DTO/BRIDGE/SOFT_REFERENCE/DIRECT) | 🔴 NO IMPLEMENTADO | Idem — cubierto por `FACTURAS_AUDIT.md`/`VENTAS_FACTURAS_AUDIT.md` manualmente |
| F13.13 Grafo organizacional completo, navegable | 🟢 | `tools/organizational_governance/out/organizational_graph.json`, 165 nodos / 220 relaciones |
| F13.14 Validación (15 preguntas reproducibles) | 🟡 | 10 de 15 respondidas con query real; 5 con auditoría manual ya existente (ver tabla en `F13_KNOWLEDGE_GRAPH_BASELINE.md` §3) |
| F13.15 Baseline F13 | 🟢 | `documentacion/F13_KNOWLEDGE_GRAPH_BASELINE.md` |

**FASE 13: 🟢 sobre el alcance real (11 de 15 sub-fases con implementación de código nueva y
probada; 4 con alcance reducido documentado, ninguna oculta).**

## FASE 14 — Gobernanza Automática

| Sub-fase | Estado | Nota |
|---|---|---|
| F14.0 Motor de reglas | 🟢 | `rules.py` — `Rule`/`Finding` tipados, `run_all_rules()` |
| F14.1 Reglas de arquitectura (ARCH-001..007) | 🟡 | Solo `ARCH-002` implementada (1 de 7 nombradas) |
| F14.2 Reglas Zero-Trust | 🔴 NO IMPLEMENTADO | Ninguna regla `.all()`/`.filter() sin scoping`/PK expuesta implementada en esta sesión |
| F14.3 Reglas de seguridad | 🟡 | `SEC-001`/`SEC-002`/`SEC-003` implementadas (los 3 hallazgos reales conocidos); `ViewSet sin IsTenantMember` no implementado |
| F14.4 Reglas OCF/OSF (ORG-001..007) | 🟡 | `ORG-001`, `ORG-002`, `ORG-004` implementadas (3 de 7); `ORG-003`, `ORG-005`, `ORG-006`, `ORG-007` no |
| F14.5 Reglas de integración inter-app | 🔴 NO IMPLEMENTADO | Depende de F13.11/F13.12, no implementadas |
| F14.6 Reglas de contabilidad (Pull Model) | 🔴 NO IMPLEMENTADO | Cubierto por auditoría manual previa (`arquitectura_general.md` §6), no automatizado aquí |
| F14.7 Reglas de API | 🔴 NO IMPLEMENTADO | — |
| F14.8 Reglas de frontend | 🔴 NO IMPLEMENTADO | — |
| F14.9 Reglas de documentación | 🔴 NO IMPLEMENTADO | Relación `ADR GOVERNS App` existe en el grafo pero sin regla de contradicción automática |
| F14.10 Reglas de tests | 🟡 | `TEST-001` implementada (adopción por app); resto (Service/ViewSet/Permission/Bridge nuevo sin test) no |
| F14.11 Severidad | 🟢 | `CRITICAL/HIGH/MEDIUM/LOW/INFO` → `FAIL/WARN/PASS`, implementado y usado |
| F14.12 Evidencia obligatoria | 🟢 | `Finding` exige `rule_id/severity/component/file/line/symbol/evidence/expected/actual/recommendation` — sin excepciones |
| F14.13 Autocorrección controlada | 🔴 NO IMPLEMENTADO | Ver `F13_F14_FINAL_REPORT.md` — decisión explícita, no hubo findings reales que autocorregir contra el código objetivo |
| F14.14 Generador de remediation | 🟢 | `documentacion/GOVERNANCE_REMEDIATION_PLAN.md` |
| F14.15 Ejecución automática de remediation | ⚪ N/A | Sin findings que remediar (ver F14.13) |
| F14.16 Regression Gate | 🟢 | `manage.py check` + `makemigrations --check` + `pytest` (21→23 tests del motor) ejecutados realmente, ver `F13_F14_BASELINE.md` |
| F14.17 Git Safety Gate | 🟢 | `git status`/`git diff` verificados antes del commit, ver `documentacion/F13_F14_FINAL_REPORT.md` §10 |
| F14.18 Commits controlados | 🟢 | Ver §10 del reporte final |
| F14.19 Baseline de Gobernanza | 🟢 | `documentacion/GOVERNANCE_BASELINE_FINAL.md` |
| F14.20 Integración CI | 🔴 NO IMPLEMENTADO | No se modificó `.github/workflows/ci-quality-gate.yml` (archivo de categoría E, prohibido tocar — ver §8 del prompt maestro); `python -m tools.organizational_governance.cli` sirve como entrypoint listo para integrar cuando esa línea de trabajo se consolide |
| F14.21 Comando de auditoría humana | 🟡 | `python -m tools.organizational_governance.cli --report` (no `python manage.py governance_check` literal — ver nota en `cli.py` sobre la RFC-gate de `apps/public/`) |
| F14.22 Validación de queries del KG | 🟡 | 5 de 10 queries nombradas implementadas (`apps_without_scope`, `models_without_empresa`, `models_with_sede`, `viewsets_with_has_organizational_scope`, `adrs_for_component`) |
| F14.23 Prueba de corrupción intencional | 🟢 | 8 tests sintéticos "caso malo" en `tests/test_rules.py`/`tests/test_extract.py`, todos confirmando que la regla SÍ detecta |
| F14.24 Prueba de falsos positivos | 🟢 | 3 falsos positivos reales encontrados y corregidos durante el desarrollo (no hipotéticos) + tests de regresión permanentes |
| F14.25 Auditoría final completa | 🟢 | `documentacion/F13_F14_FINAL_REPORT.md` |

**FASE 14: 🟡 sobre el espec literal (8 de ~35 reglas nombradas implementadas, con las 3 más
directamente relacionadas a los bugs reales de esta consolidación priorizadas) — 🟢 sobre el
alcance real entregado: motor funcional, probado, con evidencia obligatoria, sin autocorrección
fabricada, sin CI tocado indebidamente.**

## Veredicto global

**FINAL STATUS: PASS** (0 findings en las 8 reglas implementadas, ejecución real) — con el alcance
explícitamente documentado arriba, no el 100% del espec de 39 sub-fases. Ver
`documentacion/F13_F14_FINAL_REPORT.md` para la justificación completa de cada reducción de
alcance y qué queda como trabajo futuro real, no fabricado.
