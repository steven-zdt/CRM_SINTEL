# UI_UX_PATRONES_VISUALES — SINTEL ERP

**Fecha:** 2026-09-17. **Rama:** `feat/onboarding-cookie`. **Fase:** 9 de `UI_UX_MASTER_MISSION_V2_59_FASES.md`.

Inventario de patrones visuales en las 6 apps que exige la Fase 9 (Clientes, Proveedores, Compras,
Ventas, Inventario, Facturas): Page Header, Toolbar, Search, Filters, KPI, Tabs, Table, Pagination,
Badge, Button, Dropdown, Offcanvas, Form, Confirm, Alert, Empty State, Loading State, Error State.

**Clasificación** (igual que exige la Fase 9): `SHARED_EXISTING` (usa el componente compartido real) ·
`DUPLICATE` (reimplementa algo que ya existe compartido) · `INCONSISTENT` (mismo propósito,
implementado distinto dentro de la MISMA app) · `APP_SPECIFIC` (justificadamente propio del dominio) ·
`CANDIDATE_SHARED` (se repite igual sin componente compartido) · `OBSOLETE` (código muerto).

**Metodología:** auditoría estática de solo lectura sobre templates/JS reales; no requiere Capa 1
(`BLOCKED`, Fase 12). Cada fila es trazable a un archivo/línea citado. El sistema de componentes
compartidos de referencia es `apps/tenant/core/templatetags/sintel_ui.py` (`sintel_kpi_card`,
`sintel_empty_state`) y los partials `apps/tenant/core/templates/tenant/core/partials/ui/` (
`filter_bar.html`, `loading_state.html`, `error_handler.html`) y `_base_offcanvas.html`, todos
documentados previamente en `UX_MASTER_BASELINE.md` (misión UX previa, 2026-08-21).

---

## Clientes

| Patrón | Dónde se encontró | Clasificación | Nota |
|---|---|---|---|
| KPI | `partials/tabla_clientes.html` usa `{% load sintel_ui %}` + `sintel_kpi_card` (6 cards) | SHARED_EXISTING | — |
| KPI | Tab Cartera (`clientes_list.html:154-160`): KPIs inline en `<span>` texto, vía JS | CANDIDATE_SHARED | Mismo propósito que KPI cards en formato "resumen inline"; se repite igual en Proveedores/CxP |
| KPI | Tab Facturas en `offcanvas_detalle_cliente.html:170-183`: tercer formato ("historial-kpis") | INCONSISTENT | Tercera variante visual de KPI dentro de la misma app |
| Tabs | `clientes_list.html` usa `nav-pills`; `offcanvas_detalle_cliente.html` usa `nav-tabs` | INCONSISTENT | Mismo propósito, clase Bootstrap distinta dentro de la misma app |
| Search | Tab Clientes (`clientes_list.html:49-58`), hand-rolled `input-group` | DUPLICATE | Markup casi idéntico al partial compartido `filter_bar.html`, reescrito a mano |
| Search | Tab Contactos (`clientes_list.html:119-123`, `contactos_list.html:18-29`) | DUPLICATE | Misma reimplementación manual, sin `hx-get` real (JS-driven) |
| Filters | Chips `btn-outline-*` en tab Clientes y tab Cartera | CANDIDATE_SHARED | Mismo patrón repetido 2 veces en la app (y en Proveedores) sin componente compartido |
| Table | `partials/tabla_clientes.html` vía `{% render_table table %}` | SHARED_EXISTING | Fase 5-BIS aplicada |
| Table | Tabs Contactos y Cartera con grid JS custom (`data-grid="contactos"`, `data-grid="cartera"`) | INCONSISTENT | Migración Fase 5-BIS incompleta dentro de la misma app |
| Badge | Estados (`bg-success/secondary/warning/info`) en detalle y abono de cartera | APP_SPECIFIC | Uso estándar coherente |
| Offcanvas | Todos los offcanvas reescriben `<style>` propio en vez de `_base_offcanvas.html` | DUPLICATE | `_base_offcanvas.html` existe pero solo lo usa `gastos` |
| Empty State | Tabs Contactos/Cartera usan `{% sintel_empty_state %}` | SHARED_EXISTING | — |
| Empty State | `offcanvas_detalle_cliente.html:191-194` (tab Facturas) reimplementa el markup a mano | DUPLICATE | Markup idéntico al de `empty_state.html`, copiado en vez de incluido |
| Empty State | `contactos_list.html` (archivo completo) | **OBSOLETE** | Documentado como código muerto en `documentacion/F33_14B_EMPTY_STATE_INVENTORY.md` ("0 referencias, eliminado"), pero sigue en el repo |
| Loading State | Spinners hand-rolled en tabs Contactos/Cartera y en detalle de Cliente | DUPLICATE | `loading_state.html` existe (usado por Compras) pero Clientes no lo adoptó |
| Confirm | `clientes.list.js:221,244` usa `UIManager.confirm()` | SHARED_EXISTING | — |
| Alert | `alert alert-danger d-none` en todos los offcanvas de creación/edición | APP_SPECIFIC | Consistente dentro de la app |
| Form | Secciones (`section-divider`/`section-title`) en formularios de Cliente/Cartera | APP_SPECIFIC | Convención propia consistente |

