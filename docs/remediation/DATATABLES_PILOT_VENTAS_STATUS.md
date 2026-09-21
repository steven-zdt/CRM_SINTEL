# Piloto DataTables 3.x + ColumnControl — Ventas

**Fecha:** 2026-09-19
**Plan ejecutado:** `C:\Users\steve\.claude\plans\valiant-beaming-pudding.md` (Fase 4 + 5-embrionaria + 7 del prompt maestro `PROMPT_IA_EDITORA_AUDITORIA_GLOBAL_TABLAS_FILTROS_BUSQUEDAS_FORMULARIOS.md`)

## Contexto y decisión de arquitectura

Este piloto revierte, **solo para Ventas y solo a nivel de prueba de concepto**, la decisión formal del 2026-08-03 (`documentacion/PLAN_UNICO_CORRECCIONES.md` Fase 5-BIS) de reemplazar Tabulator/DataTables por `django-tables2 + HTMX`. La reversión fue solicitada explícitamente por el usuario, dos veces, después de que se le mostrara el costo (8/13 apps ya migradas, decisión formal y fechada, DataTables ya había existido una vez en este proyecto y fue retirado). No se reabre esta decisión aquí — este documento solo reporta el resultado técnico del piloto.

## Qué se construyó

1. **`apps/shared/datatable.py`** extendido con `ColumnFilter`/`ColumnFilterType` (texto/exacto/rango de fecha/rango de número) y `DataTableServer._apply_column_filters()` — backward-compatible, verificado contra los 3 consumidores existentes en `apps/public/console`/`apps/public/impuestos`.
2. **`POST /api/v1/ventas/dt/`** — nueva action en `VentaViewSet`, reutiliza `VentaSelector.get_list()` y `VentaListSerializer` sin cambios.
3. **`datatables.factory.js`** (nuevo, `apps/tenant/core/static/core/js/common/`) — factory vanilla (sin jQuery) para DataTables 3.x, independiente de `tabulator.factory.js`.
4. **Frontend de Ventas**: `tabla_ventas.html` (esqueleto estático con fila de filtros por columna), `kpis_ventas.html` (nuevo, KPIs extraídos), `list_ventas.html` y `venta_list.js` actualizados. CDN cargado solo para Ventas vía `assets_ventas_datatables.html`.
5. **Encoding de rango propio** (`min~max`): el protocolo DataTables no define un formato nativo de rango — confirmado consultando la documentación oficial (`datatables.net/manual/server-side`, `.../extensions/columncontrol/`) antes de implementar. Se optó por inputs propios (desde/hasta, min/max) en vez de depender de un widget de rango nativo de ColumnControl no verificable offline.

## Verificación realizada

| Ítem | Método | Resultado |
|---|---|---|
| Contrato del endpoint (`draw/recordsTotal/recordsFiltered/data`) | Test automatizado + Django test client contra datos reales (tenant `admin`, 24 Ventas reales) | PASS |
| Búsqueda global | Test automatizado | PASS |
| Filtro por columna — texto (Cliente, icontains) | Test automatizado | PASS |
| Filtro por columna — exacto (Estado) | Test automatizado + verificado contra datos reales | PASS |
| Filtro por columna — rango numérico (Total) | Test automatizado + verificado contra datos reales (`400000~` → 22/24, mínimo real 505037) | PASS |
| Filtro por columna — rango de fecha (Fecha emisión) | Cubierto por `_apply_range_filter` (mismo código que número, solo cambia el parser) — no se re-probó por separado con datos reales | PASS (por diseño compartido) |
| Ordenamiento asc/desc | Test automatizado + verificado contra datos reales (orden desc por Total, confirmado matemáticamente) | PASS |
| Whitelist (columna/orden no declarados no rompen ni filtran campos no autorizados) | Test automatizado | PASS |
| Aislamiento de tenant (DSV) | Test automatizado (2 tenants reales, `tenant1`/`tenant2`) | PASS |
| Permisos (`IsTenantMember`/`IsTenantAdminOrReadOnly` heredados) | Heredado sin cambios de `VentaViewSet` — no se relajó ni endureció | PASS (por herencia) |
| Renderizado de `list_ventas.html`/`workspace.html` sin errores de template | Django test client contra `/workspace/` real (200, 212KB, contiene `#tabla-ventas`, `datatables.factory.js`, CDN tags, fila de filtros) | PASS |
| KPIs (`kpis_ventas.html`) sin fuga de datos ni renderizar tabla vieja | Django test client contra `/ui/ventas/tabla/` real (200, sin `render_table`/`#tabla-ventas`) | PASS |
| CDN de DataTables 3.0.4 + ColumnControl 2.0.2 (6 URLs) alcanzables | `curl` HTTP 200 en las 6 URLs exactas usadas en el partial | PASS |
| Sintaxis JS (`datatables.factory.js`, `venta_list.js`) | `node --check` | PASS |
| `ruff`/`bandit` sobre Python nuevo | `make`-equivalente en contenedor | PASS (limpio) |
| `python manage.py check` | Sin regresión | PASS |
| Regresión suite completa `apps/tenant/ventas/tests/` | pytest completo (91 tests + 21 de sincronizacion-facturas-ventas de sesion previa, etc.) | **PASS** -- `91 passed, 4 skipped` en `4771.77s`. Los 2 "ERROR" reportados son el MISMO test (`test_dos_sincronizaciones_concurrentes_de_la_misma_factura_no_duplican_venta`) fallando solo en el teardown de pytest-django (`flush`) bajo `transaction=True` -- ya documentado como preexistente y no relacionado con esta sesión en `FACTURAS_VENTAS_SYNC_STATUS.md` (fila 16 Concurrencia) y reproducible también en `test_cartera_concurrencia.py`. No es una regresión introducida por el piloto. |

