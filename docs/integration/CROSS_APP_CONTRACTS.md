# Cross-App Contracts — SINTEL ERP

**Fecha:** 2026-08-26 | **Fase:** REL-08

Contratos explícitos para las integraciones cross-app más críticas de los 4 ciclos auditados. Cada uno con evidencia real (archivo:línea).

---

## Ciclo de Venta

### Contrato V1 — Venta → Factura → Inventario (transacción atómica única)

| Campo | Detalle |
|---|---|
| Consumer | `VentaBusinessService.procesar_y_facturar_venta()` |
| Provider | `FacturaBusinessService.crear_factura_desde_venta()` + `KardexService.registrar_movimiento()` |
| Input | DTO UBL 2.1 (emisor, receptor, líneas, totales, `cliente_uuid`, `venta_uuid`, `sede_id`) |
| Output | `Factura` (BORRADOR, origen=INTERNO) + `ItemFactura[]` + `MovimientoInventario(SALIDA_VENTA)[]` |
| Trigger | Endpoint de Ventas → `procesar_y_facturar_venta()` |
| State | `Venta.BORRADOR → FACTURADA_DIAN`; `Factura` nace `BORRADOR` |
| Idempotency | Ancla `Venta.uuid` — reintento sobre venta ya `FACTURADA_DIAN` retorna 200 sin reejecutar. `MovimientoInventario` idempotente por `UniqueConstraint(empresa, documento_origen_app, documento_origen_modelo, documento_origen_id, tipo)` |
| Rollback | `@transaction.atomic` completo — cualquier fallo (incl. stock insuficiente) revierte Venta+Factura+ItemFactura+MovimientoInventario juntos |
| Error handling | `ValueError`→400, `DjangoValidationError`→422, genérica→500 con `set_rollback(True)` explícito |
| SSoT | Ventas (Venta/consecutivo), Facturas (Factura), Inventario (stock/Kardex) |

### Contrato V2 — Factura → Contabilidad (Pull)

| Campo | Detalle |
|---|---|
| Consumer | Contabilidad (`ExtractorFacturas` + `Contabilizador`) |
| Provider | Facturas (lectura directa, sin que Facturas conozca a Contabilidad) |
| Input | `Factura` con `estado=ACEPTADA`, `tipo=FE`, no contabilizada |
| Output | `AsientoContable` + `MovimientoContable[]` (INGRESO_PRINCIPAL, IVA_GENERADO, RETEFUENTE/RETEICA/RETEIVA, CXC_CLIENTES) |
| Trigger | `ejecutar_integracion_completa()` (Celery periódico o manual) |
| State | Requiere `Factura.estado==ACEPTADA` |
| Idempotency | `UniqueConstraint(empresa, documento_origen_app, documento_origen_modelo, documento_origen_id)` condicionado a `documento_origen_reversado=False`, más chequeo previo en aplicación |
| Rollback | Cada factura se contabiliza atómicamente por separado; error en una no aborta el lote |
| Error handling | `AsientoYaExisteError` cuenta como "omitido"; otra excepción se agrega a `resultados['errores']` sin detener el resto |
| SSoT | Contabilidad (ADR-001) |

### Contrato V3 — Bancos → Factura.estado_pago (push condicional)

| Campo | Detalle |
|---|---|
| Consumer | `facturas.Factura.estado_pago` |
| Provider | `bancos.BancosCRUDService.conciliar_transaccion` |
| Input | `TransaccionBancaria` con `factura_uuid` + `conciliado=True` |
| Output | `Factura.estado_pago` recalculado (`update_fields=['estado_pago']`) |
| Trigger | Endpoint manual de conciliación en Bancos |
| State | Solo actúa si `medio_pago_codigo != '10'` (no Efectivo) |
| Idempotency | Solo escribe si el estado calculado difiere del actual |
| Rollback | **No hay rollback conjunto** — la conciliación se guarda igual aunque el recálculo en Facturas falle (degradación intencional documentada) |
| Error handling | `try/except` con `logger.warning`, no bloqueante |
| SSoT | Bancos (conciliación), Facturas (estado_pago) |

---

## Ciclo de Compra