## Proveedores

| Patrón | Dónde se encontró | Clasificación | Nota |
|---|---|---|---|
| KPI | Tab CxP (`proveedores_list.html:143-147`): KPI strip inline | INCONSISTENT (cross-app) | Mismo patrón "resumen inline" ya visto en Clientes/Cartera, sin componente compartido |
| KPI | Directorio de Proveedores — **sin KPI cards**, mismo dominio de datos que Clientes (que sí las tiene) | INCONSISTENT (cross-app) | Ausencia notable frente a Clientes |
| Tabs | `nav-pills` en Directorio/CxP/Representantes | SHARED_EXISTING (patrón) | Coherente con Compras |
| Search | Directorio (`:73-84`) y CxP (`:157-168`), hand-rolled `input-group` | DUPLICATE | Misma reimplementación manual que en Clientes |
| Search | `representantes_directory.html:12-18` | DUPLICATE | Tercera reimplementación manual, sin HTMX (Tabulator `setFilter`) |
| Filters | Chips `btn-outline-*` por tipo/estado en Directorio y CxP | CANDIDATE_SHARED | Idéntico al de Clientes, sin componente compartido |
| Table | Directorio y CxP: django-tables2+HTMX | SHARED_EXISTING | Fase 5-BIS aplicada |
| Table | `representantes_directory.html`: grid **Tabulator** client-side, JS embebido (~220 líneas) en el `<script>` del template | **INCONSISTENT / OBSOLETE** | Contradice "Zero JS in HTML"; patrón Tabulator legado abandonado en el resto de la app |
| Table | `partials/list_representantes.html`: `<table>` HTML plano poblado por JS ad-hoc | INCONSISTENT | Tercera implementación distinta para la MISMA entidad (Representante): sin django-tables2 en ningún lado, Tabulator en el directorio, tabla manual en el detalle |
| Badge | `bg-success/warning/danger` en CxP y chip de proveedor en form de representante | APP_SPECIFIC | Consistente |
| Dropdown | Autocomplete de proveedor en form de Representante (`#proveedor-ac-dd`), hecho a mano | CANDIDATE_SHARED | Potencialmente reutilizable (Compras usa select simple, no autocomplete) |
| Offcanvas | `offcanvas_form.html`, `offcanvas_cuentas_pagar.html`, `offcanvas_representante_form.html` con `<style>` propio | DUPLICATE | Mismo hallazgo que Clientes/Compras |
| Empty State | `representantes-directory-empty`/`representantes-empty-state` usan `alert alert-info` | DUPLICATE | Ninguna variante usa `sintel_empty_state` |
| Confirm | `proveedores_form.js`, `cuentas_pagar_editor.js`, `representante_editor.js` usan `UIManager.confirm()` | SHARED_EXISTING | — |
| Confirm | `representantes_directory.html:191` usa `confirm()` **nativo del navegador** | INCONSISTENT | Único punto de las 6 apps auditadas que no usa el helper compartido |
| Offcanvas (apertura) | `representantes_directory.html:236`: fallback ahora usa `w.Sintel.Core.mostrarOffcanvasSeguro(offcanvasEl)` | **FIXED (2026-09-17)** | Reemplazó el `bootstrap.Offcanvas.getOrCreateInstance().show()` prohibido por `CLAUDE.md`. Ver Hallazgos. |