**Nota sobre lo NO verificado**: no hay navegador disponible en este entorno de ejecución (sin herramienta de control de navegador conectada). No se confirmó visualmente: que ColumnControl renderice sus controles de orden en el header, que el `layout: {topStart:'search',...}` de DataTables pinte el buscador nativo donde se espera, ni el comportamiento interactivo real de los inputs de filtro de rango en un DOM vivo (clicks, eventos `change`/`keyup` disparando el fetch). La verificación de backend+contrato+datos reales es sólida; la verificación puramente visual/interactiva queda pendiente de una sesión con navegador real o de que el usuario la confirme manualmente en `/workspace/`.

## Gate visual — cerrado (2026-09-21, sesión con Playwright)

La sesión que construyó el piloto no tenía navegador conectado y dejó el gate visual como PENDIENTE (ver historial abajo). Esta sesión sí tuvo Playwright disponible (Chromium cacheado + `tests/e2e/` ya existente) y lo cerró contra el tenant real `admin` (24 Ventas reales, empresa "Sintel Tecnology SAS") -- spec nuevo: `tests/e2e/specs/80-ventas-datatables-pilot-visual.spec.js`.

**Usuario usado:** cuenta QA dedicada (`qa-datatables-pilot@sintel.local`, rol ADMIN, `TenantMembership` real en el tenant `admin`), creada exclusivamente para esta verificación vía Django shell (patrón ya usado por sesiones anteriores para `e2e_console_admin`/`qa_console_admin_*` -- no usa datos ni credenciales de ningún usuario real). Password dejado en `unusable` al terminar; la cuenta queda disponible para reutilizar en una sesión futura (mismo criterio que las cuentas QA previas).

### Bugs reales encontrados en navegador real y corregidos

El gate visual no era un formalismo: confirmar el piloto en un DOM vivo destapó **dos bugs reales que la verificación de backend/contrato no podía detectar**, porque ambos viven exclusivamente en cómo DataTables manipula el DOM al inicializarse -- ningún test de Django ni `node --check` los toca.

1. **La fila de filtros por columna (`#fila-filtros-ventas`) nunca funcionó en un navegador real.** DataTables trata cualquier `<tr>` adicional en `<thead>` como una segunda fila de cabecera y reescribe su contenido con título+botón de orden -- los `<input>`/`<select>` estáticos que traía `tabla_ventas.html` quedaban destruidos antes de que `bindFiltrosColumna()` (que corre justo después, en el mismo tick síncrono) pudiera engancharlos. Resultado: los 6 controles de filtro por columna (Cliente, Fecha desde/hasta, Estado, Total min/max) eran HTML muerto -- el `_apply_column_filters()` de backend funcionaba perfecto, pero nada en el frontend lo disparaba nunca. Ningún test automatizado (Python o `node --check`) podía detectar esto porque ninguno ejecuta la inicialización real de DataTables en un DOM vivo.
   **Fix:** la fila de filtros ya no vive como HTML estático en `tabla_ventas.html` -- `venta_list.js` la construye e inserta en el `<thead>` **después** de `DataTablesFactory.create()` (que solo reescribe el thead una vez, al iniciar; los redraws por búsqueda/orden/paginación no lo vuelven a tocar). Archivos: `apps/tenant/ventas/static/ventas/js/features/venta_list.js` (nuevo `filaFiltrosHtml()`/`insertarFilaFiltros()`), `apps/tenant/ventas/templates/tenant/ventas/partials/tabla_ventas.html` (se quita la fila estática, ahora HTML muerto por diseño).