### Contrato C1 — OrdenCompra → CuentasPagar (v3.18.0)

| Campo | Detalle |
|---|---|
| Consumer | `proveedores.CuentasPagar` |
| Provider | `compras.OrdenCompraBusinessService._sincronizar_cuenta_por_pagar()` |
| Input | `OrdenCompra` (uuid, proveedor, fecha, total, numero_documento) |
| Output | `CuentasPagar` con `orden_compra_uuid` poblado, `factura_uuid=None` |
| Trigger | `cambiar_estado_orden_compra(nuevo_estado='APROBADA')` |
| State | Cualquier estado → APROBADA (**sin validación de transición previa** — ver Findings) |
| Idempotency | `get_or_create` sobre `(empresa, proveedor, numero_factura)`, respaldado por `UniqueConstraint` |
| Rollback | **Ninguno** — anular la OC después de aprobada no reversa la CxP (decisión explícita documentada) |
| Error handling | Excepción no capturada localmente, burbujea al `except Exception` genérico → 500, rollback de toda la transacción (incluido el cambio de estado ya aplicado, por estar en `@transaction.atomic`) |
| SSoT | Proveedores (CxP), Compras (OC origen) |

### Contrato C2 — RecepcionCompra → MovimientoInventario

| Campo | Detalle |
|---|---|
| Consumer | `inventario.MovimientoInventario` / `Producto.stock_actual` |
| Provider | `compras.RecepcionCompraBusinessService.confirmar_recepcion` |
| Input | `RecepcionCompra` BORRADOR + `RecepcionCompraItem[]` |
| Output | `MovimientoInventario(ENTRADA_COMPRA)` por línea con producto resoluble |
| Trigger | Transición `BORRADOR → CONFIRMADA` |
| State | `BORRADOR` (editable) → `CONFIRMADA` (inmutable) |
| Idempotency | `select_for_update()` + `UniqueConstraint` de BD como defensa de condición de carrera |
| Rollback | Ninguno para CONFIRMADA (deliberado, "riesgo de corromper trazabilidad histórica") |
| Error handling | Líneas sin producto resoluble se omiten silenciosamente (`logger.info`, no bloqueante) |
| SSoT | Inventario (stock/Kardex), Compras (recepción origen) |

### Contrato C3 — {Factura, DocumentoSoporte, MovimientoInventario} → Contabilidad (Pull batch)

| Campo | Detalle |
|---|---|
| Consumer | `contabilidad.AsientoContable`/`MovimientoContable` |
| Provider | `ExtractorFacturas`, `ExtractorGastos`, `ExtractorInventario` (independientes entre sí) |
| Input | Documentos no contabilizados aún, filtrados por `empresa_id` |
| Output | `AsientoContable` + `MovimientoContable` (partida doble vía `ReglaContable`) |
| Trigger | Proceso batch/manual independiente por extractor — no hay una única señal que dispare los 3 juntos |
| State | Documento origen sin `AsientoContable` previo (`documento_origen_reversado=False`) para esa `(app, modelo, id)` |
| Idempotency | `UniqueConstraint` (BD) + exclusión en aplicación — doble capa |
| Rollback | Vía `asiento_reversado` (FK self) — reversales explícitos, no automáticos |
| Error handling | Documento con `ReglaContableNoDefinidaError` se acumula en `errores`, no detiene el lote |
| SSoT | Contabilidad (asiento); cada app fuente (documento origen) |

---

## Ciclo de Gasto

### Contrato G1 — Gasto → Retenciones (creación síncrona)

| Campo | Detalle |
|---|---|
| Consumer | `GastoBusinessService.procesar_gasto` |
| Provider | `contabilidad.RetencionesService` (`obtener_retenciones_desde_tercero`, `calcular_monto_retencion`, `crear_retencion`) |
| Input | NIT proveedor, `tipo_tercero=PROVEEDOR`, `naturaleza=COMPRA`, `empresa_id`; luego tipo/porcentaje/base/`documento_origen_*` |
| Output | `contabilidad.Retencion` persistida(s) |
| Trigger | Síncrono, dentro de la misma `@transaction.atomic` de `procesar_gasto` |
| State | `Retencion.reversada=False` al crear; el `DocumentoSoporte` ya existe (se crea primero) |
| Idempotency | **No idempotente por diseño** — cada llamada crea nuevas filas sin verificar existencia previa |
| Rollback | Si falla un paso posterior, `set_rollback(True)` revierte DocumentoSoporte + Retenciones ya creadas en la misma transacción |
| Error handling | `ValidationError`→400 con rollback; genérica→500 con rollback y log |
| SSoT | Contabilidad (`Retencion` es la única fuente de verdad de montos de retención) |

