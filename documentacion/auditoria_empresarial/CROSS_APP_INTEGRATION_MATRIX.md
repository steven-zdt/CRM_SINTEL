# Matriz de Integraciones Cross-App — SINTEL ERP

**Fecha:** 2026-08-27. Fuente primaria: `documentacion/F15_INTEGRATION_BASELINE.md`
(2026-08-09, grafo AST real de 368 aristas de import entre las 17 apps tenant),
actualizada con verificación de vigencia de esta sesión (2026-08-27) para las
integraciones que la propia F15 marcaba como ausentes.

Formato: ORIGEN → DESTINO | EVENTO | DATOS | ESTADO | SSoT | OBLIGATORIEDAD |
IDEMPOTENCIA | ROLLBACK | OWNER

---

| Origen | Destino | Evento | Datos | Estado | SSoT | Obligatoriedad | Idempotencia | Rollback | Owner |
|---|---|---|---|---|---|---|---|---|---|
| `ventas` | `facturas` | Venta pasa a `FACTURADA_DIAN` | DTO UBL 2.1 canónico | ✅ Confirmado, `PUSH_CONTROLLED` | `facturas.Factura` | REQUIRED_WHEN_INVOICED | Sí (consecutivo atómico, `select_for_update`) | No verificado línea por línea (delegado a agente de controles) | `facturas` |
| `ventas` | `inventario` | Venta facturada, item con producto | `KardexService.registrar_movimiento(SALIDA_VENTA)` | ✅ **Confirmado hoy** (DRIFT resuelto — F15/F18 lo marcaban ausente en 08-09) | `inventario.MovimientoInventario` | CONDITIONAL / DERIVED (solo items con `producto`, excluye servicios) | Sí (`UniqueConstraint` por `documento_origen_id`) | Reversión de venta no verificada en esta sesión | `inventario` |
| `compras` | `inventario` | `RecepcionCompra` confirmada | `KardexService.registrar_movimiento(ENTRADA_COMPRA)` | ✅ **Confirmado hoy** (DRIFT resuelto — F15/F18 lo marcaban NO implementado en 08-09) | `inventario.MovimientoInventario` | REQUIRED_WHEN_GOODS_RECEIVED | Sí (`documento_origen_modelo='RecepcionCompraItem'`) | No verificado | `inventario` |
| `facturas` (Nota Crédito) | `inventario` | NC con `ItemNotaCredito` resuelto por código | `KardexService.registrar_movimiento(ENTRADA_DEVOLUCION)` | ✅ **Confirmado hoy** (DRIFT resuelto — COLOMBIA_COMPLIANCE_TRACEABILITY.md lo marcaba "no auditado" en 08-09) | `inventario.MovimientoInventario` | CONDITIONAL / BUSINESS_REQUIRED_WHEN_RETURNED | Sí (mismo constraint) | No verificado | `inventario` |
| `inventario` (F21) | `inventario` (interno) | Traslado entre sedes solicitado→aprobado→enviado→recibido | `TrasladoInventario` + 2 `MovimientoInventario` (SALIDA/ENTRADA) | ✅ **Confirmado hoy** (DRIFT resuelto — F18.11 lo marcaba NO implementado en 08-09) | `inventario.TrasladoInventario` | OPTIONAL (solo si el tenant usa multi-sede) | Sí (2 tests de idempotencia dedicados, F21) | Sí — `cancelar()` solo antes de `EN_TRANSITO` | `inventario` |
| `facturas` | `clientes` | Factura de venta/importada requiere Cliente | `resolver_o_crear_desde_factura_venta()` | ✅ Confirmado — 2 mecanismos coexisten: `ClienteBridge` (lectura) + este método (escritura get-or-create) | `clientes.Cliente` | REQUIRED | Get-or-create, no duplica por NIT (constraint DB) | N/A (no hay reversa de creación de cliente) | `clientes` |
| `facturas` | `proveedores` | Factura de compra importada requiere Proveedor | `resolver_o_crear_desde_factura_compra()` | ✅ Confirmado, mismo patrón que clientes | `proveedores.Proveedor` | REQUIRED | Get-or-create | N/A | `proveedores` |
| `facturas` | `cotizaciones` | Lectura de Cotización origen | `CotizacionBridge` | ✅ Confirmado | `cotizaciones.Cotizacion` | OPTIONAL / CONTEXT | N/A (solo lectura) | N/A | `cotizaciones` |
| `facturas` | `bancos` | Conciliación de pago | `BancosBridge.obtener_total_conciliado()` | ✅ Confirmado — rechaza `PAGADA` si `saldo_pendiente > 0` o `total_bancos == 0` | `bancos.TransaccionBancaria` | CONDITIONAL / BUSINESS_REQUIRED_WHEN_PAID | N/A (lectura agregada) | N/A | `bancos` |
| `proyectos` | `facturas` | Lectura de factura como centro de costos | `FacturaInterAppAPI` | ✅ Confirmado, Pull | `facturas.Factura` | OPTIONAL / CONTEXT | N/A | N/A | `facturas` |
| `bancos` | `facturas`/`proveedores`/`clientes` | Vinculación manual de transacción bancaria | Soft-reference UUID (`factura_uuid`, `proveedor_uuid`, `cliente_uuid`) | ✅ Confirmado, sin lógica de cálculo, solo vinculación | Cada app propietaria de su UUID | OPTIONAL | N/A | El usuario puede desvincular manualmente (no verificado en esta sesión) | `bancos` |
| `gastos` | `contabilidad` | `DocumentoSoporte` pendiente de contabilizar | `ExtractorGastos` (Pull) + `RetencionesService` | ✅ Confirmado línea por línea en 2 sesiones distintas | `contabilidad.AsientoContable`/`Retencion` | REQUIRED | Sí (`UniqueConstraint` por documento origen) | No verificado | `contabilidad` |
| `inventario` | `contabilidad` | `MovimientoInventario` pendiente | `ExtractorInventario` (Pull) | ✅ Confirmado línea por línea (F22, ver `ACCOUNTING_FLOW_MATRIX.md`) | `contabilidad.AsientoContable` | REQUIRED (para tipos contabilizables) | Sí | No verificado | `contabilidad` |
| `facturas` | `contabilidad` | Factura pendiente | `ExtractorFacturas` (Pull) | ✅ Confirmado, Pull, sin `AsientoContable` creado desde `facturas` | `contabilidad.AsientoContable` | REQUIRED | Sí (mismo patrón) | No verificado | `contabilidad` |
| `empleados` | `contabilidad` | `Devengo` pendiente | `ExtractorNomina` (Pull) | ✅ Confirmado por nombre/consumo, no línea por línea | `contabilidad.AsientoContable` | REQUIRED | Asumido (mismo patrón), no verificado explícitamente | No verificado | `contabilidad` |
| `dashboard` | 8 apps (facturas, inventario, empleados, gastos, proyectos, clientes, sedes, proveedores) | Agregación de KPIs | 8 extractores Pull dedicados | ✅ Confirmado, todos con consumidores reales | Cada app propietaria de su dato | OPTIONAL (solo lectura agregada) | N/A | N/A | `dashboard` |
| `core` | `compras`/`perfil` | Onboarding de empresa (creación inicial) | `BusinessService` cross-app con `empresa_id` explícito | ✅ Confirmado, patrón establecido | `empresa.Empresa` | REQUIRED (solo en onboarding) | No verificado | No verificado | `core` |

