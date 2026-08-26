# Cross-App Relation Matrix — SINTEL ERP

**Fecha:** 2026-08-26 | **Fase:** REL-02 (complementada con REL-03 vía columna Tipo/Cardinalidad)

Todas las filas provienen de lectura directa de `models.py`/`services/business_service.py`/`services/selectors.py` reales, citadas en la columna Evidencia. Nada en esta tabla fue asumido sin cita de código. La tabla original propuesta en el prompt maestro (Cliente→Cotización, Cotización→Venta, etc.) se usó como punto de partida y se marca abajo con **[confirmado]** o **[corregido]** según lo que el código real mostró.

**Leyenda Dirección:** push (A escribe en B) · pull (A lee de B) · reference (soft link informativo) · derived (calculado, no persistido 1:1) · process (evento de un flujo mayor)

---

## Ciclo de Venta

| Origen | Destino | Relación | Obligación | Dirección | SSoT | Evidencia |
|---|---|---|---|---|---|---|
| Venta | Cliente | comercial | **obligatoria** (FK `PROTECT`, sin null) | push | Clientes | `ventas/models.py:149-154` — **[corregido]**: el prompt maestro la listaba "opcional/pull", el código real la exige |
| Cliente | Cotización | comercial | opcional (FK `SET_NULL`, `null=True`) | reference | Clientes | `cotizaciones/models.py:58` |
| Cotización | Venta | conversión | opcional, **sin automatización de código** | — (no existe llamada real) | Cotizaciones | ver `CROSS_APP_FINDINGS.md` IMPORTANT — **[corregido]**: el prompt maestro asumía "push"; no existe ningún método que convierta Cotización→Venta |
| Venta | Factura | fiscal | condicional (sí, si se ejecuta `procesar_y_facturar_venta`) | push | Facturas | `ventas/services/business_service.py:441-674` — **[confirmado]** |
| Venta | Inventario | salida | condicional (solo ítems con `producto` real, excluye texto libre/servicios) | push (proceso), idempotente | Inventario | `ventas/services/business_service.py:681-713` — **[confirmado]** |
| Venta | Proyecto | contexto | opcional (FK `SET_NULL`) — **pero de solo-escritura hoy**, nadie en Proyectos lee `Venta.proyecto` | reference (declarada, no consumida) | Proyectos | `ventas/models.py:156-163` — **[corregido]**: la relación existe pero está "muerta" del lado de lectura |
| ItemVenta | Producto/Servicio (inventario) | catálogo | condicional (ambos nullable, ítem de texto libre válido) | pull/reference | Inventario | `ventas/models.py:245-261` |
| Cotización | Producto/Servicio propio | catálogo | — | — | Cotizaciones (catálogo **duplicado**, no comparte tabla con Inventario) | `cotizaciones/models.py:17-35` vs `inventario/models.py:133-231` |
| Factura | Cliente | fiscal (naturaleza VENTA) | condicional | reference/pull (soft-UUID) | Clientes | `facturas/models.py:181-186` |
| Factura | Cotización | trazabilidad | opcional, editable manual, "permite orfandad" | reference | Cotizaciones | `facturas/models.py:166-179`; bridge `facturas/services/selectors.py:278-308` |
| Factura | Retenciones (Contabilidad) | fiscal | derivada, degrada a 0 si falla | pull | Contabilidad | `facturas/models.py:278-327` |
| Factura | Bancos | cobro/pago | condicional | pull (lectura de saldo) | Bancos | `facturas/models.py:333-354`; bridge `facturas/services/selectors.py:544-580` — **[confirmado]** |
| Bancos | Factura.estado_pago | conciliación | condicional (`factura_uuid` presente y medio≠Efectivo) | **push** (Bancos escribe en Facturas) | Facturas (dueño del campo) | `bancos/services/crud_service.py:127-165` — **[corregido]**: el prompt maestro la listaba "pull"; es push real, no bloqueante |
| Factura (VENTA) | Contabilidad | contable | condicional (solo `estado=ACEPTADA`, tipo FE, no contabilizada) | pull | Contabilidad | `contabilidad/integracion/extractores/facturas.py:32-85` — **[confirmado]** |
| Inventario (MovimientoInventario) | Contabilidad | costo de venta | condicional — **pero el pipeline automático real (Celery) NO la ejecuta** (ver Findings CRITICAL) | pull (declarada, no conectada) | Contabilidad | `contabilidad/integracion/extractores/inventario.py:41-122` vs `contabilidad/services/business_service.py:1043-1051` |
| Cliente (auto-creación) | Factura VENTA sin cliente_uuid | resolución | condicional, solo ruta EXTERNO/UBL | push (proceso) | Clientes | `facturas/services/business_service.py:494-511,621-630` |
| Cliente | Cartera (CxC) | cobro | opcional, **no alimentada automáticamente** desde Factura/Venta | reference (declarada, no consumida) | Clientes | ver Findings IMPORTANT |
| Proyecto | Factura (`factura_costo`) | centro de costo | opcional, asignación manual | reference (manual) | Proyectos | `proyectos/models.py:89-97` |

