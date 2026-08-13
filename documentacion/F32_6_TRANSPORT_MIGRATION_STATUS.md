# F32.6 — Migracion de los 6 `*.api.js` no conformes a `Sintel.Core.Http`

**Estado: COMPLETO.** Los 6 archivos identificados en `F32_1_2_TRANSPORT_AUDIT.md`
como reimplementaciones directas de `fetch`+CSRF+JWT (violando el contrato SSoT
"solo URLs+metodos" de F31.3) ahora delegan en `window.Sintel.Core.Http`
(`apps/tenant/core/static/core/js/lib/core-http.js`, F32.3/F32.4).

## Archivos migrados

| Archivo | Contrato original preservado | Spec E2E | Commit |
|---|---|---|---|
| `ventas/static/ventas/js/ventas.api.js` | Lanza `Error` con `.status`/`.data` | `50-ventas-api-migration.spec.js` | `53a6b9f` |
| `compras/static/compras/js/compras.api.js` | Lanza `Error` con `.status`/`.data` (5 bloques duplicados consolidados en 1 `_fetch()`) | `51-compras-api-migration.spec.js` | `4d2a692` |
| `gastos/static/gastos/js/gastos.api.js` | Lanza `Error`; `contabilidad.obtenerRetenciones()` retiene su contrato unico "retorna `null` en fallo, no lanza" | `52-gastos-api-migration.spec.js` | `784c9ad` |
| `empleados/static/empleados/js/empleados.api.js` | `request(url,options)` retorna `{ok,status,data}` (no lanza) — unico consumidor real: `contrato_list.js:38` | `53-empleados-api-migration.spec.js` | `0a24b9f` |
| `cotizaciones/static/cotizaciones/js/cotizaciones.api.js` | `request()` rechaza con objeto plano `{ok:false,status,data}` (no `Error`) — 0 consumidores externos de `request()`, solo de los 3 metodos publicos de Configuracion | `54-cotizaciones-api-migration.spec.js` | `89521fd`, `3f5e6fb` |
| `dashboard/static/dashboard/js/dashboard.api.js` | Lanza `Error` con mensaje `Error <status>: ...` — unico consumidor real: `dashboard_main.js:39` (solo usa `.message`) | `55-dashboard-api-migration.spec.js` | `d33732b` |

Cada migracion sigue el mismo patron: leer el archivo completo, `grep` de todos
los consumidores externos de cada funcion publica antes de tocar su firma,
delegar el `fetch` interno en `Core.Http.request()`, preservar exactamente el
contrato de retorno/rechazo original (varia por archivo — no se unifico a la
fuerza), verificar con `manage.py check`, escribir un spec E2E nuevo dedicado,
correrlo contra `qaisotest.sintel.net.co` via el contenedor Playwright
efimero, commitear solo si pasa en verde.

## Hallazgo colateral (fuera de alcance F32, ya resuelto)

La verificacion de `cotizaciones.api.js` (spec 54) expuso un bug real y
pre-existente no relacionado con el transporte: `ConfiguracionCotizacionViewSet`
(`apps/tenant/cotizaciones/configuracion/viewsets.py`) no heredaba
`SintelDSVMixin` (a diferencia de todo el resto de ViewSets del mismo app),
causando un 500 (`AttributeError` en `get_empresa_id`) en cada request a
`/api/v1/cotizaciones/configuracion/`. Se flageo via `spawn_task`
(`task_0bf05347`) en vez de corregirse dentro de F32 ("sin tocar logica de
negocio", instruccion explicita del usuario) — el usuario lo tomo en una
sesion paralela sobre el mismo working tree y ya esta corregido (no
commiteado por esta sesion; el spec 54 se actualizo para reflejar el
comportamiento correcto una vez confirmado).

## Regresion

Suite completa (`specs/00` a `specs/55`, 12 specs) corrida dos veces:

1. Full run: 9 passed, 3 failed. De los 3 fallos: `30-contabilidad-cuenta-crud`
   (timeout de login, contencion por la sesion paralela corriendo sobre el
   mismo `runserver` compartido — mismo patron de flake ya documentado en
   F32.5), `40-tenant-edit` (bug de consola publica ya flageado por separado,
   `task_e7c1fa06`, mas un gap de `--add-host` en este contenedor ad hoc para
   el dominio publico `sintel.net.co`), y `54-cotizaciones-api-migration`
   (asercion desactualizada tras el fix paralelo del bug de arriba).
2. Re-run aislado de los 2 specs no explicados por bugs ya conocidos
   (`30` y `54`, actualizado): ambos verdes.

Ningun fallo es atribuible a las 6 migraciones de este documento.

## Siguiente paso

F32.7 (eliminar los `http.js` duplicados) requiere primero un re-audit de
TODOS los consumidores directos de `window.http`/`HttpClient` en el arbol
estatico completo (no solo los 6 archivos `*.api.js` migrados aqui — F32.1 ya
detecto acoplamiento oculto como `window.getCookie`, usado por varios
`features/*.js` fuera de los `*.api.js`). No iniciado todavia.
