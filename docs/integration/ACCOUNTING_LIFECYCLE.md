# Accounting Lifecycle — SINTEL ERP

**Fecha:** 2026-08-26 | **Fase:** REL-10 (validación del ciclo contable completo por proceso, no por app aislada)

Cada uno de los 4 ciclos propuestos en la misión se valida aquí paso a paso contra el código real: ✅ = confirmado funcionando, ⚠️ = existe pero con gap/deuda, ❌ = no existe.

---

## Ciclo de Venta

```
Cliente
   ✅ (obligatorio, FK PROTECT)
   v
Cotización (opcional)
   ⚠️  sin automatización de código Cotización→Venta (conversión 100% manual)
   v
Venta
   ✅ Venta→Factura→Inventario en UNA transacción atómica
   v
Factura
   ⚠️  nace en BORRADOR; la transición a ACEPTADA (requisito para contabilizar)
       depende de un flujo DIAN manual/mock -- no hay adaptador de transporte real
   v
Inventario
   ✅ MovimientoInventario(SALIDA_VENTA) generado en la misma transacción
   v
Costo
   ❌ ExtractorInventario existe y está probado, pero el Celery task real
      (ejecutar_integracion_completa) NO lo incluye en su lista de extractores
      -- el costo de venta NO llega al libro mayor por el pipeline automático
   v
Bancos
   ✅ conciliación push a Factura.estado_pago (no bloqueante)
   v
Contabilidad
   ✅ ExtractorFacturas funciona (requiere Factura.estado=ACEPTADA)
```

**Veredicto Venta:** el ciclo llega completo hasta Contabilidad para el ingreso (Factura), pero el **costo de venta correspondiente queda fuera** del pipeline automático — un desbalance real entre ingreso contabilizado y costo no contabilizado si nadie ejecuta el backfill manual.

---

## Ciclo de Compra

```
Proveedor
   ✅ (obligatorio, FK PROTECT en OrdenCompra; CASCADE en DocumentoSoporte)
   v
OrdenCompra
   ✅ al pasar a APROBADA, genera CuentasPagar automáticamente (v3.18.0)
   v
Recepción
   ✅ CONFIRMADA genera MovimientoInventario(ENTRADA_COMPRA), idempotente
   v
Inventario / Gasto
   ✅ Inventario vía Kardex; Gasto (DocumentoSoporte) es un flujo INDEPENDIENTE
      (no nace de una OrdenCompra necesariamente)
   v
FacturaCompra
   ⚠️  flujo completamente independiente de OrdenCompra (vía XML DIAN) -- las
      dos cadenas de "obligación con un proveedor" (OrdenCompra→CxP vs.
      Factura→estado_pago) NUNCA se cruzan ni se deduplican entre sí
   v
Bancos / CXP
   ❌ CuentasPagar (nacida de OrdenCompra) no tiene NINGÚN bridge a Bancos.
      Solo Factura.factura_uuid es conciliable automáticamente.
   v
Contabilidad
   ✅ ExtractorFacturas + ExtractorGastos + ExtractorInventario, cada uno pull
      independiente, todos funcionando para su propio origen
```

**Veredicto Compra:** el tramo `Compra→Recepción→Inventario` y el tramo `Factura→Contabilidad` funcionan bien de forma AISLADA, pero el ciclo como lo pide la misión (una sola cadena continua `Proveedor→...→Bancos/CXP→Contabilidad`) **no existe como una sola cadena** — son 3 cadenas paralelas parcialmente conectadas (ver `BUSINESS_DEPENDENCY_GRAPH.md` §3).

---

## Ciclo de Gasto

```
Proveedor
   ✅ (obligatorio, FK CASCADE -- nota: cascada agresiva, ver Findings)
   v
Soporte/Factura
   ✅ DocumentoSoporte es el modelo real (el modelo "Gasto" ya no existe,
      absorbido en migración 0010 de 2026-05-07)
   v
Gasto
   ✅ (es el mismo modelo DocumentoSoporte, no hay paso adicional)
   v
Retenciones
   ✅ push síncrono en la misma transacción de creación (RetencionesService)
   v
Contabilidad
   ✅ ExtractorGastos funciona (pull batch)
   v
Pago
   ❌ NO EXISTE ningún camino: sin campo local de estado de pago, sin
      DocumentoSoporte→CuentasPagar, sin DocumentoSoporte→TransaccionBancaria
```

**Veredicto Gasto:** el ciclo funciona completo hasta Contabilidad — el eslabón final "→ Pago" del enunciado de la misión simplemente **no está construido**. Adicionalmente: sin reversión automática de asientos/retenciones si un `DocumentoSoporte` ya contabilizado se anula después (riesgo de asiento "fantasma").

---

## Ciclo de Nómina

```
Empleado
   ✅ (obligatorio, FK CASCADE en Contrato, PROTECT en Devengo)
   v
Contrato
   ✅ constraint DB: máximo 1 ACTIVO por empleado
   v
Período
   ✅ PeriodoNomina con máquina de estados real (TRANSICIONES_VALIDAS)
   v
Preliquidación
   ✅ estado PRELIQUIDADO -> DevengoBusinessService.procesar_devengo()
   v
Aprobación
   ✅ estado EN_REVISION -> APROBADO, con validación de devengos activos
      (gap menor: aprobar/pagar no repiten esa validación)
   v
Pago
   ⚠️  marcar_pagado() es un registro MANUAL, documentado como tal en el propio
      código en 3 lugares distintos -- no ejecuta transferencia real
   v
Contabilidad
   ✅ ExtractorNomina SÍ funciona (pull, import ORM directo, unidireccional,
      confirmado contra la hipótesis de que pudiera no existir)
```

**Veredicto Nómina:** es el ciclo MÁS completo de los 4 hasta Contabilidad (incluyendo el eslabón de aprobación con máquina de estados real en BD). El gap es idéntico al de los otros 3: "→ Bancos" es manual, honestamente documentado como tal desde el propio código (no es un hallazgo oculto).

---

## Síntesis cross-proceso (lo que "comprobar por proceso, no por app" reveló)

1. **El patrón "→ Contabilidad" está sólidamente resuelto en los 4 ciclos** vía el mismo mecanismo (Pull Model, `documento_origen_*` polimórfico, `UniqueConstraint` de idempotencia, extractores independientes por app). Esta es la parte del sistema que SÍ se comporta como "un solo sistema coherente", no como integraciones aisladas.

2. **El patrón "→ Pago/Bancos" está roto o ausente en 3 de 4 ciclos** (Compra, Gasto, Nómina) y es únicamente "no bloqueante pero funcional" en el cuarto (Venta). Esta es la brecha real y priorizable: **no es un problema de una app, es un problema de proceso transversal** — `bancos.TransaccionBancaria` solo conoce `factura_uuid`/`cliente_uuid`/`proveedor_uuid`, y ninguno de los otros 3 orígenes de obligación (`CuentasPagar` sin factura, `DocumentoSoporte`, `PeriodoNomina`) tiene un soft-reference equivalente.

3. **El costo de venta contabilizado (Inventario→Contabilidad) es el único gap "CRITICAL" que no es sobre pagos** — es una desconexión entre un extractor que funciona y probado, y el orquestador batch que lo omite. Es el fix de menor riesgo/mayor impacto de toda esta auditoría (una línea en una lista, no un rediseño).
