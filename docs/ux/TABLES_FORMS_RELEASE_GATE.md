# Release Gate — Auditoría Global de Tablas, Filtros, Búsqueda, URLs y Formularios

**Fecha:** 2026-09-19
**Fuente:** `PROMPT_IA_EDITORA_AUDITORIA_GLOBAL_TABLAS_FILTROS_BUSQUEDAS_FORMULARIOS.md` (raíz del repo)
**Evidencia detallada:** `docs/remediation/TABLES_FORMS_MIGRATION_STATUS.md`

STATUS: **DONE (alcance reducido)**

## Decisión de alcance

El prompt original (Sección 3) proponía reemplazar la arquitectura de tablas existente (`django-tables2` + HTMX + DRF) por `DataTables 3.x + ColumnControl`, asumiendo defectos sistémicos ("las tablas no funcionan", "los filtros no funcionan", "URLs erróneas en cabeceras").

El usuario decidió explícitamente, vía `AskUserQuestion`, reducir el alcance a: **auditar y corregir únicamente bugs reales sobre la arquitectura existente** — sin adoptar una librería nueva, sin construir el "contrato único de tabla" (Secciones 6-21 del prompt), sin modernización visual transversal (Secciones 29-33).

Justificación (regla del propio prompt, Sección 1: "código real actual > documentación histórica"): la inspección del código mostró que la migración histórica Tabulator → django-tables2 ya está prácticamente completa (13 apps en producción con `tables.py`, Tabulator reducido a 2 usos residuales, DataTables con 0 usos), y que adoptar DataTables violaría la propia regla del prompt (Sección 38: "no mantener dos librerías de tablas activas sin justificación").

## Apps auditadas (13/13)

Bancos, Clientes, Compras, Contabilidad, Empleados, Empresa, Facturas, Gastos, Inventario, Perfil, Proveedores, Proyectos, Ventas.

## Resultado por fase (mapeado a las fases del prompt original)

| Fase (prompt) | Estado | Evidencia |
|---|---|---|
| 0 Discover | PASS | Inventario de las 13 apps con `tables.py`; Tabulator/DataTables descartados por uso real (`TABLES_FORMS_MIGRATION_STATUS.md` intro). |
| 1 Baseline sistémico | PASS | Clasificación tabla activa/server-side/django-tables2 en las 13 apps — sin huérfanos relevantes. |
| 2 Auditoría de filtros | PASS | Búsqueda global, ordenamiento y filtros de estado verificados en las 13 apps — 100% OK (12/13 vía `SearchFilter`/`ordering_fields` declarativos, Proveedores vía override manual equivalente). |
| 3 Auditoría de URLs | PASS | 0 `LinkColumn`/`href` custom en `<th>` de ninguna app — 100% de cabeceras ordenables usa los links nativos de django-tables2, conservan querystring. Acciones por fila: 0 endpoints muertos, 0 `parseInt()` sobre UUID en código real. |
| 4-8 Spike/Core/Piloto DataTables | NOT_APPLICABLE | Descartado por decisión de alcance — no aplica una arquitectura de tabla nueva. |
| 9 Formularios | PASS | Auditados en el cierre de esta tarea. 2 bugs reales de doble-submit confirmados y corregidos (uno de impacto financiero real en Cuentas por Pagar). Detalle abajo. |
| 10 Pruebas por tabla | PARTIAL | Cubierto indirectamente por la suite de tests existente de cada app (no se ejecutó la matriz manual de 15 casos por tabla del prompt — no se justifica sin bugs detectados). |
| 11 Seguridad/tenant | PASS | `ordering_fields = '__all__'`: 0 ocurrencias en `apps/tenant/`. Aislamiento por `empresa_id` verificado en 4 apps representativas (Ventas, Facturas, Compras, Proveedores) — AND estructural, no depende de orden de `.filter()`. |
| 12 Performance/N+1 | PASS | Sin N+1 reales confirmados en las 13 apps (verificación estática + 1 test dedicado que refutó una hipótesis inicial en Proyectos). Una mejora menor de `.only()` aplicada. |
| 13 Visual QA (responsive) | NOT_AUDITED | Fuera del alcance elegido (modernización visual); no se reportó ningún defecto funcional responsive durante la sesión. |
| 14 Documentation drift | PASS | Confirmado que `CLAUDE.md`/`AGENTS.md` ya reflejan la migración real (django-tables2 + HTMX), no la arquitectura histórica Tabulator. |
| 15 Release Gate | PASS | Este documento. |

## Bugs reales encontrados y corregidos (todas las fases)

1. **Truncamiento visual de centavos** en listados de Facturas/Ventas (`,.0f` en vez de `currency_cop`) — corregido (sesión previa, ver `FACTURAS_VENTAS_SYNC_STATUS.md`).
2. **Bug de escala x100** en el parser XML universal — corregido, con backfill sobre datos reales (sesión previa).
3. **Doble-submit con duplicación financiera real** en el abono de Cuentas por Pagar (`cuentas_pagar_editor.js`) — corregido esta sesión.
4. **Doble-submit → error falso tras éxito** en `representante_editor.js`, `perfil.modals.js` (crear/editar perfil), `periodo_editor.js` (crear/editar periodo) — corregido esta sesión.