## Compras

| Patrón | Dónde se encontró | Clasificación | Nota |
|---|---|---|---|
| Tabs | `nav-pills` en `compras_list.html` para Órdenes/Plantillas | SHARED_EXISTING (patrón) | Coherente con Proveedores |
| Search | Toolbar de Órdenes: `{% include 'tenant/core/partials/ui/filter_bar.html' %}` | SHARED_EXISTING | Único de las 6 apps que realmente incluye el partial compartido en vez de reimplementarlo |
| KPI | `partials/tabla_compras.html:4-37`: 4 cards hand-rolled (`card bg-light`, `col-md-3`) | DUPLICATE | Reimplementa el propósito de `sintel_kpi_card` con markup/clases distintas |
| Table | `tabla_compras.html`, `tabla_plantillas.html` vía `{% render_table table %}` | SHARED_EXISTING | — |
| Loading State | `{% include 'tenant/core/partials/ui/loading_state.html' %}` en ambos paneles | SHARED_EXISTING | Único de las 6 apps que adoptó el partial compartido de loading |
| Badge | Estado de Orden (BORRADOR/PENDIENTE/APROBADA/RECIBIDA/ANULADA) | APP_SPECIFIC | Lógica de color por estado propia del dominio |
| Offcanvas | 3 offcanvas con `<style>` propio (`.form-label`, `.section-title`, `.offcanvas-footer`) | DUPLICATE | Ninguna de las 3 apps (Clientes/Proveedores/Compras) usa `_base_offcanvas.html` |
| Confirm | `compras_list.js` usa `UIManager.confirm()` | SHARED_EXISTING | — |
| Alert | `alert alert-danger d-none` para feedback de formularios | APP_SPECIFIC | Consistente con Clientes/Proveedores |
| Error State | No se encontró error state visual dedicado; existe `error_handler.html` compartido pero sin evidencia de uso en estas 3 apps | — | Sin fila positiva — se documenta la ausencia |

## Ventas

| Patrón | Dónde se encontró | Clasificación | Nota |
|---|---|---|---|
| Toolbar | `list_ventas.html:18-40` (Nueva Venta/Resoluciones DIAN/Refrescar) | APP_SPECIFIC | Layout propio razonable |
| Search | `list_ventas.html:41-53`, `input-group` + HTMX debounce 400ms | DUPLICATE | Casi idéntico a `filter_bar.html`, reimplementado a mano |
| Filters | `list_ventas.html:58-82`, botones `data-filtro-venta-estado` | APP_SPECIFIC | Filtro con badges de color por estado, propio del dominio |
| KPI | `partials/tabla_ventas.html:4-66`: 4 cards (Total Ventas, Monto Total, Borradores, Facturadas DIAN) | DUPLICATE | `sintel_kpi_card` sí se usa correctamente en `partials/reportes_ventas.html` de esta misma app — el listado principal no lo usa |
| Table | `partials/tabla_ventas.html:70`, `{% render_table table %}` | SHARED_EXISTING | Consistente con Fase 5-BIS |
| Table (Resoluciones) | `panel_resoluciones.html` + `resolucion_list.js`, grid Tabulator | INCONSISTENT | Tecnología distinta a la de Venta dentro de la misma app |
| Badge | `tables.py:51-54`, `render_estado` | APP_SPECIFIC | Colores mapeados a estados de negocio |
| Button | Bootstrap estándar en toda la app | SHARED_EXISTING | Uso directo sin wrapper propio, correcto |
| Offcanvas | 4 offcanvas con header/close hand-rolled | DUPLICATE | `_base_offcanvas.html` existe (usado por Gastos), Ventas no lo extiende |
| Form | Campos `form-control`/`form-label` estándar | APP_SPECIFIC | Propio del dominio DIAN/facturación |
| Confirm | `resolucion_editor.js:96,106` usa `UIManager.confirm()` | SHARED_EXISTING | Correcto |
| Confirm (Anular Venta) | `venta_editor.js:369`, `window.prompt('Motivo...')` | INCONSISTENT | Acción destructiva/irreversible sin el diálogo compartido que sí usa Resoluciones en la misma app |
| Alert / Error State | `mostrarFeedback()`/`ocultarFeedback()` duplicadas idénticas en `resolucion_editor.js:27-38` y `venta_editor.js:41-50` | DUPLICATE | Misma función copiada literalmente en 2 archivos de la misma app |
| Loading State | Solo en `reportes_ventas_container.html` (único uso de `htmx-indicator` en toda la app) | CANDIDATE_SHARED | `loading_state.html` compartido existe pero no se usa aquí; el resto de la app no muestra loading explícito |
| Empty State | `tables.py:40`, `empty_text` nativo de django-tables2 | APP_SPECIFIC | Delegado al framework |

