# AI_TEST_STRATEGY — Fases 50-58

## Implementado y pasando (ver `AI_RELEASE_GATE.md` para el resultado real de la corrida)

`apps/services/ai/tests/` -- 20 tests, separados exactamente según la
Fase 50 lo pide (no todo mezclado en un solo archivo). Corrida real
final: **20/20 PASS** (252s).

| Archivo | Categoría (Fase 50) | Qué prueba |
|---|---|---|
| `test_tool_registry.py` (4 tests) | tool tests (sin DB) | Registro/duplicados/filtrado/metadata serializable |
| `test_ai_context.py` (6 tests) | context tests (sin DB, dobles) | `build_context`: no autenticado, sin perfil, alcance EMPRESA/SEDE, contexto de pantalla sin secretos, inmutabilidad |
| `test_buscar_cliente_tool.py` (10 tests) | integration + permission tests (DB real) | Ver tabla abajo |

### `test_buscar_cliente_tool.py` -- mapeo directo a fases de la misión

**Nota de diseño real, descubierta al escribir este test:** `Empresa`
es SINGLETON por schema de tenant (constraint real del modelo) -- no
es posible construir 2 empresas distintas en un mismo schema para
probar fuga cross-empresa clásica. El aislamiento "un tenant nunca ve
datos de otro" ya está probado a nivel de SCHEMA en otras misiones de
esta sesión (`TEN-01`, `docs/e2e/ONBOARDING_E2E_REPORT.md`) -- no se
repitió aquí. Lo que sí prueba este archivo:

| Test | Fase de la misión |
|---|---|
| `test_buscar_cliente_usa_el_empresa_id_del_contexto_real` | Fase 24 (empresa_id viene del contexto real, no arbitrario) |
| `test_buscar_cliente_respeta_search` / `test_buscar_cliente_search_sin_resultados` | Fase 53 (comportamiento funcional base) |
| `test_buscar_cliente_limit_invalido_es_validation_error` | Fase 34 (error normalizado) |
| `test_buscar_cliente_bloqueado_si_ai_engine_deshabilitado` | Fase 52/63 (flags server-side) |
| `test_buscar_cliente_bloqueado_si_solo_ai_enabled_sin_read_enabled` | Fase 63 (flag específico de kind, no solo el general) |
| `test_buscar_cliente_usuario_no_autenticado_denegado` | Fase 52 (permisos) |
| `test_buscar_cliente_usuario_sin_tenant_profile_denegado` | Fase 24 (sin TenantProfile -> denegado, nunca fallback silencioso) |
| `test_tool_desconocida_devuelve_not_found` | Fase 34 (error normalizado, no traceback) |
| `test_write_tools_siguen_bloqueadas_aunque_el_flag_write_este_activo` | Fase 6/26 (WRITE bloqueado estructuralmente, no solo por flag) |

## Provider tests -- no implementados

`AnthropicProvider.complete()` no tiene test propio en esta pasada
(requeriría mockear el SDK de Anthropic o gastar una llamada real de
API en CI) -- no se fabricó un test superficial solo para tener
cobertura; se documenta como pendiente real.

## Fases 54-58 -- diseñadas, no ejecutables sin las tools que prueban

| Fase | Qué probaría | Por qué no está implementada todavía |
|---|---|---|
| 54 (duplicate) | Crear el mismo cliente dos veces vía IA -- idempotencia | No hay tool WRITE (`crear_cliente`) todavía |
| 55 (prompt injection) | Datos de negocio con instrucciones maliciosas embebidas | No hay flujo que concatene datos de negocio en un prompt todavía (`buscar_cliente` no usa `AIProvider`) |
| 56 (tool abuse) | Intentar delete/export/cross-tenant sin permiso | Solo existe 1 tool `SAFE_READ` -- no hay delete/export que probar; el aislamiento cross-tenant SÍ está probado (Fase 51) |
| 57 (factuality) | "¿Creaste el cliente?" sin haber ejecutado la tool | Requiere un flujo conversacional con `AIProvider` generando texto -- no existe todavía |
| 58 (logging) | Trace/tool call/result sin secretos | **Parcialmente cubierto** -- ver `AI_TRACING.md`, el logging real de `AIEngine` ya no incluye secretos (verificado por lectura de código), pero no hay test automatizado que lo confirme (test de logging real pendiente) |

## Governance (Fase 59) -- ejecutado como parte de esta misión

Ver `AI_RELEASE_GATE.md` para el resultado real: `manage.py check`,
`makemigrations --check --dry-run`, `git diff --check`. EKG impact
check: **no ejecutado** (mismo motivo que en la misión de migración de
servidor previa -- `tools/ekg` no se corrió formalmente contra este
módulo nuevo en esta pasada).
