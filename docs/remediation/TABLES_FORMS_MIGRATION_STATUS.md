# Tables & Forms — Auditoría Global (Estado)

**Fecha creación:** 2026-09-18
**Fecha de este cierre:** 2026-09-22
**Fuente:** `PROMPT_IA_EDITORA_AUDITORIA_GLOBAL_TABLAS_FILTROS_BUSQUEDAS_FORMULARIOS.md` (raíz del repo)

STATUS GLOBAL: **DataTables 3.x adoptado como estándar transversal — 12/12 apps del prompt migradas. Suite completa de tests ejecutada en las 12/12 apps (2026-09-21/22): PASS. Ver `docs/ux/TABLES_FORMS_RELEASE_GATE.md` para el detalle de resultados por app y los 2 bugs reales encontrados y corregidos en esta corrida final.**

---

## Historial de la decisión de alcance (importante para entender este documento)

Este documento tuvo dos fases con conclusiones OPUESTAS. Se documentan ambas para trazabilidad — la sección "Estado final" al fondo es la que aplica hoy.

### Fase A (2026-09-18): alcance reducido

La primera pasada de auditoría (FASE 0/2/3 del prompt) no encontró evidencia de los defectos sistémicos reportados ("tablas rotas", "filtros rotos", "URLs erróneas") sobre la arquitectura existente (`django-tables2` + HTMX + DRF `SearchFilter`/`OrderingFilter`). Con esa evidencia, el usuario decidió explícitamente (vía `AskUserQuestion`) **descartar** la adopción de DataTables 3.x y limitar el alcance a auditar + corregir bugs reales. Se corrigieron 2 bugs reales de doble-submit en formularios (uno con impacto financiero real en Cuentas por Pagar de Proveedores) y se cerró la tarea como DONE con ese alcance reducido.

### Fase B (2026-09-19 en adelante): reversión — adopción real de DataTables

En una sesión posterior el usuario retomó la línea original del prompt (Sección 3: DataTables 3.x + ColumnControl como estándar transversal) y pidió cerrar primero el **piloto de Ventas** (que ya existía con backend/tests en PASS pero el **gate visual pendiente** por falta de navegador). Con Playwright disponible, se cerró ese gate — y el proceso encontró **2 bugs reales de DOM** (no detectables sin navegador real):

1. DataTables reescribe el `<thead>` completo al inicializarse — una fila de filtros por columna puesta como HTML estático quedaba destruida. Fix: la fila de filtros se construye e inserta en JS **después** de `DataTablesFactory.create()`.
2. La opción `layout` de DataTables hace *merge parcial* sobre el default (`topStart:'pageLength', topEnd:'search', ...`) — sin anular `topEnd` explícitamente quedaban 2 buscadores duplicados en pantalla.

Con el piloto de Ventas validado end-to-end (backend + visual), el usuario decidió **extender el patrón a todas las apps restantes del prompt original**, con una instrucción explícita de ejecución: *"aplicar DataTables a nivel de UI/backend en todas las apps, dejando el paso de tests para el final"* (no ejecutar la suite completa después de cada app — testing progresivo/diferido, ver `CLAUDE.md §24.0`, aplicado aquí a nivel de todo un lote de trabajo, no solo un cambio puntual).

---

## Infraestructura compartida (Fase 5/6/16 del prompt)

- **Backend:** `apps/shared/datatable.py` — `DataTableSpec`/`DataTableServer`/`ColumnFilter`/`ColumnFilterType`. Contrato: cada endpoint declara `fields_map` (whitelist de columnas ordenables), `search_fields` (whitelist de búsqueda global), `column_filters` (whitelist de filtro por columna con tipo: `ICONTAINS`/`EXACT`/`DATE_RANGE`/`NUMBER_RANGE`). Nunca permite ordering/filtro arbitrario sobre campos no declarados (cumple la regla de la Sección 5 del prompt).
- **Frontend:** `apps/tenant/core/static/core/js/common/datatables.factory.js` — `Sintel.Core.DataTablesFactory.create/get/reload/search/columnSearch/columnRangeSearch`. Encapsula la config DataTables 3.0.4 + ColumnControl 2.0.2 + Bootstrap 5, con el fix de `layout` ya aplicado.
- **CDN:** `apps/tenant/core/templates/tenant/core/partials/assets_datatables_cdn.html`, incluido una vez por app (primer módulo con tabla migrada la carga; el resto de módulos de la misma app la reutilizan si comparten página).

