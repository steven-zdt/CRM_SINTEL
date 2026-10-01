# MCP_DOMAIN_MATRIX — LOOP 1

> Matriz de dominios exigida por el prompt maestro (§13
> `crud_capabilities`, §55 `DOMAIN_MCP_READY`). Para dominios de
> **negocio** (clientes, ventas, etc.) esta matriz ya existe y es más
> completa en `docs/ai/AI_TOOL_REGISTRY.md` ("Diseño — AI Domain
> Registry") — no se duplica aquí. Esta tabla cubre el dominio nuevo de
> esta misión: `platform` (auditoría de código/arquitectura).

## Dominio `platform`

| Capacidad | Estado | Owner real |
|---|---|---|
| Service Layer | `N/A` | No aplica — `platform` no tiene modelos propios, censa OTRAS apps |
| Read tool | `IMPLEMENTED`: `project_inventory`, `governance_audit`, `production_readiness`, `inspect_dependencies` (=`dependency_inventory`=`audit_dependencies`), `business_rule_inventory`, `tenant_context`, `domain_inventory`, `audit_domain`, `inspect_model`, `api_inventory` (=`inspect_api`), `django_check`, `migration_check` + previo `ai_project_map`/`tool_inventory` | `apps/services/ai/tools/{platform_audit_tools,ekg_tools,registry}.py` |
| Validate tool | `NOT_APPLICABLE` | Nada que "validar antes de crear" en un dominio de solo-lectura |
| Write tool | `BLOCKED por diseño` | `AUTO_APPROVED_KINDS` excluye WRITE; ninguna tool de código/infra escribe hoy |
| Permissions | `IMPLEMENTED` (heredado) | Mismo gate de `AIEngine.run_tool()` que el resto — `TenantProfile` válido, sin permiso granular adicional todavía |
| Tenant isolation | `N/A` | Sin datos de tenant — mismo criterio que `ai_project_map` |
| Tests | `IMPLEMENTED` | 4 unit + 3 integración (DB) `project_inventory` + 3 `governance_audit` + 1 `production_readiness` (django_db) + 5 `inspect_dependencies` + 3 `business_rule_inventory` + 2 `tenant_context` + 3 `domain_inventory` + 4 `audit_domain` + 4 `inspect_model` + 4 `api_inventory` + 2 `django_check` + 1 `migration_check` (django_db) = 39 tests reales |
| Status agregado | `DOMAIN_MCP_READY` = **parcial** (14 tools nuevas + 2 preexistentes; 4 tools restantes de `MCP_TOOL_CATALOG.md` siguen `DESIGNED`, 1 `DEFERRED`) | |

## Checklist `DOMAIN_MCP_READY` (§55 del prompt maestro) aplicado a `platform`

- [x] Service Layer — no aplica a este dominio (ver nota arriba)
- [x] CRUD auditado — solo READ existe, WRITE explícitamente fuera de alcance
- [x] permissions — heredadas de `AIEngine.run_tool()`
- [x] tenant isolation — no aplica (sin datos de tenant)
- [x] business rules — `business_rule_inventory`/`governance_audit` ya reales (snapshot EKG + AST propio); `audit_domain` (agregador) también real
- [x] transaction safety — no aplica (solo lectura, sin escritura)
- [x] idempotency — trivial (lectura pura, `idempotent=True` en `BaseTool`)
- [ ] API contract — no expuesto vía `/mcp/` (ver `ADR-MCP-001.md`); solo vía `AIEngine.run_tool()` interno
- [x] MCP tool — 12 tools nuevas registradas en `AIToolRegistry` (ver fila "Read tool")
- [x] tests — 39 tests reales (unit + integración + django_db), ver `MCP_RELEASE_GATE.md`
- [ ] cross-tenant test — no aplica (sin datos de tenant); si esto cambia en una tool futura, sí se exige
- [x] negative tests — `app_label` inexistente → `NOT_FOUND`; flags `AI_ENABLED=False`/`AI_READ_ENABLED=False` probados vía `AIEngine.run_tool()` real para `project_inventory` (`ProjectInventoryToolEngineIntegrationTests`)
- [ ] audit evidence — logging genérico de `AIEngine.run_tool()` ya cubre esto; sin evidencia de una corrida real en producción todavía

**Veredicto honesto:** `platform` **no** está `DOMAIN_MCP_READY`
completo — tiene su primera tool real y probada, pero el checklist
exige más (negative tests de flags, más tools del catálogo). No se
declara `READY` por una sola tool (Regla Absoluta del prompt maestro,
§48: nunca afirmar completado lo que no lo está).

## Dominios de negocio — estado real vs. Module Matrix aspiracional (`SINTEL_MCP_SKILLS/08`)

`08_mcp_module_matrix.md` describe un estado OBJETIVO ("CRUD +
Kardex/traslados", "CRUD + nómina gateada", etc.) que asume WRITE ya
habilitado — eso es Fase 4 completa, no implementada (`BLOCKED` por
`AUTO_APPROVED_KINDS`). Traducción a la taxonomía de esa skill
(`NOT_DISCOVERED`/`DISCOVERED`/`READ_READY`/`VALIDATE_READY`/
`DRY_RUN_READY`/`WRITE_READY`/`DOMAIN_ACTIONS_READY`/`BLOCKED`/
`DEFERRED`) usando el estado REAL de hoy — ver `MCP_SKILLS_ALIGNMENT.md`
§3 para el detalle, resumen aquí:

| Dominio | Estado real |
|---|---|
| `clientes`, `inventario`, `proveedores`, `ventas`, `compras`, `cotizaciones`, `gastos`, `proyectos`, `facturas`, `empleados`, `bancos`, `contabilidad` | `READ_READY` (AI-03 `VERIFIED`) |
| `clientes`, `proveedores`, `inventario`, `compras`, `cotizaciones`, `gastos` | además `VALIDATE_READY` (AI-04) |
| Todos los de negocio | `WRITE_READY`/`DOMAIN_ACTIONS_READY` = **no**, ninguno — `BLOCKED` a nivel de engine, no por dominio |
| `empresa`, `perfil`, `dashboard` | `NOT_DISCOVERED` para MCP/AIToolRegistry |
| `ai_knowledge` | `READ_READY` vía `buscar_conocimiento` — nunca edición directa (coincide con la propia skill) |
| `impuestos`, `reporting` | `DEFERRED` formalmente (AI-03) |
| `core`, `landing`, `db_extensions` | `NOT_APPLICABLE` (coincide con la regla explícita de las skills 01/08) |

No se duplica la tabla completa de dominios de negocio — el detalle
tool-por-tool ya vive en `docs/ai/AI_TOOL_REGISTRY.md`.
