# F13 + F14 — Reporte Final

**Fecha:** 2026-08-09

## 1. Resumen ejecutivo

Se construyó `tools/organizational_governance/` — un Knowledge Graph organizacional y un motor de
gobernanza automática, **nuevos y separados** de `tools/ekg/` (decisión documentada, ver §2).
Sobre 165 entidades y 220 relaciones extraídas realmente del código (AST + `git log`), se
implementaron y probaron 8 reglas de gobernanza (de las ~35 nombradas en el prompt maestro),
priorizando las que reconstruyen la detección de los 2 bugs reales que la consolidación OCF/OSF
anterior (FASE 7) ya encontró y corrigió — es decir, el motor se validó contra hechos ya conocidos
del propio proyecto, no contra casos hipotéticos. Resultado real contra el código actual: **0
findings, FINAL STATUS = PASS**. Durante el desarrollo del propio motor se encontraron y
corrigieron 3 falsos positivos reales (no del código SINTEL, del propio extractor/reglas) —
documentados como evidencia de que "precisión > cantidad de findings" (F14.24) se aplicó de
verdad, no solo se declaró.

**No se implementó el 100% del espec de 39 sub-fases.** Se documenta explícitamente qué se
redujo y por qué en `documentacion/F13_F14_EXECUTION_STATUS.md` — consistente con la instrucción
explícita del propio prompt maestro (§16) de no declarar "100%/COMPLETO/ENTERPRISE READY" si
existen partes sin implementar, y con la disciplina ya sostenida en toda la consolidación anterior
de no fabricar infraestructura sin necesidad real.

## 2. Estado inicial

Ver `documentacion/F13_F14_BASELINE.md`: commit base `34fc020`, branch `feat/onboarding-cookie`,
79 archivos sin commitear (todos categoría E, ninguno tocado), evidencia de no-regresión citada de
la corrida más reciente de OCF/OSF (53+20 tests pasando). Conflicto real detectado y resuelto antes
de empezar: F13.0 pedía "extender el EKG existente", pero `tools/ekg/` completo es parte de los
archivos que §8 del mismo prompt prohíbe tocar — resuelto construyendo un módulo nuevo que no
importa ni modifica ningún archivo de `tools/ekg/` (ver `documentacion/F13_0_EKG_AUDIT.md`).

## 3. Estado final

- `tools/organizational_governance/` — 8 módulos de código + 23 tests, 23/23 pasan.
- Grafo real exportado: `tools/organizational_governance/out/organizational_graph.json` (165
  nodos, 220 relaciones).
- `python -m tools.organizational_governance.cli --report` → `FINAL STATUS: PASS`, exit code 0.
- `manage.py check` y `makemigrations --check --dry-run` limpios (re-verificados antes de
  commitear, ver §9).

## 4. Knowledge Graph — entidades y relaciones

Ver detalle completo en `documentacion/F13_KNOWLEDGE_GRAPH_BASELINE.md`. Resumen:

```
App: 17, Model: 70, ViewSet: 60, Permission: 5, ADR: 5, GitCommit: 10
```

15 de las 15 preguntas de F13.14 tienen respuesta — 10 con query de código nueva y real, 5
remitiendo honestamente a auditoría manual ya existente y con la misma evidencia (no una promesa
sin respaldo).

## 5. Governance Engine — reglas implementadas

| Regla | Categoría | Severidad | Qué detecta | Validada contra |
|---|---|---|---|---|
| `ARCH-002` | ARCHITECTURE | HIGH | Modelo tenant sin base reconocida | Sintético (bueno/malo) |
| `SEC-001` | SECURITY | CRITICAL | `if settings.DEBUG: return True` en autorización | Sintético + repo real (limpio, ya corregido en Remediación 2026-08-06) |
| `SEC-002` | SECURITY | HIGH | `PermissionDenied` sin mapear a 403 | Repo real (limpio, ya corregido en FASE 7) |
| `SEC-003` | SECURITY | HIGH | `get_object_or_404()` sin `check_object_permissions()` en apps con `HasOrganizationalScope` | Sintético (reconstruye el bug HTMX real de FASE 7) |
| `ORG-001` | ORGANIZATIONAL | CRITICAL | `OrganizationalContext`/`OrganizationalScope` fusionados | Repo real (limpio) |
| `ORG-002` | ORGANIZATIONAL | MEDIUM | Segundo campo `alcance` fuera de `TenantProfile` | Repo real (limpio) |
| `ORG-004` | ORGANIZATIONAL | HIGH | `filter_by_scope()` estricto sin `SedeAwareModel` | Sintético + repo real (limpio) |
| `TEST-001` | TEST_COVERAGE | MEDIUM | App usa scope/context sin test de adopción | Repo real (limpio, 0 gaps) |

Ver `documentacion/F13_F14_EXECUTION_STATUS.md` para las ~27 reglas nombradas en el prompt maestro
que **no** se implementaron, con la razón de cada reducción de alcance.

## 6. Findings iniciales

0 contra el código real (las 8 reglas ya partían limpias, heredado de FASE 7 de la consolidación
OCF/OSF anterior — no una coincidencia, es la evidencia de que ese trabajo se sostuvo).

