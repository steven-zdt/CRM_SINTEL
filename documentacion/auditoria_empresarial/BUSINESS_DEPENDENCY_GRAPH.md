# Grafo de Dependencias de Negocio — SINTEL ERP

**Fecha:** 2026-08-27. A diferencia de `CROSS_APP_INTEGRATION_MATRIX.md`
(mecanismo técnico: Bridge/Pull/FK), este documento clasifica cada relación en
términos de **negocio**: qué es realmente obligatorio para que un proceso
empresarial se complete, qué es opcional, qué es derivado, y qué es solo
trazabilidad. Regla aplicada: no convertir todo en obligatorio.

## Leyenda

- **REQUIRED**: el proceso de negocio no puede completarse sin esta relación.
- **CONDITIONAL**: obligatorio solo si ocurre un evento de negocio específico.
- **OPTIONAL**: mejora la trazabilidad/contexto pero el proceso funciona sin ella.
- **DERIVED**: se genera automáticamente como consecuencia de otra operación, el usuario no la crea directamente.
- **REFERENCE**: soft-reference de solo trazabilidad, sin efecto en el proceso.
- **TRIGGER**: un evento en el origen dispara una operación real en el destino.

---

## Ciclo comercial (Empresa → Terceros → Oferta → Compras → Inventario/Gastos → Ventas → Facturación → Cobro/Pago → Impuestos → Contabilidad)

| Origen | Destino | Tipo | Obligatoriedad | SSoT |
|---|---|---|---|---|
| Empresa | Cliente/Proveedor | REQUIRED | Todo tercero pertenece a una Empresa (`empresa_id` FK obligatorio vía `SintelTenantBaseModel`) | `empresa.Empresa` |
| Cliente | Cotización | CONDITIONAL | Una Cotización requiere un Cliente; no toda Venta requiere pasar por Cotización primero | `clientes.Cliente` |
| Cotización | Venta | **OPTIONAL, no confirmado como TRIGGER** | Sin arista de dependencia detectada entre `cotizaciones` y `ventas` (`F15_INTEGRATION_BASELINE.md`) — una Cotización aceptada NO convierte automáticamente en Venta. Este es un gap de proceso real, no una decisión confirmada como correcta | — |
| Proveedor | OrdenCompra | REQUIRED | FK directa, sin proveedor no hay orden | `proveedores.Proveedor` |
| OrdenCompra | RecepcionCompra | CONDITIONAL | Solo si la mercancía se recibe físicamente (compras de servicio puro podrían no requerir recepción — no confirmado) | `compras.OrdenCompra` |
| RecepcionCompra (confirmada) | MovimientoInventario (ENTRADA_COMPRA) | **TRIGGER, DERIVED** | El usuario no crea el movimiento manualmente — lo dispara la confirmación de recepción | `compras.RecepcionCompra` → `inventario.MovimientoInventario` |
| Venta (facturada, item con producto) | MovimientoInventario (SALIDA_VENTA) | **TRIGGER, DERIVED, CONDITIONAL** | Solo para items con `producto` (no `servicio`) — confirmado que excluye servicios explícitamente | `ventas.Venta` → `inventario.MovimientoInventario` |
| Venta (facturada) | Factura | **TRIGGER, CONDITIONAL** | Obligatorio solo cuando el estado pasa a `FACTURADA_DIAN` — una Venta puede existir en estados previos sin Factura | `ventas.Venta` → `facturas.Factura` |
| Factura (Nota Crédito con items) | MovimientoInventario (ENTRADA_DEVOLUCION) | **TRIGGER, DERIVED, CONDITIONAL** | Solo si la NC trae líneas (`ItemNotaCredito`) resolubles a un Producto por código; si no resuelve, se omite sin bloquear la NC | `facturas.NotaCredito` → `inventario.MovimientoInventario` |
| Factura | Cartera (CxC) | **DERIVED** | El saldo pendiente se deriva de `total - pagos válidos`, no es un dato capturado aparte | `facturas.Factura` |
| Factura | Banco (conciliación) | **CONDITIONAL, REQUIRED_WHEN_PAID** | Una Factura puede existir sin pago; pero NO puede marcarse `PAGADA` sin conciliación 100% en Bancos (control real verificado, `business_service.py:915-928`) | `bancos.TransaccionBancaria` |
| Factura/Gasto | Retención (Retefuente/ReteICA/ReteIVA) | CONDITIONAL | Solo si el tercero está configurado como sujeto de retención (`ConfiguracionRetenciones`) | `contabilidad.ConfiguracionRetenciones` |
| Todo documento contabilizable | AsientoContable | **TRIGGER, DERIVED** | El usuario nunca crea un asiento manualmente para estos flujos — el Extractor lo genera desde el documento origen | `contabilidad.AsientoContable` |
| Cliente/Proveedor | Bancos (vinculación de pago) | REFERENCE | Soft-reference UUID, solo trazabilidad de conciliación manual | `bancos.TransaccionBancaria` |
| Proyecto | Cotización/Venta/Gasto | REFERENCE | Soft-reference UUID + snapshot de nombre — un Proyecto puede existir sin ninguno de los tres, y viceversa | `proyectos.Proyecto` |