## Inventario

| Patrón | Dónde se encontró | Clasificación | Nota |
|---|---|---|---|
| Tabs | `list_inventario.html:8-43`, `nav-tabs` Bootstrap nativo (5 tabs) | SHARED_EXISTING | Sin reimplementación propia |
| Toolbar | Repetido por cada tab (`list_productos.html:11-32`, etc.) | APP_SPECIFIC | Estructura similar entre tabs, acciones específicas de cada submódulo |
| Search | `list_productos.html:14-19`, `<input>` + HTMX debounce 400ms | DUPLICATE | Igual que Ventas: casi idéntico a `filter_bar.html`, reimplementado a mano |
| Search | `list_movimientos.html:31-34`, `<input>` sin atributo HTMX (gestionado por Tabulator) | INCONSISTENT | Variante adicional del buscador dentro de la misma app |
| KPI | `partials/tabla_productos.html:3-22` y `tabla_activos.html:2-33`, clase local `.kpi-card` | DUPLICATE | CSS **copiado literalmente** entre ambos templates; `sintel_kpi_card` compartido existe y no se usa en ninguno |
| Table | `tabla_categorias/productos/servicios/activos.html`, django-tables2 (Fase 5-BIS) | SHARED_EXISTING | Consistente entre los 4 submódulos migrados |
| Table (Movimientos/Kardex) | `list_movimientos.html:36`, `div#grid-movimientos` (Tabulator) | INCONSISTENT | Dejado fuera del alcance de Fase 5-BIS a propósito (comentado en `urls.py`), pero sigue siendo inconsistente frente a los otros 4 tabs |
| Pagination (Movimientos) | Paginación propia de Tabulator | INCONSISTENT | UX/controles distintos a la paginación Bootstrap del resto de tabs |
| Badge | `render_activo`/`render_estado` en Categoria/Producto/Servicio/Activo | APP_SPECIFIC | Colores por estado propios de cada entidad |
| Offcanvas | 5 offcanvas (Producto/Servicio/Activo/Categoria/Movimiento) con header/close hand-rolled | DUPLICATE | Igual que Ventas: ninguno extiende `_base_offcanvas.html` |
| Confirm | `UIManager.confirm()` en las 4 entidades con eliminar (Categoria/Producto/Servicio/Activo) | SHARED_EXISTING | Más consistente que Ventas — uso uniforme dentro de la app |
| Alert / Error State | `mostrarError()` en `movimientos_list.js:377-378` vs. `alert d-none` genérico en `list_productos.html:9` | INCONSISTENT | Mismo propósito, nombre/implementación distinta entre el tab de Movimientos y el resto |
| Loading State | No se encontró `htmx-indicator` ni spinner explícito en ningún template | — | Ausencia total, se documenta como hueco |

## Facturas

