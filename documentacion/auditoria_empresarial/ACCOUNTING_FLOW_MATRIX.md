# Matriz de Flujo Contable — SINTEL ERP

**Fecha:** 2026-08-27. Fuente primaria: `documentacion/F22_ACCOUNTING_CONTRACT.md`
(2026-08-09, verificado contra código real en esa fecha), actualizada con
verificación de vigencia de esta sesión. Complementa (no reemplaza)
`documentacion/arquitectura_general.md` §6.

## Principio arquitectónico confirmado (Pure Pull Model)

Ninguna app de negocio (`ventas`, `compras`, `facturas`, `gastos`, `inventario`,
`empleados`) crea `AsientoContable`/`MovimientoContable` directamente. Cada una
expone datos (Producto/Servicio/Movimiento/Documento) sin cuentas contables
embebidas; `contabilidad` los extrae activamente vía extractores dedicados
(`integracion/extractores/{facturas,gastos,inventario,nomina}.py`) y resuelve la
cuenta vía `ReglaContable` (configuración, no hardcode). Confirmado por grep
repo-wide (cero referencias a `AsientoContable` fuera de `contabilidad`) en
`F18_COLOMBIAN_BUSINESS_FLOWS.md` §F18.4 y re-confirmado por la app `gastos`
en esta sesión (`RetencionesService`, ver `TAX_COMPLIANCE_MATRIX.md`).

## Matriz de transacciones — Inventario → Contabilidad (verificada línea por línea, F22)

| `MovimientoInventario.tipo` | Contabilizable | `TipoTransaccion` | Cuenta DEBE | Cuenta HABER | Naturaleza |
|---|---|---|---|---|---|
| `ENTRADA_COMPRA` | Sí | `COMPRA_INVENTARIO` | 143505 (Inventario) | 220505 (Pasivo compra) | Aumenta activo |
| `SALIDA_VENTA` | Sí (confirmado generándose hoy — ver drift abajo) | `SALIDA_INVENTARIO_VENTA` | 613501 (Costo venta) | 143505 (Inventario) | Costo de venta real |
| `ENTRADA_AJUSTE` | Sí | `AJUSTE_INVENTARIO` | 143505 | 425050 (Ingreso ajuste) | Sobrante — variación económica |
| `SALIDA_BAJA` | Sí | `BAJA_INVENTARIO` | 529901 (Gasto deterioro) | 143505 | Pérdida/deterioro |
| `SALIDA_CONSUMO` | Sí | `BAJA_INVENTARIO` | 519595 (Gasto consumo interno) | 143505 | Consumo interno |
| `ENTRADA_DEVOLUCION` | Sí (confirmado implementado — ver drift abajo) | `AJUSTE_INVENTARIO` | 143505 | 613501 (reversa costo venta) | Devolución de cliente |
| `TRASLADO_SALIDA`/`TRASLADO_ENTRADA` | **No, por diseño** | — | — | — | Transferencia interna entre sedes, sin tercero ni cambio de propiedad — decisión confirmada, no un gap |
| `ASIGNACION_RESPONSABLE`/`TRASLADO_MANTENIMIENTO`/`RETORNO_MANTENIMIENTO`/`SALIDA_BAJA_ACTIVO` | Fuera de alcance del extractor de mercancía | — | — | — | Movimientos de `ActivoFijo`, no de `Producto` — deuda documentada, no fabricada |

**Tercero resuelto:** para `ENTRADA_COMPRA`, se resuelve el `Proveedor` real
recorriendo `documento_origen_id → RecepcionCompraItem → orden_compra.proveedor`
(import de lectura `contabilidad → compras`, permitido en el Pull Model). Para
salidas/ajustes, no hay FK estructurada a Cliente en `MovimientoInventario`
(solo `cliente_referencia` texto libre) — se usa `TipoTercero.OTRO` con esa
referencia. **No se bloquea la contabilización por falta de tercero, pero
tampoco se inventa un NIT falso.**

**Idempotencia:** `AsientoContable` tiene `UniqueConstraint(['empresa',
'documento_origen_app','documento_origen_modelo','documento_origen_id'],
condition=Q(documento_origen_reversado=False))` — un mismo `MovimientoInventario`
nunca genera 2 asientos activos.

### DOCUMENTATION_DRIFT confirmado desde F22 (2026-08-09) hasta hoy

