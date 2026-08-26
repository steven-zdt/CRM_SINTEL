# Business Process Lifecycle — SINTEL ERP

**Fecha:** 2026-08-26 | **Fases:** REL-04 (estados de activación) + REL-05 (procesos paralelos/derivados)

---

## Ciclo de Venta

### REL-04 — Estados de activación

```
Venta BORRADOR (crear_venta_borrador)
   |
   NO genera Factura
   NO genera movimiento de inventario

Venta -> procesar_y_facturar_venta() [transaccion atomica unica]:
   1. DSV cliente + items + resolucion de facturacion
   2. Asigna consecutivo (select_for_update sobre ResolucionFacturacion)
   3. Crea/promueve Venta (BORRADOR)
   4. Construye DTO DIAN, calcula CUFE/QR, firma XML
   5. Factura(estado=BORRADOR, origen=INTERNO) creada
   6. Venta.estado: BORRADOR -> FACTURADA_DIAN (vincula factura_asociada)
   7. Por cada ItemVenta con producto real: MovimientoInventario(SALIDA_VENTA)
   Si CUALQUIER paso falla (incl. stock insuficiente) -> rollback total (1-7 juntos)

Venta FACTURADA_DIAN -> reintento: idempotente (200, no 201, no reejecuta nada)
Venta FACTURADA_DIAN -> ANULADA: rechazado explicitamente por regla de negocio
```

```
Factura BORRADOR (nace de crear_factura_desde_venta, origen=INTERNO)
   -> estado_pago = NO_PAGADA
   -> NO es recogida por ExtractorFacturas (exige ACEPTADA)

Factura (importada UBL, origen=EXTERNO)
   -> nace en ACEPTADA inmediatamente

Factura: BORRADOR -> ENVIADA -> {ACEPTADA | RECHAZADA | ERROR_TRANSMISION} -> ANULADA
   NOTA: la matriz de transiciones validas existe en codigo pero NO esta conectada
   al endpoint real de cambio de estado -- ese endpoint acepta cualquier transicion
   manual hoy (comentario explicito FISCAL-03 en el codigo).

Factura ACEPTADA + tipo=FE + no contabilizada
   -> elegible para ExtractorFacturas (Contabilidad la recoge en el siguiente batch)

Factura conciliada en Bancos (TransaccionBancaria.conciliado=True + factura_uuid)
   -> dispara recalculo de Factura.estado_pago (NO_PAGADA/PAGO_PARCIAL/PAGADA)
   -> excepcion: medio_pago_codigo == '10' (Efectivo) nunca se toca automaticamente
```

```
MovimientoInventario creado (tipo contabilizable, producto no nulo)
   -> queda "pendiente" para ExtractorInventario
   -> PERO: ExtractorInventario NO esta en la lista de extractores que ejecuta
      el Celery task periodico real (ejecutar_integracion_completa) pese a que
      el docstring de la tarea Celery promete sincronizar Inventario.
   -> Solo se contabiliza hoy via el management command manual backfill_contabilidad.py
```

### REL-05 — Mapa de procesos: VENTA FACTURADA

```
VENTA FACTURADA
 ├── factura                (Facturas -- síncrono, misma transacción)
 ├── salida inventario      (Inventario/Kardex -- síncrono, misma transacción)
 ├── costo                  (Contabilidad -- vía ExtractorInventario, DEBERÍA ser
 │                            asíncrono/batch pero HOY NO SE EJECUTA -- ver CRITICAL)
 ├── cartera                (Clientes/CxC -- declarada, NO se alimenta automáticamente)
 ├── impuestos (retenciones) (Contabilidad -- pull vía RetencionesService, derivado)
 └── contabilidad            (Contabilidad -- vía ExtractorFacturas, asíncrono/batch,
                               SÍ se ejecuta, requiere Factura.estado=ACEPTADA primero)
```

---

## Ciclo de Compra