## Integraciones esperadas por el prompt maestro que el código real NO tiene (no inventadas)

| Integración esperada | Realidad verificada |
|---|---|
| `compras → proveedores` como Bridge | Es FK directa normal (`OrdenCompra.proveedor`), ambos dentro del mismo tenant — no es un patrón Bridge cross-bounded-context, es una relación de modelo estándar. No es un gap, es una discrepancia de expectativa vs. arquitectura real (`F15_INTEGRATION_BASELINE.md` §6). |
| `cotizaciones → ventas` | Sin arista de dependencia detectada en el grafo AST — no existe una integración automática Cotización→Venta (crear una Venta desde una Cotización aceptada). Confirmado ausente, no inventado. |
| `inventario → gastos/proyectos` directo | No existe — `inventario` no depende de ninguna de las dos; la relación es indirecta vía soft-refs (`Gastos.movimiento_inventario_uuid`, `HistorialServicio.proyecto_uuid`), dirección de lectura correcta ya confirmada en la misión de Inventario de esta sesión. |

## `UNKNOWN` — 12 patrones sin clasificación forzada (F15, backlog de revisión manual)

`contabilidad → inventario.get_movimientos_timeline`, `dashboard →
facturas.FacturaSelectors`/`→ proyectos.qs_list`, `facturas →
empresa.{EmpresaNotConfiguredError, get_empresa_emisor_data,
get_mailbox_config}`, `facturas → perfil.get_or_create_profile`, `proveedores
→ facturas.Factura` (import directo de modelo, posible falso negativo del
método de detección "todo el archivo"), `ventas → facturas.services.dian.*`
(utilidades DIAN compartidas). Ninguno se clasificó sin evidencia en F15 —
siguen como backlog de revisión manual, no como findings fabricados en esta
sesión tampoco (fuera de alcance re-investigar los 12 uno por uno aquí).

## Ciclos de import — 8 detectados, ninguno es un `ImportError` real

`empresa↔perfil`, `bancos→clientes→facturas→bancos`, `clientes↔facturas`,
`clientes→facturas→contabilidad→clientes`, `facturas↔contabilidad`,
`contabilidad↔gastos`, `facturas→contabilidad→gastos→proveedores→facturas`,
`clientes→facturas→cotizaciones→clientes`. Todos resueltos por el patrón de
imports locales (dentro de función, no a nivel de módulo) — confirmado
indirectamente por `manage.py check` limpio con las 17 apps cargadas
simultáneamente. Son pares de relaciones Pull en direcciones distintas por
motivos independientes, no una dependencia mutua real del mismo dato — ver
`F15_INTEGRATION_BASELINE.md` §5 para el detalle completo por par.
