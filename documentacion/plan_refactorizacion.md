# PLAN DE ACCIÓN POR FASES DE REFACTORIZACIÓN — SINTEL ERP v3.10.5+

**Fecha:** 2026-08-05  
**Contexto de Arquitectura:** SINTEL v3.9.1 / v3.10.5+  
**Documentos Fuente de Auditoría y Remediación:**
- `documentacion/AUDITORIA_ENTERPRISE_2026-07-26.md`
- `documentacion/PLAN_REMEDIACION.md`
- `documentacion/PLAN_UNICO_CORRECCIONES.md`
- `documentacion/AUDITORIA_CODIGO_MUERTO_EKG_2026-08-05.md`
- `REPORTE_FASE_1.md` a `REPORTE_FASE_9.md`

---

## 0. Estado de Avance General

El proceso de refactorización y remediación del codebase se encuentra estructurado en 10 Fases operativas. A continuación se presenta el tablero de estado consolidado:

| Fase | Alcance / Categoría | Estado | Entregable / Reporte |
|---|---|---|---|
| **Fase 1** | Remediación de 15 Hallazgos Críticos | ✅ Completada | `documentacion/REPORTE_FASE_1.md` |
| **Fase 2** | Arquitectura Alto (ARQ-A1..A4) | ✅ Completada | `documentacion/REPORTE_FASE_2.md` |
| **Fase 3** | Seguridad Alto + Medio (SEC-A, SEC-M) | ✅ Completada | `documentacion/REPORTE_FASE_3.md` |
| **Fase 4** | Performance Alto + Medio (PERF-A, PERF-M) | ✅ Completada | `documentacion/REPORTE_FASE_4.md` |
| **Fase 5** | Frontend Alto + Medio (FE-A1..A9, FE-M1..M6) | ✅ Completada | `documentacion/REPORTE_FASE_5.md` |
| **Fase 5-BIS** | Reemplazo de Tabulator por `django-tables2` + HTMX | 🔄 Parcial (8/16 apps; Empresa 4/4 grillas completa) | `REPORTE_FASE_5_PILOTO_TABLAS.md`, `REPORTE_FASE_5_BIS_*` |
| **Fase 6** | Simplificación, Deduplicación y Código Muerto | ✅ Completada | `documentacion/REPORTE_FASE_6.md` |
| **Fase 7** | Deuda de Testing y Cobertura Multi-Tenant | ⏳ Pendiente | Por generar (`REPORTE_FASE_7.md`) |
| **Fase 8** | DevOps, Docker y Dependencias | ✅ Completada | `documentacion/REPORTE_FASE_8.md` |
| **Fase 9** | Documentación y Gobernanza Final | ✅ Completada | `documentacion/REPORTE_FASE_9.md` |
| **Fase 10** | Validación de Entorno Runtime y CI Final | ⏳ Pendiente | Por generar (`REPORTE_FASE_10.md`) |

---

## 1. Fases Completadas — Resumen Operativo

### 1.1 Fase 1 — Hallazgos Críticos (SEC, PERF, FE, ARQ, TEST, DEVOPS, DOC)
- **Logros:** Corrección de `DEBUG` en middleware/permissions (`SEC-C1`), eliminación de endpoints inseguros (`SEC-C2`), bloqueo pesimista `select_for_update` en consecutivo de facturas (`PERF-C2`), restricción única en asientos contables (`PERF-C1`), guard anti-doble submit en formulación (`FE-C1/FE-C2`), eliminación de `http.js` crudo (`FE-C3`), inyección de `RetencionesService` en facturas (`ARQ-C1`), desacoplamiento de mixins de inventario (`ARQ-C2`), test de aislamiento de ventas (`TEST-C1`), CI con GitHub Actions (`DEVOPS-C1`), y documentación inicial (`DOC-C1/C2`).

