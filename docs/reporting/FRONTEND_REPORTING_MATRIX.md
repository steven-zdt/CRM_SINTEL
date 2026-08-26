# Reporting Hub Frontend — Matriz Frontend <-> Contrato (FASE 2)

**Fecha:** 2026-08-26

| Pantalla | Componente frontend | Endpoint/vista | Dataset | Filtros usados | Medidas | Scope | Export |
|---|---|---|---|---|---|---|---|
| Catalogo de Reportes | `reportes_landing.js` (`Sintel.Core.ReportesLanding`) | `GET /api/v1/reporting/` (JSON, via `Sintel.Reporting.API.catalog()`) | todos los registrados | — | — | — (catalogo no filtra por scope, cada dataset lo aplica en su propia ejecucion) | — |
| Resumen de Ventas -- contenedor | `reportes_ventas_container.html` | `GET /ui/ventas/reportes/` (Django view, HTML) | `ventas.resumen` | — (solo shell + formulario) | — | — | — |
| Resumen de Ventas -- resultados | `reportes_ventas.html` (partial, HTMX) | `GET /ui/ventas/reportes/tabla/` (Django view, llama `ReportQueryEngine` directamente en Python) | `ventas.resumen` | `fecha_inicio`, `fecha_fin`, `estado`, `group_by` (fecha/cliente/estado) | `cantidad_ventas`, `subtotal`, `impuestos`, `total` (siempre las 4) | `empresa` (via `OrganizationalScope`, resuelto dentro de `ReportQueryEngine.execute()`) | `<a href>` a `GET /api/v1/reporting/export/` (csv, xlsx) via `reportes_ventas.js` |

## Notas sobre el flujo

- La pantalla de Ventas **no pasa por la API JSON del Reporting Hub para la tabla/KPI** -- el view Django (`apps/tenant/ventas/views_reportes.py::VentaReportesView`) llama `ReportQueryEngine().execute(...)` DIRECTO en Python, server-side, y renderiza HTML. Esto es deliberado: sigue el mismo patron ya establecido por `VentaTableView` (server-rendered + HTMX), no introduce un roundtrip HTTP interno innecesario, y sigue cumpliendo Regla Absoluta #4 (la vista consume el dataset registrado via el Query Engine real, nunca ORM directo).
- El **Report API Client JS** (`Sintel.Reporting.API`) SI se usa para: el catalogo (`reportes_landing.js`, JSON real) y para construir la URL de export (`reportes_ventas.js::exportUrl()`, sin round-trip -- solo arma la URL para un `<a href>`).
- Ningun componente frontend construye SQL, nombres de modelo, ni tabla -- todo pasa por `ReportRequest`/`ReportQueryEngine`/`ReportProvider`.
