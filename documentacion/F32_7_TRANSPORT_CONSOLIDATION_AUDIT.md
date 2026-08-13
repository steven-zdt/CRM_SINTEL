# F32.7 — Auditoria de consumidores directos de `window.http`/`window.getCookie` (client A)

F32.6 migro los 6 `*.api.js` que reimplementaban `fetch`+CSRF+JWT por su
cuenta. Esta auditoria (F32.7) busca algo distinto: archivos que ya
delegaban correctamente en `window.http`/`window.getCookie`
(`core/js/lib/http.js`, "client A") pero que quedarian rotos en silencio si
ese archivo se elimina sin migrarlos primero a `Sintel.Core.Http`.

Metodologia: `grep` exhaustivo de `window\.http|window\.getCookie` en todo
`apps/tenant/` (no solo los patrones `window\.http\(`/`window\.http\.` usados
en la primera pasada, que resultaron insuficientes -- ver hallazgos abajo),
descartando comentarios/`.agent`/docs y verificando cada `match` real con
lectura de codigo antes de clasificarlo.

## Client B: eliminado (confirmado codigo muerto)

`apps/tenant/core/static/js/http.js` ("v3.4 unificado") removido en este
commit. Se cargaba primero en `tenant/base.html:129`, pero
`core/js/lib/http.js` (client A) se carga despues via `assets_core.html` en
`workspace.html` y sobre-escribe `window.http`/`window.getCookie` -- B nunca
ejecutaba en produccion en esa ruta. De los 4 templates que extienden
`base.html` (`workspace.html`, `tenant/dashboard/index.html`,
`errors/404.html`, `errors/403.html`), solo `workspace.html` invoca
`window.http`; los otros 3 no hacen ninguna llamada HTTP client-side.
Verificado con regresion E2E completa (14/14) antes y despues de remover B.

## Client A: NO se puede eliminar todavia

### Migrados en F32.6 (los 6 originales)

`ventas.api.js`, `compras.api.js`, `gastos.api.js`, `empleados.api.js`,
`cotizaciones.api.js`, `dashboard.api.js` -- reimplementaban `fetch` por su
cuenta (no delegaban en `window.http`). Migrados a `Sintel.Core.Http`.

### Migrados en F32.7 (consumidores directos de `window.http`, hallazgo nuevo)

Estos SI delegaban correctamente en `window.http`, pero seguian atados al
transporte viejo. Migrados a `Sintel.Core.Http.request()`/`.csrf()`:

| Archivo | Patron |
|---|---|
| `facturas/static/facturas/js/facturas.api.js` | 15 metodos + guard clause + 1 uso de `window.getCookie` |
| `proveedores/static/proveedores/js/features/representante_editor.js` | 1 llamada inline (busqueda tipeada) |
| `empleados/static/empleados/js/features/empleado_list.js` | 2 llamadas inline (`loadSummary`, `ejecutarEliminar`) |
| `empleados/templates/tenant/empleados/offcanvas_detalle_liquidacion.html` | 1 llamada inline (PATCH estado pagado) |

Verificado con E2E real (specs 56, 57).

### PENDIENTES -- confirmados como consumidores reales, NO migrados todavia

Grep exhaustivo (`window\.http|window\.getCookie`, sin restringir a
`\(` o `\.` inmediato) encontro estos consumidores reales adicionales, no
capturados por la primera pasada de auditoria (que solo buscaba
`window\.http\(` y `window\.http\.` -- insuficiente porque varios archivos
alias-an `window` a `w` y llaman `w.http(...)`, o solo lo referencian en un
guard `typeof window.http !== 'function'` antes de la llamada real):

| Archivo | Uso real |
|---|---|
| `bancos/static/bancos/js/bancos.api.js` | Guard lazy + llamadas (verificar `w.http` en cada metodo, no al cargar el modulo) |
| `bancos/static/bancos/js/features/cuenta_editor.js` | `w.http(method, url, payload)` en `guardar()`, linea 104 |
| `clientes/static/clientes/js/clientes.contactos.js` | Comentario de dependencia; verificar uso real antes de migrar |
| `empleados/static/empleados/js/features/resolucion_editor.js` | `window.http` para guardar (skill vanilla-js.md §2) |
| `empleados/static/empleados/js/features/liquidacion_editor.js` | 3 usos (guardar, boton guardar reemplaza hx-post) |
| `core/static/core/js/utils/feedback.js` | Detecta forma de respuesta de `window.http` (401) -- verificar si es deteccion pasiva o llamada activa |
| `contabilidad/static/contabilidad/js/retencion/retencion.api.js` | Dependencia declarada de `window.http` |
| `proyectos/static/proyectos/js/proyectos.api.js` | Guard + `window.proyectosAPI = {error: ...}` si no disponible |
| `contabilidad/static/contabilidad/js/pendiente/plantilla_interceptor.js` | Dependencia declarada (`pendiente/` -- posible feature no activa, verificar si se carga) |
| `contabilidad/static/contabilidad/js/libro/libro_diario.api.js` | Dependencia declarada de `window.http` |
| `empresa/static/empresa/js/features/sede_editor.js` | `throw new Error('El helper window.http no esta cargado.')` -- guard antes de uso real |
| `empresa/static/empresa/js/features/area_editor.js` | Mismo patron que `sede_editor.js` |

