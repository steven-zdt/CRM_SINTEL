# Ciclo Comercial — Matriz SSoT (FASE COMERCIAL-02)

**Fecha:** 2026-08-24. **Estado:** Definición formal, con evidencia de
código para cada afirmación (no una descripción aspiracional). Complementa
`COMERCIAL_01_AUDITORIA.md` (FASE COMERCIAL-01).

Principio del plan: `Venta → dueño comercial`, `Factura → dueño fiscal`,
`Inventario → dueño stock`, `Bancos → dueño pagos`, `Contabilidad → dueño
contable`. Esta fase verifica si el código de hoy cumple exactamente eso,
y documenta las excepciones reales donde no.

---

## 1. `Venta` — dueño comercial

**Posee:** identidad comercial de la operación (`Venta.uuid`), sus
totales comerciales (`subtotal`/`impuestos`/`total_neto`, calculados en
`VentaCRUDService.crear_venta()`), y su propio ciclo de vida
(`Venta.Estado`: BORRADOR/FACTURADA_DIAN/ANULADA).

**Cómo referencia a otros dueños (mixto, no uniforme — hallazgo real):**

| Hacia | Mecanismo | Evidencia |
|---|---|---|
| `clientes.Cliente` | **FK real** (`on_delete=PROTECT`) | `ventas/models.py:149` |
| `proyectos.Proyecto` | **FK real** (`on_delete=SET_NULL`) | `ventas/models.py:156` |
| `facturas.Factura` | **FK real** (`OneToOneField`, `on_delete=SET_NULL`) | `ventas/models.py:174` |
| `inventario.Producto`/`.Servicio` (vía `ItemVenta`) | **FK real** (`on_delete=PROTECT`, ambos nullable) | `ventas/models.py:245,254` |

**Esto contradice la lectura simplificada "todo cruce de app usa UUID
soft"** que domina la documentación de `facturas` (`cliente_uuid`,
`proveedor_uuid`, `cotizacion_uuid`, `item_inventario_uuid`, todos sin
FK). `ventas` no sigue ese patrón — usa FKs reales hacia sus 3
dependencias directas. No se declara aquí cuál convención es "correcta";
se documenta el estado real para que COMERCIAL-03+ decida con esa
información, no con una suposición.

---

## 2. `Factura` — dueño fiscal

**Posee:** la identidad fiscal DIAN (`numero`, `cufe`, `estado` UBL:
BORRADOR/ENVIADA/ACEPTADA/RECHAZADA/ANULADA), los campos de autorización/
resolución DIAN, y el XML/firma del documento electrónico.

**Cómo referencia a otros dueños:** exclusivamente **soft-UUID**, sin
ninguna FK real hacia otra app tenant: `cliente_uuid`, `proveedor_uuid`,
`cotizacion_uuid` (todas `UUIDField`, sin `ForeignKey`). Consistente en
sí misma — la inconsistencia está entre `facturas` y `ventas`, no dentro
de `facturas`.

**No es dueña de:** cálculo de impuestos del flujo `Venta→Factura` (los
recibe ya calculados en el DTO, ver `COMERCIAL_01_AUDITORIA.md` §2), ni
de `ItemFactura` cuando se origina desde una `Venta`
(`crear_factura_desde_venta()` no crea líneas — ver auditoría §1/§3).

---

## 3. `Inventario` — dueño de stock

**Posee:** `Producto.costo_promedio` (costo de referencia, estático, no
recalculado automáticamente — ver `F23_SALE_INVENTORY_CONTRACT.md` §6) y
el histórico append-only `MovimientoInventario` (Kardex), única fuente de
verdad del stock.

**Cómo escriben otras apps:** **nunca directo** — confirmado por grep en
todo el repo: cero asignaciones a `producto.stock` fuera de
`apps/tenant/inventario/`. Todo movimiento real pasa por
`KardexService.registrar_movimiento()` (`apps/tenant/inventario/services/
business_service.py`), llamado directamente desde `ventas`
(`_generar_salida_inventario()`, F23), `compras` (`confirmar_recepcion()`,
F21) y `facturas` (`_generar_entrada_devolucion()`, ver commit
`4a88bcf`). **No hay un bridge intermedio ni un servicio duplicado por
app que lo llame** — mismo servicio, mismo método, tipo de movimiento
distinto por caso de uso (`SALIDA_VENTA`/`ENTRADA_COMPRA`/
`ENTRADA_DEVOLUCION`). Este es el patrón más limpio de los 5 dominios:
una sola puerta de escritura, sin excepciones encontradas.

---

## 4. `Bancos` — dueño de pagos

**Posee:** `TransaccionBancaria` y el hecho de conciliación
(`conciliado`, `factura_uuid`/`proveedor_uuid`/`cliente_uuid` como
soft-refs en la transacción, nunca FK).

