# Reporting Hub Frontend — Arquitectura

**Fecha:** 2026-08-26
**Estado:** FRONTEND_REPORTING = COMPLETED_WITH_DEFERRED (ver §9)

---

## 1. Principio central

El frontend **solicita, presenta, filtra dentro de parametros permitidos, visualiza, exporta y navega**. El backend **autoriza, calcula, agrega, aplica scope y valida**. Ningun componente frontend construido en esta mision toca un modelo Django, arma SQL, ni decide que datos son visibles mas alla de mostrar/ocultar lo que el backend ya autorizo.

## 2. Componentes construidos

| Componente | Archivo | Rol |
|---|---|---|
| Report API Client | `apps/tenant/core/static/core/js/common/reporting.api.js` (`window.Sintel.Reporting.API`) | `catalog()`, `detail(id)`, `query(params)`, `exportUrl(params)` -- unico cliente para `/api/v1/reporting/`, ningun app tiene su propio `<app>ReportAPI.js` |
| Reportes Landing (catalogo) | `apps/tenant/core/templates/tenant/core/reportes_landing.html` + `static/core/js/reportes_landing.js` (`window.Sintel.Core.ReportesLanding`) | Lista datasets REALES (via `catalog()`), agrupa por `owner_app`, enruta al reporte especifico via HTMX si existe pantalla propia |
| Reporte Ventas -- contenedor | `apps/tenant/ventas/views_reportes.py::VentaReportesContainerView` + `templates/tenant/ventas/reportes_ventas_container.html` | Filtros (fecha/estado/agrupar) + panel HTMX-refrescado + enlaces de export |
| Reporte Ventas -- resultados | `apps/tenant/ventas/views_reportes.py::VentaReportesView` + `templates/tenant/ventas/partials/reportes_ventas.html` | Llama `ReportQueryEngine` DIRECTO (server-side), renderiza KPI (`sintel_kpi_card`) + tabla HTML plana + estados (datos/vacio/prohibido/invalido) |
| Nav "Reportes" | `apps/tenant/core/templates/tenant/core/workspace.html` (sidebar + `#tab-reportes`) | Entrada unica, sin tocar `workspace.js` (patron `data-tab` generico ya soporta cualquier tab nueva) |
| Export GET | `apps/services/reporting/api/viewsets.py::export_report` (+`_parse_export_query_params`) | Soporta GET (descarga directa via `<a href>`, sin JS) ademas del POST JSON ya existente |

## 3. Flujo real

```
Usuario hace clic en "Reportes" (sidebar)
    v
reportes_landing.js -- Sintel.Reporting.API.catalog() [JSON real]
    v
Usuario hace clic en "Ver reporte" (Ventas)
    v
HTMX GET /ui/ventas/reportes/  -->  VentaReportesContainerView
    v
Formulario dispara (load/submit/change) GET /ui/ventas/reportes/tabla/
    v
VentaReportesView -- ReportQueryEngine().execute(ReportRequest, request)  [Python directo, server-side]
    v
ReportResult -- KPI cards (sintel_kpi_card) + tabla HTML
    v
Usuario hace clic en "Exportar CSV/XLSX" (<a href>, URL armada por reporting.api.js)
    v
GET /api/v1/reporting/export/?dataset_id=...&export_format=csv  -->  descarga real del navegador
```

## 4. Report State (FASE 4)

No se construyo una maquina de estados JS generica -- con un solo flujo real (Ventas, server-rendered), los estados se resuelven en el VIEW Python y se pasan al template como contexto simple:

- **datos**: `result` presente, `is_empty=False` -> KPI + tabla.
- **vacio**: `is_empty=True` -> `{% sintel_empty_state %}`.
- **prohibido**: `error_kind='forbidden'` (capturado de `ScopeViolationError`) -> alerta amarilla, "Sin permisos para consultar este reporte en el alcance seleccionado."
- **invalido**: `error_kind='invalid'` (capturado de `ReportValidationError`) -> alerta roja, "No fue posible generar el reporte. Verifica los filtros seleccionados."

Ninguno de estos estados expone stack traces, SQL, ni nombres de modelos (FASE 7/28) -- verificado leyendo el render de los 3 estados directamente (`render_to_string`, ver §6).

