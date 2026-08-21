# APP_bancos_AUDIT — Auditoria integral (app 13/16)

Mision: `documentacion/APP_AUDIT_MASTER_STATUS.md`. Orden: ... -> gastos
-> **bancos** -> facturas -> ...

**Fecha:** 2026-08-20. **Rama:** `feat/onboarding-cookie`.

---

## FASE A/B — Mapa de negocio y modelos

`apps/tenant/bancos` tiene `.agent/AUDITORIA_FLUJO_COMPLETO.md` (v2.0,
2026-06-04, 709 lineas, "PRODUCTION READY, 0 criticos/importantes, 2
menores heredados de v1.0 -- ambos ya resueltos o sin accion
requerida") -- usado como fuente primaria.

**Verificado 1:1:** 3 modelos (`CuentaBancaria`, `ExtractoBancario`,
`TransaccionBancaria`), coincide con `APP_AUDIT_MATRIX.md`.

Resumen de negocio: **conciliacion bancaria** -- registro de cuentas
propias, ETL de extractos Excel (`pandas`/`openpyxl`), vinculacion
manual de cada transaccion con Factura/Proveedor/Cliente via soft-
reference UUID (Bounded Context §18, sin FK directa cross-app), flujo
guiado de 4 pasos para conciliar (TX -> Factura -> Tercero -> Notas),
auto-deteccion INGRESO/EGRESO por signo del valor.

**Observaciones menores heredadas (verificadas, sin accion):**
OBS-01 (naming `dcto`, convencion del extracto bancario colombiano,
sin impacto) y OBS-02 (ya resuelto en v2.0, `mes` con
`choices=MES_CHOICES`).

## FASE C/D/K — Service Layer y codigo muerto

Estructura limpia: `services/{selectors,crud_service,business_service,
api_mixins}.py` (4 archivos, coincide con matriz). **Sin
`services.py` sibling** (a diferencia de `gastos`, sin ese shadowing),
**sin `api/mixins.py` separado** (a diferencia de `perfil`/
`proyectos`, sin riesgo de colision de nombres), **sin marcadores
`deprecad`/`legacy`** en codigo de produccion.

**Conclusion FASE K: 0 lineas de codigo muerto confirmado.** Septima
app consecutiva sin hallazgos de limpieza necesarios (`perfil`,
`empleados`, `proveedores`, `inventario`, `compras`, `ventas`, ahora
`bancos` -- `cotizaciones`/`proyectos`/`gastos` si tuvieron hallazgos
en medio de esta racha).

## FASE M — Normativa colombiana

`bancos` esta en la lista explicita de apps que requieren matriz
normativa. Ver **`documentacion/audits/apps/
APP_bancos_NORMATIVE_MATRIX.md`** -- confirmado que `bancos` es un
modulo de **conciliacion/ETL**, no de calculo tributario (cero
referencias a retenciones en todo el modulo). El unico punto de
atencion es informal: no se verifico si existe validacion automatica
de que `saldo_final = saldo_inicial + sum(transacciones)` tras el
ETL (deferred P3, informativo).

## FASE Q — Tests / Regresion

Tests coleccionados: `apps/tenant/bancos/tests/`. Regresion lanzada
en background tras confirmar `db`/`redis` healthy. Sin cambios de
codigo en esta app.

## Deferred

| # | Item | Prioridad |
|---|---|---|
| 1 | No verificado si existe validacion de consistencia `saldo_final = saldo_inicial + sum(valor)` tras el ETL -- ver matriz normativa | P3 |

## FASE X — Release Gate (checklist)

- [x] Modelos verificados contra `.agent/` doc existente (FASE B)
- [x] Service Layer auditado, sin codigo muerto encontrado (FASE C/D/K)
- [x] Matriz normativa colombiana completa -- confirmado sin logica tributaria (FASE M)
- [x] `manage.py check` PASS (heredado de FASE 0, sin cambios de modelos)
- [ ] Regresion de la app -- **PENDIENTE**, en curso en background
- [x] Deferred items documentados con razon/riesgo/prioridad

## FASE Y — Decision

**PENDIENTE DE CIERRE** -- bloqueado por el resultado de la regresion
en curso. Se espera `COMPLETED_WITH_DEFERRED` (1 item P3 informativo)
si la regresion confirma 0 fallos.