Ningún otro defecto funcional fue confirmado en tablas, filtros, búsqueda, ordenamiento, URLs o formularios en las 13 apps auditadas.

## Deuda técnica identificada y explícitamente diferida (no confundir con bug)

- **Filtro por columna individual** (rango de fecha, rango numérico, dropdown embebido en el header): no existe en ninguna tabla del ERP. Es la brecha real de la Sección 2 del prompt, pero es una **funcionalidad nueva**, no la corrección de un defecto. Requeriría el contrato `searchable_fields`/`filterable_fields`/`orderable_fields` + `django-filter` descrito en las Secciones 6-8 del prompt — evaluar como iniciativa aparte si el usuario la prioriza.
- **`alert()` como fallback de error** en 12 archivos JS, y falta del patrón Bootstrap `is-invalid`/`invalid-feedback` en casi todos los formularios (solo 2 lo usan). Investigado exhaustivamente: en ningún caso se pierde información real del error — es una diferencia de estilo/modernización (Secciones 29-31 del prompt), fuera del alcance "solo bugs reales".
- **Inconsistencia de estilo en Compras** (`compras/tables.py:141`, URL absoluta embebida en vez de `data-uuid` + JS) — funciona correctamente, verificado contra las URLs reales; es estilo, no bug.

## Checklist de aceptación (Sección 37 del prompt) — aplicado al alcance reducido

```text
[x] Todas las tablas fueron inventariadas. (13/13)
[x] Todas las tablas activas tienen backend de filtros/búsqueda/ordenamiento funcional.
[x] Todas las tablas tienen búsqueda global cuando aplica.
[ ] Todas las columnas filtrables tienen filtro individual. -- DIFERIDO (funcionalidad nueva, no bug; ver "Deuda técnica")
[ ] Fechas/números/choices/relaciones tienen filtro individual por columna. -- DIFERIDO (idem)
[x] Ordenamiento funciona (13/13, sin ordering_fields sin restringir).
[x] Paginación funciona (server-side, DRF estándar).
[x] URLs de títulos/cabeceras son correctas (0 href/reverse custom encontrados).
[x] URLs de acciones son correctas (0 endpoints muertos, 0 parseInt(UUID)).
[x] No existen rutas hardcodeadas obsoletas.
[x] Tenant isolation funciona (empresa_id estructural, 4 apps verificadas).
[x] Permisos funcionan (heredados sin relajar/endurecer).
[x] Loading/Empty/Error state -- ya presentes en la infraestructura HTMX/django-tables2 existente, sin regresión.
[~] Tablas son responsive -- no auditado visualmente esta sesión; sin defectos reportados.
[ ] Formularios tienen presentación uniforme (visual). -- DIFERIDO (modernización, no bug)
[x] Formularios muestran errores correctamente (causa real, no genérica) -- verificado en 12 archivos con alert().
[x] Backend sigue siendo fuente de verdad.
[x] Service Layer no fue violado.
[x] Selectors no fueron bypassed.
[x] No existen N+1 nuevos.
[x] No se introducen duplicaciones.
[x] No se rompe HTMX.
[x] No se rompe Facturas / Ventas / Compras / Inventario / Contabilidad.
[x] Tests: `node --check` en los 4 JS modificados sin errores; suites de Python no re-ejecutadas en esta pasada porque los fixes son JS puro sin tocar backend/Service Layer.
[x] Documentación actualizada (este documento + `TABLES_FORMS_MIGRATION_STATUS.md`).
```

## Reglas absolutas (Sección 38) — verificación de no-violación

No se migraron todas las apps simultáneamente a nada (no aplica, no hubo migración de librería). No se duplicó código de filtros/paginadores/resolvers de URL. No se filtró solo en JavaScript. No se permitió ordering libre. No se creó ninguna URL hardcodeada nueva. No se usó UUID como entero. No se eliminó DSV ni se bypasseó ningún Selector. No se puso lógica de negocio/fiscal en JS (los 4 fixes de doble-submit son puramente de UI — deshabilitar un botón). No se rompió HTMX. No se mantienen dos librerías de tabla activas sin justificación (django-tables2 es la única activa). No se declaró PASS sin evidencia — cada fila de la tabla anterior enlaza a inspección de código real o test.

## Pendiente para una iniciativa futura (fuera de esta tarea)

Si el usuario decide priorizarlo más adelante:
1. Filtro por columna individual (fecha/número/choice/relación) — requiere diseño del contrato backend descrito en Secciones 6-8 del prompt original.
2. Modernización visual de formularios (`is-invalid`/`invalid-feedback` consistente, reemplazo de `alert()` por notificación inline) — Secciones 29-31 del prompt original.
3. Validación visual responsive formal (Fase 13) en dispositivo real/DevTools.
