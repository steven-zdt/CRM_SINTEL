# F33.0 — Inventario de UI Compartida

Escaneo de `apps/tenant/{bancos,clientes,compras,contabilidad,cotizaciones,
dashboard,empleados,empresa,facturas,gastos,inventario,landing,perfil,
proveedores,proyectos,ventas}` (templates + static/js), cruzado contra la
infraestructura ya compartida en `apps/tenant/core`. Metodologia: grep +
lectura de archivos representativos, no solo convenciones de nombres.

## Infraestructura ya compartida (baseline, no se re-audita como "duplicado")

- `Sintel.Core.mostrarOffcanvasSeguro` (`core/js/common/offcanvas.helper.js`) — SSoT nominal para Offcanvas (AGENTS.md §26).
- `window.UIManager` (`core/js/lib/ui-manager.js`) — notificaciones/toasts, manejo de errores HTMX 400/409/422, `confirm()`.
- `TabulatorFactory` (`core/js/common/tabulator.factory.js`) — grid legacy, en migracion (Fase 5-BIS, ~13/17 apps ya en django-tables2+HTMX).
- `Sintel.Core.Http` (`core/js/lib/core-http.js`) — cliente HTTP unico (F32), no relevante a UI.
- `core/js/helpers/crud.js`, `routes.js` — helpers genericos de CRUD/rutas.

## 1. Cards (KPI/metric)

Card de metrica (icono en circulo + numero + label) **copiado verbatim en 7
archivos** sin ningun include compartido: `clientes/partials/tabla_clientes.html:4-83`,
`gastos/partials/tabla_gastos.html:4-57`, `proyectos/partials/tabla_proyectos.html:4-55`,
`cotizaciones/list.html` (6 veces), `facturas/list_factura.html` +
`offcanvas_editar_factura.html`, `ventas/partials/tabla_ventas.html`. **No
adoptado en absoluto** en bancos/compras/contabilidad/empleados/empresa/
inventario/proveedores (mismo ola de migracion Fase 5-BIS, mitad de las
apps lo adopto, mitad no). Duplicacion trivial (solo CSS/markup), alta
oportunidad de consolidacion.

## 2. Loading states