### 1.2 Fase 2 — Arquitectura de Dominio (ALTO)
- **Logros:** Estandarización de `lookup_field="uuid"` en ViewSets tenant (`ARQ-A1`), documentación de excepciones de herencia (`ARQ-A2`), corrección parcial de endpoints directos (`ARQ-A3`), y eliminación de templates/apps huérfanas como `mail`/`mailinbox` (`ARQ-A4`).

### 1.3 Fase 3 — Seguridad (ALTO + MEDIO)
- **Logros:** DSV (Doble Verificación Semántica) reforzada en servicios de mutación, saneamiento de serializers DRF sin filtro por tenant, prevención de IDOR en claves foráneas y protección de endpoints administrativos.

### 1.4 Fase 4 — Performance y Optimización de Consultas (ALTO + MEDIO)
- **Logros:** Erradicación del problema N+1 en listados de facturas, compras y gastos mediante `.select_related()` y `.prefetch_related()`. Restricción del consumo de RAM mediante `.only()` y `.defer()` en Selectors de la capa de servicios.

### 1.5 Fase 5 — Frontend (FE-A + FE-M)
- **Logros:** Inserción del guard `data-editor-initialized` en 34 archivos `*_editor.js`. Eliminación de fugas de memoria y backdrops huérfanos de Offcanvas Bootstrap (`FE-A4`). Centralización del helper de Offcanvas (`offcanvas.helper.js`). Reemplazo de `.setData()` por `.replaceData()` en Tabulator (`FE-A6`). Reestructuración FSD de estáticos en `facturas` y `inventario`.

### 1.6 Fase 6 — Simplificación y Código Muerto
- **Logros:** Unificación de `StandardResultsSetPagination` (SSoT 20/200). Eliminación de 50 archivos huérfanos entre JS, CSS y plantillas obsoletas. Depuración de scripts sueltos en raíz.

### 1.7 Fase 8 — DevOps y Dependencias
- **Logros:** Adición de usuario no-root en `Dockerfile` (`DEVOPS-A1`), creación de `.dockerignore` (`DEVOPS-A2`), endurecimiento de configuraciones de Docker Compose (`DEVOPS-A3/A4/A5`), acotamiento de dependencias en `requirements.txt`.

### 1.8 Fase 9 — Documentación y Gobernanza
- **Logros:** Sincronización de `arquitectura_general.md` a la versión actual de la arquitectura SINTEL v3.10.5+, actualización de enlaces a `.agent/AUDITORIA_FLUJO_*.md` y restauración de indentación en archivos Python tras limpieza de caracteres Unicode/emojis.

---

## 2. Fases Activas y Pendientes — Plan de Acción Detallado

### 2.1 FASE 5-BIS (Continuación) — Expansión de `django-tables2` + HTMX

**Objetivo:** Eliminar la fricción de sincronización cliente-servidor de Tabulator migrando las grillas de datos a renderizado HTML directo con `django-tables2`, `django-filter` y HTMX.

#### Estado de Aplicación por Módulo:

