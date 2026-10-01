# MCP_TOOL_CATALOG — LOOP 1

> Complementa `docs/ai/AI_TOOL_REGISTRY.md` (catálogo completo de
> tools de negocio, sin cambios) con las tools de dominio
> `domain="platform"` que el prompt maestro pide en su §4
> "Inspección/Auditoría". Estados: `IMPLEMENTED` (código real +
> tests), `DESIGNED` (target real identificado, sin código),
> `DEFERRED` (decisión explícita de no priorizar ahora), `BLOCKED`
> (dependencia externa sin resolver).
>
> **Reconciliado con `SINTEL_MCP_SKILLS/` (raíz del repo) el
> 2026-09-25 — ver `MCP_SKILLS_ALIGNMENT.md` para el detalle completo.**
> Esas 12 skills quedan adoptadas como regla de comportamiento del
> catálogo, traducidas a la arquitectura real de `ADR-MCP-001.md`.

## Fase 1 del prompt maestro (§66) — READ/AUDIT, sin WRITE

| Tool | Estado | Fuente real a envolver | Notas |
|---|---|---|---|
| `project_inventory` | **IMPLEMENTED** | `django.apps.apps` (registro vivo) + filesystem | `apps/services/ai/tools/platform_audit_tools.py::ProjectInventoryTool`, 4 tests en `apps/services/ai/tests/test_project_inventory_tool.py` |
| `project_map` | **IMPLEMENTED** (ya existía, AI-02) | `ai_project_map` / `ProjectMapTool` | No se duplica — cubre owner/rules/docs/fk/endpoints |
| `inspect_model` | **IMPLEMENTED** | Django `Model._meta` (fields/constraints/FK, registro vivo) | `InspectModelTool`, 4 tests — smoke real: `Cliente` → 29 fields, `UniqueConstraint uniq_doc_cliente_empresa` real, relación reversa `ventas`→`Venta` (`one_to_many`) descrita correctamente |
| `inspect_service` | **DESIGNED** | `tools/ekg/out/<app>.json` (nodos Service, edges USES) | Requiere una función de consulta nueva sobre el snapshot, no solo `offline_*` existentes |
| `inspect_api` | **IMPLEMENTED** (mismo tool que `api_inventory`) | Ver fila `api_inventory` | |
| `inspect_dependencies` | **IMPLEMENTED** | `tools/organizational_governance/dependencies.py::discover_dependency_edges()`+`detect_cycles()` | `InspectDependenciesTool`, 5 tests (`test_inspect_dependencies_tool.py`) — smoke real: 425 edges, **17 ciclos de import detectados entre apps tenant** (hallazgo real, no fabricado — ver nota abajo), 0 `FORBIDDEN` |
| `domain_inventory` | **IMPLEMENTED** (alcance acotado) | `tool_metadata()` filtrado por `domain` | `DomainInventoryTool`, 3 tests — solo cubre "que AI tools existen para este dominio", NO el censo FSD completo (para eso, `project_inventory(app_label=...)`); ver docstring de la tool |
| `api_inventory` | **IMPLEMENTED** | `django.urls.get_resolver('config.urls_tenant')` (registro vivo, no snapshot) | `ApiInventoryTool`, 4 tests — smoke real: 53 endpoints bajo `path_prefix="clientes"` (`ClienteViewSet`/`CarteraViewSet` reales). **NO cubre** `permission_classes` ni el método HTTP exacto por acción (DRF no los conserva en `initkwargs` tras `as_view()` — declarado explícitamente en `not_covered`, nunca ocultado) |
| `service_inventory` | **DESIGNED** | Igual que `inspect_service`, agregado a nivel de proyecto | |
| `tool_inventory` | **IMPLEMENTED** (ya existía) | `tool_metadata()` (`apps/services/ai/tools/registry.py`) | Ya expuesto dentro de `project_inventory.data["ai_tools_registered"]` |
| `dependency_inventory` | **IMPLEMENTED** (mismo tool que `inspect_dependencies`) | Ver fila `inspect_dependencies` | No se creó una segunda tool — el prompt maestro las trata como el mismo dato con dos nombres (censo vs. inspección); `InspectDependenciesTool` cubre ambos usos |
| `integration_inventory` | **DESIGNED** | `docs/ai/AI_PROVIDER_MATRIX.md` (LLM) + revisión manual de integraciones (Wompi/DIAN/email/WhatsApp/Redis/Celery) — sin un registro vivo único hoy | Requiere primero decidir una fuente de verdad (no existe un "integration registry" en código) |
| `tenant_context` | **IMPLEMENTED** | `AIContext` (campos ya resueltos por `build_context()`) | `TenantContextTool`, 2 tests — solo refleja, `run()` no declara ningún parámetro que permita cambiarlo (verificado con `inspect.signature`) |
| `business_rule_inventory` | **IMPLEMENTED** | `tools/ekg/governance.py` (6 reglas F7) vía `load_full_offline_graph()` | `BusinessRuleInventoryTool`, 3 tests — smoke real: `overall_status=FAIL`, 31 violaciones (23 `viewsets_without_service_layer`, 6 `sede_or_area_field_without_sede_aware_model`, 2 `import_cycles_between_tenant_apps`) sobre snapshot de 2026-08-08/11 (**stale**, la tool lo reporta explícitamente, nunca lo oculta — correr `make ekg-build` refresca). Complementa, no duplica, `governance_audit` (reglas distintas, motor distinto: AST propio vs. snapshot EKG) |
| `audit_domain` | **IMPLEMENTED** | Orquesta `project_inventory`+`ai_project_map(rules_for_app)`+`inspect_dependencies`, ninguna reimplementada | `AuditDomainTool`, 4 tests — **bug real encontrado y corregido durante la construcción**: pasar el `app_label` de Django (`tenant_clientes`) tal cual a `inspect_dependencies` filtraba silenciosamente a 0 edges porque ese módulo usa nombres de CARPETA (`clientes`) — corregido derivando `ekg_folder` una sola vez y reutilizándolo en ambas sub-llamadas. Declara explícitamente lo que NO cubre (`permissions_detail`/`integrations`/`state_machines`/`transactions`/`idempotency`) |
| `audit_endpoint` | **DESIGNED** | `ai_project_map(question="endpoints_for_model")` + inspección de `permission_classes` (no extraído hoy por el EKG, ver límite documentado en `tools/ekg/governance.py`) | |
| `audit_service` | **DESIGNED** | Igual que `inspect_service` + reglas de `tools/organizational_governance/rules.py` | |
| `audit_dependencies` | **IMPLEMENTED** (mismo tool que `inspect_dependencies`) | Ver fila `inspect_dependencies` | Idem `dependency_inventory` — mismo dato, no se triplica la tool |
| `run_tests` | **DESIGNED** | `pytest <target>` con allowlist de targets (nunca shell arbitraria, §20/§72 del prompt maestro) | Riesgo adicional real, no solo teórico: esta misma sesión chocó repetidas veces con `test_sintel` "being accessed by other users" al correr pytest en paralelo (regla ya documentada en `CLAUDE.md` §"Tests") — una tool `run_tests` invocable por un agente necesita ademas un lock/cola para no permitir 2 corridas concurrentes, diseño no trivial, no resuelto aquí |
| `run_checks` | **DESIGNED** (alcance cubierto por `django_check`+`migration_check` ya reales) | Combinación directa de las 2 filas siguientes | No se crea una tool agregadora aparte todavía — un agente puede llamar ambas; agregarla es trivial cuando se priorice |
| `django_check` | **IMPLEMENTED** | `django.core.checks.run_checks()` (la función real que usa `manage.py check` internamente, no subprocess) | `DjangoCheckTool`, 2 tests — smoke real: `overall_status=PASS`, 0 errores/warnings. `include_deployment_checks` opcional |
| `migration_check` | **IMPLEMENTED** | `call_command('makemigrations', '--check', '--dry-run')` (nunca escribe migraciones) | `MigrationCheckTool`, 1 test (`django_db` — **hallazgo real al construir el test**: `makemigrations --check` SÍ consulta `django_migrations` vía `check_consistent_history()`, la primera versión del test asumía sin-DB incorrectamente, corregido). `SystemExit(1)` (la señal real de "faltan migraciones") capturado explícitamente, nunca confundido con éxito ni dejado escapar |
| `production_readiness` | **IMPLEMENTED** | `apps/public/core/production_readiness/registry.py::run_all_checks()` (misma fuente que el management command) | `ProductionReadinessTool`, 1 test (`test_production_readiness_tool.py`, `django_db`) — smoke real: `overall_status=NOT_READY` (24 checks, `DEBUG=True` en este entorno de desarrollo, esperado) |
| `governance_audit` | **IMPLEMENTED** | `tools/organizational_governance/{build,rules}.py::build_organizational_graph()`+`run_all_rules()` (misma fuente que el CLI) | `GovernanceAuditTool`, 3 tests (`test_governance_audit_tool.py`) — smoke real: `overall_status=PASS`, 0 findings en este snapshot del repo. `severity_filter` opcional (`CRITICAL`\|`HIGH`\|`MEDIUM`\|`LOW`\|`INFO`) |
| `ekg_query` | **DEFERRED** | — | Investigado: las 4 preguntas offline reales (`rules_for_app`/`docs_for_app`/`fk_relationships`/`endpoints_for_model`) ya las cubre `ai_project_map` — una tool `ekg_query` aparte duplicaría exactamente eso (§87, no duplicar). Lo único que NO cubre es Neo4j en vivo (`make ekg-ask`), que abriría una conexión de grafo en vivo desde una tool de IA — riesgo/alcance nuevo que requiere decisión explícita del usuario, no asumida aquí |
| `knowledge_search` | **IMPLEMENTED** (ya existía) | `buscar_conocimiento` / `RetrievalTool` | No se duplica |