### REL-04 — Estados de activación

```
OrdenCompra.estado:
   BORRADOR    -> sin efecto en otras apps
   PENDIENTE   -> sin efecto en otras apps
   APROBADA    -> dispara _sincronizar_cuenta_por_pagar()
                  => proveedores.CuentasPagar (get_or_create, idempotente)
   PARCIAL     -> alcanzado solo como efecto derivado de RecepcionCompra.CONFIRMADA;
                  NO vuelve a sincronizar CxP
   RECIBIDA    -> idem PARCIAL, sin nuevo efecto en CxP
   ANULADA     -> sin efecto -- la CxP ya generada NO se reversa (decision explicita)

RecepcionCompra.estado:
   BORRADOR    -> editable, sin efecto en stock
   CONFIRMADA  -> por cada linea con item_inventario_uuid resoluble:
                  MovimientoInventario(ENTRADA_COMPRA) generado
                  -> acumula ItemOrdenCompra.cantidad_recibida
                  -> re-evalua OrdenCompra.estado (PARCIAL/RECIBIDA)
                  Lineas SIN item_inventario_uuid: se omiten silenciosamente (no bloquea)
   ANULADA     -> solo permitido desde BORRADOR; CONFIRMADA es inmutable

Factura (COMPRA, via XML DIAN):
   cufe presente + repetido -> idempotencia por CUFE
   proveedor_uuid null -> se resuelve/crea Proveedor en el mismo guardar_desde_dto()
   ACEPTADA + tipo=FE -> elegible para ExtractorFacturas

DocumentoSoporte (Gasto):
   creado (sin estado propio de "aprobacion") -> en la MISMA transaccion:
   RetencionesService.crear_retencion() (push directo, sincrono)
   -> (asincrono/batch) ExtractorGastos -> AsientoContable

TransaccionBancaria.conciliado:
   conciliar_transaccion(factura_uuid=X) -> push inmediato a Factura.estado_pago
   conciliar_transaccion(proveedor_uuid=X, factura_uuid=None) -> NINGUN efecto
   sobre CuentasPagar (gap real, ver Findings)
```

### REL-05 — Mapa de procesos: ORDEN COMPRA APROBADA

```
ORDEN COMPRA APROBADA
 ├── cuentas por pagar   (Proveedores -- síncrono, automático, v3.18.0)
 └── (nada más hasta que exista una Recepción)

RECEPCION CONFIRMADA
 ├── movimiento inventario (Inventario/Kardex -- síncrono)
 ├── actualiza cantidad_recibida en ItemOrdenCompra
 └── re-evalúa estado de OrdenCompra (PARCIAL/RECIBIDA)
      └── costo de inventario (Contabilidad -- vía ExtractorInventario, batch)

FACTURA COMPRA ACEPTADA (flujo independiente, vía XML DIAN)
 ├── retenciones          (Contabilidad -- pull)
 ├── contabilidad          (Contabilidad -- vía ExtractorFacturas, batch)
 └── conciliación bancaria (Bancos -- push a Factura.estado_pago)
      X-- NO conecta con CuentasPagar generada desde OrdenCompra (cadenas separadas)
```

---

## Ciclo de Gasto

### REL-04 — Estados de activación

```
DocumentoSoporte.activo=True, anulado=False
   -> estado normal: aparece en listados, elegible para ExtractorGastos y contabilizacion

DocumentoSoporte.anulado=True
   -> excluido de extraer_pendientes() y de qs_gastos_pendientes()
   -> "irreversible" segun comentario de negocio
   -> PERO no dispara reversion automatica de Retencion/AsientoContable si el
      documento YA habia sido contabilizado antes de anularse (riesgo real)

DocumentoSoporte.activo=False (soft-delete, "desactivar")
   -> NO excluye de extraer_pendientes() (ese metodo solo filtra por anulado)
   -> un documento desactivado pero no anulado sigue siendo contabilizable
      (posible inconsistencia de estados, sin evidencia de si es intencional)

Retencion.reversada=False -> cuenta en todas las propiedades de DocumentoSoporte
Retencion.reversada=True  -> excluida de agregaciones

AsientoContable existente para (gastos, DocumentoSoporte, id)
   -> el documento pasa de estado_contable=PENDIENTE a CONTABILIZADO (derivado,
      no es un campo propio de DocumentoSoporte)
```