- ✅ **Gastos** (Piloto completo: `tables.py`, `views.py`, partials, HTMX).
- ✅ **Facturas** (Migrado: grillas de Ventas/Compras).
- ✅ **Compras** (Migrado).
- ✅ **Contabilidad** (5 de 8 grillas migradas: plantillas, retenciones, periodos, cuentas, asientos).
- ✅ **Ventas** (1 grilla real migrada: `venta_list.js`).
- ✅ **Bancos** (2 de 2 grillas migradas: cuentas y extractos).
- ✅ **Empleados** (5 de 5 grillas migradas: empleados, contratos, resoluciones, nóminas, liquidaciones).
- ⏳ **Inventario** (6 archivos Tabulator pendientes).
- ⏳ **Cotizaciones** (6 archivos Tabulator pendientes).
- 🔶 **Proveedores** — grillas "Directorio" y "Cuentas por Pagar" migradas (2026-08-05), 1 unidad pendiente:
  - ✅ Grilla "Directorio de Proveedores" (`proveedores_main.js`): `tables.py` (con `row_attrs` para click-en-fila → abre detalle, replicando el `rowClick` de Tabulator), `views.py`, `urls.py` extendido, template HTMX, `proveedores_list.html` Tab 1 actualizado, `proveedores_main.js` recortado de ~280 a ~90 líneas. Reutiliza `ProveedorSelector.get_list/get_cuentas_pagar_resumen` (misma SSoT que la API). Cubierto por `apps/tenant/proveedores/tests/test_tabla_view.py` (2/2 OK) — requirió agregar migración de `facturas` al fixture `tenant` del conftest (la cartera de CxP lee `Factura.naturaleza=COMPRA`).
  - ✅ Grilla "Cuentas por Pagar" (`cuentas_pagar_list.js`, Tab 2): `tables.py` (`CuentasPagarTable`, sobre `Factura.naturaleza=COMPRA` — la misma fuente de verdad que `CuentasPagarViewSet.list()`, no el modelo `CuentasPagar` que solo persiste abonos), `views.py` (`CuentasPagarTableView`), ruta `cuentas-pagar-tabla`, template `partials/tabla_cuentas_pagar.html`, `proveedores_list.html` Tab 2 actualizado a HTMX (`#cuentas-pagar-panel`, selector de estado y buscador ambos con `hx-include` cruzado), `cuentas_pagar_list.js` recortado a solo una función de refresco global (el botón "Abono" lo sigue manejando `cuentas_pagar_editor.js`, que ya delegaba eventos sobre `document` — sin cambios ahí). Cubierto por `apps/tenant/proveedores/tests/test_tabla_cuentas_pagar_view.py` (3/3 OK: render, filtro por estado, búsqueda). **Corrige dos bugs funcionales de paso** — ver hallazgo debajo.
  - ⏳ Historial de compras (dentro del offcanvas de detalle, `proveedores_form.js`) — no migrado, Tabulator intacto.
  - Representantes (Tab 3) no usa Tabulator, no aplica a esta fase.

### Hallazgo funcional: grilla "Cuentas por Pagar" de Proveedores nunca se inicializaba, y su buscador nunca filtraba

Al migrar esta grilla se encontraron dos bugs pre-existentes independientes:
1. **La tabla nunca se renderizaba en absoluto.** `cuentas_pagar_list.js` exponía `w.Sintel.Proveedores.CuentasPagarList.init()`, pero ningún archivo del proyecto lo invocaba — el handler `shown.bs.tab` del tab "Cuentas por Pagar" en `proveedores_main.js` solo hacía `console.log(...)`. El spinner nunca se mostraba, el grid nunca se poblaba y el empty-state tampoco aparecía: la pestaña quedaba visualmente en blanco sin ningún indicio de error.
2. **El buscador (`#search-cuentas-pagar`) no filtraba nada.** `TabulatorFactory` enviaba `?search=<texto>` a `/api/v1/proveedores/cuentas-pagar/`, pero `CuentasPagarViewSet.list()` (override completo, sin filter backends de DRF) solo leía `proveedor_uuid`, `estado_pago` y `vencidas` — el parámetro `search` se ignoraba silenciosamente y siempre devolvía la lista completa. Se agregó soporte real de búsqueda (`numero`/`emisor_razon_social`/`emisor_nit__icontains`) tanto en `CuentasPagarSelector.qs_list_facturas_compra()` como en el ViewSet, beneficiando también a cualquier consumidor API-first del endpoint, no solo a la UI.

### Bug propio encontrado y corregido durante esta migración: `django-tables2` sustituye el valor de columnas ligadas a un `CharField(choices=...)` por su `get_FOO_display()`

