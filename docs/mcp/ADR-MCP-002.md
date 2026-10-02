# ADR-MCP-002 — Reabre el protocolo MCP real (`/mcp/`) como vía adicional, gobernada por `SintelMCPView`

**Estado:** Aceptado (2026-10-02, decisión explícita del usuario tras
presentarle el conflicto con ADR-MCP-001)
**Contexto de la misión:** `PLAN_MCP_OPERACIONAL_PRIVADO_SINTEL_ERP.md`

## Contexto

`ADR-MCP-001.md` (2026-09-25) decidió que el "MCP Control Plane" sería
`AIToolRegistry`/`AIEngine`, **no** el protocolo MCP real expuesto en
`/mcp/` (`django-rest-framework-mcp`), citando como bloqueante:

1. **AI-07**: `MCPView.execute_tool()` construye un `HttpRequest()` crudo
   para invocar la acción del ViewSet, pero nunca asigna `request.method`
   — verificado en código: `HttpRequest().method is None`. Cualquier
   permiso que distinga lectura/escritura por método HTTP (`IsTenantAdminOrReadOnly`,
   usada por prácticamente todos los ViewSets tenant) trata **toda**
   llamada MCP como escritura, bloqueando con 403 a cualquier rol
   no-ADMIN incluso para `list`/`retrieve`.
2. Gap de autenticación en la capa de descubrimiento: `MCPView` monta con
   `authentication_classes = []` y `has_mcp_permission() -> True` por
   defecto — `initialize`/`tools/list` eran alcanzables sin credencial.

`ADR-MCP-001` dejó explícitamente la puerta abierta: *"Si el usuario pide
en el futuro clientes MCP externos reales, este ADR debe revisarse
explícitamente."* `PLAN_MCP_OPERACIONAL_PRIVADO_SINTEL_ERP.md` es
exactamente esa petición (Sección 29/FASE 25: Antigravity, Claude
Desktop, Cursor como clientes MCP reales contra `https://<tenant>.sintel.net.co/mcp/`).

Presentado el conflicto al usuario (ambas rutas descritas con su costo
real), eligió explícitamente **reabrir** la vía del protocolo real en vez
de traducir el plan nuevo a `AIToolRegistry`.

## Decisión

**El protocolo MCP real (`/mcp/`, `django-rest-framework-mcp`) queda
habilitado como vía operacional adicional**, gobernado íntegramente por
una capa propia — `apps/services/mcp/` — que nunca delega en el paquete
sin pasar antes por ella. `AIToolRegistry`/`AIEngine` (dominio
`platform`, ADR-MCP-001) **no se toca ni se reemplaza** — sigue siendo el
motor real para auditoría de código/arquitectura y tools de negocio
internas; ambas superficies coexisten con fronteras explícitas (la
alternativa "ambas superficies con frontera explícita" que ADR-MCP-001
dejó diferida, no descartada).

### AI-07: corregido, no rodeado

`apps/services/mcp/gateway.py::SintelMCPView.execute_tool()` es una copia
de `MCPView.execute_tool()` (`django-rest-framework-mcp==0.1.0a4`) con
una única línea agregada: `request.method` se asigna según un mapa
acción→método HTTP estándar de DRF (`list`/`retrieve`→GET,
`create`→POST, `update`→PUT, `partial_update`→PATCH, `destroy`→DELETE)
**antes** de construir el `Request` de DRF que los permisos del ViewSet
evalúan. No se actualizó el paquete (sigue en `0.1.0a4`, alpha) ni se
decoró ningún ViewSet con bypass de permisos — el fix vive enteramente
en código propio, versionado y comentado con el motivo exacto.

**Verificado en vivo (no solo en teoría)**, contra el tenant real `home`:
- Un usuario con `TenantProfile.rol='VISOR'` (no-ADMIN) — antes del fix,
  cualquier rol no-ADMIN recibía 403 en `IsTenantAdminOrReadOnly` para
  *cualquier* acción MCP — pudo ejecutar `list_projects`/
  `retrieve_projects` exitosamente (datos reales devueltos,
  `isError: false`).
- `/mcp/` sin autenticar: `initialize` y `tools/list` responden
  `Unauthorized`, nunca listan tools.
- Aislamiento cross-tenant: una Orden/Proyecto real del tenant `admin`,
  consultado vía host `home`, responde "no encontrado" — nunca filtra el
  dato del otro tenant.
- `destroy_projects`/`create_projects`/etc. no existen (`Tool not
  found`) — solo `list`/`retrieve` están registradas en esta Wave.

### Autenticación/autorización del endpoint MCP

`SintelMCPView` (no `MCPView` directo) es el único punto de montaje
permitido en `config/urls_tenant.py`/`config/urls_public.py`:

