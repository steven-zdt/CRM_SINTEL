# APP_ventas_AUDIT — Auditoria integral (app 9/16)

Mision: `documentacion/APP_AUDIT_MASTER_STATUS.md`. Orden: ... -> compras
-> **ventas** -> cotizaciones -> ...

**Fecha:** 2026-08-20. **Rama:** `feat/onboarding-cookie`.

---

## FASE A/B — Mapa de negocio y modelos

`apps/tenant/ventas` tiene `.agent/ARQUITECTURA_VENTAS.md` (v3.17.0,
2026-06-18, 988 lineas, "PRODUCTION READY, 0 CRITICOS") -- usado como
fuente primaria.

**Verificado 1:1:** 3 modelos (`ResolucionFacturacion`, `Venta`,
`ItemVenta`), coincide con `APP_AUDIT_MATRIX.md`.

Resumen de negocio: registro comercial (`Venta` como master record
antes/despues de emision DIAN), maquina de estados
`BORRADOR -> FACTURADA_DIAN -> ANULADA`, resolucion DIAN con
asignacion atomica de consecutivo (`select_for_update()`, mismo patron
que `empleados.ResolucionDIAN` y `compras.PlantillaOrdenCompra`),
integracion DIAN UBL 2.1 (orquesta pero delega la implementacion
tecnica a `facturas` -- ver FASE M), desacoplamiento contable total
(Ventas nunca toca `AsientoContable`, Contabilidad extrae via Pull
Model desde `Factura`).

**Contexto heredado de F23 (mision anterior), verificado intacto:**
`VentaBusinessService._generar_salida_inventario()`
(`business_service.py:645`) sigue presente y siendo invocada
(`business_service.py:615`) -- el pipeline venta -> inventario
(Kardex) -> contabilidad (Pull) diseñado e implementado en F23 no fue
tocado ni degradado. No se repite la investigacion completa de esa
fase, solo se confirma que sigue vigente.

## FASE C/D/K — Service Layer y codigo muerto

Estructura limpia: `services/{selectors,crud_service,business_service,
api_mixins}.py` (4 archivos, coincide con matriz). **Sin
`services/services.py`**, **sin marcadores `deprecad`/`legacy`** en
todo el codigo de produccion.

**Conclusion FASE K: 0 lineas de codigo muerto confirmado.** Sexta
app consecutiva sin hallazgos de limpieza (`perfil`, `empleados`,
`proveedores`, `inventario`, `compras`, `ventas`).

## FASE M — Normativa colombiana

`ventas` esta en la lista explicita de apps que requieren matriz
normativa. Ver **`documentacion/audits/apps/
APP_ventas_NORMATIVE_MATRIX.md`**. Hallazgo de alcance: `ventas`
orquesta el pre-proceso de facturacion (DTO UBL 2.1, consecutivo) pero
**delega la implementacion tecnica DIAN real** (CUFE, XML UBL 2.1,
firma XAdES-EPES) a `apps/tenant/facturas/services/dian/*` -- esa
correccion tecnica se auditara en `facturas` (app 14/16), no aqui.

Dentro del alcance real de `ventas`:
1. `ResolucionFacturacion.clean()` no se ejecuta en `bulk_create()`/
   ORM directo -- hallazgo YA documentado en el `.agent/` doc propio
   (2026-06-18), re-confirmado vigente (no corregido aun).
2. `porcentaje_iva` en `ItemVenta` sin validar contra tarifas vigentes
   -- mismo patron que `compras`, pero con mayor prioridad aqui porque
   el resultado es una factura DIAN real, no un documento interno.

## FASE Q — Tests / Regresion

13 tests coleccionados (`apps/tenant/ventas/tests/`). Regresion
ejecutada: **13 passed, 0 failed, 1 warning preexistente (min_value
DRF) en 2207.31s (0:36:47)**. Incluye la suite completa F23
(`test_f23_venta_inventario.py`, 7 tests: multi-item, stock
insuficiente revierte venta+factura, reintentos no duplican
movimiento, costo usa costo_promedio no precio_unitario, E2E hasta
asiento contable via extractor F22) -- todas verdes, confirma el
pipeline heredado intacto.

## Deferred

Ver tabla completa en `APP_ventas_NORMATIVE_MATRIX.md`. Resumen:

| # | Item | Prioridad |
|---|---|---|
| 1 | `ResolucionFacturacion.clean()` no ejecuta en bulk_create/ORM directo -- falta `CheckConstraint` DB (ya documentado, no nuevo) | P2 |
| 2 | `porcentaje_iva` sin validar contra tarifas de IVA vigentes -- afecta facturas DIAN reales | P2 |
| 3 | Correccion tecnica CUFE/UBL2.1/XAdES -- fuera de alcance, pendiente de `facturas` | Ver app 14/16 |

## FASE X — Release Gate (checklist)

- [x] Modelos verificados contra `.agent/` doc existente (FASE B)
- [x] Service Layer auditado, sin codigo muerto encontrado (FASE C/D/K)
- [x] Pipeline F23 (venta->inventario->contabilidad) confirmado intacto
- [x] Matriz normativa colombiana completa, con alcance delimitado hacia `facturas` (FASE M)
- [x] `manage.py check` PASS (heredado de FASE 0, sin cambios de modelos)
- [x] Regresion de la app -- 13 passed, 0 failed
- [x] Deferred items documentados con razon/riesgo/prioridad

## FASE Y — Decision

**COMPLETED_WITH_DEFERRED** -- 13/13 tests pasan, 0 regresiones,
incluyendo la suite F23 completa. 2 items P2 propios + 1 puntero a
`facturas`.