Al verificar `CuentasPagarTable` con datos reales, la columna "Estado" mostraba siempre "Sin Pago" incluso para una factura con `estado_pago="PAGADA"` (confirmado independientemente por las columnas "Saldo" y "Acciones" de la MISMA fila, que sí usaban `record.estado_pago` directo y se comportaban bien). Causa raíz: `django-tables2` sustituye automáticamente, para cualquier columna ligada a un campo de modelo con `choices`, el valor pasado al `render_<campo>()` por la etiqueta legible (`get_estado_pago_display()` → "Pagada"/"No Pagada"), no por el valor crudo del choice ("PAGADA"/"NO_PAGADA") — mi comparación `if value == "PAGADA":` nunca podía ser verdadera. Corregido cambiando la firma a `render_estado_pago(self, record)` y comparando `record.estado_pago` directo (mismo patrón ya usado en `render_saldo`/`render_acciones` de la misma tabla). **Advertencia para cualquier tabla `django-tables2` futura en este proyecto:** si una columna corresponde a un campo con `choices`, el parámetro `value` de su `render_` recibe el label humano, no el valor crudo — usar `record.<campo>` si se necesita comparar contra las constantes del choice.
- ✅ **Empresa** — las 4 grillas del módulo migradas (2026-08-05):
  - ✅ Grilla "Sede" (`sede_list.js`): `tables.py`, `views.py`, ruta agregada a `urls_ui.py` (ver nota abajo), template HTMX, `empresa_list.html` Tab 2 actualizado, `sede_list.js` recortado. Reutiliza `SedeSelector.get_list` existente. Cubierto por `apps/tenant/empresa/tests/test_tabla_sedes_view.py` (2/2 OK).
  - ✅ Grilla "Área" (`area_list.js`, Tab 3): `tables.py` (`AreaTable`, reutiliza `AreaSelector.get_list`), `views.py` (`AreaTableView`, refactorizado junto con `SedeTableView` sobre una base compartida `_EmpresaTableViewBase`), ruta `area-tabla` en `urls_ui.py`, template `partials/tabla_areas.html`, `empresa_list.html` Tab 3 actualizado a HTMX (`#areas-panel`), `area_list.js` recortado (sin Tabulator, delegación de clicks en `document.body`). Se omitió deliberadamente una columna "Responsable" — el campo `responsable_nombre` no existe en el modelo `Area` ni en ningún serializer, era un campo huérfano de la UI Tabulator anterior. Cubierto por `apps/tenant/empresa/tests/test_tabla_areas_view.py` (2/2 OK, incluye assert explícito de que "Responsable" no aparece en el HTML renderizado).
  - ✅ Grilla "Empresa" (singleton, `empresa_list.js`, Tab 1): `tables.py` (`EmpresaTable`, reutiliza `EmpresaSelector.get_list` ya existente), `views.py` (`EmpresaTableView`), ruta `empresa-tabla`, template `partials/tabla_empresa.html`, `empresa_list.html` Tab 1 actualizado a HTMX (`#empresa-panel`), `empresa_list.js` recortado (solo botón "Editar", sin "Eliminar" — la Empresa es singleton por tenant, igual que en la versión Tabulator). Lookup por `pk` (`id`), no `uuid` — el modelo `Empresa` no tiene campo `uuid` (excepción documentada, coherente con `EmpresaViewSet`). Cubierto por `apps/tenant/empresa/tests/test_tabla_empresa_view.py` (2/2 OK).
  - ✅ Grilla "MailInboxConfig" (`mailinboxconfig_list.js`, dentro del Tab 1 vía `mailinbox_list.html`): `tables.py` (`MailInboxConfigTable`), `views.py` (`MailInboxConfigTableView`), nuevo `MailInboxConfigSelector` en `services/selectors.py` (no existía selector para este modelo), ruta `mailinboxconfig-tabla`, template `partials/tabla_mailinboxconfig.html`, `mailinbox_list.html` actualizado a HTMX (`#mailinboxconfig-panel`), `mailinboxconfig_list.js` recortado. Lookup por `pk` (`id`), sin campo `uuid` (mismo caso que Empresa). Cubierto por `apps/tenant/empresa/tests/test_tabla_mailinboxconfig_view.py` (2/2 OK). **Bug funcional corregido de paso** — ver hallazgo debajo.

### Hallazgo transversal: bug de `empty_values` en las 5 tablas de esta sesión