### Contrato G2 — Contabilidad ← Gasto (Pull para asiento)

| Campo | Detalle |
|---|---|
| Consumer | `ExtractorGastos` |
| Provider | `gastos.DocumentoSoporte` (lectura ORM directa) |
| Input | `DocumentoSoporte.objects.filter(empresa_id=..., anulado=False).exclude(id__in=ya_contabilizados)` |
| Output | `TransaccionEconomica` DTO (DEBE categoría/`GASTO_GENERAL`, HABER retenciones si >0, HABER pasivo por total) → `AsientoContable` |
| Trigger | Celery beat o disparo manual desde dashboard de Contabilidad |
| State | Documento "contabilizado" es 100% derivado desde existencia de `AsientoContable` — sin campo propio en `DocumentoSoporte` |
| Idempotency | Exclusión previa + `AsientoYaExisteError` capturada (cuenta como "omitido") |
| Rollback | **Ninguno automático** si el documento se anula después de contabilizado — único camino es reversión manual |
| Error handling | Fallo de `ResolverCuentas` por documento no detiene el resto del lote |
| SSoT | Contabilidad (asiento), Gastos (datos económicos crudos) |

---

## Ciclo de Nómina

### Contrato N1 — Empleados → Contabilidad (Pull, ExtractorNomina)

| Campo | Detalle |
|---|---|
| Consumer | Contabilidad (`ExtractorNomina`) |
| Provider | Empleados (`Devengo`, import ORM directo — no HTTP, excepción documentada al patrón general) |
| Input | `Devengo` con `empresa_id`, `anulado=False`, no contabilizado |
| Output | DTO `TransaccionEconomica` (DEBE salario/auxilio/otros devengos, HABER salud/pensión/préstamos/descuentos/neto) → `AsientoContable` (`documento_origen_app='empleados'`) |
| Trigger | `ContabilidadBusinessService.ejecutar_integracion_completa()` o `backfill_contabilidad.py` |
| State | Opcional/batch — no se dispara automáticamente al crear un `Devengo` |
| Idempotency | Mismo patrón `documento_origen_*` + `UniqueConstraint` que el resto de extractores |
| Rollback | No aplica (proceso de lectura + creación de asiento, sin escritura de vuelta a Empleados) |
| Error handling | Mismo patrón "omitir sin bloquear" del resto de extractores |
| SSoT | Empleados (`Devengo`, montos), Contabilidad (`AsientoContable`, proyección derivada) |

---

## Contratos que DEBERÍAN existir y no existen (gap transversal)

| Contrato faltante | Consumer esperado | Provider esperado | Por qué falta |
|---|---|---|---|
| CuentasPagar → Bancos | `bancos.TransaccionBancaria` | `proveedores.CuentasPagar` | `TransaccionBancaria` no tiene campo `cuenta_pagar_uuid`; solo `factura_uuid` |
| DocumentoSoporte → CuentasPagar | `proveedores.CuentasPagar` | `gastos.DocumentoSoporte` | Ningún código invoca `registrar_cuenta_pagar` desde `gastos` |
| DocumentoSoporte → Bancos | `bancos.TransaccionBancaria` | `gastos.DocumentoSoporte` | `TransaccionBancaria` no tiene campo `documento_soporte_uuid` |
| PeriodoNomina(PAGADO) → Bancos | `bancos.TransaccionBancaria` | `empleados.PeriodoNomina` | `marcar_pagado()` es registro local, sin bridge — documentado como tal en el propio código |

Ver `CROSS_APP_FINDINGS.md` para la clasificación de severidad de cada uno.