### Bug real encontrado y corregido en el helper compartido (2026-09-21)

`_apply_column_filters()` (`ColumnFilterType.EXACT`) pasaba el valor crudo del filtro directo a `qs.filter(campo=valor)`. Para campos `BooleanField` (activo, reversada, anulado, etc.), Django `BooleanField.to_python()` solo acepta literales `("t","True","1")`/`("f","False","0")` — un `<select value="false">` (el patrón más común en todo el frontend de esta migración) manda `"false"` en minúscula, que **no calza** y levantaba `ValidationError` sin capturar (500 real). Confirmado por 2 tests reales que fallaron en la suite de Bancos (`test_cuenta_dt_filtro_columna_estado_exact`, `test_cuenta_dt_whitelist_columna_y_orden_no_declarados`).

Fix: `_coerce_exact_value()` normaliza `"true"/"american false"` (cualquier capitalización) y `"1"/"0"` antes de filtrar; el resto de valores se pasan tal cual (no afecta filtros `EXACT` sobre `CharField`/choices). Envuelto además en el mismo `contextlib.suppress` que ya protegía `DATE_RANGE`/`NUMBER_RANGE` — ningún valor de filtro inválido puede devolver 500 ahora.

**Impacto:** al vivir en código compartido, este fix beneficia a TODOS los endpoints `dt()` de las 12 apps que declaran un `ColumnFilter(..., ColumnFilterType.EXACT)` sobre un campo booleano (Cuentas Bancarias, Productos, Servicios, Plantillas Contables, Retenciones, Gastos, y otros). Verificado con los 2 tests que habían fallado — ambos pasan ahora (7/7 en `test_cuenta_dt.py`).

---

## Apps migradas (12/12 según el listado del prompt — Secciones 4, 8, 41, 43)

| # | App | Unidades migradas | KPIs extraídos | Notas |
|---|---|---|---|---|
| 1 | **Ventas** | Ventas | No (no tenía) | Piloto — gate visual cerrado con Playwright, 2 bugs de DOM corregidos. Columna "Factura DIAN" retirada después por redundante con "Núm. Factura" (pedido explícito del usuario). |
| 2 | **Bancos** | Cuentas Bancarias, Extractos Bancarios | Sí (Extractos: conciliación BAN-09) | — |
| 3 | **Facturas** | Facturas (tabs Ventas/Compras, 2 DataTables en la misma página) | No | `naturaleza` viaja por query string en la URL del ajax, no por el body DataTables. |
| 4 | **Clientes** | Directorio | Sí (cartera, vía `serializer_context` sin N+1) | Contactos/Historial/Cartera (sub-vistas del detalle) siguen en Tabulator — no son la grilla principal. |
| 5 | **Proveedores** | Directorio, Cuentas por Pagar, Representantes | Cuentas por Pagar: sí (KPIs propios ya existentes) | **Cuentas por Pagar** usa un endpoint `dt()` MANUAL (no `DataTableServer`) — su fuente (`qs_list_unificado()`) mezcla Factura+CuentasPagar en una lista Python, no un QuerySet real. |
| 6 | **Compras** | Órdenes de Compra, Plantillas de Numeración | Sí (Órdenes) | — |
| 7 | **Cotizaciones** | Cotizaciones (listado principal) | Sí | Productos/Servicios/Configuración (catálogos dentro del offcanvas) siguen en Tabulator — no son la grilla principal. App que faltaba del lote original; cerrada en este pase. |
| 8 | **Inventario** | Productos, Servicios, Activos Fijos | Productos y Activos Fijos: sí | Categorías y "Movimientos Recientes" (Kardex, vista agregada cross-model) fuera de alcance deliberadamente. |
| 9 | **Gastos** | Documentos Soporte, Resoluciones DIAN | Sí (Documentos Soporte) | — |
| 10 | **Empleados** | Directorio, Contratos, Resoluciones DIAN, Períodos de Nómina, Nóminas (Master), Liquidaciones (Master) | No | Nóminas/Liquidaciones son split-pane Master-Detail: el Master migró a DataTables (con `createdRow` para click-en-fila), el Detail (historial de UN empleado seleccionado) queda en django-tables2 + HTMX — no es un listado plano independiente. |
| 11 | **Proyectos** | Proyectos | Sí | TareaCorta (sub-tabla) sigue en django-tables2. |
| 12 | **Contabilidad** | Cuentas Contables, Períodos, Asientos, Retenciones, Plantillas, Pendientes, Libro Diario | Activos Fijos-style: Libro Diario sí (resumen embebido en la misma respuesta) | **Pendientes**: endpoint manual (mezcla Factura+DocumentoSoporte+Devengo+movimientos de Inventario, 4 apps). **Libro Diario**: además de migrar, se corrigió un bug real preexistente (ver abajo). Reportes (Balance/Estado de Resultados) fuera de alcance. |

