# REPORTE FASE 5-BIS — Ventas (Tabulator → django-tables2)

**Fecha:** 2026-08-04
**Alcance:** `PLAN_UNICO_CORRECCIONES.md` §"FASE 5-BIS", tercera app de la expansion por prioridad-dinero (`facturas`, `contabilidad`, **`ventas`**, `compras`).
**Estado: 1 de 1 grilla real migrada.** El plan original listaba "3 archivos" (`venta_list.js`, `resolucion_list.js`, `orden_list.js`) para esta app; la investigacion previa a tocar codigo encontro que **solo 1 de los 3 esta realmente vivo** — ver §1.

---

## 0. Hallazgo previo: 2 de los 3 archivos listados no estan en uso

Antes de migrar nada se verifico, para cada uno de los 3 archivos que el plan asignaba a `ventas`, cual es su contenedor DOM objetivo y si ese contenedor existe en algun template incluido desde `workspace.html` (el shell que agrupa todas las apps del tenant):

| Archivo | Contenedor objetivo | ¿Vivo? |
|---|---|---|
| `venta_list.js` | `#grid-listado-ventas` en `list_ventas.html` | **Si** — `list_ventas.html` se incluye en `workspace.html` linea 101. Unico grid real de esta app. |
| `orden_list.js` | `#grid-ventas` en `list_ordenes.html` | **No.** `list_ordenes.html` no tiene ningun `{% include %}` en todo el repo (grep confirmado). El script `orden_list.js` tampoco se carga desde ningun `assets_*.html` — ni siquiera se ejecuta. |
| `resolucion_list.js` | `#grid-resoluciones` | **No, pero se carga.** El script SI esta en `assets_ventas.html` (se ejecuta en cada carga de pagina), pero `#grid-resoluciones` no existe en ningun template de `ventas` — las Resoluciones DIAN ya se gestionan via `panel_resoluciones.html`, un offcanvas con una tabla HTML plana renderizada por Django (`{% for r in resoluciones %}`), sin Tabulator, sin paginacion. `resolucion_list.js` inicializa, no encuentra su contenedor, y no hace nada (`if (!container) return`) — codigo cargado pero inerte. |

**Decision: no se toco `orden_list.js` ni `resolucion_list.js`.** Motivo para no borrarlos pese a estar inertes (a diferencia del criterio usado en Fase 6 para dead-code): los commits mas recientes del repositorio en el momento de este trabajo son literalmente `feat(ventas): app OrdenVenta completa v3.10.5 - FASES 1-5` y `feat(workspace): agrega menu Ventas al sidebar` — evidencia de que el modulo "Orden de Venta" es trabajo **reciente y en progreso**, no arquitectura abandonada hace semanas (que es el criterio que si justifico borrar 50 archivos en Fase 6). Ademas, `orden_editor.js` (que si esta enlazado desde `offcanvas_crear_orden.html`) llama a `w.Sintel.Ventas.List.recargar()`, compartiendo namespace con el `List` que este reporte migra — tocar o borrar esos archivos sin visibilidad de hacia donde va ese trabajo habria sido una decision de producto disfrazada de limpieza tecnica. Queda documentado aqui para que el usuario decida su destino (completar la wiring de OrdenVenta, migrar tambien esa grilla a `django-tables2` cuando este lista, o retirarla) — no se asumio ninguna de las tres opciones.

## 1. Grilla migrada: Ventas (`Venta`)

**Archivos nuevos:**
- `apps/tenant/ventas/tables.py` — `VentaTable` (columnas: cliente con NIT, fecha, estado con badge, factura DIAN, total, ver-detalle).
- `apps/tenant/ventas/views.py` — `VentaTableView(LoginRequiredMixin, SintelDSVMixin, SingleTableView)`, reutiliza `VentaSelector.get_list(empresa_id, search, estado)` que **ya soportaba** ambos filtros (no hubo que tocar el Service Layer). KPIs (total, monto, borradores, facturadas) resueltos con `.count()`/`.aggregate(Sum(...))` sobre el queryset ya filtrado, igual que en `compras`.
- `apps/tenant/ventas/urls.py` (nuevo — la app no tenia rutas de UI propias, todo pasaba por `/api/v1/ventas/` directamente) — una sola ruta `tabla/`.
- `apps/tenant/ventas/templates/tenant/ventas/partials/tabla_ventas.html` — KPIs + `{% render_table table %}`, empaquetados juntos (mismo patron que `compras`: los 4 KPI-cards que antes vivian estaticos en `list_ventas.html` y se llenaban por JS en el callback `dataLoaded` de Tabulator ahora se recalculan server-side y se re-renderizan junto con la tabla en cada `hx-get`).
- `config/urls_tenant.py`: agregada `path('ui/ventas/', include('apps.tenant.ventas.urls', namespace='ventas'))` (no existia ningun prefijo `ui/ventas/` antes de esta fase).