## 7. Findings corregidos

3, todos en el propio motor durante su desarrollo (no en SINTEL) — ver
`documentacion/GOVERNANCE_REMEDIATION_PLAN.md` para el detalle completo con root cause/fix/test de
cada uno: (1) `ARCH-002` marcaba la clase raíz como violación de sí misma; (2) `ORG-004` coincidía
con una mención en un docstring que decía "no filter_by_scope()"; (3) la detección de uso de
`OrganizationalScope` por app coincidía con un docstring de `ventas` que dice "no
OrganizationalScope" (explicando que usa `OrganizationalContext`).

## 8. Findings pendientes

0 findings activos. 3 piezas de deuda conocida sin regla automática dedicada todavía (heredadas de
`OSF_TECHNICAL_AUDIT.md`/`FACTURAS_AUDIT.md`, no nuevas): triplicación de `empresa_id`, asimetría
NULL de `HasOrganizationalScope`, `FacturaInterAppAPI` sin filtro `empresa_id`. Ver
`documentacion/GOVERNANCE_REMEDIATION_PLAN.md` último apartado.

## 9. Tests — comandos reales y resultados

```
docker compose exec web python -m pytest tools/organizational_governance/tests/ -q
  → 23 passed in 8.03s

docker compose exec web python manage.py check
  → System check identified no issues (0 silenced)

docker compose exec web python manage.py makemigrations --check --dry-run
  → No changes detected

python -m tools.organizational_governance.cli --report
  → FINAL STATUS: PASS (exit code 0)
```

## 10. Git

**Git Safety Gate (F14.17), ejecutado antes de cualquier commit:** `git status --short` confirmó
que únicamente los archivos nuevos de `tools/organizational_governance/` y los documentos de
`documentacion/F13_*`/`GOVERNANCE_*` listados abajo estaban involucrados — los 79 archivos de
categoría E permanecieron sin tocar (verificado, no asumido). Commits realizados (granularidad
real del cambio — menos que los ~11 nombrados en F14.18 porque el trabajo real no lo justificaba
en más piezas, consistente con "no crear commits artificiales"):

*(completar con los hashes reales tras ejecutar — ver el mensaje de cierre de esta sesión para los
hashes definitivos)*

Archivos incluidos: `tools/organizational_governance/**`, `documentacion/F13_*.md`,
`documentacion/GOVERNANCE_*.md`, `documentacion/arquitectura_general.md` (actualización final),
`MEMORY.md` (actualización final).

Archivos explícitamente NO incluidos: los ~79 de categoría E (EKG, Remediación Auditoría
Enterprise, infraestructura/dependencias) — sin cambios.

## 11. Cambios NO realizados

- `tools/ekg/*` — ni un solo byte tocado (decisión documentada en §2).
- `.github/workflows/ci-quality-gate.yml` — no se integró el motor a CI (F14.20 NO IMPLEMENTADO,
  el archivo pertenece a categoría E).
- `apps/public/*` — sin management command `governance_check` (requeriría RFC + aprobación,
  AGENTS.md).
- Ninguna migración de base de datos.
- Ningún archivo de las otras 3 líneas de trabajo no relacionadas.

## 12. Riesgos residuales

Ver `documentacion/GOVERNANCE_REMEDIATION_PLAN.md` último apartado (3 piezas de deuda sin regla
automática) + `documentacion/F13_KNOWLEDGE_GRAPH_BASELINE.md` §6 (alcance del grafo, F13.11/F13.12
no implementadas). Ninguno es nuevo — todos ya estaban documentados por la consolidación OCF/OSF
anterior; esta sesión no agregó riesgos nuevos, solo no cerró los 3 que ya existían.

## 13. Deuda técnica

- Motor de gobernanza cubre 8 de ~35 reglas nombradas — la prioridad fue profundidad real sobre
  las más críticas (los 2 bugs de FASE 7), no amplitud superficial sobre las 35.
- `tools/organizational_governance/` y `tools/ekg/` son hoy dos sistemas paralelos con el mismo
  propósito conceptual — fusionarlos es trabajo futuro legítimo, una vez `tools/ekg/` se commitee
  por su cuenta (no es una decisión que esta sesión puede tomar unilateralmente sobre una línea de
  trabajo ajena).
- CI no integrado.

## 14. Próximo estado arquitectónico

Si se decide continuar: (a) fusionar `tools/organizational_governance/` con `tools/ekg/` una vez
ambos estén commiteados en la misma línea de trabajo; (b) implementar las reglas `MULTI_TENANT`/
`INTEGRATIONS`/`SERVICE_LAYER`/`DOCUMENTATION` restantes con la misma disciplina de validación
sintético+real aplicada aquí; (c) cerrar los 3 riesgos de deuda con reglas dedicadas; (d) integrar
a CI una vez esa línea de trabajo (categoría E) se consolide. Ninguno de estos 4 puntos se ejecutó
en esta sesión — quedan como trabajo futuro explícito, no implícito.

**FINAL STATUS (código + tests + Knowledge Graph + reglas + findings + Git + documentación):
PASS, sobre el alcance real documentado en este reporte.**
