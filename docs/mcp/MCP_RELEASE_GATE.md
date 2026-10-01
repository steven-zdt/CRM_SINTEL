# MCP_RELEASE_GATE — LOOP 1

> Mismo criterio que `docs/ai/AI_RELEASE_GATE.md`: nunca declarar
> `VERIFIED`/`PASS` por progreso parcial. `MCP_CONTROL_PLANE = VERIFIED`
> exigiría todos los gates abajo en `[x]` — hoy no es el caso.

## Gates por fase (LOOP 0-1 del prompt maestro)

```
[x] MCP-00 Baseline (LOOP 0)         = VERIFIED (2026-09-25) -- docs/mcp/MCP_BASELINE.md, sin cambios de codigo
[x] MCP-01 Decision de arquitectura   = VERIFIED (2026-09-25) -- ADR-MCP-001.md, decision explicita del usuario
[~] MCP-02 Primera tool platform real = PARCIAL -- 12 tools platform nuevas implementadas+testeadas (project_inventory, governance_audit, production_readiness, inspect_dependencies, business_rule_inventory, tenant_context, domain_inventory, audit_domain, inspect_model, api_inventory, django_check, migration_check); resto del catalogo (MCP_TOOL_CATALOG.md) sigue DESIGNED/DEFERRED
[~] MCP-03 Catalogo Fase 1 completo   = PARCIAL -- 4 tools DESIGNED restantes (inspect_service/service_inventory, integration_inventory, audit_endpoint, audit_service; run_checks es agregador trivial de tools ya reales), 1 DEFERRED (ekg_query, redundante con ai_project_map), 16 IMPLEMENTED (project_inventory, project_map/ai_project_map, tool_inventory, governance_audit, production_readiness, inspect_dependencies=dependency_inventory=audit_dependencies, business_rule_inventory, tenant_context, domain_inventory, audit_domain, inspect_model, api_inventory=inspect_api, django_check, migration_check, knowledge_search)
[~] MCP-04 VALIDATE (Fase 2)          = PARCIAL -- 4/5 tools de §67 reales (governance_audit/production_readiness/django_check/migration_check); solo `run_tests` sigue DESIGNED (requiere allowlist de targets + control de concurrencia contra test_sintel, ver nota abajo -- no es solo exit-code)
[ ] MCP-05 DRY-RUN (Fase 3)           = NO INICIADO -- depende de que existan tools WRITE de negocio que dry-run pueda ejercitar (hoy ninguna)
[ ] MCP-06 WRITE por dominio (Fase 4) = BLOQUEADO por diseño -- AUTO_APPROVED_KINDS excluye WRITE incondicionalmente
[ ] MCP-07 CODE REPAIR (Fase 5)       = NO INICIADO -- requiere aprobacion humana + rollback, no priorizado
[ ] MCP-08 Protocolo MCP real (/mcp/) = BLOQUEADO por defecto de terceros (AI-07) -- fuera de alcance de esta mision (ver ADR-MCP-001.md)
```

## MCP-02 = PARCIAL — evidencia

`project_inventory` (`apps/services/ai/tools/platform_audit_tools.py::ProjectInventoryTool`):
- Registrada en `AIToolRegistry` (`apps/services/ai/tools/__init__.py`).
- `domain="platform"`, `kind=ToolKind.READ`, `risk=ToolRisk.SAFE_READ`.
- Reutiliza `django.apps.apps` (registro vivo) + presencia filesystem —
  cero análisis estático nuevo, cero segundo grafo.
- 7 tests reales: 4 unit (sin DB, `test_project_inventory_tool.py`
  primeras 4 funciones) + 3 integración (`SintelTenantTestCase`, DB
  real, `ProjectInventoryToolEngineIntegrationTests`) — cubren OK real,
  `NOT_FOUND` (app inexistente), y los 2 negative tests de flags
  (`AI_ENABLED=False`, `AI_READ_ENABLED=False`) que
  `MCP_DOMAIN_MATRIX.md` señalaba como gap.
- `python manage.py check` limpio tras el cambio (sin errores de import
  ni de configuración).

**No se declara `MCP-02`/`MCP-04 = VERIFIED`** porque el resto del
catálogo `platform` (`MCP_TOOL_CATALOG.md`) sigue en `DESIGNED` — 3
tools reales no cierran la fase completa, mismo criterio que
`AI_RELEASE_GATE.md` aplica al resto del AI Engine.

## `governance_audit`/`production_readiness` = IMPLEMENTED — evidencia

