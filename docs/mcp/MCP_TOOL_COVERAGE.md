# MCP_TOOL_COVERAGE — protocolo MCP real (`/mcp/`), Wave 1

> Cobertura del protocolo MCP real (`django-rest-framework-mcp` vía
> `SintelMCPView`, ver `ADR-MCP-002.md`). **No confundir con
> `MCP_DOMAIN_MATRIX.md`** (dominio `platform` de `AIToolRegistry`,
> ADR-MCP-001, sin cambios). Toda fila de esta tabla fue verificada en
> vivo (2026-10-02) contra el tenant real `home` — ver evidencia al
> final, no solo "el endpoint existe".

## Matriz (Sección 35/39 del plan)

| App | Recurso | Read | Create | Update | Delete | Actions | Scope | Audit | Status |
|---|---|---|---|---|---|---|---|---|---|
| proyectos | Proyecto | `list_projects`/`retrieve_projects` — **VERIFIED** | — | — | — | — | `IsTenantMember` + `IsTenantAdminOrReadOnly` (vía fix AI-07) | logging estructurado (`SintelMCP`), sin persistencia | Wave 1 read-only |
| compras | OrdenCompra | `list_purchase_orders`/`retrieve_purchase_orders` — **VERIFIED** | — | — | — | — | `IsTenantMember` + `IsTenantAdminOrReadOnly` + `HasOrganizationalScope` (object-level, sin cambios) | ídem | Wave 1 read-only |
| clientes | Cliente | `list_clients`/`retrieve_clients` — **VERIFIED** | — | — | — | — | `IsTenantMember` + `IsTenantAdminOrReadOnly` | ídem | Wave 1 read-only |

Todas las demás apps (`empresa`, `proveedores`, `empleados`,
`cotizaciones`, `ventas`, `inventario`, `gastos`, `bancos`, `facturas`,
`contabilidad`, Tier B) — **`NOT_IMPLEMENTED`**, sin ViewSet decorado
todavía. No forman parte de este entregable (Sección 47 del plan: "el
primer commit NO debe intentar exponer las 16 apps inmediatamente").

## Qué se verificó por cada fila (no solo "el endpoint existe")

- [x] **tool discovery**: `tools/list` autenticado devuelve exactamente
      6 tools (`list_projects`, `retrieve_projects`,
      `list_purchase_orders`, `retrieve_purchase_orders`,
      `list_clients`, `retrieve_clients`). `destroy_projects`/
      `create_*`/etc. no existen (`Tool not found`).
- [x] **authentication**: `initialize`/`tools/list`/`tools/call` sin
      credencial → `Unauthorized`, nunca listan ni ejecutan nada.
- [x] **permission**: usuario con `TenantProfile.rol='VISOR'` (no-ADMIN)
      ejecuta `list_projects`/`retrieve_projects` con éxito — prueba
      directa de que AI-07 ya no bloquea lectura a roles no-ADMIN (antes
      del fix, `request.method=None` hacía que `IsTenantAdminOrReadOnly`
      rechazara con 403 *cualquier* acción MCP para no-ADMIN).
- [x] **tenant isolation**: UUID real de un Proyecto del tenant `admin`,
      consultado vía host `home` → "no encontrado", nunca devuelve el
      dato cross-tenant.
- [x] **serialization**: `retrieve_projects` con UUID real devuelve el
      mismo payload que `ProyectoDetailSerializer` expone por API REST
      normal (mismo ViewSet, mismo serializer — no hay una segunda
      lógica).
- [x] **service execution**: la llamada pasa por
      `ProyectoViewSet.list()/get_object()` reales (selectors +
      `.only()`/`select_related`), nunca `Model.objects.all()`.
- [x] **real DB mutation**: N/A en esta Wave (solo lectura).
- [ ] **rollback**: N/A en esta Wave (solo lectura, nada que revertir).
- [ ] **audit event persistente**: `DEFERRED` — solo `logger.info`/
      `logger.warning` en `apps/services/mcp/gateway.py` (`tool`,
      `action`, `user_id`, resultado). Sin modelo `MCPAuditEvent`
      (Fase 18 del plan) en este entregable — explícito, no omitido por
      descuido.

## Convención de nombres (Sección 31 del plan) — pendiente, cosmético

El paquete genera nombres `<acción>_<basename>` (`list_projects`,
`retrieve_projects`). La Sección 31 del plan pide `<resource>_<operation>`
(`projects_list`, `projects_get`). Requiere decorar cada método
(`@mcp_tool(name=...)`) individualmente — no bloquea la Wave 1 (los
nombres actuales son únicos y funcionales), se difiere a cuando se
agreguen acciones custom de dominio (Wave 3), momento en que de todas
formas hay que tocar cada método uno por uno.

## Evidencia (sesión 2026-10-02, tenant `home`)

```
tools/list (autenticado) -> 6 tools: list_projects, retrieve_projects,
  list_purchase_orders, retrieve_purchase_orders, list_clients, retrieve_clients

tools/call list_projects (rol VISOR)        -> isError=false, count=1
tools/call retrieve_projects(uuid real)     -> isError=false, nombre="Proyecto Auditoria QA"
tools/call retrieve_projects(uuid inventado)-> isError=true, "Proyecto no encontrado..."
tools/call retrieve_projects(uuid de OTRO tenant, host=home) -> isError=true, "no encontrado" (sin fuga)
tools/call destroy_projects (no registrada) -> isError=true, "Tool not found: destroy_projects"
tools/call list_clients                     -> isError=false, count=4
tools/call list_purchase_orders             -> isError=false, count=2
initialize/tools-list SIN autenticar        -> "Unauthorized" (RETURN_200_FOR_ERRORS=True, HTTP 200 + isError)
```

Usuario de prueba (`mcp_smoke_visor`, `TenantProfile.rol=VISOR`,
`TenantMembership` en schema `public`) creado, verificado y **eliminado**
al cierre de la sesión — no queda en ningún tenant real.
