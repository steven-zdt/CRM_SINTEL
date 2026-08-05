# REPORTE FASE 5-BIS — Contabilidad (Tabulator → django-tables2)

**Fecha:** 2026-08-04
**Alcance:** `PLAN_UNICO_CORRECCIONES.md` §"FASE 5-BIS", segunda app de la expansion por prioridad-dinero (`facturas`, **`contabilidad`**, `ventas`, `compras`).
**Estado: 5 de 8 grillas migradas.** Las 3 restantes (`pendientes`, `libro-diario`, `reportes`) quedan explicitamente fuera de este patron — ver §2.

---

## 0. Contexto especifico de esta app

A diferencia de `gastos`/`facturas`/`compras` (paginas propias), **toda la UI de contabilidad vive como sub-tabs dentro de `apps/tenant/core/templates/tenant/core/workspace.html`** (el shell SPA-like que agrupa TODAS las apps del tenant, no solo contabilidad). Esto se confirmo antes de tocar nada: `list_cuentas.html` no es una pagina, es un `{% include %}` dentro de `#subtab-cuentas`, un Bootstrap tab-pane anidado dentro de la seccion `#tab-contabilidad` (a su vez oculta con `display:none` hasta que el usuario abre el modulo). El patron HTMX ya usado por `compras`/`gastos`/`facturas` (`hx-trigger="load, <evento> from:body"` en el panel) sigue funcionando igual en este contexto — se mantuvo la misma convencion en vez de introducir un mecanismo de carga perezosa distinto solo para esta app.

## 1. Grillas migradas (5/8)

| Grilla | Modelo | Archivos nuevos/tocados |
|---|---|---|
| Cuentas Contables | `CuentaContable` | `tables.py::CuentaContableTable`, `views.py::CuentaContableTableView`, `tabla_cuentas.html`, `list_cuentas.html`, `cuenta_list.js` |
| Periodos Contables | `PeriodoContable` | `tables.py::PeriodoContableTable`, `views.py::PeriodoContableTableView`, `tabla_periodos.html`, `list_periodos.html`, `periodo_list.js` |
| Asientos Contables | `AsientoContable` | `tables.py::AsientoContableTable`, `views.py::AsientoContableTableView`, `tabla_asientos.html`, `list_asientos.html`, `asiento_list.js` |
| Retenciones (solo lectura) | `Retencion` | `tables.py::RetencionTable`, `views.py::RetencionTableView`, `tabla_retenciones.html`, `list_retenciones.html`, `retencion_list.js` |
| Plantillas Contables | `PlantillaContable` | `tables.py::PlantillaContableTable`, `views.py::PlantillaContableTableView`, `tabla_plantillas.html`, `list_plantillas.html`, `plantilla_list.js` |

Un solo `apps/tenant/contabilidad/tables.py` y un solo `apps/tenant/contabilidad/views.py` nuevos, con una clase por grilla cada uno (no se crearon 5 pares de archivos — la app ya es un modulo grande con muchos submodulos JS, un solo `tables.py`/`views.py` es mas facil de mantener que 5 pares dispersos).

**Patron replicado identico al de `compras`/`gastos`/`facturas`:**
- `tables.py`: `django_tables2.Table` por modelo, columna `acciones` con botones `data-uuid` (no PK entero — algunas vistas Tabulator anteriores usaban `data-id` con el PK entero; se normalizo a `data-uuid` en todas, que es lo que exige `CLAUDE.md` — "UUID lookup, not PK". Los endpoints de `render-offcanvas`/`cerrar`/`aprobar`/`delete` ya aceptaban ambos via `get_*_by_identifier()`/`mutation_lookup_fields`, asi que el cambio es compatible sin tocar la API).
- `views.py`: `SingleTableView` + `LoginRequiredMixin` + `SintelDSVMixin.get_empresa_id()` (misma fuente de aislamiento que `BaseTenantViewSet`), reutilizando los Selectors ya existentes (`CuentaContableSelector`, `PeriodoContableSelector`, `PlantillaContableSelector`) mas filtros de busqueda/estado aplicados en la vista (no se toco el Service Layer).
- Templates `list_*.html`: el `<div id="grid-X">` vacio (poblado antes por Tabulator) se reemplaza por `<div id="X-panel" hx-get=... hx-trigger="load, X-updated from:body" hx-target="this" hx-boost="true">`. Los inputs de busqueda y los `<select>` de filtro pasan a usar `hx-get`/`hx-trigger="change"`/`hx-include` en vez de `ajaxParams` de Tabulator.
- JS `*_list.js`: se elimina toda inicializacion de Tabulator/columnas/formatters. Cada archivo queda reducido a: delegacion de eventos sobre el panel persistente (ver/editar/eliminar/acciones especiales como cerrar-periodo o aprobar-asiento) y un `reload()` que dispara un `CustomEvent` en `document.body` (mismo nombre que el `hx-trigger` del panel). Los `*_editor.js` de cada submodulo (`cuenta_editor.js`, `periodo_editor.js`, `asiento_editor.js`, `plantilla_editor.js`) **no se tocaron** — ya llamaban a `w.XList.reload()` con la misma firma, siguen funcionando sin cambios.