Al construir el test de Sede se descubrió que `django-tables2` solo invoca `render_<campo>()` cuando el valor de la celda **no** está en `Column.empty_values` (por defecto `(None, '')`). Con un campo `blank=True` vacío (`""`), la librería nunca llama al render personalizado — muestra su propio placeholder genérico en su lugar, silenciosamente, sin excepción ni test que lo detecte a menos que se verifique explícitamente el texto esperado ("Sin asignar", "—", etc.) en un campo vacío. Esto afectaba potencialmente a **todas las columnas con `render_X` que manejan el caso vacío** en las 5 tablas construidas esta sesión (Perfil, Proyectos, Clientes, Proveedores, Empresa/Sede) — corregido agregando `empty_values=()` a cada columna afectada, y re-verificado con la suite completa (9/9 tests OK tras el fix). Aplica también como advertencia para cualquier tabla `django-tables2` futura en este proyecto: si `render_<campo>` tiene lógica para "sin dato", la columna necesita `empty_values=()` explícito. La tabla `AreaTable` construida después ya incorporó `empty_values=()` desde el inicio en las 4 columnas.

### Hallazgo de seguridad: IDOR en `MailInboxConfigViewSet` (corregido 2026-08-05)

Al investigar la migración pendiente de MailInboxConfig se encontró que `MailInboxConfigViewSet.get_queryset()` (`apps/tenant/empresa/api/viewsets.py`, ~línea 561) no filtraba por `empresa_id` en ninguna rama — el modelo `MailInboxConfig` tiene FK obligatoria a `Empresa`, por lo que cualquier usuario autenticado del tenant podía potencialmente listar/acceder a la configuración de buzón de **otras empresas dentro del mismo schema** (violación de la regla `empresa_id` obligatorio en toda query tenant, AGENTS.md). Confirmado con el usuario y corregido de inmediato reutilizando el helper existente `resolve_tenant_empresa(self.request, self)` (mismo patrón que `SedeViewSet`/`AreaViewSet` en el mismo archivo). La migración UI de MailInboxConfig a `django-tables2` se completó a continuación en la misma sesión (ver arriba).

### Hallazgo funcional: grilla MailInboxConfig nunca renderizaba (IDs Tabulator/template desincronizados)

Al construir la migración de MailInboxConfig se encontró que la grilla Tabulator anterior estaba rota desde su origen: `apps/tenant/empresa/templates/tenant/empresa/mailinbox_list.html` declaraba el contenedor como `#grid-mailinbox` / `#search-mailinbox`, pero `mailinboxconfig_list.js` (`initTabulator()`) buscaba `#grid-mailinboxconfig` / `#search-mailinboxconfig` — un desajuste de IDs que hacía que `querySelector` nunca encontrara el elemento, `TabulatorFactory.create()` nunca se ejecutara, y la librería solo emitiera un `console.warn` silencioso sin excepción visible. El botón "Nueva Configuración" seguía funcionando (usaba atributos `hx-get` propios, independientes del grid), por lo que el problema pasaba desapercibido salvo al intentar *ver* la lista de buzones configurados. La migración a `django-tables2` corrige esto de raíz (el template y la vista comparten la misma URL con nombre, no IDs de string duplicados) y queda cubierta por test. Lección: cualquier grid Tabulator restante en el proyecto debería auditarse por el mismo patrón de desajuste antes de asumir que "simplemente no tiene datos".

### Hallazgo transversal: regresión `pytest-django` 4.13.0 incompatible con Django 5.0.14 (corregido 2026-08-05)