### REL-05 — Mapa de procesos: DOCUMENTO SOPORTE CREADO

```
DOCUMENTO SOPORTE CREADO (procesar_gasto, transacción atómica)
 ├── retenciones     (Contabilidad -- síncrono, misma transacción, push directo)
 └── contabilidad     (Contabilidad -- vía ExtractorGastos, batch posterior)
      X-- pago         NO EXISTE ningún camino hacia CuentasPagar ni TransaccionBancaria.
                        El ciclo declarado en la misión ("...-> Pago") se corta aquí.
```

---

## Ciclo de Nómina

### REL-04 — Estados de activación (cadena real, confirmada por lectura de código)

```
PeriodoNomina.estado (TRANSICIONES_VALIDAS es la única fuente de verdad de transición):
   ABIERTO -> PRELIQUIDADO -> EN_REVISION -> APROBADO -> PAGADO -> CERRADO
   + ANULADO (desde cualquier estado antes de PAGADO)
   + BLOQUEADO (pausa reversible, no transiciona automáticamente)

   ABIERTO       -> sin efecto en otras apps
   PRELIQUIDADO  -> DevengoBusinessService.procesar_devengo() calcula/persiste Devengos
   EN_REVISION   -> valida que existan Devengos activos (único chequeo de esta forma
                     en toda la cadena -- aprobar/pagar NO repiten esta validación,
                     gap teórico de "período avanza sin devengos activos")
   APROBADO      -> registro de aprobado_por (SET_NULL, sin forzar preservar atribución)
   PAGADO        -> marcar_pagado(): registro MANUAL, sin ejecución de transferencia real
                     (documentado explícitamente como tal en el propio código)
   CERRADO       -> fin del ciclo local

Devengo (vía PeriodoNomina) -> Contabilidad:
   Devengo creado (empresa+anulado=False, no contabilizado) -> ExtractorNomina lo recoge
   en el siguiente batch -> AsientoContable (gasto de personal + pasivo nómina).
   Relación PULL real, unidireccional, funcional (confirmado, no hipótesis).
```

### REL-05 — Mapa de procesos: PERIODO NOMINA APROBADO

```
PERIODO NOMINA APROBADO
 └── PAGADO (transición manual)
      ├── contabilidad  (vía ExtractorNomina, batch -- SÍ funciona)
      └── X-- bancos     NO EXISTE. marcar_pagado() es un registro local sin
                          ejecución de transferencia ni conciliación real.
```

---

## Patrón transversal observado en los 4 ciclos

En los cuatro ciclos, el tramo **"documento aprobado/confirmado → asiento contable"** funciona de forma consistente (Pull Model, ADR-001, batch/Celery, idempotente por `UniqueConstraint` sobre `documento_origen_*`). El tramo que consistentemente **falla o no existe** es el ÚLTIMO eslabón de cada cadena: **"→ Pago/Bancos"**:

| Ciclo | Tramo final declarado | Estado real |
|---|---|---|
| Venta | Factura → Bancos | Existe (push, no bloqueante) — **funciona** |
| Compra | CuentasPagar → Bancos | **No existe** (CRITICAL) |
| Gasto | DocumentoSoporte → CuentasPagar/Bancos | **No existe** (CRITICAL) |
| Nómina | PeriodoNomina PAGADO → Bancos | **No existe** (registro manual documentado) |

Ver `CROSS_APP_FINDINGS.md` para el detalle accionable de cada gap.