**Casos especiales resueltos en `tables.py`/`views.py` (no triviales, documentados por columna):**
- `AsientoContableTable.cuadratura`: columna calculada comparando `total_debe`/`total_haber` por fila (antes se calculaba en JS). El filtro `?cuadratura=cuadrado|no_cuadrado` se resuelve server-side con `Q(total_debe=F(total_haber))`, reemplazando el filtro client-side que antes solo operaba sobre la pagina cargada (bug latente de Tabulator: paginacion remota + filtro client-side solo filtraba la pagina visible, no el dataset completo — el reemplazo server-side es mas correcto, no solo una migracion 1:1).
- `AsientoContableTableView`: `movimientos_count` se resuelve con `.annotate(Count("movimientos", distinct=True))` en vez de `prefetch_related` (que traeria todas las filas de `MovimientoContable` solo para contar) — evita N+1 sin sobre-cargar datos no usados por la tabla.
- `PlantillaContableTable.lineas_count`/`modo`: mismo critero que `PlantillaContableListSerializer.get_lineas_count`/`get_modo` (paridad exacta con la API), pero resuelto con `.annotate(Count("lineas", distinct=True))` en la vista en vez de `obj.lineas.count()` por fila (que en la API es aceptable por paginacion pequeña, pero en una tabla de 20 filas por pagina evita 20 queries extra).
- `RetencionTable`: sin columna `acciones` -- las retenciones son de solo lectura (Pull Model, `RetencionesService`), tal como ya indicaba el comentario original en `list_retenciones.html`. `retencion_list.js` quedo casi vacio (sin Tabulator no hay nada que inicializar; se conserva solo el export de `reload()` por consistencia con el resto de submodulos).

## 2. Fuera de alcance deliberado: `pendientes`, `libro-diario`, `reportes`

Estas 3 grillas **no son listados CRUD planos** sobre un solo modelo — son vistas agregadas/cross-app:
- **Pendientes** (`qs_facturas_pendientes`, `qs_gastos_pendientes`, `qs_nominas_pendientes`, `qs_inventario_movimientos_recientes_pendientes`): combina filas heterogeneas de 4 apps distintas (Factura, DocumentoSoporte, Devengo, movimientos de Inventario) en una sola lista, cada una con su propio shape de datos.
- **Libro Diario** (`get_libro_diario_periodo`): consolida `DocumentoEnriquecido` de 3 extractores (`ExtractorFacturas`, `ExtractorGastos`, `ExtractorNomina`), no es un QuerySet de un modelo Django — es una lista de objetos de dominio construidos en Python.
- **Reportes** (`balance_prueba_selector`, `estado_resultados_selector`): retornan listas de `dict` con totales jerarquicos (saldo anterior, debito/credito del periodo, nuevo saldo) agrupados por cuenta — mas cercano a un reporte financiero con subtotales que a una tabla paginable/ordenable fila-por-fila.

Forzar estas 3 vistas al patron `django_tables2.Table` (que espera un `QuerySet` homogeneo de un solo modelo) habria requerido O bien aplanar datos heterogeneos a un formato artificial de tabla (perdiendo la semantica de "documento enriquecido"/"reporte con totales"), o bien usar `django_tables2.Table(data=lista_de_dicts)` sin aprovechar ninguna de las ventajas reales de la libreria (ordenamiento/paginacion sobre queryset del servidor) — en ambos casos el costo/riesgo supera el beneficio frente a simplemente dejarlas como estan (Tabulator client-side, ya funcionando) hasta que haya una razon de negocio para rediseñarlas especificamente. **Decision: no migradas, quedan con Tabulator.** Si en el futuro se decide migrarlas, cada una necesita su propio diseño (no es el mismo patron mecanico aplicado aqui) — no asumir que es "lo mismo pero con mas trabajo".

