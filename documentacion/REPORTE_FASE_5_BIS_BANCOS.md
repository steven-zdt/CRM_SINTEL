# REPORTE FASE 5-BIS — Bancos (Tabulator → django-tables2)

**Fecha:** 2026-08-04
**Alcance:** `PLAN_UNICO_CORRECCIONES.md` §"FASE 5-BIS", primera app del bloque "resto" (dinero: `facturas`/`contabilidad`/`ventas`/`compras` ya cerrado; `bancos` es la siguiente por tocar dinero via conciliación bancaria).
**Estado: 2 de 2 grillas reales migradas.** El plan listaba 3 archivos (`extracto_list.js`, `transaccion_list.js`, `cuenta_list.js`); `transaccion_list.js` **no existe en el repositorio** — nunca se creó. Las transacciones ya se renderizan server-side dentro del offcanvas de detalle de extracto (`offcanvas_detalle_extracto.html`, `{% for tx in transacciones %}`), sin Tabulator, desde antes de este plan.

---

## 1. Grillas migradas

| Grilla | Modelo | Archivos nuevos/tocados |
|---|---|---|
| Cuentas Bancarias | `CuentaBancaria` | `tables.py::CuentaBancariaTable`, `views.py::CuentaBancariaTableView`, `tabla_cuentas.html`, `list_bancos.html`, `cuenta_list.js` |
| Extractos Bancarios | `ExtractoBancario` | `tables.py::ExtractoBancarioTable`, `views.py::ExtractoBancarioTableView`, `tabla_extractos.html`, `list_bancos.html`, `extracto_list.js` |

**Patron replicado identico al de `compras`/`gastos`/`facturas`/`contabilidad`/`ventas`**, con una particularidad propia de esta app: a diferencia de las anteriores, `bancos.main.js` es un **orquestador centralizado** que maneja TODA la delegacion de eventos de acciones de fila (editar/eliminar cuenta, ver/conciliar/procesar/eliminar extracto) sobre `document.body`, mas un modal de confirmacion de eliminacion compartido entre ambas grillas. Ese archivo **no se tocó**: los botones que genera `tables.py` conservan el mismo nombre de atributo (`data-id`, con valor UUID -- igual que el Tabulator original, que ya hacía `rowData.uuid || rowData.id`) y las mismas clases (`.btn-edit-cuenta`, `.btn-delete-cuenta`, `.btn-view-extracto`, `.btn-conciliar-extracto`, `.btn-procesar-extracto`, `.btn-delete-extracto`), asi que la delegacion de `bancos.main.js` sigue funcionando sin cambios.

`cuenta_list.js`/`extracto_list.js` quedan reducidos a: `refresh()` (dispara `CustomEvent('cuenta-updated'|'extracto-updated')` en `document.body`, mismo nombre que el `hx-trigger` del panel), `init()`/`redraw()` como no-ops (conservados solo porque `bancos.main.js` los invoca en `shown.bs.tab` y en el listener `tab-activated` del modulo -- ya no hace falta que hagan nada, el panel HTMX se auto-carga con `hx-trigger="load"`), y `procesarExtracto(uuid)` (sin cambios de logica, solo su `refresh()` final ahora dispara el evento en vez de `table.replaceData()`).

**Caso especial:** `ExtractoBancarioTable.conciliacion`/`acciones` necesitan `tx_pendientes` (transacciones sin conciliar), que no era un campo anotado en `ExtractoBancarioSelector.get_list()` -- ese selector ya anota `total_transacciones` y `tx_conciliadas` (via `Count`), asi que `tx_pendientes` se calcula en el render de la tabla (`total - conciliadas`) igual que hacia el JS original, sin tocar el Service Layer.

**Limpieza incidental:** el boton de "buscar" (`data-action="search"`) y el atributo `data-search-input` en ambos formularios de busqueda nunca estuvieron conectados a ningun handler JS (la busqueda la resolvia `TabulatorFactory` escuchando el input directamente via `searchInputSelector`) -- eran decorativos. Se eliminaron al reemplazar los inputs con `hx-get`/`hx-trigger="keyup changed delay:400ms, search"`, que sí depende exclusivamente del input.

## 2. Verificacion

Sin Docker/venv funcional en este host (misma limitacion de toda la sesion). Verificado con `python -m py_compile` (`tables.py`, `views.py`, `urls.py`, `conftest.py`, `test_multitenant_isolation.py` -- todos OK) y `node --check` (`cuenta_list.js`, `extracto_list.js` -- OK). Grep de `grid-cuentas`/`grid-extractos` dentro de `apps/tenant/bancos/` confirma cero referencias colgantes tras el reemplazo. `apps/tenant/bancos/tests/` no existia -- se creó completo (`__init__.py`, `conftest.py` con fixtures `tenant1`/`tenant2`, `test_multitenant_isolation.py`).

**Antes de dar esta migracion por validada en runtime**, incluir en el batch de validacion final ya definido para el resto de Fase 5-BIS:
```
pytest apps/tenant/bancos/tests/test_multitenant_isolation.py -v
```
y abrir manualmente el modulo Bancos: ambas sub-pestañas (Cuentas/Extractos), buscar, paginar, ordenar, crear/editar/eliminar cuenta, importar/procesar/conciliar/eliminar extracto, y confirmar que el detalle de extracto (con sus transacciones, ya server-rendered desde antes) sigue abriendo correctamente.

## 3. Progreso de la expansion Fase 5-BIS (actualizado)

| App | Estado |
|---|---|
| `gastos` | Migrado (piloto) |
| `facturas` | Migrado |
| `compras` | Migrado |
| `contabilidad` | Migrado 5/8 grillas (3 fuera de alcance deliberado) |
| `ventas` | Migrado 1/1 grilla real (2 archivos del plan resultaron ser codigo no conectado, en progreso) |
| `bancos` | Migrado 2/2 grillas reales (1 archivo del plan nunca existió) |
| resto (~12 apps) | Pendiente: `empleados`, `inventario`, `cotizaciones`, `proveedores`, `empresa`, `proyectos`, `clientes`, `dashboard`, `perfil`, `core` |
