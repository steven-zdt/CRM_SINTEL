# AI_TOOL_REGISTRY — Fases 11-16 (+ AI-02/AI-03, misión evolución contextual, 2026-09-01)

## Implementado (6 tools reales)

| Tool | Dominio | Kind | Risk | Confirmación | Servicio subyacente |
|---|---|---|---|---|---|
| `buscar_cliente` | `clientes` | READ | `SAFE_READ` | No | `apps.tenant.clientes.services.selectors.ClienteSelector` |
| `ai_project_map` | `platform` (transversal, ver `AI_EKG.md`* nota abajo) | READ | `SAFE_READ` | No | `django.apps.apps.get_models()` (owner) + `tools/ekg/queries.py` + snapshots `tools/ekg/out/<app>.json` (rules/docs/fk) |
| `buscar_producto` | `inventario` | READ | `SAFE_READ` | No | `apps.tenant.inventario.services.selectors.ProductoSelector` (incluye `stock_actual`, cubre AI-03.2 completa sin tool separada de stock) |
| `buscar_proveedor` | `proveedores` | READ | `SAFE_READ` | No | `apps.tenant.proveedores.services.selectors.ProveedorSelector` |
| `consultar_venta` | `ventas` | READ | `SAFE_READ` | No | `apps.tenant.ventas.services.selectors.VentaSelector` (filtro por `estado`, incluye nombre de cliente) |
| `consultar_compra` | `compras` | READ | `SAFE_READ` | No | `apps.tenant.compras.services.selectors.OrdenCompraSelector` — **primera tool que respeta alcance organizacional real** (sede/área), no solo `empresa_id`, ver `AI_CONTEXT_MODEL.md` |

`*` La misión de evolución pide un documento `AI_EKG.md` dedicado —
decisión explícita: no se crea, para no duplicar contenido casi
idéntico al ya existente en `AI_ENGINE_ARCHITECTURE.md` §"EKG / Knowledge
Graph tool" (Regla 9 de esa misión, "NO DUPLICAR"). El detalle de
`ai_project_map` vive ahí y aquí; se actualizan ambos in situ.

Metadata completa vía `apps.services.ai.tools.tool_metadata()` (nunca
se expone el objeto Python de la tool en sí, solo el dict
serializable -- Regla Absoluta 12).

## Diseño — AI Domain Registry (Fase 11), no implementado

Para cada dominio del ERP, el patrón a replicar (usando `clientes`
como ejemplo ya construido):

| Dominio | Owner (app) | Read tools (diseño) | Validation tools (diseño) | Write tools (diseño) |
|---|---|---|---|---|
| `clientes` | `apps.tenant.clientes` | `buscar_cliente` ✅ **implementada** | `validar_cliente` | `crear_cliente` |
| `proveedores` | `apps.tenant.proveedores` | `buscar_proveedor` ✅ **implementada** | `validar_proveedor` | `crear_proveedor` |
| `productos`/`inventario` | `apps.tenant.inventario` | `buscar_producto` ✅ **implementada** (incluye stock, `consultar_stock` no necesita tool separada) | `validar_producto` | `crear_producto` |
| `cotizaciones` | `apps.tenant.cotizaciones` | `consultar_cotizacion` | `validar_cotizacion` | `crear_borrador_cotizacion` |
| `ventas` | `apps.tenant.ventas` | `consultar_venta` ✅ **implementada** (filtro por estado, nombre de cliente) | `validar_venta` | (no priorizada -- pipeline propietario complejo) |
| `facturas` | `apps.tenant.facturas` | `consultar_factura` | `validar_factura` | **nunca directa** -- ver `FASE 21` de la misión, pipeline propietario obligatorio |
| `compras` | `apps.tenant.compras` | `consultar_compra` ✅ **implementada** (respeta alcance sede/área real) | `validar_compra` | (no priorizada) |
| `gastos` | `apps.tenant.gastos` | `consultar_gasto` | `validar_gasto` | `crear_gasto` |
| `proyectos` | `apps.tenant.proyectos` | `consultar_proyecto` | -- | -- |
| `empleados` | `apps.tenant.empleados` | `consultar_empleado` | -- | -- (datos sensibles, ver `AI_SECURITY_MODEL.md`) |
| `bancos` | `apps.tenant.bancos` | `consultar_banco` | `verificar_pago` | -- (datos sensibles) |
| `contabilidad` | `apps.tenant.contabilidad` | `consultar_asiento` | `validar_asiento` | **orquesta el Asistente Contable existente, no lo duplica** (ver `AI_ENGINE_ARCHITECTURE.md`) |
| `impuestos` | `apps.public.impuestos` | `consultar_impuestos` | -- | -- |
| `reporting` | `apps.tenant.dashboard` | `consultar_reporte` | -- | -- |

Cada fila de esta tabla es una tool **por construir**, siguiendo
exactamente el patrón de `BuscarClienteTool`
(`apps/services/ai/tools/clientes_tools.py`): envolver un
Selector/Service ya existente, nunca reimplementar la consulta.

## Fase 14 — Validation tools (diseño)

Contrato esperado (no implementado): `ToolResult.data` con forma
`{"valid": bool, "warnings": [...], "missing_data": [...]}`. Reutiliza
las validaciones YA existentes en cada `business_service.py` (ej.
`FacturaBusinessService`, `VentaBusinessService`) -- una `validate_*`
tool nunca reimplementa reglas de negocio, las invoca.

## Fase 15 — Suggestion tools (diseño)

Sugerencia ≠ escritura (regla explícita). Contrato esperado:
`ToolResult.data` con el valor sugerido + `"confidence"` +
`"reasoning"` breve -- nunca un ID de un registro ya creado, porque no
se creó nada.

## Fase 16 — Write tools (diseño, explícitamente no implementado)

**Ninguna tool WRITE existe ni se registrará hasta que exista un
flujo de aprobación real** (`AI_RELEASE_GATE.md`, ítem bloqueante).
`AIEngine.run_tool()` ya rechaza estructuralmente cualquier tool con
`kind=WRITE` hoy mismo (`AUTO_APPROVED_KINDS`), así que registrar una
tool WRITE sin ese flujo fallaría en producción de inmediato -- no es
solo una intención documentada.

## Clasificación de riesgo (Fase 3/12) — aplicada, no solo tabulada

`ToolRisk` (`apps/services/ai/tools/base.py`): `SAFE_READ`,
`SENSITIVE_READ`, `SAFE_WRITE`, `SENSITIVE_WRITE`, `HIGH_RISK`. La
única tool real (`buscar_cliente`) es `SAFE_READ` -- devuelve solo
campos ya visibles en la UI de listado de clientes
(`ClienteSelector.LIST_FIELDS`), sin datos financieros/fiscales
detallados (esos viven en `DETAIL_FIELDS`, no expuestos por esta
tool).
