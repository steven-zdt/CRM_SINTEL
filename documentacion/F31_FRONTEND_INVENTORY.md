# F31.0 — Inventario Real del Frontend

**Fecha:** 2026-08-12 · Rama `feat/onboarding-cookie`.
**Alcance:** solo lectura. **0 archivos de codigo modificados.** Este
documento es la entrada de F31.1 (contrato Frontend) y no autoriza ningun
cambio por si mismo.

**Metodologia:** grep estructural sobre `apps/tenant/*/static/` y
`apps/tenant/*/templates/` para 8 patrones (`Tabulator`/`TabulatorFactory`,
`render_table`/`django_tables2`, `hx-get|hx-post|hx-trigger|hx-swap|hx-target|hx-boost`,
`fetch()`/jQuery/axios/XHR, `window.Sintel.`, `bootstrap.Offcanvas` crudo vs
`mostrarOffcanvasSeguro`, guard `dataset.editorInitialized`, presencia de
`<app>.api.js`), verificado archivo por archivo donde el conteo agregado no
alcanzaba (p.ej. confirmar que un `http.js` duplicado esta realmente
huerfano, no solo que existe).

---

## 1. Matriz por app

| App | Grilla | API JS | Editor guard | HTMX | Tabulator | Estado |
|---|---|---|---|---|---|---|
| bancos | django-tables2 (2 tablas) | `bancos.api.js` unico | si (2/2 editores) | si | no | **Migrado** |
| clientes | Tabulator + django-tables2 (1 tabla) | `clientes.api.js` unico | no verificado | si | si (2 archivos) | **Coexistencia** |
| compras | django-tables2 (1 tabla) | `compras.api.js` unico | si | si | no | **Migrado** (piloto F29/F30) |
| contabilidad | django-tables2 (5 tablas) + Tabulator (reportes/pendientes/libro diario) | **8 archivos `*.api.js` fragmentados** (sin SSoT unico) | no verificado | si | si (3 archivos, casos complejos) | **Coexistencia deliberada** (reportes/libro diario son candidatos legitimos a permanecer en Tabulator, F31.7) |
| core | N/A (app de infraestructura) | N/A | N/A | si (workspace/dashboard shells) | aloja `TabulatorFactory` (motor compartido) | **Infraestructura -- requiere consolidacion** (ver §3) |
| cotizaciones | Tabulator (grid) + HTMX (offcanvas/forms) | `cotizaciones.api.js` unico | si (3/3 editores) | si | si | **Hibrido** -- grid en Tabulator, resto en HTMX |
| dashboard | Tabulator | `dashboard.api.js` unico | no verificado | **no detectado** | si | **Solo Tabulator, 0 HTMX** -- confirma la hipotesis original del usuario |
| empleados | django-tables2 (6 tablas, dominante) + Tabulator residual (`nomina_historial.js`) | `empleados.api.js` unico | no verificado (editores no usan el guard `dataset.editorInitialized`) | si | si (1 archivo) | **Mayormente migrado**, 1 uso residual de Tabulator |
| empresa | django-tables2 (4 tablas) | `empresa.api.js` unico (mas `empresa.list.js`) | si (2/2 editores) | si | no | **Migrado** |
| facturas | django-tables2 (1 tabla) | `facturas.api.js` unico | si | si | no (2 menciones en `facturas_list.js` son comentarios historicos sobre el reemplazo Fase 5-BIS, verificado -- no hay codigo Tabulator real) | **Migrado** |
| gastos | django-tables2 (2 tablas) | `gastos.api.js` unico | no verificado | si | no | **Migrado** |
| inventario | **Solo Tabulator** (5 archivos, via `TabulatorFactory`) | `inventario.api.js` unico | si (3 editores confirmados) | si (solo en offcanvas/forms, no en grid) | si (dominante) | **No migrado** -- contradice la hipotesis original del usuario (asumia que solo cotizaciones/dashboard seguian en Tabulator puro) |
| landing | minimo (1 archivo JS) | no aplica (paginas estaticas de marketing) | no aplica | no detectado | no | **Fuera de alcance** de modernizacion de grillas |
| perfil | django-tables2 (1 tabla) | `perfil.api.js` unico | no verificado | si | no | **Migrado** |
| proveedores | django-tables2 (2 tablas) + Tabulator (1 archivo, `proveedores_main.js`) | `proveedores.api.js` + `representante.api.js` (2 archivos, por sub-entidad) | no verificado | si | si (1 archivo) | **Mayormente migrado**, 1 uso residual |
| proyectos | django-tables2 (1 tabla) + Tabulator (`nueva_tarea_list.js`) | `proyectos.api.js` unico | no verificado | si | si (1 archivo) | **Mayormente migrado**, 1 uso residual |
| ventas | django-tables2 (1 tabla) + Tabulator (`resolucion_list.js`) | `ventas.api.js` unico | no verificado | si | si (1 archivo) | **Mayormente migrado**, 1 uso residual |

