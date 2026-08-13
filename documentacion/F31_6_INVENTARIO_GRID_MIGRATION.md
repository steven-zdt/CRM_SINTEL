# F31.6 — Migración de grillas: `inventario` (Tabulator → django-tables2 + HTMX)

**Fecha:** 2026-08-12 · Piloto interno de F31.6, elegido tras corregir la
prioridad de migración en `F31_FRONTEND_CONTRACT.md` §3 (Grupo 1 real:
`dashboard` + `inventario`, no `dashboard` + `cotizaciones`).

## 1. Hallazgo de partida: migración a medias, ya comiteada

Al investigar `inventario` para elegirlo como piloto se descubrió que
**el backend de esta migración ya existía**, comiteado en una sesión
anterior (`60d8a33`, "migracion Fase 5-BIS a django-tables2"):
`apps/tenant/inventario/tables.py` (4 `Table` classes completas: Categoria,
Producto, Servicio, ActivoFijo, con formatters y `data-uuid` ya correctos)
y `apps/tenant/inventario/views.py` (4 `SingleTableView` completas,
incluyendo KPIs server-side para Producto/ActivoFijo). Pero **nunca se
conectó**: `urls.py` no tenía las rutas, no existían los templates
partial (`partials/tabla_*.html`), y el frontend (templates de lista +
JS) seguía 100% en Tabulator. F31.0 había detectado correctamente
"inventario 100% Tabulator" porque auditó el frontend, sin saber que el
backend ya estaba listo y simplemente desconectado.

Este documento cubre **completar** esa migración, no diseñarla desde
cero.

## 2. Alcance

**Migradas (4 de 5 grillas reales del módulo):** Categorías, Productos,
Servicios, Activos Fijos.

