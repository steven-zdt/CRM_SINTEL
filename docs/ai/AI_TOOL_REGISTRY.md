# AI_TOOL_REGISTRY — Fases 11-16 (+ AI-02/AI-03/AI-04, misión evolución contextual, 2026-09-01)

## Definición de "AI-03 terminado" (decisión explícita, 2026-09-01)

**No** es "existen READ tools para los 13 dominios del ERP". **Es**:
AI-03 está cerrado cuando todo dominio actualmente elegible tiene su
READ tool implementada/testeada/registrada, y todo dominio no
elegible queda formalmente bloqueado por una dependencia explícita
(no como "pendiente" ambiguo que una auditoría futura reinterprete
como incompleto).

```
AI-03 READ/SUGGEST TOOLS -- CERRADO (2026-09-01, ver "Cierre formal" abajo)
├── VERIFIED (implementadas, testeadas, registradas)
│   ├── clientes, inventario, proveedores, ventas, compras
│   ├── cotizaciones, gastos, proyectos
│   ├── facturas (READ-only permanente, ver fila en la tabla abajo)
│   ├── empleados (SENSITIVE_READ, ver AI_SECURITY_MODEL.md -- PII solo rol ADMIN, salud/nomina nunca)
│   ├── bancos (SENSITIVE_READ, ver AI_SECURITY_MODEL.md -- numero de cuenta siempre enmascarado, saldos/movimientos nunca)
│   └── contabilidad (SUGGEST, ver AI_CONTABILIDAD_INTEGRATION.md -- envuelve el Asistente Contable ya existente, requiere rol ADMIN, nunca escribe)
│
└── DEFERRED (fuera de alcance actual, no es deuda pendiente)
    ├── impuestos   → owner_phase = TBD, reason = domain intentionally deferred
    └── reporting   → owner_phase = TBD, reason = domain intentionally deferred
```

### Cierre formal de AI-03 (2026-09-01)

Los 3 dominios que estaban `BLOCKED BY DESIGN` (empleados, bancos,
contabilidad) quedaron `VERIFIED` en el orden acordado con el usuario
(`task_a8ca8af1` → facturas → `AI_SECURITY_MODEL.md` → empleados →
bancos → diseño de integración contable → contabilidad). No quedan
dominios `BLOCKED` -- solo `impuestos`/`reporting`, que son `DEFERRED`
por decisión explícita, no deuda técnica. **AI-03 se declara cerrado
bajo la definición de la sección anterior**: no implica que los 13
dominios del ERP tengan una tool -- implica que todo dominio elegible
la tiene, y los no elegibles están formalmente registrados como fuera
de alcance.

## AI-04 (Validation Engine) — primer lote, 2026-09-01

Mismo criterio VERIFIED/BLOCKED/DEFERRED que AI-03. Patrón: cada tool
`validar_*` envuelve `Serializer.is_valid()` del serializer DRF de
ESCRITURA real de cada dominio (nunca reimplementa la regla, ver
`apps/services/ai/tools/_validation.py`) -- `.is_valid()` nunca escribe
en la base de datos, solo `.save()` lo hace, y esta tool nunca lo
llama. Contrato de salida: `{"valid": bool, "warnings": [...],
"missing_data": [...]}` (ya documentado desde Fase 14, implementado
por primera vez aquí).

```
AI-04 VALIDATION TOOLS -- primer lote cerrado (2026-09-01)
├── VERIFIED (Serializer de escritura confirmado sin dependencia de un
│   │         request de Django real -- solo necesita empresa_id/empresa)
│   ├── clientes, proveedores, inventario (productos)
│   └── compras, cotizaciones, gastos
│
└── PENDIENTE (investigacion real hecha, no wrap-a-ciegas)
    ├── ventas    → VentaDetailSerializer NO tiene metodo validate()
    │                propio (verificado) -- la logica de negocio real
    │                vive en otro lado (posiblemente ligada a
    │                COMERCIAL-05, la maquina de estados Venta<->Factura
    │                que el usuario ya identifico como trabajo aparte).
    │                Envolver el serializer tal cual solo validaria
    │                campos, no las reglas reales -- se prefiere no
    │                implementar antes que implementar algo enganoso.
    ├── facturas, empleados, bancos, contabilidad → no aplica ("validar"
    │                antes de crear no tiene sentido para dominios
    │                READ-only/import-only o para el Asistente Contable,
    │                que ya valida internamente antes de sugerir)
    └── impuestos, reporting → mismo DEFERRED que en AI-03
```

**Hallazgos reales durante la implementación** (documentados porque
cambian lo que "valid: True" realmente garantiza en cada dominio):

- `validar_producto`: NO detecta `codigo` duplicado -- la constraint
  real usa `Lower('codigo')` (expresión), que DRF no valida
  automáticamente; solo se descubre en el `.save()` real.