### Patrón "endpoint manual" (2 casos, documentados explícitamente en el código)

`apps/shared/datatable.py::DataTableServer` asume un `QuerySet` real de un solo modelo. Dos fuentes de datos en el ERP mezclan varios modelos/apps en una lista Python ya materializada:

- **Proveedores → Cuentas por Pagar** (`CuentasPagarSelector.qs_list_unificado()`): Factura(COMPRA) + CuentasPagar.
- **Contabilidad → Pendientes** (`DocumentosPendientesViewSet._construir_pendientes()`): Factura + DocumentoSoporte + Devengo + movimientos de Inventario.

Para ambos se escribió un `dt()` que habla el mismo contrato JSON `{draw, recordsTotal, recordsFiltered, data}` pero pagina/ordena/filtra en Python sobre la lista ya construida — sin tocar el helper compartido ni forzarlo a soportar algo que no es su responsabilidad.

### Bug real preexistente encontrado y corregido: Libro Diario (Contabilidad)

Al migrar se descubrió que la integración `libro_diario_list.js` ↔ `LibroDiarioViewSet.list()` ya estaba rota en producción:

1. El JS (comentario propio: *"v3.7.7: Fuente de datos cambiada a AsientoContable"*) definía columnas alineadas con `AsientoContableListSerializer`, pero el backend seguía devolviendo documentos de 3 extractores cross-app (Factura/Gastos/Nómina) con una forma completamente distinta — el listado nunca mostró los campos correctos.
2. El JS mandaba `periodo_uuid` al elegir un período del dropdown; el backend solo leía `periodo` (`YYYY-MM`) o `fecha_inicio`/`fecha_fin` — la selección de período se ignoraba en silencio y la vista caía al mes en curso.

Fix (con autorización explícita del usuario, ver conversación): se agregó `LibroDiarioViewSet.dt()`, que consulta `AsientoContable` directo (la fuente que el JS siempre esperó) y resuelve `periodo_uuid` correctamente vía `PeriodoContable`. `list()`/`get_libro_diario_periodo()` (los extractores cross-app) **no se tocaron** — siguen activos para otros consumidores (`apps/tenant/contabilidad/reporting/provider.py`) y mantienen su cobertura de tests existente (`test_api_contabilidad.py`).

---

## Deliberadamente NO migrado (secundario, documentado en cada `tables.py`/JS)

| App | Tabla/vista | Por qué |
|---|---|---|
| Ventas | Resolución DIAN (selector de numeración) | Picker pequeño, no una grilla de listado — no solicitado. |
| Clientes | Contactos, Historial, Cartera (sub-vistas del detalle de un cliente) | Drill-down de UN registro, no un listado independiente. |
| Proveedores | Historial de compras (offcanvas de detalle) | Idem. |
| Cotizaciones | Productos, Servicios, Configuración (catálogo, offcanvas) | Catálogos reutilizables, no el listado principal. |
| Inventario | Categorías | No solicitado. |
| Inventario | Movimientos Recientes (Kardex) | Vista agregada cross-model (`get_movimientos_timeline()`, MovimientoInventario + HistorialServicio en Python), mismo criterio que Pendientes/Contabilidad pero no priorizada. |
| Empleados | Historial de Nóminas/Liquidaciones (Detail del Master-Detail) | Depende de la selección hecha en el Master, no es un listado independiente. |
| Proyectos | TareaCorta | No solicitado. |
| Contabilidad | Reportes (Balance de Prueba, Estado de Resultados) | Vista de reporte, no un listado CRUD. |