Al intentar correr `test_tabla_areas_view.py` (recién creado) se obtuvo `AttributeError: type object 'PytestDjangoTestCase' has no attribute '_pre_setup_ran_eagerly'` en TODOS los tests marcados `@pytest.mark.django_db`, incluyendo `test_tabla_sedes_view.py` que había pasado horas antes en esta misma sesión — confirmando que era una regresión de entorno, no un bug del código nuevo. Causa raíz: `requirements.txt` fijaba `pytest-django>=4.7,<5.0`, un rango demasiado amplio que resolvió a `4.13.0`, versión incompatible con Django 5.0.14 (API interna de fixtures cambiada). Corregido acotando el pin a `pytest-django>=4.7,<4.9` (rango verificado funcionando) con comentario `REGR-M1` explicando el porqué, y aplicado de inmediato en el contenedor corriendo vía `pip install "pytest-django>=4.7,<4.9"` (instaló 4.8.0). Re-verificado: `test_tabla_sedes_view.py` (2/2) y `test_tabla_areas_view.py` (2/2) pasan correctamente tras el downgrade. Lección aplicable a todo `requirements.txt` del proyecto: los rangos de versión sueltos (`<N.0` en vez de un tope menor) no garantizan compatibilidad con el resto del stack fijado — deben verificarse contra la versión exacta de Django en uso, no solo contra el major.
- 🔶 **Proyectos** — grid principal migrado (2026-08-05), sub-panel pendiente:
  - ✅ `proyectos_list.js` (grid principal, 10 columnas): `tables.py`, `views.py`, `urls.py` extendido, `selectors.kpis_list()` (agregacion server-side con `Count`/`Sum`/`Avg` condicionales — antes los KPIs se calculaban client-side desde las filas cargadas en Tabulator; con paginacion server-side eso ya no reflejaba el universo completo, se decidio con el usuario ir por agregacion server-side), template HTMX combinando KPIs+tabla, `proyectos_list.html` actualizado (chips de fase vía `hx-get`), `proyectos_list.js` recortado (delegación de clicks movida a `document.body`). Cubierto por `apps/tenant/proyectos/tests/test_tabla_view.py` (2/2 OK): valida que los KPIs se agregan sobre TODO el conjunto filtrado (no solo la página visible) y que el filtro `?fase=` afecta tabla y KPIs a la vez.
  - ⏳ `nueva_tarea_list.js` (panel secundario "Nueva tarea" con mini state-machine de avance de estado PENDIENTE→EN_PROCESO→COMPLETADA) — **no migrado, queda como unidad separada** por su complejidad y su naturaleza de sub-panel modal distinto al listado principal.
  - Como parte de esta migración se encontró `apps/tenant/proyectos/templates/tenant/proyectos/list.html` (v2.60, referencias a Tabulator/`#grid-proyectos`) sin ninguna referencia en el repo — candidato a código muerto, delegado como tarea aparte (no forma parte del alcance de Fase 5-BIS).
- 🔶 **Clientes** — grilla principal migrada (2026-08-05), 3 sub-grillas pendientes:
  - ✅ Grilla "clientes" (`clientes.list.js`, tab principal): `tables.py`, `views.py`, `urls.py` extendido, template HTMX (KPIs+tabla), `clientes_list.html` actualizado (chips por tipo vía `hx-get`), `clientes.list.js` recortado (delegación de clicks movida a `document.body`, scoping `#clientes-panel`). Reutiliza integramente los selectors ya existentes (`ClienteSelector.get_cliente_list/get_kpis/get_cartera_resumen`) — misma SSoT que la API DRF, sin duplicar lógica de agregación (a diferencia de Proyectos, donde hubo que construirla). Cubierto por `apps/tenant/clientes/tests/test_tabla_view.py` (2/2 OK): valida KPIs, filtro por tipo, y que la columna Cartera usa el mismo `get_cartera_resumen` de la API.
  - ⏳ Grilla "contactos" (mismo archivo `clientes.list.js`, tab secundario) — no migrada, Tabulator intacto.
  - ⏳ Grilla "historial de facturas" (dentro del offcanvas de detalle de cliente) — no migrada, Tabulator intacto.
  - ⏳ Grilla "cartera" / cuentas por cobrar (`clientes.cartera.js`, con flujo de registro de abonos) — archivo completo sin tocar, unidad separada por su complejidad (financiera, con formularios de abono).
  - Bug encontrado y corregido durante esta migración: `django_tables2`'s `table.page.object_list` devuelve objetos `BoundRow` (envoltorio de renderizado), no instancias del modelo — hay que acceder al modelo real vía `.record` (`row.record.uuid`, no `row.uuid`).
  - Se encontró `apps/tenant/clientes/templates/tenant/clientes/list.html` sin ninguna referencia (mismo patrón que ventas/proyectos) — delegado como tarea aparte.