## Discovery/Read/Validate genéricos (`SINTEL_MCP_SKILLS/01`, `/10`) — ver `MCP_SKILLS_ALIGNMENT.md` §2

| Tool | Estado | Notas |
|---|---|---|
| `crud_capabilities` | **DESIGNED** | Distinto de `domain_inventory` (ya implementada) — censo por MODELO de Create/Read/Update/Delete/Service/API/Permissions/Tests/Status, cruzando `inspect_model` con presencia de Serializer de escritura/`ServiceMixin`/`BusinessService`/tests. No implementado, gap real encontrado al reconciliar con las skills |
| `read_record`, `list_records`, `search_records`, `get_related_records` | **DESIGNED** | Genérico por modelo — cada dominio ya tiene su tool específica (`buscar_cliente`, etc.); una versión genérica arriesga violar la Regla Absoluta de tools semánticas si no se diseña con cuidado |
| `validate_create`, `validate_update` | **IMPLEMENTED** (ya existían, AI-04) | = `validar_*` por dominio, `AI_TOOL_REGISTRY.md` |
| `validate_delete`, `validate_domain_action`, `dry_run` genérico | **DESIGNED** | Sin equivalente real todavía |

## Hallazgos reales encontrados al construir este catálogo (§49 — reportar, no ocultar)