| Patrón | Dónde se encontró | Clasificación | Nota |
|---|---|---|---|
| Toolbar | `list_factura.html:60-90` (`#toolbar-facturas`, Importar/Refrescar/Sincronizar/Historial) | APP_SPECIFIC | Muy propio del dominio (ingesta de correo/XML) |
| Search | `list_factura.html:82-89`, `#search-factura` | DUPLICATE | Markup casi idéntico a `filter_bar.html` (que Gastos ya usa vía include), reimplementado a mano |
| KPI | `list_factura.html:23-58`, `#panel-totales-netos` (Ventas/Compras Netas) | DUPLICATE | `sintel_kpi_card`/`kpi_card.html` cubren el mismo patrón visual; Facturas lo reimplementa con extras (desglose Sub/IVA, borde de color) |
| Tabs | Listado (`<ul id="...-tabs">` con `<button>`) vs. editor (`<a>` con `nav-link`) | INCONSISTENT | Dos implementaciones de tabs dentro de la misma app |
| Table | `partials/tabla_facturas.html`, `{% render_table table %}` (`FacturaTable`) | SHARED_EXISTING | Config global `DJANGO_TABLES2_TEMPLATE = bootstrap5.html` |
| Pagination | Heredada del template estándar de django-tables2 | SHARED_EXISTING | Sin markup propio |
| Badge | Estados DIAN/pago (`_BADGE_DIAN`, `render_estado`/`render_estado_pago`) | APP_SPECIFIC | Mapeos de color/ícono propios del dominio de facturación electrónica |
| Confirm | `facturas_main.js:196`, `facturas_editor.js:410`, `UIManager.confirm()` | SHARED_EXISTING | Correcto |
| Offcanvas | 4 offcanvas (crear/editar/detalle/pendientes) con `<div class="offcanvas offcanvas-end">` hand-rolled | DUPLICATE | `_base_offcanvas.html` existe y **sí lo usa Gastos**; Facturas no lo extiende en ninguno |
| Offcanvas (apertura) | `mostrarOffcanvasSeguro(...)` en `facturas_list.js`/`facturas_main.js` | SHARED_EXISTING | Cumple AGENTS.md §26; sin `getOrCreateInstance().show()` en esta app |
| Form | Tabs del editor: campos XML (readonly, `bg-light`) vs. campos manuales (tarjeta azul "Gestión Manual") | APP_SPECIFIC | Convención propia y explícita ("campo XML = fuente de verdad"), no aplica a otras apps |
| Confirm (subida masiva) | `#upload-summary`/`#upload-progress-wrap` en `offcanvas_crear_factura.html` | CANDIDATE_SHARED | Patrón de "importar batch con contador + progreso" es genérico (aplicable a extractos bancarios, CSV) pero no existe componente compartido; cada importador lo resuelve a mano |
| Alert | `#feedback-facturas-list`, `#form-factura-feedback`, `#import-feedback`, todos `alert alert-danger d-none` con variaciones de atributos | INCONSISTENT | Mismo propósito, clases ligeramente distintas entre pantallas de la misma app |
| Empty State | Filas `<tr><td colspan>` con `bi-inbox` en editor y detalle | DUPLICATE | `empty_state.html` cubre el mismo patrón pero está pensado para bloque `<div>`, no fila de tabla — duplicación forzada por limitación del componente compartido, no solo descuido |
| Loading State | `list_factura.html:132-135,151-154` y `offcanvas_pendientes_factura.html:15-18`, spinners con leves variantes entre sí | DUPLICATE / INCONSISTENT | `loading_state.html` ya cubre el caso y Gastos lo usa vía include; Facturas lo reimplementa 2 veces distintas |
| Error State | `{% include 'tenant/core/partials/error_handler.html' %}` en 2 offcanvas | SHARED_EXISTING | Aquí sí se reutiliza correctamente |
| Modal (legado) | `offcanvas_importar_factura.html`, `#importModal` Bootstrap modal | **OBSOLETE** | No referenciado por ningún include/JS/vista; código muerto tras migrar a subida drag&drop |

---

## Resumen cuantitativo de clasificaciones

