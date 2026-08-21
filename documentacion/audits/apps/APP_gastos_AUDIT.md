# APP_gastos_AUDIT — Auditoria integral (app 12/16)

Mision: `documentacion/APP_AUDIT_MASTER_STATUS.md`. Orden: ... -> proyectos
-> **gastos** -> bancos -> ...

**Fecha:** 2026-08-20. **Rama:** `feat/onboarding-cookie`.

---

## FASE A/B — Mapa de negocio y modelos

`apps/tenant/gastos` tiene `.agent/AUDITORIA_FLUJO_GASTOS.md` mas
`AUDITORIA_INTEGRACION_GASTOS_CONTABILIDAD.md` -- usados como
contexto, verificados contra el codigo actual.

**Verificado 1:1:** 2 modelos (`ResolucionDIAN`, `DocumentoSoporte`),
coincide con `APP_AUDIT_MATRIX.md`.

**Explicacion de las 22 migraciones para 2 modelos** (senal flageada
en FASE 1 como posible iteracion de schema frecuente): confirmada
como evolucion arquitectonica deliberada, no churn descontrolado --
migraciones 0011/0017 agregaron `retefuente_porcentaje`/
`reteica_porcentaje` directamente en `DocumentoSoporte`; migracion
`0021_remove_deprecated_retencion_fields.py` los elimino, migrando el
modulo hacia el Pull Model puro (retenciones leidas desde
`contabilidad.Retencion`, no almacenadas localmente). Sumado a
migraciones de desacoplamiento contable (`cuenta_*_uuid` agregado y
luego eliminado, 0013-0015/0020) y ajustes de constraints/indices a
medida que se refinaron las reglas de negocio (`unique_ds_vendedor_
factura` -> `unique_ds_vendedor_documento`). Mismo patron de
"desacoplamiento contable" ya visto en `inventario`/`clientes`/
`empleados` -- explicado, no es un hallazgo nuevo.

## FASE C/D/K — Service Layer y codigo muerto (CONFIRMADO Y CORREGIDO)

**Encontrado codigo muerto real, con la evidencia mas fuerte posible:
shadowing de import a nivel de filesystem.** `apps/tenant/gastos/`
tenia **simultaneamente** un archivo `services.py` (398 bytes) Y un
paquete `services/` (directorio con `__init__.py`) -- el mismo tipo
de colision que ya se documento como bug historico en `empresa`
(`documentacion/_archive/CORRECCION_IMPORT_EMPRESA.md`, 2025), pero
aqui nunca se corrigio.

**Verificado empiricamente (no solo por grep):** se ejecuto
`import apps.tenant.gastos.services` en un interprete Python real --
la traza de carga confirma que Python resuelve el import al PAQUETE
(`services/__init__.py`), nunca al archivo sibling `services.py`. El
archivo `services.py` es **estructuralmente inalcanzable**: ningun
import de `apps.tenant.gastos.services` puede llegar jamas a el, sin
importar cuantos consumidores lo "importen" (todos terminan
resolviendo al paquete). Su contenido (`GastoBusinessService`,
`ResolucionBusinessService`, `materializar_gasto_desde_dto`
re-exportados desde `business_service.py`) ya estaba duplicado
correctamente en `services/__init__.py` (el paquete real), por lo que
ningun consumidor real se ve afectado.

**DEAD_CONFIRMED, eliminado:** `apps/tenant/gastos/services.py`
completo (398 bytes, el archivo entero era inalcanzable).

Resto del Service Layer (`services/{selectors,crud_service,
business_service,api_mixins}.py`) verificado limpio -- sin
`api/mixins.py` separado (a diferencia de `proyectos`, sin riesgo de
colision de nombres), `GastoServiceMixin`/`ResolucionServiceMixin`
confirmados como los realmente usados por `GastoViewSet`/
`ResolucionDIANViewSet`.

## FASE M — Normativa colombiana (RESUELVE EL HALLAZGO P1 DE `proveedores`)

`gastos` esta en la lista explicita de apps que requieren matriz
normativa. Ver **`documentacion/audits/apps/
APP_gastos_NORMATIVE_MATRIX.md`** -- contiene el hallazgo mas
importante de esta sesion hasta ahora: **resuelve con evidencia
directa el CONTRACT_DRIFT P1 dejado abierto en la auditoria de
`proveedores`** (app 6/16).

`GastoBusinessService.procesar_gasto()` (`business_service.py:
189-200`) calcula retenciones llamando a
`contabilidad.RetencionesService.obtener_retenciones_desde_tercero()`
-- **una tercera implementacion, independiente y correctamente
centralizada en Contabilidad**, NO las funciones de `proveedores`
(`obtener_configuracion_retenciones`/`calcular_componentes_retencion`,
que se confirma ahora que **nunca tuvieron ningun consumidor real**,
ni siquiera el que su propia documentacion afirmaba). El mecanismo
real funciona correctamente (Pull Model, config por tercero+naturaleza
+empresa, con fallback a default) -- **no hay gap funcional real en
el sistema**, solo codigo muerto en `proveedores` que quedo
documentado como si estuviera conectado.

**Accion tomada:** se actualiza `APP_proveedores_AUDIT.md` y
`APP_AUDIT_MASTER_STATUS.md` en esta misma sesion para reclasificar
ese hallazgo de P1 a P3 (limpieza de codigo muerto, informativo) --
**sin modificar codigo de `proveedores`** (esa app ya esta cerrada
con regresion confirmada; el ajuste es solo de documentacion/
prioridad, no reabre la auditoria ni requiere re-testear esa app).

## FASE Q — Tests / Regresion

21 tests coleccionados (`apps/tenant/gastos/tests/`). Regresion
ejecutada: **21 passed, 0 failed, 3 warnings preexistentes (min_value
DRF + `format_html()` sin args) en 3944.24s (1:05:44)**.

## Deferred

Ninguno nuevo para `gastos` en si. Ver actualizacion de
`APP_proveedores_AUDIT.md` (item reclasificado P1 -> P3).

## FASE X — Release Gate (checklist)

- [x] Modelos verificados contra `.agent/` doc existente (FASE B)
- [x] 22 migraciones explicadas (evolucion arquitectonica deliberada, no churn)
- [x] Service Layer auditado, codigo muerto encontrado y eliminado (FASE C/D/K, verificado empiricamente)
- [x] Matriz normativa colombiana completa -- resuelve hallazgo P1 pendiente de `proveedores` (FASE M)
- [x] `manage.py check` PASS (heredado de FASE 0, sin cambios de modelos)
- [x] Regresion de la app -- 21 passed, 0 failed
- [x] Sin deferred items nuevos pendientes

## FASE Y — Decision

**COMPLETED** -- 21/21 tests pasan, 0 regresiones. Codigo muerto
eliminado sin impacto (confirmado inalcanzable por definicion).