- `authentication_classes = [JWTAuthentication, SessionAuthentication]`
  (JWT estricta, no la variante `Relaxed`-en-DEBUG de
  `BaseTenantViewSet` — un agente MCP nunca debe degradar a
  `AnonymousUser` silenciosamente).
- `has_mcp_permission()` reutiliza `IsTenantMember`
  (`apps/tenant/api/permissions.py`) — autenticado + membresía activa en
  el tenant resuelto por `TenantMainMiddleware` vía Host header. La
  autorización fina por tool (rol/alcance organizacional) la sigue
  resolviendo cada ViewSet dentro de `execute_tool()`, sin un RBAC
  paralelo (regla explícita de la Sección 6.2 del plan).

### Alcance de este ADR: Wave 1 READ-ONLY, 3 apps piloto

Consistente con la Sección 47 del plan ("el primer commit NO debe
intentar exponer las 16 apps inmediatamente"), esta decisión cubre
únicamente:

- `apps/services/mcp/` (gateway + registro), reemplazo de los 2 mounts
  `mcp/` existentes.
- 3 ViewSets piloto, **solo `list`/`retrieve`**: `ProyectoViewSet`,
  `OrdenCompraViewSet`, `ClienteViewSet` — mismas relaciones que el plan
  recomienda validar primero (Proyecto ↔ OrdenCompra ↔ Cliente).
- Ver `MCP_TOOL_COVERAGE.md` para el detalle verificado.

Explícitamente **fuera de alcance** de este ADR (quedan para Waves
futuras, cada una con su propio gate):

- `create`/`update`/`partial_update`/`destroy` — requieren antes la
  matriz de política CRUD por rol (Fase 3 del plan) y el modelo de
  confirmación para operaciones destructivas (Fase 7).
- Acciones de dominio (`avanzar_fase`, `cambiar_estado`,
  `project_attach_purchase_order`, etc.) — Fase 8/9/10/11 del plan.
- Auditoría persistente (`MCPAuditEvent`, Fase 18) — por ahora, solo
  logging estructurado (`logger.info`/`logger.warning` en
  `SintelMCPView`), explícitamente insuficiente como audit trail real;
  no se fabricó un modelo+migración para no inflar el alcance de este
  entregable.
- Rate limiting, bulk operations, idempotency keys, observabilidad con
  métricas — Fases 14/15/19/21.
- Renombrar las tools a la convención `<resource>_<operation>` de la
  Sección 31 (hoy usan el default del paquete,
  `<operation>_<resource>`) — cosmético, no bloquea lectura real.

## Alternativas consideradas

- **Mantener ADR-MCP-001 tal cual** (traducir el plan nuevo a
  `AIToolRegistry`) — descartada por decisión explícita del usuario: el
  plan nuevo pide clientes MCP externos reales (Claude Desktop, Cursor,
  Antigravity vía `mcp-remote`), algo que `AIToolRegistry` no puede
  servir sin protocolo MCP real de por medio.
- **Actualizar `django-rest-framework-mcp` a una versión que corrija
  AI-07** — no evaluada: el paquete sigue en rango pre-release
  (`>=0.1.0a4,<0.2`) sin garantía de API estable entre versiones alpha;
  corregir en código propio es auditable y no depende del timing de un
  release de terceros.
- **Bypass de permisos del ViewSet** (`BYPASS_VIEWSET_PERMISSIONS=True`)
  — descartada: delegaría la autorización completa al gate de
  `has_mcp_permission()` (binario, sin rol/alcance), perdiendo el
  `IsTenantAdminOrReadOnly`/`HasOrganizationalScope` real de cada
  ViewSet. El plan exige explícitamente reutilizar los permisos
  existentes (Sección 6.2), no reemplazarlos.

## Consecuencias

- `docs/mcp/MCP_ARCHITECTURE.md`, `MCP_DOMAIN_MATRIX.md`,
  `MCP_SKILLS_ALIGNMENT.md`, `MCP_TOOL_CATALOG.md` (todos de la misión
  LOOP 1) **no se modifican** — siguen describiendo correctamente el
  dominio `platform` de `AIToolRegistry`, que sigue vigente sin cambios.
- `MCP_BASELINE.md` y `MCP_RELEASE_GATE.md` reciben un addendum fechado
  2026-10-02 señalando esta nueva vía, sin reescribir su contenido
  LOOP 0/1 original.
- Cualquier Wave futura (create/update/acciones de dominio/delete) debe
  medirse contra un release gate propio antes de habilitarse —
  `docs/mcp/MCP_RELEASE_GATE.md` §Wave 1 ya lista los pendientes
  explícitos.
- Si el usuario pide en el futuro exponer `create`/`update`/`destroy`,
  ese trabajo requiere primero la matriz de política CRUD (Fase 3 del
  plan) — no se infiere de esta decisión.