**Relación con `Factura` — híbrida, no un Pull puro:**

1. **Push de notificación:** `TransaccionBancariaCRUDService.
   conciliar_transaccion()` (`apps/tenant/bancos/services/
   crud_service.py:129`), al marcar `conciliado=True`, **llama
   directamente** a `FacturaInterAppAPI.recalcular_estado_pago_
   automatico(transaccion.factura_uuid)` — Bancos inicia la actualización,
   no espera a que Facturas pregunte. El fallo de este recálculo se
   captura y solo se loguea (`except Exception: logger.warning(...)`) —
   **no bloquea la conciliación** si falla, decisión explícita de
   diseño.
2. **Pull de dato real:** dentro de ese recálculo, `Factura.
   total_pagado_bancos`/`.saldo_pendiente` (`@property`) leen
   `BancosBridge.obtener_total_conciliado()` — la aritmética real
   (`Sum(ABS(valor))` de transacciones conciliadas) vive en `Bancos`,
   `Factura` solo la consulta.

**Conclusión:** Bancos es dueño de la verdad de conciliación y **decide
cuándo** Facturas debe refrescar su `estado_pago` derivado; Facturas
nunca escribe en `TransaccionBancaria`. No es "Pull puro" en el sentido
estricto de F22/F23 (donde el extractor decide cuándo leer) — aquí el
lado dueño (`Bancos`) empuja la señal, pero el dato en sí sigue siendo
Pull (`Factura` nunca cachea `total_pagado_bancos` como columna propia).

---

## 5. `Contabilidad` — dueño contable

**Posee:** `AsientoContable`/`MovimientoContable` — confirmado por grep en
todo el repo: **cero** `.objects.create()` de estos dos modelos fuera de
`apps/tenant/contabilidad/`. Ninguna app fuente (`ventas`, `facturas`,
`inventario`, `bancos`) escribe contabilidad directamente, en ningún
punto del código actual.

**Mecanismo (Pull Model, ADR-001):** `Extractor<App>` (`ExtractorFacturas`,
`ExtractorInventario`, `ExtractorNomina`, etc., todos en `apps/tenant/
contabilidad/`) leen de la app fuente cuando `Contabilidad` decide
generar asientos (`backfill_asientos_*` / procesamiento por período) — la
app fuente nunca sabe que Contabilidad existe. Confirma exactamente el
principio del plan: `Factura` no debe convertirse en dueña de lógica
contable, y hoy no lo es.

---

## 6. Matriz resumen

| Dominio | Dueño | Escritura externa permitida | Mecanismo |
|---|---|---|---|
| Identidad comercial | `Venta`/`ItemVenta` | — | N/A, es la fuente |
| Identidad fiscal DIAN | `Factura`/`ItemFactura` | `ventas` (crea `Factura`, no `ItemFactura`) | Llamada directa a `crear_factura_desde_venta()`, sin Pull ni bridge |
| Stock | `MovimientoInventario`/`Producto.costo_promedio` | `ventas`, `compras`, `facturas` | `KardexService.registrar_movimiento()`, puerta única |
| Pagos/conciliación | `TransaccionBancaria` | — (Facturas solo lee) | Pull (`BancosBridge`) + push de notificación (`FacturaInterAppAPI`) |
| Contabilidad | `AsientoContable`/`MovimientoContable` | — (ninguna app fuente escribe) | Pull puro (`Extractor<App>`), ADR-001 |

**Único dominio con escritura cruzada directa (no Pull, no bridge):**
`ventas → facturas` vía `crear_factura_desde_venta()` — coherente con que
`Venta` sea la dueña de "cuándo" se factura (decisión comercial), pero es
el único punto de los 5 donde una app de dominio escribe directamente en
el modelo de otra, sin capa intermedia. Documentado, no corregido en esta
fase (definición de SSoT, no refactor).

---

## 7. Consolidación para COMERCIAL-03+

- El contrato `Venta → DTO → Factura` (COMERCIAL-03) ya tiene un solo
  punto de construcción (`_construir_dto_factura()`) y un solo punto de
  consumo (`crear_factura_desde_venta()`) — formalizarlo es documentar,
  no reconstruir (confirma `COMERCIAL_01_AUDITORIA.md` §8).
- La inconsistencia FK-real-vs-soft-UUID entre `ventas` y `facturas`
  (§1) no bloquea ninguna fase siguiente del plan, pero es información
  relevante si en algún momento se evalúa desacoplar `ventas` de
  `clientes`/`proyectos` (hoy no está en alcance del plan del usuario).
- `Bancos↔Facturas` (§4) y `Contabilidad↔Facturas` (§5) ya cumplen el
  principio del plan sin cambios pendientes — COMERCIAL-08/09 son de
  mantener, no de construir, confirmado con evidencia.