**Archivos modificados:**
- `list_ventas.html`: los 4 KPI-cards estaticos se movieron a `tabla_ventas.html` (se recalculan en cada carga en vez de quedar desactualizados hasta el proximo `dataLoaded`); el input de busqueda y los 4 pills de filtro por estado pasan de JS/`ajaxParams` a `hx-get`/`hx-include` (los botones de estado usan `name="estado" value="X"` — htmx incluye automaticamente el par name/value del elemento disparador); `#grid-listado-ventas` (vacio, poblado por Tabulator) se reemplaza por `#ventas-panel` (`hx-get`/`hx-trigger="load, venta-updated from:body"`); se eliminaron el spinner y el empty-state manuales (redundantes: `django-tables2` ya maneja el estado vacio via `Meta.empty_text`); se limpio el CSS scoped `.tabulator` (selectores muertos, ya no aplica ninguna clase de Tabulator) dejando solo lo que sigue siendo relevante (`.badge-sm`, `.btn-xs`).
- `venta_list.js`: reducido de 313 a ~70 lineas. Se elimina toda inicializacion de Tabulator, columnas, formatters, `dataLoaded`/`dataFiltered`, el listener `tab-activated` (ya no aplica, HTMX se encarga del redraw via `hx-trigger`), y el patron "Anti-Zombies" (`_SintelVentasTable.destroy()`, ya no existe instancia de Tabulator que destruir). Se conserva: `List.recargar()`/`List.reload()` (misma firma que `venta_editor.js` ya invocaba, ahora dispara `CustomEvent('venta-updated')` en `document.body`), `List.abrirDetalle(uuid)` (sin cambios, sigue usando HTMX contra el offcanvas), delegacion de evento click sobre `#ventas-panel` para el boton "ver detalle", y el toggle visual `.active` de los pills de estado (ahora solo estetico -- la carga real de datos la dispara el propio `hx-get` del boton).
- `venta_editor.js`: **no se toco** — ya llamaba a `w.Sintel.Ventas.List.recargar()` con la misma firma, sigue funcionando sin cambios.

**Test nuevo:** `test_multitenant_isolation_ventas_tabla_html` agregado a `apps/tenant/ventas/tests/test_multitenant_isolation.py` (que ya existia con cobertura API de 3 niveles -- listado/IDOR-detalle/IDOR-FK -- pero nada sobre la vista HTML nueva, que no pasa por DRF).

## 2. Verificacion

Misma limitacion de entorno de toda la sesion (sin Docker/venv funcional): verificado con `python -m py_compile` (`tables.py`, `views.py`, `urls.py`, `config/urls_tenant.py`, `test_multitenant_isolation.py` — todos OK) y `node --check` (`venta_list.js` — OK). Grep de `grid-listado-ventas` en todo el árbol confirma cero referencias colgantes tras el reemplazo.

**Antes de dar esta migracion por validada en runtime**, incluir en el batch de validacion final (ya definido para el resto de Fase 5-BIS):
```
pytest apps/tenant/ventas/tests/test_multitenant_isolation.py -v
```
y abrir manualmente el modulo Ventas en el workspace: buscar, filtrar por pill de estado, paginar, ordenar por columna, crear una venta y confirmar que la tabla se refresca (`venta-updated`), y ver-detalle desde la fila.

## 3. Progreso de la expansion Fase 5-BIS (actualizado)

| App | Estado |
|---|---|
| `gastos` | Migrado (piloto) |
| `facturas` | Migrado |
| `compras` | Migrado |
| `contabilidad` | Migrado 5/8 grillas (3 fuera de alcance deliberado) |
| `ventas` | Migrado 1/1 grilla real (2 archivos del plan original resultaron ser codigo no conectado — ver §0) |
| resto (~13 apps) | Pendiente |
