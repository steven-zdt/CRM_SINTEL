# AI_MEMORY_POLICY — Fase 27

**No implementado.** No existe hoy ningún flujo conversacional
multi-turno real (`buscar_cliente` es una llamada única, sin turno
anterior que recordar) -- construir un modelo de sesión sin un
consumidor real habría sido especulativo.

## Diseño para cuando exista un flujo conversacional real

- **Session memory** (contexto de la conversación actual): vive en
  Redis (ya usado como cache/broker en este proyecto, no se introduce
  una dependencia nueva), con TTL corto, scoped por
  `(tenant_schema, user_id, session_id)`.
- **Durable preferences** (si el usuario pide "recuerda que prefiero
  X"): requeriría un modelo Django nuevo, tenant-scoped
  (`SintelTenantBaseModel`, con `empresa_id` -- igual que cualquier
  otro modelo de este codebase), **no implementado**, evaluado caso a
  caso cuando exista la necesidad real.
- **Nunca persistir:** passwords, secrets, tokens, ni el contenido
  completo de documentos sensibles (nómina/bancos) dentro de la
  memoria de sesión -- solo referencias (IDs/UUIDs) que se resuelven
  de nuevo contra el Selector correspondiente en cada turno, respetando
  siempre el `AIContext` del turno actual (no el de cuando se guardó
  la referencia -- los permisos pueden haber cambiado entre turnos).

## No se guarda indiscriminadamente toda la conversación

Regla explícita de la Fase 27, ya reflejada en el diseño de arriba:
la memoria de sesión es de corta duración y con propósito (continuar
la tarea actual), no un log completo y permanente de todo lo dicho.
