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
| **Fase 5-BIS** | Reemplazo de Tabulator por `django-tables2` + HTMX | 🔄 Parcial (7/16 apps) | `REPORTE_FASE_5_PILOTO_TABLAS.md`, `REPORTE_FASE_5_BIS_*` |
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
- 🔶 **Proveedores** — grilla "Directorio" migrada (2026-08-05), 2 unidades pendientes:
  - ✅ Grilla "Directorio de Proveedores" (`proveedores_main.js`): `tables.py` (con `row_attrs` para click-en-fila → abre detalle, replicando el `rowClick` de Tabulator), `views.py`, `urls.py` extendido, template HTMX, `proveedores_list.html` Tab 1 actualizado, `proveedores_main.js` recortado de ~280 a ~90 líneas. Reutiliza `ProveedorSelector.get_list/get_cuentas_pagar_resumen` (misma SSoT que la API). Cubierto por `apps/tenant/proveedores/tests/test_tabla_view.py` (2/2 OK) — requirió agregar migración de `facturas` al fixture `tenant` del conftest (la cartera de CxP lee `Factura.naturaleza=COMPRA`).
  - ⏳ Grilla "Cuentas por Pagar" (`cuentas_pagar_list.js`, Tab 2) — no migrada, Tabulator intacto.
  - ⏳ Historial de compras (dentro del offcanvas de detalle, `proveedores_form.js`) — no migrado, Tabulator intacto.
  - Representantes (Tab 3) no usa Tabulator, no aplica a esta fase.
- 🔶 **Empresa** — grilla "Sede" migrada (2026-08-05), 3 pendientes:
  - ✅ Grilla "Sede" (`sede_list.js`): `tables.py`, `views.py`, ruta agregada a `urls_ui.py` (ver nota abajo), template HTMX, `empresa_list.html` Tab 2 actualizado, `sede_list.js` recortado. Reutiliza `SedeSelector.get_list` existente. Cubierto por `apps/tenant/empresa/tests/test_tabla_sedes_view.py` (2/2 OK).
  - **Nota de arquitectura descubierta:** `apps/tenant/empresa/urls_ui.py` tiene un docstring "DEPRECADO — todas las rutas retornan 404", pero eso aplica solo a una ruta legacy puntual (`empresa-card-partial`), no a todo el archivo — el grid real de Sede vive en `empresa_list.html` dentro del tab activo de `workspace.html` (patrón estándar, igual que las demás apps), no en el shell estático paralelo `core/static/tenant/core/empresa/index.html` (ese es una ruta legacy deliberada y con su propio smoke test, `/empresa/` y `/empresas/` redirigen ahí — no se tocó).
  - ⏳ Área (`area_list.js`), Empresa/singleton (`empresa_list.js`), MailInboxConfig (`mailinboxconfig_list.js`) — no migrados, Tabulator intacto.

### Hallazgo transversal: bug de `empty_values` en las 5 tablas de esta sesión

Al construir el test de Sede se descubrió que `django-tables2` solo invoca `render_<campo>()` cuando el valor de la celda **no** está en `Column.empty_values` (por defecto `(None, '')`). Con un campo `blank=True` vacío (`""`), la librería nunca llama al render personalizado — muestra su propio placeholder genérico en su lugar, silenciosamente, sin excepción ni test que lo detecte a menos que se verifique explícitamente el texto esperado ("Sin asignar", "—", etc.) en un campo vacío. Esto afectaba potencialmente a **todas las columnas con `render_X` que manejan el caso vacío** en las 5 tablas construidas esta sesión (Perfil, Proyectos, Clientes, Proveedores, Empresa/Sede) — corregido agregando `empty_values=()` a cada columna afectada, y re-verificado con la suite completa (9/9 tests OK tras el fix). Aplica también como advertencia para cualquier tabla `django-tables2` futura en este proyecto: si `render_<campo>` tiene lógica para "sin dato", la columna necesita `empty_values=()` explícito.
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
