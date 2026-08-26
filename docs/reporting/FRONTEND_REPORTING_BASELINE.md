# Reporting Hub Frontend — Baseline (FASE 0)

**Fecha:** 2026-08-26
**Alcance:** infraestructura frontend REAL ya existente que el Reporting Hub Frontend reutiliza. Ninguna de estas piezas se creo en esta mision -- se auditaron primero (Regla Absoluta #5).

---

## 1. Infraestructura compartida ya existente (reutilizada, no duplicada)

| Pieza | Ubicacion | Rol en esta mision |
|---|---|---|
| `Sintel.Core.Http` | `apps/tenant/core/static/core/js/lib/core-http.js` | Unico cliente HTTP del proyecto (F32.7 completo -- el viejo `window.http` fue removido, confirmado en `assets_core.html:9-13`). `reporting.api.js` lo envuelve, no lo reemplaza. |
| `Sintel.Core.UserContext` | `apps/tenant/core/static/core/js/common/user_context.js` | Cache de sede/area/rol/alcance ya resuelto por el backend. Disponible para futuros filtros de sede/area en pantallas de Reportes (no consumido todavia -- el primer dataset, `ventas.resumen`, no tiene campo sede). |
| `Sintel.Core.mostrarOffcanvasSeguro` | `apps/tenant/core/static/core/js/common/offcanvas.helper.js` | No usado en esta pasada (Reportes no abre offcanvas todavia), pero es el helper obligatorio si una fase futura lo necesita. |
| `SintelFeedback` | `apps/tenant/core/static/core/js/utils/feedback.js` | Sistema de toast/alerta sobre SweetAlert2. Referenciado como el mecanismo correcto para errores JS-side (el server-rendered usa sus propios estados, ver §3). |
| `{% sintel_kpi_card %}` | `apps/tenant/core/templatetags/sintel_ui.py` | Card de KPI reutilizable verbatim -- usado en `reportes_ventas.html` sin modificar su markup. |
| `{% sintel_empty_state %}` | idem | Estado vacio reutilizable -- usado para "sin datos". |
| django-tables2 + HTMX | `apps/tenant/ventas/{tables.py,views.py}` + `templates/tenant/ventas/partials/tabla_ventas.html` | Patron de referencia para HTMX (`hx-get`/`hx-trigger`/`hx-target`), NO para la tabla de resultados en si (ver §3, decision de diseño). |
| Sidebar/tabs de workspace | `apps/tenant/core/templates/tenant/core/workspace.html` + `static/core/js/workspace.js` | `data-tab`/`workspace-tab` generico, sin lista hardcodeada -- agregar "Reportes" no requirio tocar JS. |

## 2. Gaps confirmados (no asumidos)

- **Sin libreria de graficos.** Grep exhaustivo de Chart.js/ApexCharts/D3/amCharts/Highcharts en `apps/tenant` -- cero resultados reales. FASE 11 (graficos) queda diferida explicitamente: no se agrega una dependencia nueva sin que un caso real la justifique.
- **Sin patron de exportacion previo.** El unico boton "Exportar" en todo el repo (`apps/tenant/contabilidad/templates/tenant/contabilidad/reporte_page.html:68-70`) es client-side, Tabulator-bound (`.download()` sobre datos ya renderizados en el navegador) -- no golpea ningun endpoint real. La integracion con `POST/GET /api/v1/reporting/export/` es greenfield.
- **`TabulatorFactory` es infraestructura LEGACY**, no el patron a seguir -- usado hoy solo en apps aun no migradas a django-tables2 (Inventario, Cotizaciones, per `documentacion/PLAN_UNICO_CORRECCIONES.md` FASE 5-BIS). Ventas y Proyectos ya migraron; son el patron de referencia real.
- **Sin nav "Reportes" previa** -- ni siquiera como placeholder. Se agrego en esta mision.

## 3. Decision de diseño: tabla de resultados NO usa django-tables2

`django_tables2.Table` declara sus columnas de forma ESTATICA en una clase Python ligada a un modelo/queryset. Un `ReportResult` tiene columnas DINAMICAS (dependen del `group_by` elegido por el usuario en tiempo de request). Generar una `Table` dinamicamente via `type()` por cada request es una complejidad real que esta pasada no justifica con un solo dataset. Se opto por una tabla HTML plana (Bootstrap `table table-sm`), construida en el view Python a partir de `ReportResult.columns`/`.rows` (precomputado como lista de listas para evitar lookup dinamico `row[column]`, no soportado nativamente por el motor de templates de Django). Documentado explicitamente para que una fase futura no lo trate como un descuido.

## 4. Como se valida en vivo (limitacion de entorno)

El navegador sandboxed de esta sesion bloquea (`ERR_BLOCKED_BY_CLIENT`) el burst de ~40 requests que `workspace.html` dispara al cargar TODOS los modulos de golpe -- esto incluye `workspace.js` mismo (el propio motor de cambio de tabs), confirmado que afecta a CUALQUIER tab, no solo a Reportes. Verificacion real usada en su lugar: `curl` con cookie de sesion Django real (creada server-side via shell, mismo patron ya usado en la mision CONT-19) contra las vistas HTML, y `curl` con JWT real contra la API -- ambos con datos reales del tenant `home`. Ver `docs/reporting/FRONTEND_REPORTING_ARCHITECTURE.md` §6 para el detalle completo de lo verificado.