## Ciclo de nómina (Empleados → Nómina → Pago → Contabilidad → Soporte)

| Origen | Destino | Tipo | Obligatoriedad | SSoT |
|---|---|---|---|---|
| Empleado | Contrato | REQUIRED | Un Devengo requiere un Contrato vigente | `empleados.Contrato` |
| Contrato | Devengo (período) | REQUIRED | Todo período de nómina liquidado requiere Contrato | `empleados.Devengo` |
| Devengo | Pago | CONDITIONAL | El Devengo puede existir en estados previos (preliquidado) sin pago aún registrado | `empleados.Devengo` |
| Devengo | AsientoContable | **TRIGGER, DERIVED** | Vía `ExtractorNomina`, mismo patrón Pull que el resto | `contabilidad.AsientoContable` |
| Devengo | TransmisionNominaDIAN | **CONDITIONAL, separado a propósito** | Modelo separado del Devengo — confirma que la obligación de nómina electrónica NO se mezcla con el cálculo de nómina interno | `empleados.TransmisionNominaDIAN` |

## Ciclo de activos fijos

| Origen | Destino | Tipo | Obligatoriedad |
|---|---|---|---|
| ActivoFijo | MovimientoInventario (tipos ACTIVO) | **TRIGGER, DERIVED** | `ASIGNACION_RESPONSABLE`/`TRASLADO_MANTENIMIENTO`/`RETORNO_MANTENIMIENTO`/`SALIDA_BAJA_ACTIVO` cambian `ActivoFijo.estado` atómicamente |
| ActivoFijo | AsientoContable (depreciación) | **CONDITIONAL, no confirmado** | `APP_ORIGEN_PREFIJOS['inventario']` incluye prefijo `'51'` (gastos de depreciación) — el mecanismo de depreciación periódica en sí (cálculo, no solo la cuenta) no fue verificado línea por línea en ninguna auditoría previa ni en esta sesión |

## Relaciones REQUIRED vs. sobre-obligadas — corrección explícita

Siguiendo la regla "no convertir todo en obligatorio" (§32 del prompt maestro),
se documentan explícitamente las relaciones que el prompt maestro asumía como
posiblemente obligatorias y que el código real trata como opcionales:

- **Venta → Proyecto**: OPTIONAL/CONTEXT, nunca REQUIRED — confirmado por soft-reference con `SET_NULL`.
- **Cotización → Producto/Servicio del catálogo de Inventario**: NO EXISTE la relación en absoluto — los ítems de Cotización son texto libre, no consumen `inventario.Producto`/`Servicio` (confirmado en la misión de auditoría de Cotizaciones de esta sesión). No es opcional: simplemente no está conectado.
- **Compras → Proveedores**: FK directa normal dentro del mismo tenant, no un patrón Bridge cross-context — no se fuerza a tratar como una integración cross-app compleja donde no lo es.

## Gap de proceso más significativo de este grafo

**Cotización → Venta no es un TRIGGER real.** El ciclo comercial completo que
el prompt maestro describe (`Cliente → Cotización → Venta → Inventario →
Factura → Cobro → ...`) tiene una discontinuidad real en el paso Cotización→
Venta: aceptar una Cotización no crea ni vincula automáticamente una Venta.
Si el negocio espera que ese paso sea automático, es un GAP funcional real,
no solo una decisión de diseño confirmada — requiere verificación de producto
sobre si esto es intencional (cada Venta se crea manualmente, la Cotización es
solo un documento comercial previo sin efecto transaccional) o un gap real a
cerrar.