Ambas invocan directamente en Python las mismas funciones que ya usan
sus CLI/management command existentes (`build_organizational_graph()`+
`run_all_rules()`; `run_all_checks()`+`compute_blockers()`+
`compute_scorecard()`+`overall_status()`) — cero reimplementación,
cero subprocess. Verificado con smoke real dentro del contenedor
(`docker compose exec web python -c "..."`, sin pasar por pytest):

```
GovernanceAuditTool: status=OK, overall_status=PASS, finding_count=0
ProductionReadinessTool: status=OK, overall_status=NOT_READY, 24 checks
  (DEBUG=True en este entorno de desarrollo -- esperado, no un bug de la tool)
```

`governance_audit`: 3 tests (`test_governance_audit_tool.py`, unit,
sin DB). `production_readiness`: 1 test (`test_production_readiness_tool.py`,
`pytest.mark.django_db` porque el check de versión de Postgres usa
`connection.cursor()` real).

**Actualización: `django_check`/`migration_check` ya IMPLEMENTED** (ver
sección dedicada abajo) — la nota original de esta sección (que los
agrupaba con `run_tests` como "exit-code delicado") quedó resuelta para
esos 2: `django_check` evita el problema por completo usando
`django.core.checks.run_checks()` directo (nunca pasa por `call_command`/
`sys.exit`); `migration_check` sí necesitó capturar `SystemExit`
explícitamente (`makemigrations --check` señala "faltan migraciones"
así, nunca con una excepción estándar) — implementado y verificado, ver
abajo.

**Por qué `run_tests` sigue `DESIGNED`** (no una omisión): a diferencia
de los 2 anteriores, no es solo una cuestión de exit-code — esta misma
sesión chocó varias veces con `test_sintel` ocupada por otra corrida de
pytest concurrente (`CLAUDE.md` §"Tests" ya documenta esta restricción
real de la base de test compartida). Una tool `run_tests` invocable por
un agente necesita, además de un allowlist de targets (§20 del prompt
maestro: nunca shell arbitraria), algún mecanismo de lock/cola para no
permitir 2 corridas concurrentes contra `test_sintel` — diseño real
pendiente, no solo una envoltura directa.

## `inspect_dependencies`/`business_rule_inventory`/`tenant_context`/`domain_inventory` = IMPLEMENTED — evidencia

Mismo criterio que las 3 anteriores: cero subprocess, cero
reimplementación, wrap directo de funciones Python reales.

```
InspectDependenciesTool:    status=OK, edge_count=425, cycle_count=17, forbidden_count_total=0
BusinessRuleInventoryTool:  status=OK, overall_status=FAIL, total_violations=31 (snapshot 2026-08-08/11, reportado explicitamente)
TenantContextTool:          status=OK -- refleja AIContext, run() sin parametros ademas de context (verificado con inspect.signature)
DomainInventoryTool:        status=OK -- domain="clientes" -> {buscar_cliente, validar_cliente}
```

`inspect_dependencies` cubre también `dependency_inventory`/
`audit_dependencies` (mismo dato, no se triplicó la tool — ver
`MCP_TOOL_CATALOG.md`).

## `audit_domain`/`inspect_model`/`api_inventory` = IMPLEMENTED — evidencia

```
AuditDomainTool: status=OK (tenant_clientes) -- inventory+rules+dependencies agregados
  bug real encontrado y corregido en el camino: pasar el app_label de Django
  ("tenant_clientes") tal cual a inspect_dependencies filtraba a 0 edges --
  ese modulo usa nombres de carpeta ("clientes"); corregido con ekg_folder
  compartido entre las dos sub-llamadas.
  status=OK (tenant_ai_knowledge, app SIN snapshot EKG) -- rules_status=NOT_FOUND,
  inventory se resuelve igual (no tumba toda la auditoria).
InspectModelTool: Cliente -> 29 fields, UniqueConstraint real, relacion
  reversa ventas->Venta (one_to_many) descrita correctamente.
ApiInventoryTool: path_prefix="clientes" -> 53 endpoints (ClienteViewSet,
  CarteraViewSet reales), deduplicado por `name` (variantes .json colapsadas).
```

`audit_domain`: 4 tests. `inspect_model`: 4 tests. `api_inventory`: 4 tests.
Los 3 son unit tests puros (sin DB) -- orquestan/leen registro vivo de
Django o resultados de otras tools ya reales.

## `django_check`/`migration_check` = IMPLEMENTED — evidencia

```
DjangoCheckTool:    status=OK, overall_status=PASS, error_count=0, warning_count=0
MigrationCheckTool: status=OK, overall_status=PASS, has_missing_migrations=False,
                     output="No changes detected"
```