- `validar_cotizacion`/`validar_gasto`: el chequeo de alcance
  organizacional de sede (`sede_esta_en_alcance()`) requiere un
  `request` de Django real y **degrada a "permitido" sin uno**
  (comportamiento documentado de esa función, no un bug) -- estas 2
  tools sí reproducen el chequeo anti-IDOR más simple ("la sede
  pertenece a esta empresa"), pero no el de alcance organizacional
  fino.
- `validar_gasto`: `subtotal`/`total`/`resolucion_dian` son
  `read_only` en `GastoDetailSerializer` -- el business service los
  calcula aparte. "valid: True" en `validar_gasto` solo garantiza que
  `proveedor` (y `sede`, si se incluye) son correctos, no que los
  montos lo sean.
- `validar_cotizacion`: pese a que `Cotizacion.cliente`/`configuracion`
  permiten `NULL` a nivel de modelo, `CotizacionSerializer` los declara
  sin `required=False` -- son requeridos a nivel de serializer aunque
  no lo sean a nivel de base de datos.

## Implementado (19 tools reales: 13 READ/SUGGEST + 6 VALIDATE)

| Tool | Dominio | Kind | Risk | Confirmación | Servicio subyacente |
|---|---|---|---|---|---|
| `buscar_cliente` | `clientes` | READ | `SAFE_READ` | No | `apps.tenant.clientes.services.selectors.ClienteSelector` |
| `ai_project_map` | `platform` (transversal, ver `AI_EKG.md`* nota abajo) | READ | `SAFE_READ` | No | `django.apps.apps.get_models()` (owner) + `tools/ekg/queries.py` + snapshots `tools/ekg/out/<app>.json` (rules/docs/fk) |
| `buscar_producto` | `inventario` | READ | `SAFE_READ` | No | `apps.tenant.inventario.services.selectors.ProductoSelector` (incluye `stock_actual`, cubre AI-03.2 completa sin tool separada de stock) |
| `buscar_proveedor` | `proveedores` | READ | `SAFE_READ` | No | `apps.tenant.proveedores.services.selectors.ProveedorSelector` |
| `consultar_venta` | `ventas` | READ | `SAFE_READ` | No | `apps.tenant.ventas.services.selectors.VentaSelector` (filtro por `estado`, incluye nombre de cliente) |
| `consultar_compra` | `compras` | READ | `SAFE_READ` | No | `apps.tenant.compras.services.selectors.OrdenCompraSelector` — **primera tool que respeta alcance organizacional real** (sede/área), no solo `empresa_id`, ver `AI_CONTEXT_MODEL.md` |
| `consultar_cotizacion` | `cotizaciones` | READ | `SAFE_READ` | No | `apps.tenant.cotizaciones.services.selectors.CotizacionSelector` — respeta sede vía filtro NULL-safe (OSF Fase F7) |
| `consultar_gasto` | `gastos` | READ | `SAFE_READ` | No | `apps.tenant.gastos.services.selectors.DocumentoSelector` (modelo `DocumentoSoporte`) — mismo filtro NULL-safe de sede |
| `consultar_proyecto` | `proyectos` | READ | `SAFE_READ` | No | `apps.tenant.proyectos.services.selectors.qs_list` — mismo filtro NULL-safe de sede |
| `consultar_factura` | `facturas` | READ | `SAFE_READ` | No | `apps.tenant.facturas.services.selectors.FacturaSelectors.qs_list` — **READ-only permanente por diseño** (FASE 21): nunca habrá `crear_factura`/`anular_factura`/`transmitir_factura` en el AI Engine, esa escritura vive solo en el pipeline propietario (`FacturaBusinessService`) |
| `buscar_empleado` | `empleados` | READ | `SENSITIVE_READ` | No | `apps.tenant.empleados.services.selectors.EmpleadoSelector` — **primer dominio sensible**: PII (`numero_documento`/`email`/`telefono`) solo si `context.rol == "ADMIN"`, salud/afiliación (EPS/AFP/ARL) y nómina (`Contrato`/`Devengo`) nunca expuestos por esta tool, `limit` máximo 10 (no 50); ver clasificación completa en `AI_SECURITY_MODEL.md` |
| `consultar_cuenta_bancaria` | `bancos` | READ | `SENSITIVE_READ` | No | `apps.tenant.bancos.services.selectors.CuentaBancariaSelector` — número de cuenta **siempre enmascarado** (`****1234`, sin excepción de rol), saldos/movimientos (`ExtractoBancario`/`TransaccionBancaria`) nunca expuestos por esta tool, `limit` máximo 10; ver `AI_SECURITY_MODEL.md` |
| `sugerir_asiento_contable` | `contabilidad` | **SUGGEST** | `SENSITIVE_READ` | **Sí** | `apps.tenant.contabilidad.services.business_service.ContabilidadBusinessService.sugerir_lineas_asiento_ia` — **envuelve el Asistente Contable ya existente en producción**, no lo reimplementa; requiere `context.rol == "ADMIN"` (mismo permiso que el endpoint real `POST /pendientes/asistente-ia/`); nunca escribe un `AsientoContable` (esa persistencia sigue siendo `contabilizar_documento_manual()`, un flujo de confirmación humana fuera de esta tool); ver `AI_CONTABILIDAD_INTEGRATION.md` |
| `validar_cliente` | `clientes` | **VALIDATE** | `SAFE_READ` | No | `ClienteDetailSerializer.is_valid()` — reutiliza la regla anti-duplicidad de documento (FASE 4) ya existente, nunca escribe |
| `validar_proveedor` | `proveedores` | **VALIDATE** | `SAFE_READ` | No | `ProveedorDetailSerializer.is_valid()` — misma regla anti-duplicidad |
| `validar_producto` | `inventario` | **VALIDATE** | `SAFE_READ` | No | `ProductoDetailSerializer.is_valid()` — valida que `categoria` pertenezca al tenant y sea aplicable a productos; **no** detecta `codigo` duplicado (constraint con `Lower()`, DRF no la valida) |
| `validar_compra` | `compras` | **VALIDATE** | `SAFE_READ` | No | `OrdenCompraCreateUpdateSerializer.is_valid()` (el serializer de ESCRITURA, distinto del `Detail` read-only) — valida `fecha_entrega >= fecha` y al menos 1 item |
| `validar_cotizacion` | `cotizaciones` | **VALIDATE** | `SAFE_READ` | No | `CotizacionSerializer.is_valid()` — requiere `Empresa` real en contexto (resuelta internamente); valida que `cliente`/`configuracion`/`sede` pertenezcan al tenant |
| `validar_gasto` | `gastos` | **VALIDATE** | `SAFE_READ` | No | `GastoDetailSerializer.is_valid()` (alias de `DocumentoSoporteDetailSerializer`) — solo `proveedor`/`sede` son realmente controlados por este serializer, montos son `read_only` |

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
| `clientes` | `apps.tenant.clientes` | `buscar_cliente` ✅ **implementada** | `validar_cliente` ✅ **implementada** | `crear_cliente` |
| `proveedores` | `apps.tenant.proveedores` | `buscar_proveedor` ✅ **implementada** | `validar_proveedor` ✅ **implementada** | `crear_proveedor` |
| `productos`/`inventario` | `apps.tenant.inventario` | `buscar_producto` ✅ **implementada** (incluye stock, `consultar_stock` no necesita tool separada) | `validar_producto` ✅ **implementada** (no detecta codigo duplicado, ver nota AI-04) | `crear_producto` |
| `cotizaciones` | `apps.tenant.cotizaciones` | `consultar_cotizacion` ✅ **implementada** (sede NULL-safe) | `validar_cotizacion` ✅ **implementada** | `crear_borrador_cotizacion` |
| `ventas` | `apps.tenant.ventas` | `consultar_venta` ✅ **implementada** (filtro por estado, nombre de cliente) | `validar_venta` -- **investigado, no implementada**: `VentaDetailSerializer` no tiene `validate()` propio, ver nota AI-04 | (no priorizada -- pipeline propietario complejo) |
| `facturas` | `apps.tenant.facturas` | `consultar_factura` ✅ **implementada** (sede NULL-safe) | `validar_factura` | **nunca directa** -- ver `FASE 21` de la misión, pipeline propietario obligatorio |
| `compras` | `apps.tenant.compras` | `consultar_compra` ✅ **implementada** (respeta alcance sede/área real) | `validar_compra` ✅ **implementada** | (no priorizada) |
| `gastos` | `apps.tenant.gastos` | `consultar_gasto` ✅ **implementada** (sede NULL-safe) | `validar_gasto` ✅ **implementada** (solo proveedor/sede, montos son read-only) | `crear_gasto` |
| `proyectos` | `apps.tenant.proyectos` | `consultar_proyecto` ✅ **implementada** (sede NULL-safe) | -- | -- |
| `empleados` | `apps.tenant.empleados` | `buscar_empleado` ✅ **implementada** (`SENSITIVE_READ`, PII solo ADMIN) | -- | -- (datos sensibles, ver `AI_SECURITY_MODEL.md`) |
| `bancos` | `apps.tenant.bancos` | `consultar_cuenta_bancaria` ✅ **implementada** (`SENSITIVE_READ`, número siempre enmascarado) | `verificar_pago` | -- (datos sensibles) |
| `contabilidad` | `apps.tenant.contabilidad` | `consultar_asiento` (diseño, no implementada) | `sugerir_asiento_contable` ✅ **implementada** (SUGGEST, orquesta el Asistente Contable existente, ver `AI_CONTABILIDAD_INTEGRATION.md`) | -- |
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