| Clasificación | Ocurrencias (aprox., 6 apps) | Lectura |
|---|---|---|
| `SHARED_EXISTING` | ~20 | Cuando existe, el sistema compartido se usa correctamente — el problema no es que el sistema falle, es que no se adoptó de forma pareja |
| `DUPLICATE` | ~24 | La categoría más numerosa — Search, KPI, Offcanvas y Loading State son los patrones más reimplementados a mano en vez de incluir el partial ya existente |
| `INCONSISTENT` | ~13 | Concentrado en Tabs, Table (Tabulator legado conviviendo con django-tables2) y Confirm/Alert dentro de la MISMA app |
| `CANDIDATE_SHARED` | ~6 | KPI inline strip (Clientes/Cartera, Proveedores/CxP), filtros por chips, autocomplete de proveedor, patrón de subida batch con progreso |
| `APP_SPECIFIC` | ~15 | Mayormente Badges de estado de negocio y Toolbars — correctamente no compartidos |
| `OBSOLETE` | 3 | `contactos_list.html` (Clientes), grid Tabulator de `representantes_directory.html` (Proveedores), `offcanvas_importar_factura.html` (Facturas) |

## Hallazgos notables (transversales a las 6 apps)

1. **`_base_offcanvas.html` existe pero solo lo adopta 1 de las 6 apps auditadas (Gastos).** Clientes,
   Proveedores, Compras, Ventas, Inventario y Facturas reimplementan el mismo `<style>` de header/
   botón-cerrar/footer en cada uno de sus offcanvas — es la duplicación más extendida de todo el
   inventario (más de 15 templates afectados).

2. **`filter_bar.html` (buscador compartido) solo lo usa Compras.** Las otras 5 apps reimplementan a
   mano un markup casi idéntico (mismo `input-group`, mismo debounce de 400ms, mismo `name="q"`) en
   al menos 8 pantallas distintas.

3. **KPI tiene 4 formatos visuales conviviendo sin un único componente:** `sintel_kpi_card` (Clientes/
   Cliente, Ventas/Reportes), cards hand-rolled con clases propias (Compras, Ventas/listado
   principal), "KPI strip" de texto inline (Cartera, CxP), y CSS de KPI copiado y pegado literalmente
   entre dos templates de Inventario (`list_productos.html`/`list_activos.html`).

4. **Tabulator legado convive con la migración a django-tables2 dentro de las mismas apps.**
   Proveedores (`Representante`), Ventas (`ResolucionFacturacion`) e Inventario (`MovimientoInventario`)
   mantienen grids Tabulator con JS embebido en el propio `.html` — en el caso de Proveedores, esto
   contradice explícitamente la convención "Zero JS in HTML" del resto de la app ya migrada.

5. **`FIXED` (2026-09-17) — uso confirmado del anti-patrón prohibido por `CLAUDE.md`:**
   `representantes_directory.html:236` (Proveedores) tenía un fallback a
   `bootstrap.Offcanvas.getOrCreateInstance().show()`, la única instancia detectada en las 6 apps
   auditadas — violación directa de la regla no-negociable ("PROHIBIDO — acumula backdrops. Usar
   `mostrarOffcanvasSeguro(el)`"). A diferencia de los demás hallazgos de esta fase (deuda de
   consistencia documentada sin corregir), este sí era candidato a fix quirúrgico inmediato y se
   corrigió: el fallback ahora llama a `w.Sintel.Core.mostrarOffcanvasSeguro(offcanvasEl)`, el mismo
   helper que ya usa el resto del proyecto (`apps/tenant/core/static/core/js/common/offcanvas.helper.js`).
   Cambio de una línea, sin tests dedicados nuevos (no había ninguno cubriendo la rama de fallback;
   el flujo principal sigue pasando por `w.UIManager?.handleOffcanvas`, que ya delega en el mismo
   helper).

6. **Confirmaciones destructivas inconsistentes dentro de la misma app:** Ventas usa el diálogo
   compartido `UIManager.confirm()` para eliminar una Resolución, pero usa `window.prompt()` nativo
   para Anular una Venta (acción igualmente irreversible); Proveedores usa `confirm()` nativo del
   navegador en `representantes_directory.html`, el único punto de las 6 apps que no pasa por el
   helper compartido.

---

**FIN — Fase 9 de `UI_UX_MASTER_MISSION_V2_59_FASES.md`.**
