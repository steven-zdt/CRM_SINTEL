# Release Gate — Auditoría Global de Tablas, Filtros, Búsqueda, URLs y Formularios

**Fecha creación:** 2026-09-19
**Fecha de este cierre:** 2026-09-22
**Fuente:** `PROMPT_IA_EDITORA_AUDITORIA_GLOBAL_TABLAS_FILTROS_BUSQUEDAS_FORMULARIOS.md` (raíz del repo)
**Evidencia detallada:** `docs/remediation/TABLES_FORMS_MIGRATION_STATUS.md`

STATUS: **PASS — DataTables 3.x adoptado como estándar transversal (12/12 apps migradas). Suite completa de tests ejecutada en las 12 apps (2026-09-21/22): 0 fallos reales pendientes. 2 bugs reales encontrados y corregidos durante esta corrida (detalle abajo); el resto de fallos observados son un patrón de infraestructura de tests preexistente y no relacionado (`transaction=True` + threads + teardown `flush()`), confirmado en 4 apps distintas.**

## Decisión de alcance (revisada — ver historial completo en `TABLES_FORMS_MIGRATION_STATUS.md`)

Este release gate se emitió originalmente el 2026-09-19 con **STATUS: DONE (alcance reducido)** — el usuario había decidido, vía `AskUserQuestion`, descartar la adopción de DataTables 3.x y limitar el trabajo a corregir bugs reales sobre `django-tables2`+HTMX. Esa decisión fue **revertida** en una sesión posterior: el usuario retomó la propuesta original del prompt (Sección 3) y pidió adoptar DataTables 3.x + ColumnControl como estándar transversal, empezando por un piloto en Ventas y extendiéndolo luego a las 11 apps restantes.

Este documento reemplaza esa versión anterior. Se cambia el STATUS a `IN_PROGRESS` (no `DONE`) porque, aunque el trabajo de migración en sí está completo en las 12 apps, la **Sección 36 del prompt ("nunca declarar PASS sin evidencia") impide declarar PASS del Release Gate completo** mientras la suite de tests no se haya ejecutado — paso que el propio usuario diferió explícitamente a un momento final ("deja test para el último paso"), no cancelado.

## Apps migradas (12/12 — el universo del prompt original)

Ventas (piloto), Bancos, Facturas, Clientes, Proveedores, Compras, Cotizaciones, Inventario, Gastos, Empleados, Proyectos, Contabilidad — ~28 unidades de listado individuales entre módulos principales y submódulos. Detalle unidad por unidad, incluidos los 2 patrones de endpoint manual y las exclusiones deliberadas (sub-vistas de detalle, catálogos offcanvas, reportes): `TABLES_FORMS_MIGRATION_STATUS.md`.

## Resultado por fase (mapeado a las fases del prompt original)