- ⚠️ **Dashboard** — **excepción arquitectónica documentada, NO migrar**: `apps/tenant/dashboard/urls.py` está deshabilitado explícitamente ("API-First estricto v2.30 — no debe incluirse en `config/urls_tenant.py`"). Añadir una `SingleTableView` violaría esa regla. Ver Definition of Done §3: "o cuentan con una excepción arquitectónica documentada en SSoT".
- ✅ **Perfil** (1/1 grilla migrada, 2026-08-05): `tables.py`, `views.py`, `urls_ui.py`, `partials/tabla_perfiles.html`, `list.html` actualizado a HTMX, `perfil.page.js` recortado (delegación de clicks movida a `document.body`), `perfil.modals.js` actualizado. Replica exactamente el guard de seguridad `[SEG-5]` (un ADMIN nunca puede eliminar su propia fila) — cubierto por test nuevo `apps/tenant/perfil/tests/test_tabla_view.py` (2/2 tests OK).
- ⏸️ **Core** (1 archivo Tabulator, `common/tabulator.factory.js`) — **no es una grilla propia**, es la librería compartida que consumen los 9 módulos aún pendientes. Solo puede eliminarse al final, después de migrar todo lo demás.

#### Protocolo Estándar de Migración por Módulo:
1. **Crear `apps/tenant/<app_name>/tables.py`**: Declarar la clase `Table` heredando de `tables.Table`, consumiendo el Selector de la capa de servicios con campos filtrados explícitamente (`.only()`).
2. **Crear vistas HTML en `apps/tenant/<app_name>/views.py`**: Definir `SingleTableView` o `FilterView` usando `LoginRequiredMixin` + `SintelDSVMixin.get_empresa_id()`.
3. **Crear template partial `partials/tabla_<modelo>.html`**: Renderizar `{% render_table table %}` con plantilla Bootstrap 5.
4. **Actualizar `templates/tenant/<app_name>/<modelo>_list.html`**: Sustituir el div contenedor de Tabulator por un contenedor HTMX (`hx-get`, `hx-trigger="load, <evento> from:body"`).
5. **Recortar `static/<app_name>/js/features/<modelo>_list.js`**: Eliminar la inicialización de Tabulator, conservando únicamente la delegación de eventos del DOM y manejo de Offcanvas.

---

### 2.2 FASE 7 — Deuda de Testing y Aislamiento Multi-Tenant (TEST-C2)

**Objetivo:** Garantizar la prevención absoluta de IDOR y filtrado cruzado entre inquilinos mediante la incorporación de suites de prueba de aislamiento multi-tenant en todas las aplicaciones del ecosistema.

#### Matriz de Cobertura de Aislamiento Tenant (3 Niveles Exigidos por App):
1. **Prueba de Listado Isomórfico**: Verificar que `GET /api/v1/<app>/` retorne únicamente registros pertenecientes al `empresa_id` del usuario autenticado.
2. **Prueba Anti-IDOR Directo**: Verificar que `GET /api/v1/<app>/{uuid}/` de un registro perteneciente a *Tenant B* retorne `404 Not Found` al ser consultado por *Tenant A*.
3. **Prueba Anti-IDOR de Clave Foránea (DSV)**: Verificar que mutaciones (`POST`/`PUT`/`PATCH`) referenciando IDs de entidades relacionadas pertenecientes a otro tenant sean rechazadas con `400 Bad Request` o `404 Not Found`.

#### Roadmap de Implementación por Prioridad Financiera:

