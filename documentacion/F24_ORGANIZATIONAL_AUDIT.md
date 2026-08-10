# F24 — Auditoria Organizacional (Empresa / Sede / Area)

**Fecha:** 2026-08-10

## 1. Empresa (tenant)

Singleton por schema fisico (django-tenants), hecho ya establecido en F21 y reusado
sin cambios en F22/F23. Verificado de nuevo en F24 via los tests multi-tenant
(`test_f24_e2e_multitenant_dsv.py`): cada schema tiene exactamente una `Empresa`,
nunca 2 filas en el mismo schema representando "otro tenant".

## 2. Sede

- `RecepcionCompra.sede`, `MovimientoInventario.sede`, `TrasladoInventario.sede_origen/destino`
  siguen siendo el mecanismo real de scoping por sede (F21).
- F24.10 (multi-sede) verificado con un escenario nuevo, mas cercano al ejemplo
  literal del prompt maestro (Bogota=100, Barranquilla=50, venta Bogota=20 ->
  Bogota=80/Barranquilla=50 sin contaminacion, venta Barranquilla=10 ->
  Bogota=80/Barranquilla=40): `test_f24_multi_sede_stock_independiente`.
- `Venta` sigue sin campo `sede` propio (decision preservada de F23, no re-abierta):
  `sede_id` se transporta como parametro de contexto explicito
  (`OrganizationalContext.resolve(request).sede_id`), nunca se acepta del payload del
  cliente. Confirmado sin cambios.

## 3. Area

Sin cambios de comportamiento en F21/F22/F23 respecto a `Area` mas alla de lo ya
documentado (DSV de Area en `crear_orden_compra`, ver
`apps/tenant/compras/services/business_service.py:162-180`: si se envia un `area`,
debe pertenecer a la misma empresa Y a la misma sede de la orden). F24 no encontro
ninguna app del circuito con logica de scope por `Area` no cubierta ya por F21.

## 4. `OrganizationalContext` / `OrganizationalScope` -- mecanismo unico reusado

F24 no crea un tercer mecanismo de scope. Verificado que `filter_by_scope()`/
`filter_by_scope_null_safe()` (usados en `compras/services/selectors.py`) y
`OrganizationalContext.resolve()` (usado para resolver `sede_id` en `ventas`) siguen
siendo los unicos puntos de entrada. Sin nuevas clases de scope introducidas.

## 5. Alcance EMPRESA/SEDE/AREA por usuario

No se creo un test HTTP nuevo con `APIClient` + roles (`TenantProfile.alcance`)
autenticados via request real -- los tests de F21/F22/F23/F24 verifican DSV y scope a
nivel de `BusinessService`/ORM directo (mismo criterio establecido desde F21: "no
existe un patron `APIClient`/`force_authenticate` en las suites de
compras/inventario/ventas", confirmado por busqueda en F24.1). El comportamiento de
`filter_by_scope()` ante `alcance='SEDE'`/`alcance='AREA'` ya esta cubierto por los
tests propios de esas apps fuera del circuito F21-F23 (`test_scope_isolation_f14.py`,
`test_scope_object_level_f13.py`, `test_scope_selectors_f7.py` en
`apps/tenant/inventario/tests/`, preexistentes, no tocados por F24).

## Veredicto

Sin hallazgos organizacionales nuevos. El modelo Empresa/Sede/Area se comporta segun
lo documentado en F21/F22/F23; F24 solo añadio cobertura E2E explicita para
multi-sede que antes se verificaba indirectamente.
