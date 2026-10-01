# MCP_SECURITY_MODEL — Fase 24-26/36-43, LOOP 1

> No duplica `docs/ai/AI_SECURITY_MODEL.md` (regla explícita del
> prompt maestro §87/AGENTS.md) — hereda su modelo completo (4
> verificaciones estructurales en `AIEngine.run_tool()`, `ToolRisk`
> como metadata sin enforcement automático, clasificación de campos
> sensibles). Este documento cubre **solo lo específico de las tools
> `domain="platform"`** nuevas de esta misión (ver `ADR-MCP-001.md`).

## Qué cambia con `domain="platform"`

- **No hay datos de tenant que proteger** en `project_inventory` (y en
  el resto del catálogo diseñado): censa la estructura del *código*
  (apps, modelos, presencia de carpetas, reglas de gobernanza), no
  filas de ninguna tabla `tenant_*`. Por eso no filtra por
  `context.empresa_id` — mismo criterio ya usado por `ai_project_map`.
- **Sigue pasando por las 4 verificaciones de `AIEngine.run_tool()`**
  sin excepción: `AI_ENABLED`, `AI_READ_ENABLED`, `tool.kind in
  AUTO_APPROVED_KINDS`, `build_context(request)` válido. Un caller sin
  `TenantProfile` no ejecuta `project_inventory` aunque el resultado no
  sea información de un tenant — no existe un segundo camino de
  autorización "más liviano" para tools de plataforma.
- **Superficie nueva de exposición**: `project_inventory` revela
  estructura interna del código (qué apps existen, qué management
  commands tiene cada una, si falta `services/`/`tests/`) a cualquier
  usuario autenticado con `TenantProfile` válido — no solo a un
  `ADMIN`. Es información arquitectónica, no de negocio, pero un
  atacante con una cuenta `OPERADOR` legítima podría usarla para
  mapear superficie de ataque (ej. "qué apps no tienen `tests/`"). Se
  acepta este riesgo en `ToolRisk.SAFE_READ` porque:
  1. Es la misma información que ya es pública para cualquiera con
     acceso al repositorio (git, CI, este mismo directorio `docs/`).
  2. No expone secretos, código fuente, ni datos de negocio — solo
     nombres de apps/modelos/comandos y booleanos de presencia
     estructural.
  3. Si en el futuro se agregan tools de plataforma que sí revelen
     algo más sensible (ej. contenido de reglas de negocio, hallazgos
     de auditoría con severidad P0), deben clasificarse
     `SENSITIVE_READ` como mínimo y documentarse aquí explícitamente
     — no se hereda `SAFE_READ` por defecto para tools futuras de este
     dominio.
- **`ToolRisk` sigue sin enforcement automático** (mismo hallazgo que
  `AI_SECURITY_MODEL.md` ya documenta para el resto del catálogo):
  `AIEngine.run_tool()` no lee `tool.risk`. Cualquier control adicional
  para una tool `platform` futura debe implementarse dentro de su
  propio `run()`.

## Auditoría de acceso

Sin cambios respecto al mecanismo ya existente: `AIEngine.run_tool()`
loguea `tool_name`/`kind`/`status`/`user_id`/`empresa_id` para
**cualquier** tool, incluidas las de `domain="platform"` — no se
necesita ningún cambio en `ai_engine.py` antes de registrar
`project_inventory` (verificado leyendo el código, mismo mecanismo que
ya cubre tools `SENSITIVE_READ` de negocio).

## Operaciones destructivas / WRITE / CODE_REPAIR (§32-34 del prompt maestro)

Ninguna tool `platform` implementada en esta pasada escribe nada — ni
en la base de datos, ni en el filesystem del proyecto. `propose_code_fix`/
`apply_code_fix` (§31-32, §70 del prompt maestro) **no se diseñan
todavía**: requieren primero que exista un flujo de aprobación humana
real (mismo bloqueo estructural que ya aplica a `WRITE` de negocio,
`AUTO_APPROVED_KINDS`) y una estrategia de rollback — quedan
`NOT_IMPLEMENTED`, sin fecha, hasta que el usuario priorice esa fase
explícitamente (LOOP 5 del prompt maestro, §85).

## Comandos prohibidos (§33/§72 del prompt maestro) — confirmado, sin cambios

Ninguna tool de esta misión expone ni expondrá `shell(command)`,
`exec(command)`, `python(code)`, `sql(query)`, `docker(command)`,
`filesystem_write(path, content)` genéricos. `run_tests`/`django_check`/
`migration_check`/`governance_audit`/`production_readiness` (cuando se
implementen) invocan comandos **allowlisted y fijos** (ej. `pytest
<target_validado>`, `manage.py check`), nunca una cadena arbitraria
construida desde el input del agente.