**Correccion importante a la hipotesis del usuario (F31.6):** el prompt
asumia que "cotizaciones y dashboard son las dos apps que todavia estan
exclusivamente en Tabulator". La evidencia real muestra que **`inventario`
tambien esta 100% en Tabulator** (5 archivos via `TabulatorFactory`, 0
tablas `django-tables2` encontradas) -- y que **`cotizaciones` es hibrida**
(HTMX ya cubre offcanvas/formularios, pero el grid principal sigue en
Tabulator), no "exclusivamente Tabulator". El Grupo 1 de prioridad de
migracion (F31.6) deberia ser **`dashboard` e `inventario`**, no
`dashboard` y `cotizaciones`.

## 2. Patron de grilla dominante: ya es HTMX + django-tables2

**14 de 17 apps** usan HTMX (`hx-get`/`hx-post`/`hx-trigger`/`hx-swap`) en
al menos una plantilla. **12 de 17 apps** ya renderizan al menos una tabla
via `{% render_table %}` (django-tables2). La migracion "Fase 5-BIS"
mencionada en `CLAUDE.md` esta considerablemente mas avanzada de lo que el
prompt original asumia -- el patron dominante YA es HTMX + django-tables2,
no Tabulator. El trabajo real pendiente de F31 no es "migrar de Tabulator",
sino:
1. Cerrar los **7 usos residuales** de Tabulator en apps ya mayormente
   migradas (empleados, proveedores, proyectos, ventas -- 1 archivo cada
   una) donde probablemente sea una vista/tabla que quedo fuera del barrido
   original.
2. Decidir explicitamente sobre **inventario** y **dashboard** (Grupo 1
   real).
3. Confirmar que la coexistencia de **contabilidad** (reportes, pendientes,
   libro diario) es la excepcion deliberada que F31.7 ya anticipa
   (comportamiento complejo/interaccion dinamica), no deuda tecnica.

## 3. Core Frontend -- hallazgos de fragmentacion (insumo directo para F31.2)

`apps/tenant/core/static/core/js/` tiene **dos directorios paralelos con
responsabilidades que suenan superpuestas**:

- `lib/`: `ajax-setup-csrf.js`, `api-helpers.js`, `dom-utils.js`, `http.js`,
  `ui-manager.js`
- `helpers/`: `crud.js`, `error-service.js`, `modal-service.js`, `routes.js`

Ademas, `common/` tiene `offcanvas.helper.js`, `sede_selector.js`,
`tabulator.factory.js`, `notyf.init.js` -- una tercera categoria.

**Hallazgo concreto de duplicacion:** existen **dos archivos `http.js`**:
- `apps/tenant/core/static/core/js/lib/http.js` -- referenciado activamente
  (`assets_core.html`, `dashboard/index.html`).
- `apps/tenant/core/static/js/http.js` -- **fuera del namespace de la app**
  (viola el patron `static/<app>/js/`, la regla de gobernanza
  `js_outside_own_app_static_path` deberia detectarlo pero la corrida
  actual reporta 0 hallazgos para esa regla -- posible gap del extractor,
  no verificado a fondo en este pase) y **sin ninguna referencia encontrada
  en plantillas** -- candidato fuerte a codigo muerto, a confirmar con
  `git log`/`git blame` antes de tocar.

Esto es exactamente el patron `utils1.js`/`utils2.js`/`http.js` duplicado
que el prompt de F31.1 identifica como riesgo a evitar -- ya existe hoy,
no es hipotetico.

## 4. Patron Offcanvas -- violacion de gobernanza real, no hipotetica