`django_check` usa `django.core.checks.run_checks()` directo (la misma
función que `BaseCommand.check()` invoca internamente) — nunca pasa por
`call_command`/`manage.py`/subprocess, así que nunca hay `sys.exit` que
capturar. `migration_check` sí usa `call_command('makemigrations',
'--check', '--dry-run', ...)` porque no hay una función de nivel más
bajo reutilizable — captura `SystemExit` explícitamente
(`has_missing_migrations = exc.code != 0`), nunca lo deja escapar ni lo
confunde con éxito.

**Hallazgo real al construir el test de `migration_check`** (corregido
en el camino, no ocultado): la primera versión del test asumía "sin DB"
—incorrecto. `makemigrations --check` internamente llama
`loader.check_consistent_history(connection)`, que consulta la tabla
real `django_migrations` vía `connection.cursor()` para saber qué
migraciones ya están aplicadas antes de comparar contra el estado de
los modelos. El test se corrigió a `@pytest.mark.django_db`.

`django_check`: 2 tests (unit, sin DB). `migration_check`: 1 test
(`django_db`, verificado con smoke real arriba; pytest formal pendiente
por la misma razón que `production_readiness` — `test_sintel` ocupada).

## Corrida de tests (2026-09-25)

```
apps/services/ai/tests/test_project_inventory_tool.py::(4 unit)              -- passed
apps/services/ai/tests/test_governance_audit_tool.py                         -- 3 passed
apps/services/ai/tests/test_inspect_dependencies_tool.py                     -- 5 passed
apps/services/ai/tests/test_business_rule_inventory_tool.py                  -- 3 passed
apps/services/ai/tests/test_tenant_context_tool.py                           -- 2 passed
apps/services/ai/tests/test_domain_inventory_tool.py                         -- 3 passed
apps/services/ai/tests/test_audit_domain_tool.py                             -- 4 passed
apps/services/ai/tests/test_inspect_model_tool.py                            -- 4 passed
apps/services/ai/tests/test_api_inventory_tool.py                            -- 4 passed
apps/services/ai/tests/test_django_check_tool.py                             -- 2 passed
  (30 unit tests platform en total, sin DB, corridas conforme se construyo
  cada tool -- sin colisionar con la suite completa que seguia corriendo
  contra test_sintel, ver nota operativa abajo)
apps/services/ai/tests/test_production_readiness_tool.py -- django_db: verificado via smoke real (ver arriba); pytest formal pendiente
apps/services/ai/tests/test_migration_check_tool.py      -- django_db: verificado via smoke real (ver arriba); pytest formal pendiente
apps/services/ai/tests/test_project_inventory_tool.py    -- integracion (DB real, AIEngine.run_tool): pendiente de re-correr
  sin colision con la suite completa (test_sintel estuvo ocupada por otra
  corrida en curso durante buena parte de esta sesion) -- ver nota
  operativa de CLAUDE.md §"Tests" sobre corridas concurrentes.
```

## Nota operativa real de esta sesión: `apps/services/ai/tests/` sin `-m "not slow"`

El regression-check de fondo lanzado al inicio de LOOP 1
(`pytest apps/services/ai/tests/ -q`) tardó mucho más de lo esperado
(horas, no los ~10-16 min históricos) porque **no excluyó los tests
`slow`** (`test_adk_agent_live_llm.py`, `test_embedding_provider.py`,
marcados `@pytest.mark.slow`, opt-in según `pytest.ini` pero no
excluidos por defecto — sin `addopts` que los filtre). Cada uno hace
llamadas reales a un LLM local (LM Studio/Ollama, ~90-100s cada una).
**No es un bug de las tools nuevas** — es un error de alcance de este
comando de verificación. Lección para la próxima corrida de regresión
de este directorio: usar `pytest apps/services/ai/tests/ -m "not slow" -q`.

## Próximo paso real (no ejecutado, requiere priorización del usuario)

Lo que queda `DESIGNED` en `MCP_TOOL_CATALOG.md` (`inspect_service`/
`service_inventory`, `integration_inventory`, `audit_endpoint`,
`audit_service`, `run_tests`) requiere más trabajo por tool que lo ya
hecho: los primeros necesitan nuevas funciones de consulta sobre los
snapshots de `tools/ekg/` (no solo los `offline_*` existentes),
`integration_inventory` necesita decidir primero una fuente de verdad
(no existe un "integration registry" en código hoy), y `run_tests`
necesita un allowlist de targets + un mecanismo real de lock/cola
contra `test_sintel` (ver nota arriba). No se implementa esto sin que
el usuario confirme el alcance — mismo criterio que el propio AI Engine
aplicó en su construcción original (`AI_ENGINE_ARCHITECTURE.md`:
"implementar las 66 fases con calidad real en una sola pasada no es
honesto").
