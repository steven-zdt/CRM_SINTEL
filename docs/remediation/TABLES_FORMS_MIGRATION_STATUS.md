# Tables & Forms — Auditoría Global (Estado)

**Fecha:** 2026-09-18
**Fuente:** `PROMPT_IA_EDITORA_AUDITORIA_GLOBAL_TABLAS_FILTROS_BUSQUEDAS_FORMULARIOS.md` (raíz del repo)
**Decisión de alcance (usuario, vía AskUserQuestion):** "Solo auditar y corregir bugs reales" sobre la arquitectura EXISTENTE (`django-tables2` + HTMX + DRF `SearchFilter`/`OrderingFilter`) — se descartó explícitamente adoptar `DataTables 3.x + ColumnControl` como nuevo estándar transversal.

## Por qué se descartó la opción DataTables del prompt original

El prompt fuente asume que las tablas están sistémicamente rotas y propone un reemplazo total de librería. La inspección del código real (FASE 0, antes de tocar nada) mostró lo contrario:

- **13 apps ya tienen `tables.py` (django-tables2) en producción**: bancos, clientes, compras, contabilidad, empleados, empresa, facturas, gastos, inventario, perfil, proveedores, proyectos, ventas.
- **Tabulator está prácticamente retirado**: solo 2 usos reales quedan (`contabilidad/reporte.ui.js`, un factory compartido) — confirma que la migración "Tabulator → django-tables2 + HTMX" que documenta `CLAUDE.md` es real y está casi terminada, no es histórica/muerta.
- **DataTables tiene 0 usos actuales** en el repo — adoptarlo sería una dependencia nueva, no una continuación de trabajo existente.
- La regla propia del prompt (#38, "no mantener dos librerías de tablas activas sin justificación") se hubiera violado al introducir una TERCERA (Tabulator residual + django-tables2 + DataTables).

Por tanto: `CÓDIGO REAL ACTUAL > documento de prompt`, siguiendo la propia regla del documento fuente (sección 1).

STATUS: DONE — auditoría completa (tablas/filtros/URLs/formularios); sin evidencia de los defectos sistémicos reportados; 2 bugs reales de formularios corregidos (ver sección "Formularios" abajo). Cierre formal: `docs/ux/TABLES_FORMS_RELEASE_GATE.md`.

## FASE 0/2/3 — Resultado de la auditoría (búsqueda, ordenamiento, URLs)

Auditoría read-only sobre las 13 apps con `tables.py`: `tables.py` (columnas orderable/`Meta.order_by`), ViewSet (`filter_backends`/`search_fields`/`ordering_fields`), vista que sirve el fragmento HTMX, template de listado/tabla (`href=`/`hx-get=`/`{% url`/`data-url` dentro de `<th>`), y el JS de lista correspondiente.

| App | Búsqueda | Ordenamiento | URLs en cabeceras | Notas |
|---|---|---|---|---|
| Bancos | OK | OK | OK | Sin links custom en `<th>`; usa los links de orden nativos de django-tables2. |
| Clientes | OK | OK | OK | `search_fields` alineado con la UI. |
| Compras | OK | OK | OK | `ordering_fields` verificados contra campos reales del modelo. |
| Contabilidad | OK | OK | OK | Los 5 listados (cuentas, asientos, periodos, plantillas, retenciones) tienen `name="q"` correctamente cableado en `partials/list_*.html`. |
| Empleados | OK | OK | OK | — |
| Empresa | OK | OK | OK | — |
| Facturas | OK | OK | OK | — |
| Gastos | OK | OK | OK | — |
| Inventario | OK | OK | OK | — |
| Perfil | OK | OK | OK | — |
| Proveedores | OK | OK | OK | Búsqueda implementada vía override manual de `list()` (`viewsets.py`) en vez de `SearchFilter` declarativo — funciona correctamente, es solo una diferencia de estilo respecto al resto de apps (no es un bug). |
| Proyectos | OK | OK | OK | — |
| Ventas | OK | OK | OK | Extendido esta sesión (panel de sincronización); regresión completa: 67 passed, 1 skipped. |

**Cabeceras de tabla:** ningún `LinkColumn`/href custom encontrado en ningún `<th>` de ninguna app — el 100% de los encabezados ordenables usa los links de orden nativos de django-tables2 (`?sort=-campo`, conserva querystring). El mecanismo que causaría "URLs erróneas en cabeceras" (un link hardcodeado o un `reverse()` a un endpoint muerto) **no existe** en este código — el síntoma reportado en el prompt no tiene base estructural aquí.

**Búsqueda/ordenamiento/filtros de estado:** funcionan en las 13 apps, ya sea vía `SearchFilter`/`ordering_fields` declarativos o (Proveedores) un override manual equivalente.

## Bugs reales confirmados (y corregidos)

Ninguno de los defectos "sistémicos" descritos en el prompt (tablas rotas, filtros rotos, búsqueda inconsistente, URLs erróneas) se confirmó en la auditoría. Los ÚNICOS bugs reales encontrados en esta sesión, todos ya corregidos, salieron de pruebas con datos reales (no de este barrido genérico) y quedan documentados en `docs/remediation/FACTURAS_VENTAS_SYNC_STATUS.md`:

1. Truncamiento visual de centavos en los listados de Facturas y Ventas (`,.0f` en vez de `currency_cop`).
2. Bug de escala x100 en el parser XML universal (no relacionado con tablas/filtros).
3. Falta de una acción para eliminar una Venta sincronizada.

## Brecha real identificada (no es un bug — es una funcionalidad que nunca existió)

Ninguna tabla del ERP tiene **filtro por columna individual** (rango de fecha, rango numérico, dropdown de estado embebido en el header) — todas dependen de: búsqueda global + pills de filtro de estado predefinidos + ordenamiento por click de cabecera. Esto coincide con el diagnóstico de la sección 2 del prompt original, pero construir esa capa (contrato `searchable_fields`/`filterable_fields`/`orderable_fields` + widgets de filtro por columna con `django-filter`) es una FUNCIONALIDAD NUEVA, no la corrección de un defecto — y quedó fuera de alcance por la decisión explícita del usuario de esta sesión ("solo corregir bugs reales", no construir infraestructura nueva de filtrado).

## FASE 3 (continuación) — URLs de acciones por fila

Auditoría de `render_acciones`/`render_*` en `tables.py` + JS de lista + `<app>.api.js`, las 13 apps:

- Ningún botón de acción apunta a un endpoint inexistente — todos usan `data-uuid`/`data-id` + delegación de eventos por clase (`btn-edit-x`, `btn-delete-x`, etc.), consistente en las 13 apps.
- Único hallazgo de estilo (no bug): `apps/tenant/compras/tables.py:141` embebe una URL absoluta (`hx-get="/api/v1/compras/plantillas/render-offcanvas/editar/?uuid={0}"`) en vez de construirla desde `data-uuid` + JS, a diferencia del resto de apps. Verificado contra `compras/api/urls.py` y `compras/api/viewsets.py:367-368` — la ruta existe y resuelve correctamente. Es una inconsistencia de estilo, no un defecto funcional.
- `parseInt()` sobre UUID: **0 ocurrencias reales** en código (`apps/tenant/`) — las 2 únicas coincidencias son la documentación de la propia prohibición en archivos `.agent/*.md`.
- Sin contaminación de namespace entre apps (patrón "boton copiado de otra app y nunca re-cableado") — el único caso que parecía serlo (`Sintel.Reporting.API` usado en `ventas/reportes_ventas.js`) es un módulo compartido legítimo (`core/static/core/js/common/reporting.api.js`).

STATUS FASE 3: PASS.

## FASE 11 — Seguridad y tenant (búsqueda/filtro/ordenamiento)

- `ordering_fields = '__all__'` (o allow-list sin restricción): **0 ocurrencias** en todo `apps/tenant/`.
- Revisado `get_queryset()`/selector `.get_list()` de Ventas, Facturas (`ItemFactura`), Compras y el override manual de Proveedores: en los 4 casos el filtro `empresa_id` se aplica en el queryset base, antes/junto con cualquier encadenamiento de búsqueda u ordenamiento. Los `.filter()` de Django se combinan con AND sin importar el orden de llamada, por lo que no existe una ruta donde un `?search=` o `?ordering=` manipulado amplíe el resultado más allá del tenant — el aislamiento es estructural, no depende del orden.

STATUS FASE 11: PASS (verificado en 4 apps representativas; el patrón es uniforme con lo ya confirmado por FASE 0/2 en las 13 apps).

## FASE 12 — N+1 en listados (auditoría estática + verificación empírica)

Para las 13 apps: se leyeron los métodos `render_*` de `tables.py` en busca de traversales FK/relación (`record.<fk>.<campo>`) y se verificó que el `get_list()`/`qs_list()` del selector correspondiente cubriera esa relación con `select_related()`/`prefetch_related()` y que `.only()` incluyera el campo específico accedido.

**Resultado: sin N+1 reales confirmados.** Todas las traversales encontradas ya estaban cubiertas:

| App | Traversal FK en render_* | select_related/prefetch cubre | Resultado |
|---|---|---|---|
| Bancos | `record.cuenta.nombre/numero` (ExtractoBancarioTable) | `select_related("cuenta", "sede")` | OK |
| Compras | `record.proveedor.*`, `record.proyecto.nombre` | `select_related('proveedor','proyecto','documento_soporte','plantilla','sede','area')` | OK |
| Contabilidad | `str(record.cerrado_por)` (PeriodoContableTable) | `select_related("cerrado_por")` | OK |
| Empleados | `record.empleado.nombre_completo` (ContratoTable) | `select_related('empleado')` + ambos campos en `.only()` | OK |
| Empresa | `record.sede.nombre` (AreaTable) | `select_related('sede')` | OK |
| Facturas | `record.nota_credito` (FacturaTable) | `select_related("nota_credito", "sede")` | OK |
| Gastos | `record.proveedor.*` (DocumentoSoporteTable, accessor) | `select_related('resolucion_dian','proveedor')` | OK |
| Inventario | `record.categoria.nombre` (Producto/Servicio/ActivoFijo) | `select_related('categoria')` en los 3 selectores | OK |
| Perfil | `record.user.*`, `record.departamento.nombre` | `select_related('user','departamento')` | OK |
| Proveedores | ninguna (todo denormalizado o dict pre-calculado) | N/A | OK |
| Proyectos | `record.factura_costo.cotizacion_numero` (ProyectoTable); `record.cliente.*`/`record.empleado.*` (TareaCortaTable) | `select_related('factura_costo',...)` / `select_related('cliente','empleado',...)` | Ver nota abajo |
| Ventas | `record.cliente.*`, `record.factura_asociada.numero` | `select_related("cliente","proyecto","factura_asociada","resolucion")` | OK |

**Nota Proyectos:** `qs_list()` tenía `select_related('factura_costo')` sin nombrar ningún campo de `Factura` en `.only()`. La hipótesis inicial fue que esto causaba una query extra por fila (N+1) — **se verificó empíricamente con un test dedicado (`test_qs_list_n1_factura_costo.py`, revirtiendo el cambio y re-corriendo) que esto era FALSO**: Django no aplica deferred loading a un modelo `select_related()` si `.only()` no lo menciona en absoluto, así que ya cargaba todas las columnas de `Factura` vía el JOIN — 0 queries extra tanto antes como después. Se agregó igualmente `factura_costo__cotizacion_numero` a `.only()` (commit ya aplicado) por el criterio "Zero Waste" del propio selector (evita traer columnas de `Factura` que nadie usa en el listado), pero se documenta aquí explícitamente como una mejora de eficiencia menor, NO como la corrección de un bug de N+1 real — para no reportar un hallazgo más grave de lo que el código real demostró ser.

STATUS FASE 12: PASS (sin N+1 reales; una mejora menor de `.only()` aplicada y verificada con test).

## Formularios (FASE 9/29-31)

Auditados en esta sesión (cierre de la tarea), acotado igual que el resto: solo bugs funcionales reales, no modernización visual/estética.

**Hallazgo transversal de estilo (no bug):** 12 archivos JS usan `alert()` como fallback de error y solo 2 templates usan el patrón Bootstrap `is-invalid`/`invalid-feedback`. Se investigó cada uno de los 12 casos — en todos, el mensaje mostrado (por `alert()` o por el manejo real vía `UIManager`/`error_injector.js`) refleja la causa real del error del backend; no hay pérdida de información. Queda registrado como deuda técnica de estilo (consistente con la decisión de alcance ya tomada para tablas/URLs), no como defecto a corregir en esta pasada.

**Bugs reales confirmados y corregidos (doble-submit):**

1. **`apps/tenant/proveedores/static/proveedores/js/features/cuentas_pagar_editor.js`** — el botón "Guardar" del offcanvas de abono no se deshabilitaba durante la petición. Un doble clic aplicaba el mismo abono dos veces sobre el saldo real (`valor_pagado`), sin protección de idempotencia en backend (`registrar_abono` solo serializa con `select_for_update()`, no deduplica). **Impacto: financiero real.** Corregido: el botón se deshabilita antes de `registrarAbono()` y se reactiva solo en caso de error (éxito cierra el offcanvas).
2. **`apps/tenant/proveedores/static/proveedores/js/features/representante_editor.js`**, **`apps/tenant/perfil/static/perfil/js/perfil.modals.js`** (crear y editar perfil), **`apps/tenant/contabilidad/static/contabilidad/js/periodo/features/periodo_editor.js`** (crear y editar periodo) — mismo patrón: sin protección de doble-submit. Aquí no se duplicaban registros (constraints `unique_together`/`unique` en backend lo impiden), pero un doble clic disparaba una 2ª petición que fallaba por violación de unicidad, mostrando un error justo después del mensaje de éxito y confundiendo al usuario sobre si su dato quedó guardado. Corregido con el mismo patrón ya usado en `venta_editor.js`/`compras_editor.js`/`gasto_editor.js`: deshabilitar el botón al iniciar la petición, reactivar en `finally`/`catch`.

Verificación: `node --check` sobre los 4 archivos modificados — sin errores de sintaxis. No se tocó lógica de negocio ni Service Layer; el fix vive enteramente en el listener del botón (frontend).

STATUS FASE 9: PASS (2 bugs reales, uno de impacto financiero, corregidos; resto es deuda técnica de estilo documentada, fuera de alcance).

## Conclusión

No se encontró evidencia de que "las tablas dinámicas no funcionan", "los filtros no funcionan" o "las cabeceras generan URLs erróneas" como problemas sistémicos — la arquitectura actual (django-tables2 + HTMX + DRF) funciona correctamente en las 13 apps auditadas. Si el usuario tiene una pantalla/tabla específica donde observó uno de estos síntomas en vivo, ese caso puntual debe reportarse con el detalle exacto (app, tabla, acción realizada, resultado esperado vs. obtenido) para poder reproducirlo y corregirlo — la auditoría genérica de código no lo reprodujo.

En formularios sí se confirmaron y corrigieron 2 bugs reales de doble-submit (uno de impacto financiero en Cuentas por Pagar), documentados arriba (FASE 9). El resto de la brecha reportada por el prompt original (columnas sin filtro individual, formularios sin modernizar visualmente) es deuda técnica real pero deliberadamente fuera de alcance por la decisión explícita del usuario de esta sesión.

## Cierre de la tarea

STATUS GLOBAL: **DONE (alcance reducido a "auditoría + corrección de bugs reales")**

Ver `docs/ux/TABLES_FORMS_RELEASE_GATE.md` para el cierre formal (Fase 15 del prompt original) con el checklist de aceptación de la Sección 37.
