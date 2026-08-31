# AI_RELEASE_GATE — Fases 60-61, 66

`AI_ENGINE = VERIFIED` solo si TODOS los ítems están en `[x]`. Estado
real, 2026-08-31:

```
[x] provider abstraction        -- AIProvider (ABC) implementado
[x] Anthropic compatible        -- AnthropicProvider real, reutiliza el patron del Asistente Contable
[ ] OpenAI compatible           -- diseñado (AI_PROVIDER_MATRIX.md), no implementado -- sin caller real que lo ejerza
[ ] local provider              -- diseñado, no implementado, mismo motivo
[x] context engine              -- AIContext + build_context, SSoT real (tenant_profile), probado
[ ] EKG integration             -- diseñado (ai.project_map), no implementado
[x] User Access Context         -- build_context() deriva SIEMPRE de request.user.tenant_profile, nunca del payload
[x] tool registry               -- AIToolRegistry real, con metadata serializable, probado
[x] read tools                  -- 1 tool real end-to-end (buscar_cliente), probada con aislamiento por empresa_id
[ ] validation tools            -- diseñadas (AI_TOOL_REGISTRY.md), no implementadas
[ ] suggestion tools            -- diseñadas, no implementadas
[x] write controls              -- AUTO_APPROVED_KINDS excluye WRITE incondicionalmente -- estructural, no solo documentado
[ ] approvals (flujo real)      -- no implementado -- consecuencia directa de no tener tools WRITE todavia
[~] audit                       -- logging real por tool call (tool/kind/status/user/empresa), sin persistencia estructurada ni trace_id
[~] tracing                     -- logging basico real; tracing de workflow completo NO implementado (AI_TRACING.md)
[ ] session (memoria)           -- diseñada (AI_MEMORY_POLICY.md), no implementada -- sin flujo conversacional real que la necesite
[x] tenant isolation            -- garantia de SCHEMA ya verificada en otras misiones de esta sesion (TEN-01); a nivel de tool se prueba que empresa_id viene siempre del contexto real, ver nota en AI_TEST_STRATEGY.md (Empresa es singleton por schema)
[ ] prompt injection defense    -- diseñado, no implementado -- ningun flujo real concatena datos de negocio en un prompt todavia
[~] sensitive data controls     -- ninguna tool sensible existe todavia (buscar_cliente no toca nomina/bancos/impuestos) -- nada que fallar, pero tampoco nada probado
[ ] MCP read                    -- MCP sigue inerte (0 ViewSets decorados) -- sin cambios en esta pasada, deliberado
[ ] MCP write controls          -- N/A, MCP read tampoco existe
[x] tests                       -- 20/20 PASS (ver corrida real abajo)
[x] governance                  -- manage.py check PASS, makemigrations --check PASS, git diff --check PASS
[x] documentation                -- 11 documentos en docs/ai/, todos distinguiendo implementado vs diseñado
```

## Corrida real de tests (2026-08-31)

```
apps/services/ai/tests/ -- 20 items
20 passed in 252.26s
```

3 intentos reales hasta llegar a la corrida limpia (documentado con
honestidad, no oculto):
1. `Empresa()` no tiene campo `nombre` (solo `razon_social`/`nit`) -- bug propio del test.
2. `Empresa.direccion` es obligatorio (`blank=False`) -- bug propio del test.
3. **Hallazgo real de arquitectura**, no un bug: `Empresa` es
   SINGLETON por schema de tenant (constraint del modelo) -- el diseño
   original del test asumía 2 empresas en un mismo schema, algo
   estructuralmente imposible aquí. Rediseñado para reflejar la
   arquitectura real (ver `AI_TEST_STRATEGY.md`).

## `AI_ENGINE` = **NOT_VERIFIED** (honesto, no `BLOCKED_SAFE`)

No es un bloqueo de infraestructura como en las misiones de
producción/migración previas -- es, con toda honestidad, **alcance
real ejecutado de una misión de 66 fases que pedía una plataforma
completa**. Lo implementado (núcleo del engine + 1 dominio READ
completo, probado de punta a punta con aislamiento real) es
deliberadamente pequeño y **verificable**, en vez de fabricar 66 fases
sin sustancia real detrás.

## Fase 62 — Go-live controlado, primer escalón alcanzado

```
READ_ONLY_ASSISTANT     <- aqui, con 1 dominio (clientes) -- flags AI_ENABLED+AI_READ_ENABLED en False por defecto
VALIDATION_ASSISTANT    <- no alcanzado
SUGGESTION_ASSISTANT    <- no alcanzado
WRITE_ASSISTANT         <- no alcanzado, ni debe alcanzarse sin el flujo de aprobacion de la Fase 26
```

`AI_ENABLED`/`AI_READ_ENABLED`/etc. quedan en `False` por defecto
(`config/settings.py`) -- el AI Engine no se activa en ningun entorno
solo porque el codigo exista, requiere habilitacion explicita.

## Siguiente paso real (no ejecutado, fuera de esta pasada)

Replicar el patrón `BuscarClienteTool` (Tool -> Selector existente ->
SSoT, con tests de aislamiento) a 2-3 dominios más de bajo riesgo
(`proveedores`, `productos`) antes de tocar `VALIDATE`/`SUGGEST`, y
solo abordar `WRITE` cuando exista un diseño concreto del flujo de
aprobación (preview → confirmación → servicio → auditoría, Regla
Absoluta 7) con al menos un caso de uso real detrás.