- **17 ciclos de import reales entre apps tenant** (`inspect_dependencies`,
  smoke real sobre el AST actual del repo, ej. `clientes ↔ facturas`,
  `empresa ↔ perfil`). No es una afirmación teórica del prompt maestro —
  es la salida real de `discover_dependency_edges()`+`detect_cycles()`
  corrida en esta sesión. **Fuera de alcance corregirlos aquí** (esta
  misión construye tools de auditoría, no repara arquitectura por su
  cuenta) — queda como hallazgo para una misión de remediación aparte,
  con evidencia real lista en `inspect_dependencies(app_label=...)`.
- **El snapshot EKG (`tools/ekg/out/*.json`) tiene 1-1.5 meses de
  antigüedad** (2026-08-08 a 2026-08-11) respecto a esta sesión
  (2026-09-25) — `business_rule_inventory` lo reporta explícitamente
  (`snapshot_oldest`/`snapshot_newest`), nunca lo oculta. Sus 31
  violaciones reportadas (`viewsets_without_service_layer=23`, etc.)
  deben leerse como "estado a esa fecha", no como el estado exacto de
  hoy — correr `make ekg-build` antes de actuar sobre ellas.

## Fuera de alcance de LOOP 1 (fases posteriores del prompt maestro)

| Tool | Estado | Motivo |
|---|---|---|
| `create_record`/`update_record`/`delete_record`/`execute_domain_action`/`bulk_create`/`bulk_update` (§13-18 del prompt maestro, skill 02/03/10) | `BLOCKED` por diseño | `AUTO_APPROVED_KINDS` excluye `WRITE` incondicionalmente hoy; requiere primero un flujo de aprobación real (§69 LOOP 4). **No implementar sin autorización explícita del usuario** — regla confirmada de nuevo en `MCP_SKILLS_ALIGNMENT.md` §6 |
| `audit_tenant_isolation`, `audit_frontend_api_contract`, `audit_integrations` (skill 10) | `DESIGNED` | Nuevos, no investigados; `audit_integrations` comparte el mismo gap que `integration_inventory` (sin fuente de verdad única) |
| `propose_code_fix`/`apply_code_fix` (§31-32, skill 07) | `NOT_IMPLEMENTED` | LOOP 5 (§85), requiere rollback strategy + aprobación humana, no priorizado en esta pasada |
| MCP Resources / MCP Prompts (§45-46) | `N/A` bajo esta arquitectura | Dependen del protocolo MCP real, descartado en `ADR-MCP-001.md` |

## Regla de implementación (heredada, sin excepción)

Cada tool `DESIGNED` de esta tabla, al implementarse, debe:
1. Ser una subclase real de `BaseTool` en `apps/services/ai/tools/`
   (nunca lógica inline en una vista).
2. `domain="platform"`, `kind=ToolKind.READ` (o `VALIDATE` si aplica),
   nunca `WRITE` en esta fase.
3. Reutilizar la fuente real listada en esta tabla — nunca reimplementar
   el análisis (`tools/ekg/`, `tools/organizational_governance/`,
   registro vivo de Django) dentro de `apps/services/ai/`.
4. Tener tests reales antes de declararse `IMPLEMENTED` (mismo criterio
   que el resto del AI Engine — ver `AI_TEST_STRATEGY.md`).
5. Registrarse en `apps/services/ai/tools/__init__.py` y actualizar esta
   tabla en el mismo cambio.