| Fase (prompt) | Estado | Evidencia |
|---|---|---|
| 0 Discover | PASS | Inventario completo de las 12 apps y sus unidades de listado (`TABLES_FORMS_MIGRATION_STATUS.md` tabla principal). |
| 1 Baseline sistémico | PASS | Heredado de la auditoría original (sin huérfanos relevantes) + confirmado de nuevo al recorrer cada app durante la migración. |
| 2 Auditoría de filtros | PASS | Cada endpoint `dt()` declara whitelist explícita (`fields_map`/`search_fields`/`column_filters`) — sin ordering/filtro libre en ninguna de las 12 apps. |
| 3 Auditoría de URLs | PASS | Acciones por fila usan `data-uuid` + JS (`htmx.ajax()`); 1 caso corregido en esta migración (Compras, botón "Editar" de Plantillas usaba `hx-get` crudo, roto bajo filas inyectadas por ajax — ver detalle en `MIGRATION_STATUS.md`). |
| 4 Spike técnico | PASS | Resuelto en el piloto de Ventas (sesión previa): DataTables 3.0.4 + ColumnControl 2.0.2 + Bootstrap 5 vía CDN, sin build step, compatible con el resto del stack (HTMX, offcanvas). |
| 5 Contrato único de tabla | PASS | `apps/shared/datatable.py` (`DataTableSpec`/`DataTableServer`/`ColumnFilter`) — un solo helper para las 12 apps, sin duplicación. |
| 6 Backend por tabla | PASS | 26/28 unidades vía `DataTableServer` estándar; 2 unidades (Proveedores/Cuentas por Pagar, Contabilidad/Pendientes) vía endpoint manual documentado — única alternativa viable porque su fuente es una lista Python ya materializada desde varios modelos/apps, no un QuerySet. |
| 7 Filtros por columna | PASS | `ColumnFilterType.ICONTAINS/EXACT/DATE_RANGE/NUMBER_RANGE` implementados y usados según el tipo de cada columna en las 12 apps — esta era la brecha real identificada (y diferida) en la auditoría de alcance reducido; queda resuelta. |
| 8 Piloto (Ventas) | PASS | Gate visual cerrado con Playwright en sesión previa — 2 bugs reales de DOM encontrados y corregidos (rewrite de `<thead>` por DataTables destruía una fila de filtros estática; `layout` con merge parcial duplicaba el buscador). Base para las 11 apps siguientes. |
| 9 Formularios | PARTIAL | Bugs reales de doble-submit (4 formularios, 1 con impacto financiero real) corregidos en la auditoría original. La modernización visual transversal (`form-section`/`form-grid`/`form-actions`, Secciones 29-33) **no se ejecutó** — la migración de esta fase fue de listados, no de formularios; ver "Deuda técnica" abajo. |
| 10 Pruebas por tabla | PASS | Test dedicado escrito por cada endpoint `dt()` nuevo (contrato básico, aislamiento tenant, filtro de columna, búsqueda global). **Suite completa ejecutada en las 12/12 apps** (2026-09-21/22) — resultado y evidencia por app en `TABLES_FORMS_MIGRATION_STATUS.md`. |
| 11 Seguridad/tenant | PASS | Cada `dt()` reutiliza el selector/scoping ya existente de su app (nunca reimplementa filtrado por `empresa_id`); whitelist explícita hace estructuralmente imposible el vector de `ordering=__all__` descrito en la Sección 11. Test de aislamiento multi-tenant dedicado y ejecutado en las 12 apps. Bug real de permisos encontrado y corregido en esta corrida (ver abajo: `dt()` bloqueado para no-ADMIN). |
| 12 Performance/N+1 | PARTIAL | Sin N+1 nuevos por diseño (mismos `.only()`/selectors auditados en la Fase A, KPIs vía `serializer_context` sin N+1 adicional). **No se midió a escala** (50k+ registros) — no ejecutado en esta pasada. |
| 13 Visual QA (responsive) | PARTIAL | Solo Ventas (el piloto) tiene gate visual formal con Playwright, desktop+mobile. Las 11 apps restantes siguen el mismo patrón ya validado (misma factory JS compartida, mismo CSS) pero no se verificaron visualmente una por una. |
| 14 Documentation drift | PASS | Este documento y `TABLES_FORMS_MIGRATION_STATUS.md` reescritos para reflejar el estado real; `CLAUDE.md`/`AGENTS.md` no mencionan la librería de tabla específica (quedan válidos sin cambios). |
| 15 Release Gate | **PASS** | Este documento. Suite completa ejecutada en las 12/12 apps, 2 bugs reales encontrados y corregidos en el proceso, evidencia documentada — consistente con la Sección 36 ("no declarar PASS sin evidencia"). |

## Bugs reales encontrados y corregidos (acumulado, todas las fases de esta tarea)

