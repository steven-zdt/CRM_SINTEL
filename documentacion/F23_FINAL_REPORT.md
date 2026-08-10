# F23 — Reporte Final

**Fecha:** 2026-08-10

## 1. Estado inicial

Commit base `4354674` (branch `feat/onboarding-cookie`). F21 y F22 COMPLETED. Brecha declarada
por F22 (`F22_INVENTARIO_BASELINE.md` §4, `F22_FINAL_REPORT.md` §21): `SALIDA_VENTA` no tenia
datos reales porque `ventas`/`facturas` nunca llamaban a `KardexService`.

## 2. Estado final

`VentaBusinessService.procesar_y_facturar_venta()` genera `MovimientoInventario(SALIDA_VENTA)`
real por cada `ItemVenta` con producto (excluyendo servicios), en el momento exacto en que la
Venta pasa a `FACTURADA_DIAN`, reutilizando `KardexService.registrar_movimiento()` sin duplicar
nada. `ExtractorInventario` (F22, sin cambios) ya detecta estos movimientos nuevos
automaticamente. **9/9 tests nuevos pasan, 45/45 en la regresion consolidada F21+F22+F23.**
Governance `FINAL STATUS: PASS`, 0 aristas `FORBIDDEN`, 0 imports de produccion
`ventas -> contabilidad`. **0 migraciones nuevas** (ningun modelo se modifico).

## 3. Hallazgo mas importante de esta fase: bug real de atomicidad (no de F23, expuesto por F23)

`VentaBusinessService.procesar_y_facturar_venta()` estaba decorado `@transaction.atomic`, pero su
propio `try/except` capturaba toda excepcion y la convertia en un retorno `(False, {...}, codigo)`
**sin volver a lanzarla**. Django solo revierte un bloque `atomic()` cuando la excepcion escapa de
la funcion decorada — al ser capturada internamente, Django confirma (commit) todo lo escrito
hasta ese punto, sin importar que la funcion reporte `ok=False`.

Este patron **ya existia antes de F23** (no lo introdujo esta fase), pero nunca se habia
manifestado: todos los puntos de fallo previos (DSV de cliente, items, resolucion DIAN) ocurren
**antes** de cualquier escritura real (`Venta`/`Factura`). `_generar_salida_inventario()` (F23) es
el primer paso capaz de fallar (stock insuficiente) **despues** de que `Venta` y `Factura` ya
fueron persistidas — expuso el bug en la practica de inmediato, en el primer test real de stock
insuficiente.

**Correccion:** `transaction.set_rollback(True)` en los 3 bloques `except` del metodo. Alcance
minimo, quirurgico, dentro del mismo metodo que F23 ya estaba modificando — no se toco ningun
otro flujo de `ventas`/`facturas`. Ver `F23_TEST_MATRIX.md` §5 para el detalle completo,
incluyendo como el test que lo expuso confirma la correccion.

## 4. Diseno — decisiones basadas en codigo real, no en hipotesis

- **Evento disparador**: `procesar_y_facturar_venta()`, no un concepto de "confirmacion" o
  "despacho" (no existen en el modelo). Ver `F23_INVENTORY_ISSUE_POLICY.md`.
- **Costo**: `Producto.costo_promedio` (campo real existente, estatico — nunca recalculado
  automaticamente), nunca `precio_unitario`/`precio_venta`. Ver `F23_SALE_INVENTORY_CONTRACT.md` §6.
- **Sede**: el mismo parametro `sede_id` que ya fluye hacia `Factura.sede`
  (`OrganizationalContext.resolve()`, sin re-derivar, sin aceptar del payload del cliente).
- **Documento origen**: `ItemVenta` (no `Venta`), mismo criterio de granularidad que F21 uso con
  `RecepcionCompraItem`.
- **Stock insuficiente**: se reutiliza la validacion ya existente de `KardexService` — rechazo
  atomico completo (§3), sin "reserva" ni "permitir negativo" (ninguno tiene soporte en el modelo).
- **Multi-item**: 1 `MovimientoInventario` por `ItemVenta` con producto, sin agregacion.

## 5. Reducciones de alcance — DEFERRED, documentadas explicitamente

- **Devoluciones** (`ENTRADA_DEVOLUCION` desde `NotaCredito`): `NotaCredito` es un documento de
  solo cabecera (subtotal/impuestos/total, sin `ItemNotaCredito`) — no hay de donde derivar
  cantidad/producto devuelto sin crear un modelo nuevo, fuera del alcance minimo de F23. El
  mecanismo `ENTRADA_DEVOLUCION` en si ya existe y esta probado desde F22.
- **Reverso de inventario por anulacion**: no aplica — `anular_venta()` rechaza estructuralmente
  cualquier venta ya `FACTURADA_DIAN` (`"Una venta facturada no puede anularse directamente. Emita
  nota credito."`), confirmado por test real. No existe el escenario que resolver.