1. **`compras`**: Crear `test_multitenant_isolation.py` (ampliar cobertura mínima existente).
2. **`facturas`**: Crear `test_multitenant_isolation.py` para comprobantes de venta y compra.
3. **`contabilidad`**: Crear `test_multitenant_isolation.py` para asientos y plan de cuentas.
4. **`inventario`**: Crear `test_multitenant_isolation.py` para movimientos, bodegas y productos.
5. **Apps Restantes**: `core`, `empresa`, `perfil`, `empleados`, `proyectos`, `proveedores`, `clientes`, `cotizaciones`, `dashboard`.

#### Tareas Adicionales de Testing:
- **TEST-A2**: Corregir assertion tautológica `try/except: pass` + `assert True` en `tests/public/tenants/test_integrity.py:328`.
- **TEST-M1**: Triar y documentar las 26 pruebas con `@skip` en el repositorio para reactivar las aplicables o justificar las exenciones.
- **TEST-M2 (nuevo, 2026-08-05)**: `apps/tenant/proveedores/tests/test_idempotence_v2614.py::TestHTTPStatusCodesProveedores` (2 tests, `@pytest.mark.django_db(transaction=True)`) falla de forma reproducible con `POST /api/v1/proveedores/` → 404 y, en el teardown, `django.db.utils.NotSupportedError: cannot truncate a table referenced in a foreign key constraint` (Postgres, `perfil_tenantprofile` → `accounts_user`). Verificado con `git stash` que la falla es **idéntica en el estado base del repo** (sin ningún cambio de esta sesión) — no relacionado con la migración de Cuentas por Pagar. Candidato para la próxima ronda de TEST-M1.

---

### 2.3 FASE 10 — Gobernanza de CI, Docker y Validación Integrada de Entorno

**Objetivo:** Cerrar el ciclo de refactorización asegurando la validez en ejecución real (*runtime*) de todos los cambios aplicados y restableciendo el control de calidad automatizado estricto.

#### Acciones Requeridas:

1. **Validación Integrada en Entorno Docker/venv Funcional**:
   - Levantar stack de prueba y ejecutar la suite completa: `make dj-check && make test`.
   - Ejecutar pruebas manuales y e2e de los listados migrados a `django-tables2`.
2. **Endurecimiento de Integración Continua (CI)**:
   - Eliminar la cláusula `continue-on-error: true` para `ruff check` y `bandit` en `.github/workflows/ci-quality-gate.yml`.
3. **Consolidación de Migraciones de Base de Datos**:
   - Ejecutar `python manage.py squashmigrations gastos` y `proveedores` para consolidar historiales de migración fragmentados.
4. **Auditoría de Seguridad de Imágenes Docker**:
   - Verificar con `docker history` que ningún secreto ni archivo sensible (`.env`) quede embebido en las capas de construcción.

---

## 3. Matriz de Criterios de Aceptación (Definition of Done)

Para declarar formalmente finalizado el Plan de Refactorización de SINTEL v3.10.5+, se deben cumplir al 100% las siguientes condiciones:

- [ ] **Cero Errores de Sintaxis**: Todos los archivos `.py` del proyecto pasan `python -m py_compile` sin fallos ni advertencias de caracteres Unicode/emojis.
- [ ] **Aislamiento Multi-Tenant Cubierto**: El 100% de las `TENANT_APPS` cuentan con su respectivo archivo `test_multitenant_isolation.py` validando las 3 capas anti-IDOR.
- [ ] **Estandarización de Tablas**: Todas las aplicaciones CRUD han completado su transición a `django-tables2` + HTMX o cuentan con una excepción arquitectónica documentada en SSoT.
- [ ] **Gobernanza CI Activa**: La canalización de CI ejecuta y aprueba tests, linters (`ruff`) y escaneo de seguridad (`bandit`) sin banderas de tolerancia de error (`continue-on-error`).
- [ ] **Documentación Sincronizada**: `documentacion/arquitectura_general.md` y los archivos `.agent/AUDITORIA_FLUJO_*.md` reflejan con exactitud los endpoints, vistas y modelos vigentes en el proyecto.