## Ciclo de Compra

| Origen | Destino | Relación | Obligación | Dirección | SSoT | Evidencia |
|---|---|---|---|---|---|---|
| Compra (OrdenCompra) | Proveedor | comercial | **obligatoria** (FK `PROTECT`) | push | Proveedores | `compras/models.py:153-158` — **[confirmado]** |
| Compra | Recepción | logística | condicional (requiere OrdenCompra `APROBADA`/`PARCIAL`) | process | Compras | `compras/services/business_service.py:409-413` — **[confirmado]** |
| Recepción | Inventario | entrada | condicional (solo líneas con `item_inventario_uuid` resoluble; sin producto → se omite sin bloquear) | derived (push vía Kardex) | Inventario | `compras/services/business_service.py:511-589` — **[confirmado exacto]** |
| OrdenCompra (APROBADA) | CuentasPagar (Proveedores) | obligación de pago | **obligatoria y automática** al llegar a APROBADA (v3.18.0, hoy) | push, idempotente | Proveedores | `compras/services/business_service.py:341-403` |
| CuentasPagar | OrdenCompra | trazabilidad | opcional (poblado solo si nace de OC) | reference (soft-UUID) | Compras | `proveedores/models.py:245-252` |
| CuentasPagar | Bancos | conciliación | **NO EXISTE — CRITICAL** | — | — | ver Findings; grep exhaustivo sin resultados en `apps/tenant/bancos/` |
| Factura (COMPRA) | Proveedor | fiscal | condicional (`proveedor_uuid` nullable, se resuelve en importación) | reference/pull (soft-UUID) | Proveedores | `facturas/models.py:188-193` |
| Factura (COMPRA, importación) | Proveedor (auto-resolución) | resolución | condicional, solo si `proveedor_uuid` vacío | push (proceso) | Proveedores | `facturas/services/business_service.py:513-527,646-649` |
| Factura (COMPRA) | Bancos/CXP | cobro/pago | condicional | pull (Bancos) / — (CXP: ninguna llamada real desde Facturas) | Bancos | `bancos/services/crud_service.py:127-163` — **[corregido]**: Factura→CuentasPagar NO existe como llamada automática, solo Bancos→Factura.estado_pago |
| Factura (COMPRA) | Contabilidad | contable | condicional | pull | Contabilidad | `contabilidad/integracion/extractores/facturas.py:1-85` — **[confirmado]** |
| DocumentoSoporte (Gasto) | Contabilidad | contable | condicional (`anulado=False`, sin asiento previo) | pull | Contabilidad | `contabilidad/integracion/extractores/gastos.py:1-52` — **[confirmado]** |
| MovimientoInventario (ENTRADA_COMPRA) | Contabilidad | costo de inventario | condicional | pull | Contabilidad | `contabilidad/integracion/extractores/inventario.py:20-122,177-196` |

