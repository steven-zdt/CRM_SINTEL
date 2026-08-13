# F31 (continuacion) — Cierre de Grupo 2: grillas residuales de Tabulator

**Fecha:** 2026-08-13 · Rama `feat/onboarding-cookie`.

## 1. Contexto

`F31_FRONTEND_INVENTORY.md` (F31.0) identifico 4 apps "mayormente
migradas" con exactamente 1 archivo residual de Tabulator cada una
(empleados, proveedores, proyectos, ventas) -- "Grupo 2", de menor riesgo
que el Grupo 1 real (`dashboard`/`inventario`, ya cerrado en F31.6). El
cierre de F31 (`F31_FINAL_REPORT.md`) dejo Grupo 2 explicitamente fuera de
alcance. Esta sesion lo retoma y lo cierra, mas un hallazgo adicional no
previsto: WIP preexistente sin commitear para `empresa`/`proveedores` que
resulto ser trabajo genuino y completo, no descartable.

## 2. Hallazgo de partida: WIP huerfano en el arbol de trabajo

Antes de tocar Grupo 2, `git status` revelo ~550 lineas de cambios sin
commitear en `empresa`/`proveedores`/`gastos`/`empleados` -- mismo estilo,
mismos patrones y misma disciplina de comentarios que el resto de F31
(hallazgos de bugs reales documentados inline), pero de una sesion
anterior. Verificado exhaustivamente antes de tocarlo:
- `apps/tenant/empresa/api/` y `apps/tenant/proveedores/api/` (capa DRF)
  sin ningun cambio -- el WIP era 100% capa UI (tables.py/views.py/
  selectors.py/templates/JS), sin riesgo de romper contratos API.
- `manage.py check` y `makemigrations --check --dry-run`: limpios.
- Suite completa de las 4 apps (133 tests): **115 passed, 18 failed**.
  Los 18 fallos se investigaron uno por uno -- **confirmados pre-existentes
  e independientes del WIP**: reproducen en aislamiento total, y las
  areas que tocan (sesiones/auth, aislamiento multi-tenant, API
  `/api/v1/proveedores/`) no tienen ni un solo archivo modificado por el
  WIP. Ninguno de los tests nuevos que trae el WIP esta en la lista de
  fallos. Flageados por separado (ver §6), no bloquean este cierre.

Resultado: 4 commits para el WIP verificado (`e531b77` empresa,
`f7019f2` proveedores, `9cd6f1f` gastos, `c375fa8` empleados) -- ver
detalle por app abajo.

## 3. `empresa` -- 3 grillas nuevas (Area, Empresa, MailInboxConfig)

`Sede` ya estaba migrada. Completa las otras 3 reutilizando los mismos
selectors que la API DRF. **2 bugs reales encontrados y documentados** (ya
presentes en el WIP, no nuevos de esta sesion):
1. Columna "Responsable" de `AreaTable` omitida deliberadamente -- leia un
   campo (`responsable_nombre`) que no existe en el modelo ni calcula
   ningun serializer; siempre mostraba "Sin asignar" en produccion.
2. `htmx:afterSettle` en `assets_empresa.html` generaba un bucle de
   refresco infinito (~47 req/s) -- las 4 tablas viven dentro del mismo
   contenedor que el listener observaba, asi que cada refresco disparaba
   su propio settle. Eliminado; cada modulo ya dispara su propio evento
   `*-updated` sobre `body`, que es lo unico que sus `hx-trigger` necesitan.

## 4. `proveedores` -- grilla Cuentas por Pagar

Reutiliza `CuentasPagarSelector.qs_list_facturas_compra` (misma SSoT que
la API DRF; fuente real es `Factura.naturaleza='COMPRA'`, no el modelo
`CuentasPagar`, que solo persiste abonos). **Bug real**: la grilla nunca
se renderizaba en produccion -- `init()` nunca era llamado desde
`proveedores_main.js`. Incluye tambien un evento `proveedor-updated`
(cache-invalidation para `Compras.Utils`) que ya estaba escrito en el WIP,
verificado y comiteado junto con el resto.

## 5. `gastos` / `empleados` -- namespacing de IDs

Ambas apps tienen una pestana "Resoluciones DIAN" con IDs genericos sin
prefijo (`#resoluciones-panel`, `#tab-resoluciones`, `#search-resolucion`).
Si ambos modulos coexistieran en el mismo DOM (HTMX boost/navegacion sin
recarga completa), el ID duplicado rompe `hx-target` (resuelve el primer
match, no el correcto). Renombrados a `#gastos-resoluciones-panel` /
`#empleados-resoluciones-panel` respectivamente. 2 commits (uno por app).

## 6. Issue separado: 18 fallos pre-existentes flageados

No corregidos en esta sesion -- fuera de alcance de "gobernanza frontend"
y requieren investigacion propia. Flageados via `spawn_task`
(`task_c3296519`): 404 en `POST /api/v1/proveedores/` (candidato: commit
`28e7f3d`, validacion de `ALLOWED_HOSTS` antes de resolucion de URL),
fallos de sesion/auth y aislamiento multi-tenant en `gastos`/`empleados`.

## 7. Cierre real de Grupo 2

Con el WIP de empresa/proveedores ya committeado, se investigo cada uno
de los 4 archivos residuales originales de F31.0:

- **`proveedores/proveedores_main.js`**: ya no existe -- la grilla
  "Directorio de Proveedores" ya estaba migrada (`ProveedorTable`/
  `ProveedorTableView`, preexistentes). Grupo 2 para proveedores ya
  estaba resuelto antes de esta sesion; solo faltaba Cuentas por Pagar
  (§4).
- **`empleados/nomina_historial.js`**: **NO migrado, deliberadamente**.
  Es una grilla de drill-down anidada dentro de un offcanvas (historial de
  nominas por empleado especifico) -- misma categoria que el Kardex de
  `inventario` (F31.6) y el historial de compras de `proveedores_form.js`
  (ambos ya excluidos con la misma justificacion, regla F31.7). Documentado
  como excepcion consistente, no como trabajo pendiente.
- **`ventas/resolucion_list.js`**: **eliminado como codigo muerto**, no
  migrado. Investigacion confirmo que su contenedor objetivo
  (`#grid-resoluciones`) no existe en ningun template de `ventas`, y
  ningun archivo llama a `window.Sintel.Ventas.ResolucionList` (grep
  completo, 0 referencias externas). La UI real de gestion de Resoluciones
  DIAN en `ventas` ya vive en un offcanvas server-rendered
  (`panel_resoluciones.html`, servido por `ventas/api/viewsets.py:306`)
  que `resolucion_editor.js` ya recarga completo tras cada accion
  (`_recargarPanel()`, `htmx.ajax`) -- nunca invoca `ResolucionList`. Mismo
  patron de codigo muerto que `error-service.js` (F31.2).
- **`proyectos/nueva_tarea_list.js`**: **migrado** -- panel "Nueva Tarea"
  (tareas cortas embebidas en Proyectos). Unico de los 4 que requeria
  parametros dinamicos (empleado de contexto, estado, busqueda) que un
  `hx-trigger="load"` estatico no puede expresar; se dispara explicitamente
  via `htmx.ajax()` en cada `refresh()` (mismo mecanismo que los modulos
  `*_editor.js` ya usan para offcanvas parametrizados). KPIs y filtrado,
  antes client-side sobre las filas de Tabulator, ahora server-side en
  `TareaCortaTableView`/`TareaCortaSelector.qs_por_empleado()`. Logica de
  negocio preservada exacta (avanzar estado, eliminar, contexto por
  empleado).

## 8. Verificacion

- `manage.py check` y `makemigrations --check --dry-run`: limpios en cada
  paso.
- `tools/ekg/governance.py --offline` (ejecutado como modulo:
  `python -m tools.ekg.governance --offline`): **conteos identicos al
  baseline de F30/F31** -- 23 `viewsets_without_service_layer`, 6
  `sede_or_area_field_without_sede_aware_model`, 2
  `import_cycles_between_tenant_apps`, 0 en el resto. 0 hallazgos nuevos.
- Tests nuevos: 3 archivos para `empresa` (Area/Empresa/MailInboxConfig),
  1 para `proveedores` (CuentasPagar), 1 para `proyectos` (TareaCorta, 4
  tests) -- todos pasan. Un test (`test_tabla_tareas_cortas_boton_
  acciones_usa_uuid`) fallo en el primer intento por un bug del propio
  test (consulta directa al modelo sin `schema_context`, no un bug de
  produccion) -- corregido y reverificado.
- Misma limitacion de navegador que el resto de F31 (§9 de
  `F31_FINAL_REPORT.md`): sin verificacion visual posible en este entorno.

## 9. Commits de esta sesion

```
e531b77 feat: Fase 5-BIS -- migrar grillas Area/Empresa/MailInboxConfig a django-tables2+HTMX
f7019f2 feat: Fase 5-BIS -- migrar grilla Cuentas por Pagar (proveedores) a django-tables2+HTMX
9cd6f1f fix: gastos -- namespacear IDs del panel de Resoluciones DIAN
c375fa8 fix: empleados -- namespacear IDs del panel de Resoluciones DIAN
02aa179 fix: ventas -- eliminar resolucion_list.js (codigo muerto)
c053366 feat: Fase 5-BIS -- migrar panel Nueva Tarea (tareas cortas) a django-tables2+HTMX
```

## 10. Estado de Grupo 2 (F31.0) tras esta sesion

| App | Archivo residual (F31.0) | Resolucion |
|---|---|---|
| empleados | `nomina_historial.js` | Excepcion deliberada (drill-down anidado, misma regla que Kardex/historial-compras) |
| proveedores | `proveedores_main.js` | Ya resuelto antes de esta sesion (grilla ya migrada) |
| proveedores | `cuentas_pagar_list.js` (hallazgo adicional, no en F31.0) | Migrado |
| proyectos | `nueva_tarea_list.js` | Migrado |
| ventas | `resolucion_list.js` | Eliminado (codigo muerto) |

**Grupo 2 cerrado.** El unico Tabulator restante en estas 4 apps es
`nomina_historial.js`, documentado como excepcion consistente con la
regla F31.7 (drill-down anidado, coexistencia deliberada). El cluster
`http.js`/`jwt-auth.js`/6 `api.js` (F31.2/F31.3) sigue diferido por el
mismo motivo estructural documentado en `F31_FINAL_REPORT.md` §9 -- no
hay entorno de ejecucion de JavaScript disponible (sin navegador
funcional, sin Node.js, sin `pytest-playwright`), asi que no es una
decision de riesgo que mas esfuerzo pueda superar.