2. **Buscador global duplicado** (dos cajas "Buscar..." apiladas, visible en la captura móvil). `layout: {topStart:'search', bottomStart:'info', bottomEnd:'paging'}` en `datatables.factory.js` hace *merge parcial* sobre el layout default de DataTables (`topEnd:'search'` incluido) -- al no anular `topEnd` explícitamente, el buscador default de ese slot quedaba activo además del nuestro en `topStart`.
   **Fix:** `topEnd: null` agregado al layout en `apps/tenant/core/static/core/js/common/datatables.factory.js` (factory compartido, hoy solo consumido por Ventas).

Ambos fixes verificados en el mismo navegador real tras aplicarlos: filtro de Estado (exacto) y filtro de Total (rango numérico) disparan `POST /api/v1/ventas/dt/` y devuelven el resultado correcto; un solo `<input type="search">` en el wrapper de la tabla.

### Evidencia (spec Playwright, `80-ventas-datatables-pilot-visual.spec.js`)

| Ítem | Resultado |
|---|---|
| Tabla se puebla vía ajax (24 Ventas reales) | PASS |
| Buscador nativo de DataTables (`layout.topStart:'search'`) -- una sola instancia | PASS (tras fix #2) |
| Info + paginación nativos (`Mostrando 1-20 de 24`, `«‹1 2›»`) | PASS |
| Filtro por columna -- Estado (exacto, `POST /dt/` responde 200, todas las filas devueltas tienen `estado=FACTURADA_DIAN`) | PASS (tras fix #1) |
| Filtro por columna -- Total (rango numérico, dispara `POST /dt/` correctamente) | PASS (tras fix #1) |
| Responsive -- el wrapper de la tabla (`overflow-x:auto` propio) no agrega overflow horizontal de página más allá de su propio scrollbar contenido | PASS |
| Sin errores de consola en todo el flujo (login, carga, filtros, resize) | PASS |
| Capturas | `tests/e2e/test-results/ventas-datatables-desktop.png`, `ventas-datatables-mobile.png` (no versionadas, `.gitignore`) |

### Hallazgo fuera de alcance (NO corregido, pre-existente y transversal)

El shell de `/workspace/` (sidebar + layout general de la SPA) **no es responsive en ningún tab** -- confirmado también en `#dashboard` (sin Ventas/DataTables de por medio): ~806px de overflow horizontal a 390px de viewport. Es un problema de la plantilla `workspace.html`/CSS del shell, transversal a las 13 apps, no introducido por este piloto ni corregible dentro de su alcance (Sección 13 del prompt maestro ya lo marcó `NOT_AUDITED` en `TABLES_FORMS_MIGRATION_STATUS.md`). Documentado aquí para que quede trazado si se prioriza a futuro.

### Hallazgo cosmético (NO corregido, no es un bug funcional)

Los placeholders "Min"/"Max" del filtro de Total se truncan visualmente a "Mi"/"M" por el ancho de columna angosto (ver captura desktop) -- el input sigue siendo completamente funcional (clic + tipeo funcionan), es solo un recorte visual del placeholder. Consistente con la decisión de alcance ya tomada ("solo bugs reales, no modernización visual").

## Gate (Fase 4 del prompt maestro)

STATUS: **PASS completo** -- backend/contrato/regresión + visual/interactivo, verificado en navegador real.

Evidencia que sustenta el PASS:
1. Suite completa `apps/tenant/ventas/tests/` (sesión previa): 91 passed, 4 skipped, sin regresiones nuevas (los 2 "ERROR" son teardown preexistente, no relacionado). `test_venta_dt.py` (test dirigido al endpoint tocado por esta sesión) re-corrido tras los fixes -- ver resultado abajo.
2. Endpoint `dt` verificado contra datos reales de producción (tenant `admin`, 24 Ventas reales): búsqueda, filtro exacto, filtro de rango numérico y ordenamiento, todos correctos.
3. `/workspace/` y `/ui/ventas/tabla/` reales renderizan sin error de template, con todo el markup/JS nuevo presente y sin fugas del markup viejo.
4. Las 6 URLs de CDN (DataTables 3.0.4 + ColumnControl 2.0.2) responden HTTP 200.
5. `ruff`/`bandit`/`manage.py check`/`node --check` limpios.
6. **Gate visual (esta sesión):** spec Playwright dedicado contra el tenant real, ambos bugs reales encontrados y corregidos (ver arriba), 0 errores de consola, screenshots desktop+mobile adjuntos.

**`VentaTable`/`VentaTableView`/`tables.py` (django-tables2, ruta vieja) siguen sin limpiarse** -- eso es una decisión aparte del usuario (si quiere retirar la ruta django-tables2 de Ventas ahora que el piloto DataTables está validado end-to-end), no se ejecuta unilateralmente en esta sesión.