## Ciclo de Gasto

| Origen | Destino | Relación | Obligación | Dirección | SSoT | Evidencia |
|---|---|---|---|---|---|---|
| DocumentoSoporte | Proveedor | fiscal | **obligatoria** (FK `CASCADE` — nota: cascada agresiva, ver Findings) | push | Proveedores | `gastos/models.py:140-147` — **[confirmado, con matiz de cascada peligrosa]** |
| DocumentoSoporte | ResolucionDIAN | numeración | **obligatoria** (FK `PROTECT`) | push | Gastos | `gastos/models.py:121-126` |
| DocumentoSoporte | Retenciones (Contabilidad) | fiscal | **obligatoria en el flujo de creación**, síncrona | push (Gastos dispara, Contabilidad escribe su propia tabla) | Contabilidad | `gastos/services/business_service.py:189-221` — **[confirmado]** |
| DocumentoSoporte | Contabilidad (asiento) | contable | condicional (batch) | pull | Contabilidad | `contabilidad/integracion/extractores/gastos.py:1-52` |
| DocumentoSoporte | CuentasPagar / Bancos | pago | **NO EXISTE — CRITICAL** | — | — | grep exhaustivo, ver Findings |
| DocumentoSoporte | MovimientoInventario | trazabilidad | opcional, sin uso real en el asiento contable | reference (soft-UUID, declarada no consumida) | Inventario | `gastos/models.py:206-211` |

## Ciclo de Nómina

| Origen | Destino | Relación | Obligación | Dirección | SSoT | Evidencia |
|---|---|---|---|---|---|---|
| Contrato | Empleado | laboral | **obligatoria** (FK `CASCADE`) | push | Empleados | `empleados/models.py:178` |
| Devengo | Empleado / Contrato | laboral | **obligatoria** (FK `PROTECT` ×2) | push | Empleados | `empleados/models.py:288-289` |
| Devengo | PeriodoNomina | orquestación | condicional (`null=True`, "nullable por compatibilidad historica") | reference | Empleados | `empleados/models.py:358-365` |
| Devengo (via PeriodoNomina) | Contabilidad | contable | opcional/batch, **SÍ existe y funciona** | pull (import ORM directo, unidireccional) | Contabilidad | `contabilidad/integracion/extractores/nomina.py:7-53` — **[corregido]**: el prompt maestro dejaba abierta la duda; se confirma que SÍ está construida |
| PeriodoNomina (PAGADO) | Bancos | pago | **NO EXISTE** — `marcar_pagado()` es registro manual, documentado como tal en 3 lugares del propio código | — | — | `empleados/services/business_service.py:660-674` |
| Empleado | ResolucionDIAN | numeración | opcional | reference | Empleados | `empleados/models.py:106-114` |
| TransmisionNominaDIAN | Devengo / ResolucionDIAN | fiscal | obligatoria (1:1) | push | Empleados | `empleados/models.py:507-508` |

---

## Nota sobre cardinalidades (REL-03, detalle completo en `CROSS_APP_FINDINGS.md`)

Todos los tipos de relación real encontrados en el sistema: **FK real** (con `on_delete` explícito: `PROTECT`/`CASCADE`/`SET_NULL`), **soft-UUID** (campo `*_uuid` sin FK, documentado como Bounded Context), y **llamada de servicio** (Push o Pull vía `business_service.py`/`selectors.py` con `empresa_id` explícito). No se encontró ningún `ManyToManyField` cross-app en los 4 ciclos auditados — todas las relaciones N:M reales están contenidas dentro de una misma app (no cruzan Bounded Context). No se encontró ningún `OneToOneField` cross-app salvo `Venta.factura_asociada → Factura` y `TransmisionNominaDIAN.devengo → Devengo`.