Ninguna de estas coexiste con DataTables como "segunda librería activa sin justificación" (regla Sección 38) — siguen en `django-tables2`/HTMX o Tabulator porque son sub-vistas de detalle o vistas agregadas, un caso distinto al de un listado principal.

---

## Fase 9 — Formularios

**Estado: parcial, heredado de la Fase A.** Se corrigieron 2 bugs reales de doble-submit (uno con impacto financiero real, Cuentas por Pagar de Proveedores) en la auditoría original. La modernización visual transversal (Secciones 29-33 del prompt: `form-section`/`form-grid`/`form-actions` como sistema de diseño compartido) **no se ejecutó** — los formularios (offcanvas HTMX) no se tocaron en la migración de tablas a DataTables, por diseño (la migración fue de listados, no de formularios).

## Fase 10/19 — Tests

**Estado: PASS.** Patrón de test establecido y aplicado en cada migración (contrato básico, aislamiento multi-tenant, filtro por columna, búsqueda global — mismo patrón que `test_venta_dt.py`); suite completa ejecutada en las 12/12 apps el 2026-09-21/22 (paso que el usuario había diferido deliberadamente al final del lote de trabajo, no cancelado — ejecutado tal como se acordó).

Resultado por app (detalle completo en `docs/ux/TABLES_FORMS_RELEASE_GATE.md`):