Cuando exista un SEGUNDO flujo real orientado a JS (no server-rendered), se generalizara `Report State` a un modulo JS compartido -- construirlo ahora, sin un segundo consumidor real, seria anticipar necesidad sin evidencia (Regla Absoluta #7 del Reporting Hub backend, aplicada aqui por extension).

## 5. Filtros, KPI, tabla, export -- decisiones

- **Filtros** (FASE 5): declarados por dataset (`ventas.resumen` expone `fecha_inicio`, `fecha_fin`, `estado`, `cliente_id`) -- el formulario de Ventas solo muestra los que el dataset soporta. `sede`/`area` NO se muestran porque `Venta` no tiene esos campos (verificado, no asumido).
- **KPI** (FASE 10): `{% sintel_kpi_card %}`, valores tomados de `ReportResult.totals` -- CERO calculo en JavaScript.
- **Tabla** (FASE 9): HTML plana server-rendered, ver justificacion en `FRONTEND_REPORTING_BASELINE.md` §3 (columnas dinamicas, no encajan en `django_tables2.Table` estatica).
- **Graficos** (FASE 11): NO construidos. Sin libreria de charts instalada (confirmado, baseline §2) y sin evidencia de que una tabla+KPI sea insuficiente para el unico dataset real disponible.
- **Export** (FASE 12): un solo endpoint (`/api/v1/reporting/export/`), consumido por `<a href>` simple -- nunca se creo `export_ventas()`/`export_facturas()`.

## 6. Verificacion en vivo (con datos reales)

Sandbox de navegador de esta sesion bloquea el burst de requests de `workspace.html` (incluye `workspace.js` mismo, afecta CUALQUIER tab) -- ver `FRONTEND_REPORTING_BASELINE.md` §4. Verificacion real usada:

| Verificacion | Metodo | Resultado |
|---|---|---|
| Contenedor Ventas renderiza | `curl` + cookie de sesion real | 200, formulario + panel presentes |
| Resultados con datos reales | `curl` + cookie de sesion real, `?group_by=estado` | KPI correctos ($20,000 subtotal, $3,800 impuestos, $23,800 total) + fila real |
| Estados vacio/prohibido/invalido | `render_to_string()` directo (shell) | Los 3 renderizan sin excepcion, mensajes correctos, sin stack traces |
| Export GET csv/xlsx | `curl` + JWT real | csv: texto correcto con fila TOTAL; xlsx: `Content-Type` correcto, archivo real no vacio |
| Archivos JS servidos | `curl` a cada `/static/.../*.js` | 200 en los 3 (`reporting.api.js`, `reportes_landing.js`, `reportes_ventas.js`) |
| `manage.py check` | local venv | limpio |

## 7. Bug real encontrado y corregido durante esta mision

**Colision de nombre con el parametro reservado `format` de DRF.** El endpoint de export aceptaba `?format=csv/xlsx` via GET. `rest_framework.negotiation.DefaultContentNegotiation.filter_renderers()` intercepta el query param `format` (setting `URL_FORMAT_OVERRIDE`, default `'format'`) para SU PROPIA negociacion de contenido, y levanta `Http404` -- no `406` -- cuando el valor no coincide con ningun renderer registrado (`json`/`api`). Efecto real: **todo enlace de descarga `<a href>` habria devuelto 404 silencioso para cualquier usuario**, mientras que el mismo valor via POST (JSON body, fuera de `query_params`) funcionaba perfectamente -- lo que hizo el bug especialmente dificil de sospechar sin probar el camino GET real. Confirmado en vivo (curl) antes y despues del fix. Corregido: el parametro se renombro a `export_format` en el serializer, el parser de query params, y el cliente JS (`reporting.api.js`). Test de regresion agregado (`test_export_get_con_export_format_csv_funciona`, mas un test explicito documentando que `?format=` sigue sin funcionar por diseño de DRF).

## 8. Deuda diferida (explicita, no oculta)

| Item | Por que se difiere |
|---|---|
| Datasets/pantallas de Inventario, Facturas, Gastos, Clientes, Proveedores, Empleados (FASE 16-20) | Solo `ventas.resumen` tiene pantalla propia esta pasada -- el patron (`ver §3`) es mecanicamente replicable, documentado en `docs/reporting/REPORTING_ARCHITECTURE.md` §8 (loop de expansion del backend, aplica igual al frontend) |
| Sub-tab de Reportes DENTRO de cada app (ej. Ventas > Reportes como pestaña interna) | Se opto por una entrada UNICA transversal (`#tab-reportes`) en vez de tocar `list_ventas.html` -- cero riesgo de regresion en una pantalla existente y real, y coincide con el diseño explicito de FASE 13 ("Crear una entrada comun") |
| Graficos (FASE 11) | Sin libreria instalada, sin evidencia de necesidad |
| Ejecucion asincrona / UI de progreso (FASE 29) | El backend mismo no tiene `ReportExecution` todavia (diferido en `REPORTING_ARCHITECTURE.md` backend §9) -- nada que integrar en el frontend |
| Responsive/accesibilidad exhaustivos (FASE 25-26) | El markup reutiliza `sintel_kpi_card`/Bootstrap grid ya responsive por diseño (usado en produccion en Dashboard/Ventas), pero no se hizo una pasada de auditoria dedicada de accesibilidad en esta mision |
| Migracion de Contabilidad/Dashboard (FASE 21-22) | Explicitamente fuera de alcance por regla de la mision (Contabilidad) y por alto riesgo/bajo beneficio sin mas de un dataset probado (Dashboard) |

## 9. Release Gate

**Ventas** — `FRONTEND_REPORTING_COMPLETED`:
- [x] Report API integrado (catalogo + export URL)
- [x] Dataset correcto (`ventas.resumen`)
- [x] Scope (`OrganizationalScope`, vía `ReportQueryEngine`)
- [x] Filtros (declarados por el dataset, no inventados)
- [x] Tabla
- [x] KPI
- [ ] Grafico -- diferido, sin necesidad evidenciada
- [x] Export (csv, xlsx)
- [x] Estados (datos/vacio/prohibido/invalido)
- [x] Errores normalizados, sin detalle tecnico expuesto
- [ ] Responsive/accesibilidad -- reutiliza componentes ya responsive, sin auditoria dedicada
- [x] Sin duplicacion (Report API Client unico, sin `ventasReportAPI.js`)
- [x] Documentacion

**Resto de apps**: pendientes (ver §8).

## 10. Estado final

**FRONTEND_REPORTING = COMPLETED_WITH_DEFERRED**

El nucleo transversal (Report API Client, catalogo, patron de pantalla server-rendered, export real) esta completo y probado con datos reales de punta a punta para un dataset (`ventas.resumen`). El patron queda documentado y es mecanicamente replicable para el resto de apps sin volver a auditar arquitectura. No se declara `PRODUCTION_READY` -- no es un estado que esta mision evalue.