- **Despacho/entrega parcial**: no existe ese concepto en `Venta`/`ItemVenta` — una venta
  facturada siempre genera la salida completa de cada item.
- **Frontend**: sin cambios — F23 es enteramente backend.

## 6. Tests

Ver `documentacion/F23_TEST_MATRIX.md`. 9/9 nuevos, 45/45 en regresion consolidada F21+F22+F23.

## 7. Seguridad / Tenant Isolation

Verificado con 2 schemas reales (`tenant1`/`tenant2`) — una venta de un tenant nunca genera
movimientos ni toca stock de otro. `sede_id` nunca se acepta del payload del cliente (via
`OrganizationalContext.resolve()`, DSV existente sin cambios).

## 8. Organizacion (Empresa/Sede/Area)

`Venta` sigue sin campo `sede` propio (decision NO tomada por F23 — se preserva el estado
existente, `sede_id` sigue siendo un dato de contexto transportado, no un campo de scoping). Sin
cambios a `OrganizationalContext`/`OrganizationalScope`.

## 9. Idempotencia

`documento_origen_app='ventas'`, `documento_origen_modelo='ItemVenta'`, `documento_origen_id=item.id`
— mismo `UniqueConstraint` de `MovimientoInventario` que F21 establecio, sin cambios de modelo.
Verificado por test real (reintento directo no duplica).

## 10. Contabilidad (Pull, sin cambios)

`ExtractorInventario` (F22) detecta los `MovimientoInventario(SALIDA_VENTA)` nuevos sin ningun
cambio de codigo — verificado por el test E2E (`test_e2e_venta_facturada_hasta_asiento_contable_via_extractor_f22`):
Venta -> SALIDA_VENTA -> Extractor -> DTO -> Contabilizador -> AsientoContable cuadrado.

## 11. Governance

```
python -m tools.organizational_governance.cli --report
FINAL STATUS: PASS
```

0 findings nuevos. Grafo de dependencias: 375 aristas totales (373 en F22, +2 nuevas
`ventas -> inventario`, ambas `CONTROLLED`/`PUSH_CONTROLLED`, ninguna `FORBIDDEN`). 0 imports de
produccion `ventas -> contabilidad` (el unico import de `contabilidad` en `apps/tenant/ventas/` es
en el test E2E, verificando el Pull, no un acoplamiento real).

## 12. Knowledge Graph

Extendido automaticamente por reconstruccion AST — relaciones reales nuevas:
`Venta -> ItemVenta -> MovimientoInventario`, sin crear un segundo grafo.

## 13. Archivos modificados

- `apps/tenant/ventas/services/business_service.py` — nuevo metodo
  `_generar_salida_inventario()`, 1 llamada nueva dentro de `procesar_y_facturar_venta()`, fix de
  atomicidad (`transaction.set_rollback(True)` x3), 1 import nuevo (`DjangoValidationError`).
- 2 archivos de test nuevos (`apps/tenant/ventas/tests/test_f23_venta_inventario{,_multitenant}.py`).
- 8 documentos nuevos en `documentacion/`.
- `documentacion/arquitectura_general.md` sincronizado.

**Nada mas cambio.** `apps/tenant/facturas/`, `apps/tenant/inventario/`, `apps/tenant/contabilidad/`
sin tocar.

## 14. Migraciones

**0 nuevas.** Ningun modelo se modifico.

## 15. Riesgos restantes (reales, no especulativos)

- El bug de atomicidad corregido en §3 solo se corrigio en `procesar_y_facturar_venta()` — si
  existen otros metodos `@transaction.atomic` con el mismo patron try/except-sin-reraise en otras
  apps, siguen teniendo el mismo riesgo latente (no auditado en esta fase, fuera del alcance
  quirurgico de F23 — mencionado aqui como riesgo conocido, no resuelto).
- `SALIDA_VENTA` ahora si genera datos reales, pero sigue dependiendo de que el tenant tenga
  `ReglaContable`/`PeriodoContable` configurados (mismo prerequisito operativo que F22 ya
  documento).

## 16. Deuda tecnica

- Devoluciones de inventario por Nota Credito (§5).
- Auditoria del patron `@transaction.atomic` + try/except en otros `BusinessService` del proyecto
  (§15) — no se hizo en esta fase.

---

**FINAL STATUS: PASS, sobre el alcance real documentado en este reporte y en
`documentacion/F23_EXECUTION_STATUS.md`.** No se declara "F23 100% completo respecto al literal
del prompt maestro" — las reducciones de alcance (devoluciones, despacho parcial, reverso por
anulacion) estan documentadas individualmente en §5, no ocultas.