| App | Resultado |
|---|---|
| Ventas | 92 passed, 4 skipped, 2 errors (infra conocida) |
| Bancos | 100 passed (tras corregir el bug #7 de `_coerce_exact_value`) |
| Facturas | 207 passed, 12 skipped |
| Clientes | 52 passed, 1 error (infra conocida) |
| Proveedores | 58 passed (tras corregir un test obsoleto, ver bug nuevo abajo) |
| Compras | 58 passed (tras corregir un bug real de permisos, ver bug nuevo abajo) |
| Cotizaciones | 70 passed |
| Inventario | 58 passed |
| Gastos | 44 passed |
| Empleados | 98 passed |
| Proyectos | 128 passed, 2 skipped, 1 error (infra conocida) |
| Contabilidad | 126 passed, 2 errors (infra conocida) |

**Total: ~1091 tests passed, 0 fallos reales sin resolver.** Los 6 "errors" (Ventas x2, Clientes x1, Proyectos x1, Contabilidad x2) son la misma causa raíz en los 4 archivos: `@pytest.mark.django_db(transaction=True)` + hilos reales para probar condiciones de carrera (`select_for_update`), donde el `flush()` automático de pytest-django en el teardown falla (`Database test_sintel couldn't be flushed`) — patrón de infraestructura de tests preexistente a esta migración (esos tests no tocan tablas/DataTables), no bloqueante: la aserción de negocio del test ya había pasado antes de que el teardown fallara.

**2 bugs reales adicionales encontrados y corregidos durante esta corrida final:**

- **Proveedores — test obsoleto:** `test_tabla_cuentas_pagar_view.py` seguía apuntando a `/ui/proveedores/cuentas-pagar/tabla/`, la URL HTMX vieja retirada al migrar esa grilla (4 tests fallaban con 404). No era un bug de producción, pero sí una brecha real de cobertura — el endpoint `dt()` de Cuentas por Pagar no tenía ningún test dedicado hasta ahora. Reescrito para probar `POST /api/v1/proveedores/cuentas-pagar/dt/`, misma cobertura funcional que antes (render, filtro por estado, búsqueda, CxP sin factura).
- **Compras — bug real de permisos:** `IsTenantAdminOrReadOnly` (usada por las 14 apps con ViewSets DRF) trata cualquier método fuera de `SAFE_METHODS` como escritura reservada a ADMIN. Como `dt()` usa POST por convención de DataTables (aunque es 100% lectura), un usuario no-ADMIN con alcance SEDE que antes SÍ veía el listado de Órdenes de Compra (vía GET/HTMX) quedó bloqueado con 403 tras migrar — regresión real de UX/permisos, encontrada por `test_scope_pilot_f5.py`. Corregida en la fuente compartida (`apps/tenant/api/permissions.py::IsTenantAdminOrReadOnly.has_permission()`): `view.action == "dt"` ahora se trata como lectura, igual que `SAFE_METHODS`. Fix único, beneficia a las 12 apps sin tocar cada ViewSet.

**Cada app, sin excepción:** `node --check` (JS) y `python -c "import ast; ast.parse(...)"` (Python) sin errores; `docker compose exec web python manage.py check` limpio después de cada tanda de cambios, incluida la corrida final tras el fix de permisos.

## Fase 11 — Seguridad/tenant

Verificado exhaustivamente en Ventas y Bancos (tests de aislamiento multi-tenant dedicados, `force_login` cruzado entre 2 tenants, verificación de 401/403 sin sesión). Cada `dt()` reutiliza el selector/scoping ya existente de la app (`get_qs_list()`, `OrganizationalScope`, `SintelDSVMixin`) — nunca reimplementa el filtrado por `empresa_id`. Test de aislamiento multi-tenant escrito para cada app migrada (mismo patrón). **No se hizo un barrido de seguridad ofensivo adicional** (manipulación de `ordering`/`search`/`page` más allá de lo que ya cubren los tests de whitelist) — el diseño del helper compartido (whitelist explícita de campos ordenables/filtrables) hace estructuralmente imposible el vector descrito en la Sección 11 del prompt (`ordering_fields='__all__'` nunca se usa; confirmado en la auditoría de Fase A y no reintroducido).

## Fase 12 — Performance

**No ejecutado a escala (50/500/5.000/50.000+ registros).** El diseño (server-side, `.only()` heredado de los selectors existentes, sin `SELECT *`, agregados server-side para KPIs) sigue los mismos principios que ya pasaron la auditoría N+1 de la Fase A, pero no se generó dataset de prueba a gran escala ni se midió tiempo de respuesta/queries bajo carga en esta pasada.

## Fase 13 — Visual QA responsive

**Solo Ventas tiene gate visual formal con Playwright** (desktop + mobile, encontrando y corrigiendo los 2 bugs de DOM documentados arriba). Las otras 11 apps se migraron siguiendo el mismo patrón ya validado visualmente en Ventas (misma factory compartida, mismo CSS de Bootstrap 5), pero **no se verificaron visualmente una por una** en esta pasada.

## Fase 14 — Documentation drift

Este documento reemplaza la versión de la Fase A. `docs/ux/TABLES_FORMS_RELEASE_GATE.md` se actualiza en conjunto. Comentarios `WARNING: v2.61: DataTables eliminado / migrado a Tabulator` encontrados como código muerto/histórico en `apps/tenant/contabilidad/api/urls.py` — no se tocaron (son comentarios, no código activo, y documentan una decisión de una versión anterior no relacionada con esta migración).

---

## Checklist de aceptación (Sección 37) — releído contra el estado real

```text
[x] Todas las tablas fueron inventariadas (12 apps del prompt + secundarias documentadas).
[x] Todas las tablas activas (listado principal) tienen backend de filtros/búsqueda/ordenamiento vía DataTableServer o endpoint manual equivalente.
[x] Todas las tablas migradas tienen búsqueda global (search_fields explícito).
[x] Columnas filtrables tienen filtro individual por columna (ColumnFilter: ICONTAINS/EXACT/DATE_RANGE/NUMBER_RANGE) -- a diferencia de la Fase A, esto SÍ se construyó (era la brecha identificada entonces).
[x] Fechas/números/choices tienen filtro individual (DATE_RANGE/NUMBER_RANGE/EXACT).
[~] Relaciones (selector remoto) -- no se construyó un selector remoto de catálogo grande nuevo; los filtros relacionales existentes (cliente__razon_social, etc.) usan ICONTAINS sobre el campo denormalizado, no un autocomplete remoto dedicado.
[x] Ordenamiento funciona (whitelist explícita por endpoint, sin ordering libre).
[x] Paginación funciona (server-side, contrato DataTables estándar).
[x] URLs de acciones son correctas (data-uuid + JS, sin hardcodear).
[x] No se introdujeron rutas hardcodeadas nuevas.
[x] Tenant isolation funciona (reutiliza selectors/scoping existente en las 12 apps; tests dedicados ejecutados en las 12 apps).
[x] Permisos funcionan -- 1 bug real encontrado y corregido (dt() bloqueado para usuarios no-ADMIN via POST), resto heredado de cada ViewSet sin relajar/endurecer.
[x] Loading/Empty/Error state -- provistos por DataTables nativo (processing indicator, "No se encontraron registros").
[~] "Limpiar filtros" -- no se agregó un botón dedicado nuevo; el buscador nativo de DataTables y los selects de columna se limpian manualmente (gap real frente a la Sección 23 del prompt).
[x] Backend sigue siendo fuente de verdad (todo filtro/orden pasa por whitelist server-side).
[x] Service Layer no fue violado (cada dt() reutiliza selectors/servicios existentes).
[x] Selectors no fueron bypassed.
[x] No existen N+1 nuevos conocidos (KPIs con serializer_context sin N+1, movimientos_count/lineas_count vía SerializerMethodField consistente con el patrón ya auditado en Fase A).
[x] No se rompe HTMX (offcanvas/formularios intactos, solo se tocó la capa de listado).
[x] No se rompe Facturas/Ventas/Compras/Inventario/Contabilidad (verificado con manage.py check en cada tanda; suite completa verificada en Ventas y Bancos).
[x] Tests: patrón establecido, aplicado y EJECUTADO en 12/12 apps -- ~1091 passed, 0 fallos reales sin resolver.
[x] Documentación actualizada (este documento + RELEASE_GATE).
```

## Reglas absolutas (Sección 38) — verificación de no-violación

No se migraron todas las apps simultáneamente (se hizo secuencial, app por app, con `manage.py check` entre cada una). No se creó una tabla diferente por módulo — un solo helper compartido (`apps/shared/datatable.py`) y una sola factory JS (`datatables.factory.js`) para las 12 apps. No se duplicó código de filtros/paginadores/resolvers de URL. No se filtró solo en JavaScript (`serverSide: true` en las 12 apps). No se permitió ordering libre (whitelist `fields_map` en cada endpoint). No se crearon URLs hardcodeadas nuevas. No se usó UUID como entero (`data-uuid`, sin `parseInt()`). No se eliminó DSV ni se bypasseó ningún Selector. No se puso lógica de negocio/fiscal en JS. No se rompió HTMX. **Sí se mantienen 2 librerías de tabla activas** (`django-tables2` para las sub-vistas de detalle/Master-Detail documentadas arriba, Tabulator residual en 6 sub-vistas de catálogo/detalle) — con justificación explícita en cada caso (sub-vista de UN registro, no un listado principal), consistente con la Sección 40 del prompt ("puede mantenerse si existe justificación técnica"). No se declaró PASS sin evidencia — cada fila de este documento enlaza a un hallazgo, un test o una verificación de `manage.py check` real.

---

## Pendiente, no bloqueante (mejoras futuras, no iniciar sin que el usuario lo pida)

1. Validación visual (Playwright) de una muestra representativa de las 11 apps no-piloto, replicando el rigor aplicado a Ventas (único gate visual formal hasta ahora).
2. Performance a escala (Fase 12, 50k+ registros) — no hay evidencia de que sea necesario, pero tampoco se midió.
3. Botón "Limpiar filtros" transversal (gap real identificado arriba) y selector remoto para relaciones sobre catálogos grandes (Sección 7 del prompt) — mejoras incrementales.
4. Investigar de raíz el patrón de infraestructura `transaction=True`+threads+teardown `flush()` (6 ocurrencias en 4 apps, ninguna relacionada con esta migración) si se prioriza dejar la suite en 0 errores reportados.