El helper canonico (`mostrarOffcanvasSeguro`, `core/js/common/offcanvas.helper.js`)
existe y es el patron obligatorio segun `AGENTS.md`/`CLAUDE.md`
("`getOrCreateInstance().show()` en Offcanvas -- PROHIBIDO -- acumula
backdrops"). Sin embargo, **14 archivos de features en 6 apps** llaman
directamente a `bootstrap.Offcanvas.getOrCreateInstance()` o
`new bootstrap.Offcanvas()`, evitando el helper:

| App | Archivos con offcanvas crudo |
|---|---|
| empleados | 5 (`liquidacion_list.js`, `liquidacion_editor.js`, `nomina_historial.js`, `resolucion_editor.js`, `devengo_editor.js`) |
| bancos | 2 (`cuenta_editor.js`, `extracto_editor.js`) |
| proveedores | 2 (`proveedores_form.js`, `representante_editor.js`) |
| facturas | 2 (`facturas_list.js`, `facturas_main.js`) |
| proyectos | 1 (`proyectos_editor.js`) |
| empresa | 1 (`mailinboxconfig_editor.js`) |

Verificado con un ejemplo real
(`bancos/static/bancos/js/features/cuenta_editor.js:48`):
```js
new bootstrap.Offcanvas(offcanvasEl).show();
```
Esto es exactamente el anti-patron que la regla ya documentada prohibe --
no una hipotesis de riesgo futuro, sino una violacion existente en 6 de 17
apps. **No se corrige en F31.0** (alcance solo-lectura); queda como
prioridad directa para F31.2/F31.5.

## 5. Guard de editor (`dataset.editorInitialized`)

Adopcion confirmada en 13 archivos `*_editor.js`, cubriendo al menos:
bancos, inventario, empresa, cotizaciones, compras, facturas. **No
confirmada** para los editores de: empleados, ventas, gastos, proveedores,
proyectos, clientes, perfil, contabilidad, dashboard -- requeriria una
segunda pasada dedicada por archivo (fuera del alcance de este inventario
agregado).

## 6. API JS -- SSoT roto en `contabilidad`

Todas las apps salvo `contabilidad` mantienen exactamente 1
`<app>.api.js` como SSoT de endpoints (algunas, como `proveedores`, tienen
un segundo archivo legitimo por sub-entidad: `representante.api.js`).
`contabilidad` tiene **8 archivos `*.api.js`** repartidos por
subcarpeta de feature (`asiento/`, `cuenta/`, `libro/`, `periodo/`,
`plantilla/`, `reporte/`, `retencion/`, con un archivo suelto
`tipo_comprobante.api.js`) -- sin un `contabilidad.api.js` raiz que actue
como indice. No necesariamente es un problema (contabilidad es la app mas
grande y compleja, con 8 sub-dominios reales), pero rompe la convencion de
"1 archivo = 1 SSoT por app" que el resto del proyecto sigue. Candidato a
decision explicita en F31.1 (aceptar el patron "1 api.js por sub-dominio"
como variante valida para apps grandes, o consolidar).

## 7. jQuery / patrones legacy

Solo **2 archivos** en todo el arbol de `apps/tenant/` usan sintaxis
jQuery-like (`$(...)`), ambos en `core/js/lib/` (`ajax-setup-csrf.js`,
`helpers/modal-service.js`). Baja prioridad -- confirma que el proyecto ya
esta mayoritariamente en Vanilla JS ES6+ como documenta `CLAUDE.md`; estos
2 archivos son candidatos a revisar durante la consolidacion de Core
(§3), no una migracion masiva.

## 8. `window.Sintel` -- adopcion amplia

53 archivos usan el namespace `window.Sintel.<App>`, cubriendo
practicamente todas las apps de negocio. Confirma que la convencion de
namespacing ya esta bien establecida -- **no** es un area que F31 necesite
corregir de forma masiva.

## 9. Conclusion -- alcance real de F31 vs el prompt original

El prompt original de F31 asumia una fragmentacion mas profunda de la que
existe realmente. Los datos muestran:

- **Ya migrado o mayormente migrado a HTMX + django-tables2:** bancos,
  compras, empresa, facturas, gastos, perfil (6 apps limpias) + empleados,
  proveedores, proyectos, ventas (4 apps con 1 uso residual cada una).
- **Coexistencia deliberada, posiblemente correcta (F31.7):** contabilidad
  (reportes/libro diario/pendientes -- casos con "comportamiento
  complejo").
- **No migrado -- Grupo 1 real de F31.6:** `dashboard` e `inventario`
  (no `cotizaciones`, que ya es hibrida).
- **Fuera de alcance de grillas:** `landing`, `core` (infraestructura).
- **Hallazgos concretos, no hipoteticos, para F31.2:** duplicacion real
  (`http.js` x2, uno huerfano), fragmentacion de `lib/`+`helpers/` en Core,
  y 14 violaciones reales del patron Offcanvas obligatorio en 6 apps.

**Recomendacion para F31.1:** el "contrato Frontend" que propone el
prompt original sigue siendo el paso correcto, pero debe partir de estos
hallazgos reales (consolidar `lib/`+`helpers/`, eliminar el `http.js`
huerfano, cerrar las 14 violaciones de Offcanvas) en vez de asumir una
reconstruccion desde cero. La prioridad de migracion de grillas debe
ajustarse: Grupo 1 = `dashboard` + `inventario`, no `dashboard` +
`cotizaciones`.

**No se toco ningun archivo de codigo en este pase.** F31.0 termina aqui;
F31.1 (contrato Frontend) requiere una decision explicita del usuario
sobre las correcciones de alcance identificadas arriba antes de proceder.