**Explícitamente NO migrada: "Movimientos Recientes" (Kardex)**
(`list_movimientos.html` / `movimientos_list.js` / `movimientos_editor.js`
/ `inventario_list.js`) — decisión ya documentada en el propio docstring
de `tables.py` (comiteada antes de esta sesión): consume
`get_movimientos_timeline()`, una vista agregada cross-model (combina
`MovimientoInventario` + `HistorialServicio` en dicts de Python, "Ledger
Universal"), el mismo tipo de vista compleja que ya quedó fuera de
alcance en `contabilidad` (reportes/libro diario) y en `dashboard`
(KPIs por sede) — coexistencia deliberada, no deuda pendiente (regla
F31.7).

## 3. Trabajo completado en esta sesión

- **`urls.py`**: agregadas las 4 rutas (`categoria-tabla`,
  `producto-tabla`, `servicio-tabla`, `activo-tabla`), verificadas con
  `reverse()` bajo `TENANT_URLCONF`.
- **4 templates partial nuevos** (`partials/tabla_categorias.html`,
  `tabla_productos.html`, `tabla_servicios.html`, `tabla_activos.html`) —
  `{% render_table table %}`, más los KPI strips de Productos/Activos
  migrados a Django template tags (antes calculados en JS desde
  `dataLoaded` de Tabulator, ahora ya vienen resueltos en el contexto por
  `get_context_data()` del backend ya existente).
- **4 templates de lista actualizados** (`list_categorias.html`,
  `list_productos.html`, `list_servicios.html`, `list_activos.html`):
  contenedor `#<modelo>-panel` con
  `hx-get/hx-trigger="load, <modelo>-updated from:body"/hx-target=this`
  reemplaza el `#grid-<modelo>` de Tabulator; buscador con
  `hx-get`+`hx-trigger="keyup changed delay:400ms, search"`. Botones de
  "Nuevo X" **sin tocar** (ya usaban HTMX correctamente, no dependían de
  Tabulator).
- **4 archivos `*_list.js` reescritos** (`categorias_list.js`,
  `productos_list.js`, `servicios_list.js`, `activos_list.js`): eliminada
  toda inicialización de Tabulator (columnas, formatters, paginación --
  ahora en `tables.py`/`views.py`, server-side). Se preservó intacta la
  lógica de negocio real de cada uno (validación "producto/activo activo
  → no eliminar" en productos/activos, función `verKardex()` completa en
  productos, mensajes de confirmación específicos) -- solo cambió *cómo*
  se dispara y *a qué elemento* se delega (de `grid.addEventListener` a
  `document.body.addEventListener`, para sobrevivir a los re-renders
  HTMX del panel).
- **1 test nuevo** (`apps/tenant/inventario/tests/test_tablas_htmx.py`,
  6 tests): no existía cobertura previa para las 4 `TableView` (el
  backend se había comiteado sin tests). Regla F31: FALTA COBERTURA
  CRÍTICA → CREAR.

## 4. Bug real #1 — WRONG_LOOKUP: botones enviaban `id`, el backend exige `uuid`

Verificado leyendo el backend antes de escribir el frontend:
`CategoriaItemViewSet.get_object()` (y el mismo patrón en
Producto/Servicio/ActivoFijo ViewSets, todos heredan de
`BaseTenantViewSet` con `lookup_field="uuid"`) resuelve el registro por
**uuid**, no por id entero. El JS Tabulator legacy (`categorias_list.js`
et al., pre-migración) enviaba `data-id="${rowData.id}"` (PK entero) a
`DELETE /categorias/{id}/` y `GET /categorias/gestor-offcanvas/?id={id}`
-- ambos endpoints interpretan ese valor como uuid. **Editar o eliminar
una categoría/producto/servicio/activo desde la grilla estaba roto en
producción** (404/400 garantizado, nunca antes detectado porque nadie
había podido probar el flujo completo end-to-end con datos reales antes
de este pase).

`tables.py` (ya comiteado) **ya usa `data-uuid="{0}" record.uuid`
correctamente** -- el bug ya estaba corregido en el backend preparado,
solo hacía falta conectar el frontend para que el fix tomara efecto. Los
4 `*_list.js` reescritos leen `btn.dataset.uuid` (no `.dataset.id`),
cerrando el bug para las 4 grillas. Test dedicado
(`test_categoria_tabla_boton_acciones_usa_uuid_no_id`) fija el contrato
para que no regrese.

## 5. Bug real #2 — `FieldError` en `ProductoTableView.get_context_data()`

Encontrado por el test nuevo, no por inspección de código: `qs.only(
"stock_actual", "costo_promedio")` en la línea del cálculo de
`kpi_valor_total` re-restringía campos sobre un queryset que YA tenía su
propio `.only(*PRODUCTO_LIST_FIELDS)` (con `categoria__nombre`, que
implica `select_related`) -- Django rechaza un segundo `.only()` que
entra en conflicto con relaciones ya traversadas:
`FieldError: Field Producto.categoria cannot be both deferred and
traversed using select_related at the same time`. **Esto habría
producido un 500 real la primera vez que alguien abriera la pestaña de
Productos en producción** -- otro bug preexistente en el código ya
comiteado, nunca antes ejecutado. Fix: `stock_actual`/`costo_promedio` ya
están en `PRODUCTO_LIST_FIELDS`, así que el segundo `.only()` era
innecesario -- se eliminó, iterando `qs` directamente.

## 6. Simplificación deliberada: sin `rowClick`-to-edit

El Tabulator legacy abría el offcanvas de edición al hacer click en
cualquier parte de la fila (no solo en el botón "Editar"), requiriendo un
flag (`_eliminando<Modelo>`) para evitar que un click de eliminación
disparara también el editor. Los 4 `*_list.js` nuevos **no reproducen
esto** -- solo los botones explícitos abren acciones. Es la decisión ya
consistente con el patrón probado de `bancos`/`gastos` (ningún archivo ya
migrado en el proyecto usa `rowClick`), y elimina la necesidad del flag
de carrera. No es un recorte de alcance oculto: se documenta aquí
explícitamente como cambio de UX deliberado, consistente con el resto de
la base de código ya migrada.

## 7. Verificación

- `manage.py check`: limpio.
- Los 4 nombres de URL resuelven correctamente (`reverse()` bajo
  `TENANT_URLCONF`).
- Los 8 templates tocados/nuevos parsean sin error de sintaxis
  (`get_template()`).
- `test_tablas_htmx.py` (6 tests, incluye creación de registros reales,
  verificación de contenido renderizado, filtro de búsqueda, y el
  contrato uuid): **6/6 passed** tras el fix de `ProductoTableView`
  (§5) -- el primer intento encontró exactamente ese bug real
  (`FieldError`), confirmando el valor de escribir el test antes de
  comitear.
- **No fue posible verificar visualmente en navegador** (misma
  limitación que F31.2 -- sin credenciales de tenant, sin
  `pytest-playwright` instalado). La verificación se apoyó en pruebas
  Django reales (HTTP real contra la vista, con datos reales, no mocks)
  más revisión manual línea por línea de cada archivo JS reescrito contra
  el original.