F22 documentaba `SALIDA_VENTA` como "mecanismo listo, sin datos reales aún" y
`ENTRADA_DEVOLUCION` sin trigger real de Notas Crédito. Evidencia de esta misma
sesión (misión de auditoría de Inventario, 2026-08-27) y de
`documentacion/arquitectura_general.md` líneas 1610-1616/1678-1684 confirma que
AMBOS ya están implementados: `ventas._generar_salida_inventario()` genera
`SALIDA_VENTA` real por cada `ItemVenta` con producto (excluye servicios), y
`facturas` genera `ItemNotaCredito` + `ENTRADA_DEVOLUCION` real desde Notas
Crédito, con test `test_devolucion_nota_credito.py`. **El flujo de Inventario →
Contabilidad para mercancía está hoy completo end-to-end**, no parcial como
documentaba F22.

## Otros flujos contables (Pull Model, confirmados en auditorías previas)

| Origen | Extractor | `contabilidad` recibe | Estado |
|---|---|---|---|
| `facturas` (Factura de venta/compra) | `extractores/facturas.py` | Ingreso/gasto + IVA + retenciones asociadas | Confirmado, Pull |
| `gastos` (`DocumentoSoporte`) | `extractores/gastos.py` | Gasto + retenciones vía `RetencionesService` | Confirmado línea por línea esta sesión (ver `TAX_COMPLIANCE_MATRIX.md` §2) |
| `empleados` (`Devengo`) | `extractores/nomina.py` | Gasto de nómina (salarios, prestaciones, aportes) | Confirmado por nombre de archivo + consumo real; no revisado línea por línea (deferred P3) |
| `inventario` (`MovimientoInventario`) | `extractores/inventario.py` | Ver matriz arriba | Confirmado línea por línea (F22) |

## Costo unitario cero — manejo de riesgo de dato (F22 §6)

El extractor de inventario **no omite silenciosamente** un movimiento con
`costo_unitario=0` (eso ocultaría que el movimiento sí necesita contabilizarse).
En su lugar, llega a `Contabilizador.contabilizar()` con `monto=0` en ambas
líneas, y `validar_no_vacio()` lanza `AsientoNoCuadradoError` — capturado y
agregado a `resultados['errores']` del comando `backfill_contabilidad`, visible
pero no fatal para el resto del batch. Confirmado como el patrón correcto: un
gap de dato real (falta costo) se muestra como error explícito, no se pierde.

## Costo promedio — decisión confirmada, no un bug

`Producto.costo_promedio` es un campo **estático**, nunca recalculado
automáticamente por ninguna entrada de Kardex (ni `ENTRADA_COMPRA` ni otra) —
decisión arquitectónica deliberada y documentada (`documentacion/
F23_SALE_INVENTORY_CONTRACT.md` §6, re-confirmada en la misión de Inventario de
esta sesión). No es costeo FIFO/promedio-ponderado real — es "el mejor costo de
referencia disponible en el modelo actual". Implementar costeo real sería un
método nuevo, fuera de alcance de una auditoría/corrección.

## Sede — decisión confirmada de no propagar a los modelos contables

Ni `AsientoContable` ni `MovimientoContable` tienen campo `sede_id` — decisión
documentada (F22 §7): agregarlo "solo para resolver F22" está prohibido por el
prompt maestro original (no diseñar especulativamente) y no hay requisito de
negocio verificado que lo exija hoy. La trazabilidad de sede sigue disponible
indirectamente vía `MovimientoInventario.sede → documento_origen_id`.

## Reversas contables

`AsientoContable.documento_origen_reversado` (boolean) existe como campo — el
`UniqueConstraint` de idempotencia lo excluye explícitamente
(`condition=Q(documento_origen_reversado=False)`), lo que confirma que el
mecanismo de reversa SÍ está contemplado a nivel de esquema (permite volver a
contabilizar un documento origen tras reversar el asiento anterior). El flujo
operativo completo de "cómo se marca reversado un asiento" (quién puede
hacerlo, si genera un asiento de reversa espejo o solo desactiva el original)
no fue verificado línea por línea en esta sesión — ver hallazgo pendiente en
`BUSINESS_GAP_MATRIX.md` (delegado al agente de controles internos, en curso).

## Periodos contables

`PeriodoContable` (modelo) + `seed_periodos_contables.py` existen. El
mecanismo de apertura/cierre y si impide contabilizar en un período cerrado
no fue verificado línea por línea en ninguna auditoría previa — delegado al
agente de controles internos de esta sesión (ver `INTERNAL_CONTROL_MATRIX.md`).