**Confirmados como codigo muerto (NO migrar, no se cargan en ningun
template real):**

- `empresa/static/empresa/js/empresa.api.js` — se autodeclara `DEPRECATED
  v2.40`, ningun `assets_empresa.html` lo incluye con `<script>`.
- `core/static/core/js/landing/landing.api.js` — ni
  `core/templates/tenant/core/partials/landing/assets_landing.html` ni
  `landing/templates/tenant/landing/partials/assets_landing.html` (los 2
  bundles que lo referencian) son incluidos por ningun template padre.

### Hallazgo colateral: shell estatico de `/dashboard/`

`apps/tenant/core/static/tenant/core/dashboard/index.html` (el shell
independiente al que redirige `/dashboard/`, ver F32.1) carga
`core/js/lib/http.js` pero **nunca lo invoca** -- su unico `<script>` inline
llama `window.initDashboardPage()`, funcion que no existe en ningun archivo
cargado por esa pagina. Esta pagina ya esta rota independientemente de
esta migracion (bug ya flagged por separado, dashboard tab asset 404s). No
bloquea la eliminacion eventual de client A, pero tampoco se toca aqui
(fuera de alcance F32 -- UI redesign).

## Actualizacion: la auditoria "exhaustiva" no lo era

Los 12 archivos de la tabla "PENDIENTES" de arriba SI se migraron
(commit `756d3b5`), verificados con `manage.py check` + regresion E2E
completa (14/14). Pero ese grep (`window\.http|window\.getCookie`) segui­a
sin capturar el patron mas comun del codebase: casi todo `*.api.js` y
varios `*_editor.js`/`*_list.js` envuelven su IIFE como
`(function(w) { ... })(window)` y llaman `w.http(...)`, nunca
`window.http(...)` literal. Un grep final con `\bw\.http\(|window\.http\(|
window\.getCookie\(` encontro **46 archivos `.js` adicionales** con
llamadas reales (no comentarios), repartidos en inventario (11), empresa
(5, incluyendo el ya confirmado muerto `empresa.api.js`), proyectos (2),
facturas (6), empleados (4), contabilidad (9, incluyendo `cuenta.api.js`,
`asiento.api.js`, `periodo.api.js`, `tipo_comprobante.api.js`,
`plantilla.api.js` -- los "5 archivos contabilidad" que la primera pasada
de F32.1 no habia detectado en absoluto), clientes (3), proveedores (2),
core/helpers (2, incluyendo el ya confirmado muerto `landing.api.js`).

## Conclusion (actualizada -- F32.7 COMPLETO)

El usuario decidio migrar los 46 archivos restantes en la misma sesion.
Completado: los 46 archivos (inventario 15, contabilidad 8, facturas 5,
empresa 5, empleados 4, clientes 3, proveedores 2, proyectos 2, bancos 1,
core/helpers 1) migrados con el mismo patron mecanico (`window.http(...)`/
`w.http(...)` -> `Sintel.Core.Http.request(...)`, guards de disponibilidad
actualizados), verificados con `manage.py check` + regresion E2E completa
en cada tanda (0 regresiones en ningun punto).

Con los 52 consumidores reales (F32.6: 6 + F32.7: 46) migrados, **client A
(`core/js/lib/http.js`) tambien se elimino** -- confirmado sin consumidores
vivos por grep exhaustivo, `<script>` removido de `assets_core.html`
(unico punto de carga real). `Sintel.Core.Http` es ahora el unico cliente
HTTP del frontend tenant. Regresion final: 22/22 specs E2E en verde contra
`qaisotest.sintel.net.co`.

Excepciones documentadas, no tocadas (correctamente fuera de alcance):
- `empresa/static/empresa/js/empresa.api.js`, `core/static/core/js/landing/
  landing.api.js` -- codigo muerto confirmado (ningun `<script>` real los
  carga).
- Shell estatico de `/dashboard/` (`tenant/core/static/tenant/core/
  dashboard/index.html`) -- mantiene su propio `<script>` hardcodeado hacia
  el ahora-eliminado `lib/http.js` (404 silencioso), pero esa pagina ya
  estaba rota por separado (llama `window.initDashboardPage()`, funcion
  inexistente) y nunca invocaba `window.http`. Bug pre-existente, flagged
  aparte (`task_8c73f54c`), no de esta migracion.

F32.7 cierra aqui. Siguiente: F32.8 (matriz de regresion completa: 401/403/
CSRF/refresh JWT/upload/HTMX/offcanvas) segun el plan original del
usuario.