## 3. Bloqueante explicito (misma limitacion de entorno de toda la sesion)

No hay Docker/venv funcional en este host (confirmado de nuevo: `python manage.py check` falla con `ModuleNotFoundError: No module named 'django'`). Verificado unicamente con:
- `python -m py_compile` sobre `tables.py`, `views.py`, `urls.py`, `conftest.py`, `test_multitenant_isolation.py` — todos OK.
- `node --check` sobre los 5 `*_list.js` — todos OK.
- Lectura manual cruzada de cada `*_editor.js` para confirmar que la firma de `w.XList.reload()` no cambio (no requirieron edicion).
- Grep de `grid-cuentas|grid-periodos|grid-asiento|grid-retencion|grid-plantillas` en toda la app para confirmar cero referencias colgantes tras el reemplazo (encontro solo un doc de auditoria historico y una plantilla huerfana preexistente `contabilidad_periodos_list.html`, sin `include` en ningun lado — no se toco, es limpieza de codigo muerto fuera de alcance de esta tarea).

**Antes de dar esta migracion por validada en runtime, ejecutar como minimo:**
```
pytest apps/tenant/contabilidad/tests/test_multitenant_isolation.py -v
```
y abrir manualmente el modulo Contabilidad en el workspace (las 5 pestañas migradas: Cuentas, Periodos, Asientos, Retenciones, Plantillas) para confirmar paridad visual/funcional con la version Tabulator que reemplazan — buscar, paginar, ordenar por columna, crear/editar/eliminar, y las acciones especiales (cerrar periodo, aprobar asiento). Por decision ya tomada en esta fase (`PLAN_UNICO_CORRECCIONES.md`), esta validacion se hace una sola vez al final de toda la expansion, no app por app.

## 4. Archivos nuevos/tocados (resumen)

```
NUEVO  apps/tenant/contabilidad/tables.py
NUEVO  apps/tenant/contabilidad/views.py
NUEVO  apps/tenant/contabilidad/templates/tenant/contabilidad/partials/tabla_cuentas.html
NUEVO  apps/tenant/contabilidad/templates/tenant/contabilidad/partials/tabla_periodos.html
NUEVO  apps/tenant/contabilidad/templates/tenant/contabilidad/partials/tabla_asientos.html
NUEVO  apps/tenant/contabilidad/templates/tenant/contabilidad/partials/tabla_retenciones.html
NUEVO  apps/tenant/contabilidad/templates/tenant/contabilidad/partials/tabla_plantillas.html
NUEVO  apps/tenant/contabilidad/tests/conftest.py
NUEVO  apps/tenant/contabilidad/tests/test_multitenant_isolation.py
M      apps/tenant/contabilidad/urls.py (5 rutas *-tabla/ agregadas)
M      apps/tenant/contabilidad/templates/tenant/contabilidad/partials/list_cuentas.html
M      apps/tenant/contabilidad/templates/tenant/contabilidad/partials/list_periodos.html
M      apps/tenant/contabilidad/templates/tenant/contabilidad/partials/list_asientos.html
M      apps/tenant/contabilidad/templates/tenant/contabilidad/partials/list_retenciones.html
M      apps/tenant/contabilidad/templates/tenant/contabilidad/partials/list_plantillas.html
M      apps/tenant/contabilidad/static/contabilidad/js/cuenta/features/cuenta_list.js
M      apps/tenant/contabilidad/static/contabilidad/js/periodo/features/periodo_list.js
M      apps/tenant/contabilidad/static/contabilidad/js/asiento/features/asiento_list.js
M      apps/tenant/contabilidad/static/contabilidad/js/retencion/features/retencion_list.js
M      apps/tenant/contabilidad/static/contabilidad/js/plantilla/features/plantilla_list.js
```

No se toco `apps/tenant/contabilidad/api/viewsets.py` (la API DRF sigue viva para creacion/edicion/acciones y consumidores API-first) ni ningun `*_editor.js`.

## 5. Progreso de la expansion Fase 5-BIS (actualizado)

| App | Estado |
|---|---|
| `gastos` | Migrado (piloto) |
| `facturas` | Migrado |
| `compras` | Migrado |
| `contabilidad` | Migrado 5/8 (pendientes/libro-diario/reportes fuera de alcance, ver §2) |
| `ventas` | Pendiente (siguiente por prioridad-dinero) |
| resto (~14 apps) | Pendiente |
