# Tax Service — Conciliación Fiscal

**Fecha:** 2026-08-26

---

## Que se implemento en esta pasada

**Conciliacion por documento y por periodo (FASE 25/26), a nivel de LECTURA**: `tax.iva` y `tax.retenciones` permiten responder, con datos reales:

- ¿Cuanto IVA generamos en un periodo? -> `tax.iva`, filtro `naturaleza=VENTA`, medida `valor_iva`.
- ¿Cuanto IVA descontamos? -> `tax.iva`, filtro `naturaleza=COMPRA`.
- ¿Cual es el saldo fiscal calculado? -> `tax.iva` sin `group_by`, `totals.saldo_fiscal_calculado`.
- ¿Cuanta retencion (por tipo) se aplico, neta de reversas? -> `tax.retenciones`, filtro `tipo`.

**No se implemento** (FASE 12, "documento -> impuesto origen -> impuesto contabilizado -> diferencia") una conciliacion AUTOMATICA que compare el valor en `FacturaImpuesto`/`Retencion` contra el valor efectivamente contabilizado en `MovimientoContable`/`ImpuestoDocumento` y marque `REQUIERE_REVISION` cuando difieren. Razon: esto requeriria un JOIN confiable entre `Retencion.asiento_contable` (nullable, no siempre poblado segun el flujo) y los montos de `MovimientoContable` correspondientes, y **no existe evidencia en el codigo de que ese vinculo este garantizado en el 100% de los casos** (ver `TAX_BASELINE.md` §3: `Retencion` y `ImpuestoDocumento` son escritos por procesos DISTINTOS -- `RetencionesService` vs `Contabilizador` -- sin una FK bidireccional confirmada entre ambos para todo tipo de documento). Construir esta conciliacion sin esa evidencia violaria la Regla Absoluta #7 ("no inventar reglas fiscales"). Queda **REVIEW/BLOCKED** explicitamente, no oculto.

## Estados fiscales -- separados, no mezclados (FASE 4/14)

| Estado | Como se determina hoy | Implementado |
|---|---|---|
| CALCULADO | Existe la fila en `FacturaImpuesto`/`Retencion` | Si (es la base de ambos datasets) |
| CONTABILIZADO | `Retencion.asiento_contable` no es null | **No expuesto todavia** como dimension/filtro -- el campo existe en el modelo pero no se agrego a `tax.retenciones` en esta pasada (mantenerlo simple hasta que un consumidor real lo pida) |
| REVERSADO | `Retencion.reversada=True`, o fila con `monto` negativo | Implicito en el `monto` neto (ver `TAX_DATASETS.md`); no expuesto como dimension separada |
| CONCILIADO | Comparacion formal documento vs. contabilidad | **No implementado** (ver arriba) |
| PAGADO | Vinculo a una transaccion bancaria real | **No implementado -- gap confirmado, no inventado** (ver siguiente seccion) |
| DECLARADO | Presentacion formal ante DIAN | **No implementado** -- no existe ningun modelo de declaracion en el sistema |

Ningun dataset de esta mision usa un campo unico `estado_impuesto` que mezcle estas dimensiones -- cada estado no implementado simplemente NO aparece, en vez de aproximarse con un valor inventado.

## Bancos -- por que "PAGADO" no se puede determinar hoy (FASE 13/14)

Confirmado en `TAX_BASELINE.md` §6: `TransaccionBancaria` no tiene ningun campo que la vincule a una retencion, un IVA, ni a una obligacion DIAN -- solo soft-references a `factura`/`proveedor`/`cliente` y conciliacion MANUAL generica. **No se construyo ningun mecanismo de conciliacion bancaria-fiscal en esta mision** -- hacerlo sin ese vinculo real seria inventar una regla de negocio (Regla Absoluta #7). El Tax Service no escribe en Bancos (Regla Absoluta #13 respetada por diseño: nunca se importa `apps.tenant.bancos` desde los providers construidos).

## Alertas (FASE 28) -- no implementadas, honestamente

Las alertas que la mision sugiere (retencion sin contabilizar, reversa sin conciliacion, pago no identificado) dependen TODAS de la conciliacion formal que se dejo como REVIEW/BLOCKED arriba. Implementarlas ahora seria construir sobre una base que el propio codigo no soporta con evidencia -- se difieren junto con la conciliacion.