1. Truncamiento visual de centavos en listados de Facturas/Ventas — corregido (sesión previa a esta migración).
2. Bug de escala x100 en el parser XML universal — corregido, con backfill sobre datos reales (sesión previa).
3. Doble-submit con duplicación financiera real en el abono de Cuentas por Pagar — corregido (auditoría original, alcance reducido).
4. Doble-submit → error falso tras éxito, 3 formularios más (representantes, perfil, periodos contables) — corregido (auditoría original).
5. **DataTables reescribe `<thead>` al inicializar**, destruyendo una fila de filtros estática puesta antes de `create()` — corregido en el piloto de Ventas: la fila de filtros ahora se inserta en JS después de inicializar.
6. **`layout` de DataTables hace merge parcial sobre el default**, duplicando el buscador (`topEnd`) si no se anula explícitamente — corregido en el piloto de Ventas, propagado a la factory compartida (afecta a las 12 apps).
7. **`_apply_column_filters` (EXACT) crashea con `ValidationError` sobre `BooleanField`** cuando el valor viene en minúscula (`"false"`, el caso más común desde un `<select>` HTML) — bug en código compartido (`apps/shared/datatable.py`), encontrado en la primera corrida de suite completa (Bancos), corregido con `_coerce_exact_value()`, afecta potencialmente a cualquier filtro `EXACT` booleano de las 12 apps.
8. **Botón "Editar" de Plantillas de Compras roto bajo DataTables** — usaba `hx-get` crudo en el HTML de la fila; como DataTables inyecta filas vía ajax, `htmx.process()` nunca corre sobre ellas y el atributo queda inerte. Corregido: `data-uuid` + `htmx.ajax()` en JS.
9. **Libro Diario de Contabilidad — bug preexistente, no introducido por esta migración**: el filtro de período (`periodo_uuid`) era ignorado en silencio por el backend, y las columnas del JS ya no correspondían a la forma real de datos que el `list()` devolvía. Corregido, con autorización explícita del usuario, agregando un endpoint `dt()` separado que consulta la fuente correcta (`AsientoContable`) sin tocar el `list()`/extractor cross-app original (que sigue sirviendo a Reportes).
10. **Test obsoleto de Proveedores (`test_tabla_cuentas_pagar_view.py`)**: apuntaba a `/ui/proveedores/cuentas-pagar/tabla/`, la URL HTMX vieja retirada al migrar esa grilla a DataTables — 4 tests fallaban con 404 real (no un bug de producción, pero sí una brecha de cobertura: el endpoint `dt()` de Cuentas por Pagar no tenía ningún test dedicado). Corregido: archivo reescrito para probar `POST /api/v1/proveedores/cuentas-pagar/dt/`, conservando la misma cobertura funcional (render, filtro por estado, búsqueda, inclusión de CxP sin factura).
11. **Bug real de permisos en `dt()` (Compras, y potencialmente cualquier app)**: `IsTenantAdminOrReadOnly` trata cualquier método fuera de `SAFE_METHODS` (GET/HEAD/OPTIONS) como escritura reservada a ADMIN. Como `dt()` usa POST por convención de DataTables (aunque es una acción de solo lectura), un usuario no-ADMIN con alcance SEDE que antes SÍ podía ver el listado de Órdenes de Compra (vía GET/HTMX) quedaba bloqueado con 403 tras la migración — regresión real de seguridad/UX encontrada por `test_scope_pilot_f5.py::test_dt_con_alcance_sede_ve_todas_las_sedes_asignadas`. Corregido en la fuente compartida `apps/tenant/api/permissions.py::IsTenantAdminOrReadOnly.has_permission()`: se trata `view.action == "dt"` como lectura, igual que `SAFE_METHODS` — beneficia a las 12 apps sin tocar cada ViewSet individualmente.

## Deuda técnica identificada y explícitamente diferida (no confundir con bug)

- **Botón "Limpiar filtros" transversal**: no se agregó en ninguna de las 12 apps. Gap real frente a la Sección 23 del prompt — el usuario puede limpiar manualmente el buscador y cada filtro de columna, pero no hay un solo clic. Candidato a mejora incremental sobre la factory compartida.
- **Selector remoto (autocomplete) para relaciones sobre catálogos grandes** (Sección 7): los filtros relacionales existentes usan `ICONTAINS` sobre el campo denormalizado (ej. `cliente__razon_social`), no un selector remoto dedicado. Suficiente para los volúmenes actuales; no bloqueante.
- **Modernización visual de formularios** (`is-invalid`/`invalid-feedback` consistente, reemplazo de `alert()`, Secciones 29-31): no tocada en esta migración (que fue de listados). Sigue siendo la misma deuda identificada en la auditoría original.
- **Performance a escala** (Fase 12, 50k+ registros): diseño server-side sin `SELECT *` y sin N+1 conocidos, pero no medido bajo carga real en esta pasada.

## Resultado de la suite completa (2026-09-21/22) — las 12/12 apps