4-5 implementaciones: (1) spinner HTMX-panel estandar (~15+ archivos,
consistente), (2) reloj de arena en tab-header (coexiste con #1), (3)
spinner Tabulator legacy con `display:none` JS-toggled (`clientes_list.html`,
tabs Contactos/Cartera), (4) string `"loading"` propio de `TabulatorFactory`
(config-level, base legacy sancionada), (5) **2 prototipos Tailwind
huerfanos** con su propio CSS de spinner (`dashboard/static/tenant/dashboard/index.html`
+ 5 hermanos bajo `core/static/tenant/core/{dashboard,contabilidad,empresa,facturas,perfil}/index.html`)
-- **confirmado codigo muerto** (ningun view/template los referencia), una
3a familia de UI (Tailwind CDN) durmiendo en el repo. Duplicacion trivial
(#1 vs #3); #5 es ruido de codigo muerto, bajo urgencia pero facil de
limpiar.

## 3. Empty states

2 convenciones: (1) `empty_text` de django-tables2 (baseline correcto,
estructura HTML unificada por la libreria) pero **wording inconsistente**
(4 variantes de frase para el mismo mensaje semantico, incluso dentro de
`empleados/tables.py`); (2) div "icono bi-inbox + texto muted" hand-rolled
para grids legacy/tablas anidadas en offcanvas (`clientes_list.html`,
`contactos_list.html`, `bancos/offcanvas_detalle_extracto.html`,
`facturas/offcanvas_editar_factura.html`, `proveedores/offcanvas_form.html`
+ `partials/representantes_directory.html`, este ultimo con un 3er
sub-variante envuelto en `alert-info`). Duplicacion trivial-a-moderada.

## 4. Error states (carga fallida, no validacion de formulario)

Mayoria delega correctamente al toast compartido (`UIManager.notifyError`/
`SintelFeedback.error`, ~38 archivos JS) -- fuera de alcance, correcto.
Excepcion real: `contabilidad` tiene su propio patron de caja de error
inline (`#error-container-{cuentas,asiento,periodos,plantilla}`,
markup identico en 4 partials) pero **no existe equivalente en ninguna de
las otras 12 apps** -- patron de una sola app, no duplicacion cross-app.
Severidad baja.

## 5. Confirmaciones de eliminar/destructivo

**El hallazgo mas serio de divergencia de comportamiento real.** 3
mecanismos genuinamente distintos:
1. `window.confirm()` nativo -- ~30 sitios en 12 apps, cada una con su
   propio string, sin compartir copy.
2. `UIManager.confirm()` (SweetAlert2, con fallback a nativo) -- usado
   solo en 2 archivos (`compras/features/compras_list.js`,
   `gastos/features/gasto_list.js`).
3. Modal Bootstrap hand-rolled por app (`id="confirmarEliminarModal[Suffix]"`,
   markup casi identico) -- reimplementado 4 veces: `bancos/list_bancos.html`
   (vivo, gestionado a mano con `bootstrap.Modal.getOrCreateInstance()` en
   `bancos.main.js`), `empleados/empleados_list.html` (vivo, mismo patron
   hand-rolled en `empleado_list.js`), `compras/compras_list.html` y
   `gastos/gastos_list.html` (**ambos codigo muerto** -- ningun JS los
   referencia, remanente de antes de la migracion a SweetAlert2; el de
   gastos ademas comparte `id` con el de empleados, riesgo de colision si
   alguna vez coexisten en la misma pagina).

Usuarios ven un `confirm()` nativo del navegador en la mayoria de apps, un
dialogo SweetAlert2 estilizado en 2, y un modal Bootstrap completo (a
veces no funcional) en 2 mas.

## 6. Filtros / busqueda

Comportamiento HTMX **unificado** (debounce, `hx-trigger`, `name="q"`
identicos en todos los toolbars encontrados) -- sin reimplementacion de JS
en ningun lado. El markup del wrapper si diverge en 3 variantes:
input-group+boton (`bancos`, `compras`, `gastos`, `proveedores`),
input-group+icono sin boton (`clientes`, `facturas`, `ventas`,
`cotizaciones`), input bare sin wrapper (`empleados`, `inventario`).
`clientes_list.html` ademas agrega un 4o patron (fila de pills de filtro)
no replicado en ninguna otra app. Duplicacion trivial (solo markup), el
contrato JS/HTMX ya esta unificado.

## 7. Paginacion

**Sin duplicacion -- la categoria mas limpia del inventario.** Todas las
listas migradas usan `{% render_table table %}` de django-tables2
(paginacion/orden 100% server-side), confirmado en >25 sitios en 11 apps.
0 implementaciones hand-rolled de Anterior/Siguiente encontradas. Buen
baseline de referencia para lo que deberia verse la consolidacion.

## 8. Badges de estado

Divergencia real y significativa para el mismo estado semantico
("Activo"). `inventario/tables.py` por si solo tiene **3 renderizados
distintos** del mismo toggle Activo/Inactivo en 3 metodos del mismo
archivo. Cross-app: `bg-success`/`bg-danger` plano (`clientes`), `bg-success`/
`bg-secondary` plano (`contabilidad` cuenta, `empresa`), `bg-success`/
`bg-danger` (`contabilidad` plantilla -- distinto al de cuenta 60 lineas
antes en el MISMO archivo), variante "subtle" con borde (`inventario`
Producto), variante `bg-opacity-10` translucida (`gastos`, `ventas`,
`empresa` en otros badges). Wording tambien diverge: "Activo"/"Activa"/
"Vigente". 17 metodos `render_activo`/`render_estado` en 7 apps. Color
siempre verde=activo (consistente), pero la familia de clases y el texto
no. Severidad moderada -- gap real de consistencia visual, no solo teorico.

## 9. Botones "Nuevo X"

**Altamente consistente** -- la convencion mejor adoptada del inventario.
Receta identica (`btn btn-primary btn-sm` + `hx-get render-offcanvas/crear/`
+ `data-create-button`) confirmada en 6+ archivos. Variacion minima
(`me-1` vs `me-2`) sin impacto. Severidad negligible.

## 10. Alerts (pagina, no toast)

3 usos legitimos, cada uno internamente consistente: mensajes de Django
(`core/partials/_messages.html`, SSoT correcto, sin duplicar), alerts
contextuales dentro de formularios offcanvas (contenido especifico por
formulario, variacion esperada, >50 ocurrencias solo para awareness), y
cajas `#form-{entity}-feedback`/`#feedback-{entity}-{mode}` (fuera de
alcance -- validacion de formulario -- pero con convencion de `id`
consistente sin drift, hallazgo positivo). Sin accion necesaria.

## 11. Modals (Bootstrap plano, no Offcanvas)

Inconsistencia arquitectonica real: modals coexisten con el estandar
offcanvas dentro de las MISMAS apps. `empresa/templates/tenant/empresa/modals.html`
(~213 lineas, 3 modals completos Ver/Editar/Crear Empresa) **confirmado
codigo muerto** (no incluido en ningun template, ningun JS lo referencia
-- la Empresa CRUD real ya usa offcanvas). `empresa/mailinbox_modals.html`
(`#modal-mailinbox-form`) **sigue vivo** mientras Sedes/Areas en la MISMA
app ya usan offcanvas -- sin razon tecnica encontrada para la diferencia,
parece un remanente sin migrar.

## 12. Violaciones de Offcanvas (no usan `mostrarOffcanvasSeguro`)

**El hallazgo mas significativo del inventario completo.** No existe un
unico helper mandatado en la practica -- existen DOS, mas llamadas crudas
sueltas:
- `mostrarOffcanvasSeguro` -- ~25 archivos consumidores.
- **Una segunda implementacion "safe offcanvas" escrita independientemente**:
  `UIManager.handleOffcanvas(selector, action)` (`ui-manager.js:321-374`)
  -- hace el mismo dispose-antes-de-show + limpieza de backdrop, pero es
  una funcion separada con firma distinta (`show`/`hide`) y TAMBIEN maneja
  el cierre (que `mostrarOffcanvasSeguro` no hace). Usado en **~22 archivos**
  con adopcion comparable al helper "oficial". Ninguno de los dos helpers
  sabe del otro; AGENTS.md §26 solo nombra `mostrarOffcanvasSeguro`, pero
  en la practica casi tantos archivos usan `UIManager.handleOffcanvas`.
- **Instanciacion cruda `new bootstrap.Offcanvas(...)`**, sin ningun
  helper, sin dispose, sin limpieza de backdrop -- violaciones reales:
  `compras/features/compras_list.js` (lineas 89,293,311), `perfil/perfil.modals.js`
  (58,81), `contabilidad/pendiente/plantilla_interceptor.js` (147),
  `gastos/features/gasto_list.js` (110,271) + `resolucion_editor.js` (29-30),
  `inventario/features/movimientos_editor.js` (584).
- **La misma logica de fallback (dispose+backdrop+new Offcanvas) copiada a
  mano al menos 6 veces** en vez de ser una funcion compartida:
  `contabilidad/asiento_list.js`, `cuenta_list.js`, `periodo_list.js`,
  `plantilla_list.js` (bloque identico `if (UIManager?.handleOffcanvas)
  {...} else {...}` en 4 archivos separados), `libro_diario_list.js`, y un
  6o caso re-pegado y renombrado en `empresa/empresa_list.html` como
  `window.sintelAbrirOffcanvasEmpresa`, comentado explicitamente como
  copiado del "patron inventario v3.9.0" en vez de compartirse via `core`.

Severidad **alta** -- exactamente el tipo de duplicacion que el helper fue
creado para prevenir (su propio docstring cita "16 reimplementaciones
locales... 2 rotas"), y la consolidacion quedo incompleta: un segundo
helper "safe" completo vive en paralelo con adopcion comparable, al menos
5 archivos instancian Offcanvas crudo (riesgo real de backdrops huerfanos
segun la propia advertencia del helper), y el mismo snippet pequeño de
dispose/cleanup se copio a mano al menos 6 veces en 2 apps distintas.

---

# F33.1 — Clasificacion

Regla aplicada: una abstraccion solo se crea si existe repeticion real +
comportamiento comun + API estable. Taxonomia: `SHARED_EXISTING` /
`DUPLICATE` / `APP_SPECIFIC` / `CANDIDATE_SHARED` / `OBSOLETE`.

| # | Hallazgo | Clasificacion | Razon |
|---|---|---|---|
| 1 | Card KPI (7 copias) | **CANDIDATE_SHARED** | Repeticion real (7x), markup identico, API obvia (color/icono/valor/label) -- candidato limpio para un template tag/include |
| 2a | Spinner HTMX-panel (~15 archivos, consistente) | **CANDIDATE_SHARED** | Ya consistente en la practica; formalizarlo en un partial evita drift futuro, no corrige nada roto hoy |
| 2b | Spinner Tabulator legacy | **APP_SPECIFIC** | Atado al patron Tabulator, ya en migracion via F33.3 (Table Contract) -- no consolidar por separado |
| 2c | Prototipos Tailwind (2 archivos, 6 sitios) | **OBSOLETE** | Codigo muerto confirmado (0 referencias) -- candidato a eliminar, no a "compartir" |
| 3a | `empty_text` django-tables2 (wording inconsistente) | **CANDIDATE_SHARED** | Mecanismo ya SSoT (la libreria); el wording necesita 1 diccionario de strings compartido, no un componente nuevo |
| 3b | Empty state hand-rolled (icono, 6 archivos + 1 sub-variante) | **CANDIDATE_SHARED** | Repeticion real, comportamiento comun, candidato a partial |
| 4 | Error state contabilidad-only | **APP_SPECIFIC** | Un solo app, no hay repeticion cross-app que justifique una abstraccion |
| 5a | `window.confirm()` nativo (~30 sitios) | **DUPLICATE** (del target ya existente) | El reemplazo YA EXISTE (`UIManager.confirm()`); esto es adopcion incompleta de un SSoT ya construido, no falta de abstraccion |
| 5b | `UIManager.confirm()` (2 archivos) | **SHARED_EXISTING** | Es el target correcto -- subutilizado, no duplicado |
| 5c | Modal confirmar-eliminar vivo (bancos, empleados) | **DUPLICATE** | Reimplementa lo que `UIManager.confirm()` ya resuelve, con gestion manual de `bootstrap.Modal` |
| 5d | Modal confirmar-eliminar muerto (compras, gastos) | **OBSOLETE** | Confirmado sin JS que lo referencie -- eliminar markup |
| 6 | Wrapper de filtro/busqueda (3 variantes de markup) | **CANDIDATE_SHARED** | Comportamiento JS/HTMX ya unificado; solo el markup wrapper diverge -- candidato de bajo riesgo |
| 7 | Paginacion (django-tables2) | **SHARED_EXISTING** | Ya consolidado, sin accion |
| 8 | Badges de estado (4+ convenciones, 17 metodos) | **CANDIDATE_SHARED** | Repeticion real, mismo semantico (activo/inactivo), API estable (estado→color/label) -- candidato a template filter |
| 9 | Boton "Nuevo X" | **SHARED_EXISTING** | Ya consistente en la practica, variacion minima no accionable |
| 10a | Django messages partial | **SHARED_EXISTING** | Ya es SSoT |
| 10b | Alerts contextuales en formularios | **APP_SPECIFIC** | Contenido especifico por formulario -- variacion esperada, no duplicacion |
| 10c | Cajas `#form-X-feedback` | **SHARED_EXISTING** (convencion) | Consistente sin necesitar un helper nuevo |
| 11a | `empresa/modals.html` (3 modals completos) | **OBSOLETE** | Codigo muerto confirmado -- eliminar |
| 11b | `empresa/mailinbox_modals.html` (vivo, sin migrar) | **CANDIDATE_SHARED** (via migracion) | Debe unirse al patron Offcanvas ya usado por sus hermanos Sedes/Areas en la misma app -- no es un componente nuevo, es completar una migracion ya en curso |
| 12a | `mostrarOffcanvasSeguro` (~25 archivos) | **SHARED_EXISTING** | El helper "oficial" segun AGENTS.md §26 |
| 12b | `UIManager.handleOffcanvas` (~22 archivos) | **DUPLICATE** | Reimplementacion independiente del mismo problema que #12a ya resuelve -- **el hallazgo de mayor prioridad de todo el inventario** |
| 12c | `new bootstrap.Offcanvas()` crudo (6 archivos) | **DUPLICATE** | Viola el proposito explicito del helper (riesgo de backdrops huerfanos) |
| 12d | Snippet de fallback copiado a mano (6+ sitios) | **DUPLICATE** | Mismas 4-6 lineas repetidas en vez de una funcion compartida |

## Prioridad de consolidacion real (evidencia, no preferencia)

1. **Offcanvas (#12b/c/d)** -- el caso mas fuerte: ya existe el target
   (`mostrarOffcanvasSeguro`), la duplicacion es medible (2 helpers con
   adopcion comparable, ~47 archivos combinados) y el riesgo es real
   (backdrops huerfanos, documentado por el propio helper).
2. **Confirmaciones (#5a/c/d)** -- mismo patron: el target ya existe
   (`UIManager.confirm()`), solo 2/34+ sitios lo usan.
3. **Card KPI, Empty states, Badges, Filtros** (#1, #3, #6, #8) -- duplicacion
   real mas menor, buenos candidatos de "quick win" via template
   tags/includes, bajo riesgo.
4. **OBSOLETE** (#2c, #5d, #11a) -- eliminar con evidencia, no requiere
   diseño de componente.

Dado que #1 y #2 (offcanvas, confirmaciones) ya tienen su target
construido y solo falta consolidar la adopcion -- **no ameritan un
`Sintel.Core.UI` nuevo**, ameritan retirar el helper duplicado y migrar
sus consumidores al que ya existe. El contrato `Sintel.Core.UI` (F33.2) se
disena entonces para lo que SI falta: Card, Badge, EmptyState, y el
wrapper de Filtros -- las 4 categorias donde no existe ningun target
previo.