| App | Resultado | Notas |
|---|---|---|
| Ventas | 92 passed, 4 skipped, 2 errors | Errores: patrón de infra conocido (`transaction=True`+threads+teardown `flush()`), no relacionado con la migración. |
| Bancos | 100 passed (2 failed → corregidos) | Los 2 failed originales eran el bug de `_coerce_exact_value` (bug #7 arriba), corregido y reverificado. |
| Facturas | 207 passed, 12 skipped | Sin fallos. |
| Clientes | 52 passed, 1 error | Mismo patrón de infra conocido. |
| Proveedores | 58 passed (4 failed → corregidos) | Los 4 failed eran el test obsoleto (bug #10 arriba), reescrito y reverificado. |
| Compras | 58 passed (1 failed → corregido) | El failed era el bug real de permisos en `dt()` (bug #11 arriba), corregido y reverificado. |
| Cotizaciones | 70 passed | Sin fallos. |
| Inventario | 58 passed | Sin fallos. |
| Gastos | 44 passed | Sin fallos. |
| Empleados | 98 passed | Sin fallos. |
| Proyectos | 128 passed, 2 skipped, 1 error | Mismo patrón de infra conocido. |
| Contabilidad | 126 passed, 2 errors | Mismo patrón de infra conocido. |

**Total: ~1091 tests passed, 0 fallos reales sin resolver.** Los 6 "errors" restantes (Ventas x2, Clientes x1, Proyectos x1, Contabilidad x2) son todos instancias del mismo patrón de infraestructura de tests: `@pytest.mark.django_db(transaction=True)` combinado con hilos reales para probar condiciones de carrera (`select_for_update`), donde el `flush()` automático de pytest-django en el teardown falla (`Database test_sintel couldn't be flushed`) por una interacción conocida entre `TransactionTestCase` y el pool de conexiones en este entorno — confirmado idéntico en 4 archivos de test distintos, preexistente a esta migración (esos tests no tocan tablas/DataTables), y no bloqueante para el resultado del propio test (la aserción de negocio ya pasó antes de que el teardown fallara).

## Checklist de aceptación (Sección 37 del prompt) — aplicado al alcance real (DataTables adoptado)

```text
[x] Todas las tablas fueron inventariadas. (12 apps del prompt + secundarias documentadas)
[x] Todas las tablas activas (listado principal) tienen backend de filtros/búsqueda/ordenamiento funcional.
[x] Todas las tablas migradas tienen búsqueda global.
[x] Columnas filtrables tienen filtro individual por columna (ICONTAINS/EXACT/DATE_RANGE/NUMBER_RANGE) -- brecha cerrada respecto al release gate anterior.
[x] Fechas/números/choices tienen filtro individual.
[~] Relaciones -- filtro por ICONTAINS sobre campo denormalizado, sin selector remoto dedicado (deuda técnica, no bloqueante).
[x] Ordenamiento funciona (whitelist explícita, sin ordering libre).
[x] Paginación funciona (server-side, contrato DataTables).
[x] URLs de acciones son correctas (data-uuid + JS; 1 bug real corregido en Compras).
[x] No se introdujeron rutas hardcodeadas nuevas.
[x] Tenant isolation funciona (reutiliza selectors/scoping existente; verificado con suite completa en las 12/12 apps).
[x] Permisos funcionan -- 1 bug real encontrado y corregido (dt() bloqueado para no-ADMIN, bug #11), resto heredado sin relajar/endurecer.
[x] Loading/Empty/Error state -- provisto por DataTables nativo.
[ ] "Limpiar filtros" -- no implementado (deuda técnica identificada arriba).
[x] Backend sigue siendo fuente de verdad.
[x] Service Layer no fue violado.
[x] Selectors no fueron bypassed.
[x] No existen N+1 nuevos conocidos (no medido a escala).
[x] No se rompe HTMX (offcanvas/formularios intactos).
[x] No se rompe Facturas/Ventas/Compras/Inventario/Contabilidad (manage.py check limpio en cada tanda; suite completa PASS en las 12/12 apps).
[x] Tests: escritos y EJECUTADOS en 12/12 apps -- ~1091 passed, 0 fallos reales sin resolver (ver tabla de resultados arriba).
[x] Documentación actualizada (este documento + TABLES_FORMS_MIGRATION_STATUS.md).
```

## Reglas absolutas (Sección 38) — verificación de no-violación

No se migraron todas las apps simultáneamente (secuencial, app por app, `manage.py check` entre cada una). Un solo helper backend (`apps/shared/datatable.py`) y una sola factory JS (`datatables.factory.js`) para las 12 apps — sin duplicación de filtros/paginadores/resolvers de URL. No se filtró solo en JavaScript (`serverSide: true` en las 12 apps). No se permitió ordering libre. No se crearon URLs hardcodeadas nuevas. No se usó UUID como entero. No se eliminó DSV ni se bypasseó ningún Selector. No se puso lógica de negocio/fiscal en JS. No se rompió HTMX. Se mantienen 2 librerías de tabla activas (`django-tables2` para sub-vistas Master-Detail/detalle documentadas, Tabulator residual en 6 sub-vistas de catálogo) **con justificación técnica explícita en cada caso** (sub-vista de un solo registro o catálogo reutilizable, no un listado principal) — consistente con la excepción de la Sección 40. No se declaró PASS sin evidencia: el STATUS pasó a `PASS` únicamente después de ejecutar la suite completa en las 12/12 apps y documentar cada resultado (tabla arriba), incluidos los 2 bugs reales que esa corrida encontró y corrigió.

## Pendiente, no bloqueante (mejoras futuras, no iniciar sin que el usuario lo pida)

1. Validación visual Playwright de una muestra de las 11 apps no-piloto (solo Ventas tiene gate visual formal).
2. Medición de performance a escala (50k+ registros, Fase 12).
3. Botón "Limpiar filtros" transversal y selector remoto para relaciones sobre catálogos grandes.
4. Investigar de raíz el patrón de infraestructura `transaction=True`+threads+teardown `flush()` (6 ocurrencias en 4 apps) si se prioriza limpiar la salida de `pytest` a 0 errores — no bloquea ningún resultado de negocio hoy.
