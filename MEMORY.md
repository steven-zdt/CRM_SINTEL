# 🧠 Memory Bank - SINTEL ERP

**Propósito:** Mantener un registro persistente a largo plazo del estado del proyecto, contexto activo y decisiones arquitectónicas (ADRs) para evitar refactorizaciones cíclicas o regresiones por pérdida de contexto del modelo.

---

## 🏗️ 1. Decisiones Arquitectónicas (ADRs) Establecidas e Inmutables

Estas decisiones ya han sido tomadas y consolidadas en el código. **No deben ser refactorizadas ni cuestionadas.**

*   **ADR-001: Feature-Sliced Design (FSD)**
    *   Cada modelo tiene un ecosistema aislado en el frontend y backend.
    *   Prohibido compartir plantillas monolíticas (ej. `modals.html`).
*   **ADR-002: Service Layer Pura**
    *   `crud_service.py`: Única capa con transacciones a BD.
    *   `business_service.py`: Única capa para lógica, idempotencia y validación IDOR.
    *   `selectors.py`: Única capa para queries GET, uso estricto de `.only()`.
*   **ADR-003: Aislamiento Multi-Tenant (Zero-Trust)**
    *   Todo modelo tenant hereda de `SintelTenantBaseModel` obligatoriamente.
    *   Toda mutación DML filtra y valida explícitamente `empresa_id`.
*   **ADR-004: Bridge de Esquema Público**
    *   Solo `apps/tenant/core` y `apps/tenant/api` pueden interactuar con el esquema `public`.
    *   Las demás apps usan `apps.tenant.core.services.membership`.
*   **ADR-005: Integración Contable Unificada**
    *   Ningún módulo crea `AsientoContable` directamente.
    *   Todos delegan a `Contabilizador(empresa_id).contabilizar(dto)`.
*   **ADR-006: Frontend Reactivo (Server-Driven)**
    *   Grillas: migracion en curso de Tabulator a `django-tables2` + HTMX (server-rendered, decision 2026-08-03 — ver `documentacion/PLAN_UNICO_CORRECCIONES.md` Fase 5-BIS). `gastos`, `facturas`, `compras` ya migradas; ~16 apps siguen en Tabulator hasta que la expansion continue.
    *   HTMX para acciones asíncronas y Out-of-Band (OOB) swaps.
    *   Offcanvas: siempre via `window.Sintel.Core.mostrarOffcanvasSeguro(el)` (`core/js/common/offcanvas.helper.js`), nunca `getOrCreateInstance()` directo.

---

## 📌 2. Contexto de Implementaciones Recientes

*   **2026-05-04 | Módulo Proyectos:** Se implementó control de errores SQL explícito (`IntegrityError`) convirtiendo violaciones 500 en respuestas 400 controladas en `save_proyecto`.
*   **2026-05-04 | Módulo Facturas:** Expansión del `FacturaListSerializer` para incluir snapshots históricos (`emisor_razon_social`, `receptor_razon_social`). UI en Tabulator actualizada, deprecando la columna redundante "Cliente".
*   **2026-05-04 | Módulo Clientes (Hotfix v2.62.1):** 
    *   **UI/Frontend:** Sincronización de IDs DOM en Offcanvas y creación de SSoT inmutable en JavaScript (`DOM`).
    *   **Backend (DRF):** Resolución de error 500 (`TypeError: unexpected keyword argument 'id'`) igualando la firma de las acciones (`id=None`) con `lookup_url_kwarg='id'`.
    *   **Backend (Service Layer):** Resolución de error 500 (`AttributeError: no attribute 'contacto_selector'`) mediante la herencia estricta de `ContactoClienteServiceMixin` en el `ClienteViewSet` para asegurar la inyección de dependencias entre dominios relacionados.
*   **2026-05-06 | Modulo Gastos + Docker:** Se corrigio el arranque Docker forzando `DATABASE_HOST=db` en `web` y `celery`. Se estabilizo `apps/tenant/gastos` corrigiendo referencias ORM, templates HTMX, contrato JSON de creacion, cache de resolucion sin signals, fallback de empresa para sesiones y compatibilidad de `DocumentoSoporte`. Validado con `py_compile`, `manage.py check`, `pytest apps/tenant/gastos/tests -q` (6 passed) y contenedores Docker activos.
*   **2026-05-06 | Antigravity MCP + Skills:** Se amplio `sintel_agent_unified.py` para descubrir skills en carpetas `SKILL.md`, skills markdown legacy bajo `.agents/skills/<grupo>/<skill>.md`, `.antigravity/skills` y `documentacion/skills`. Se agrego el skill `.antigravity/skills/sintel-antigravity-mcp` y la skill workflow `.agents/skills/workflow/antigravity-mcp.md`.
*   **2026-05-06 | Antigravity Flash Oficial:** Se validaron fuentes oficiales de Google sobre Antigravity y Gemini 3 Flash. Se agregaron herramientas MCP `antigravity_official_context`, `antigravity_flash_brief` y `antigravity_flash_check`, mas la guia `documentacion/ANTIGRAVITY_FLASH_OFICIAL.md`, para respuestas Flash breves, verificables y con fuente oficial cuando aplique.
*   **2026-05-06 | Generalizacion MCP Por App:** Se elimino dependencia de apps concretas en las herramientas nuevas. `check_infrastructure_health` ya no usa tabla default de un modulo, `antigravity_flash_brief` detecta cualquier app tenant dinamicamente y se agrego `sintel_app_quality_plan(app_name, scope)` como marco reusable para auditoria, validacion y handoff de cualquier `apps/tenant/<app_name>`.
*   **2026-06-05 | Nueva app `bancos`:** Estados de cuenta bancarios y conciliacion manual via UUID soft-references (`CuentaBancaria`, `ExtractoBancario`, `TransaccionBancaria`).
*   **2026-06-17 | Nueva app `compras`:** `OrdenCompra` + `ItemOrdenCompra`.
*   **2026-06-17 | Nueva app `ventas`:** `OrdenVenta` completa (Fases 1-5) — `ResolucionFacturacion`, `Venta`, `ItemVenta`.
*   **2026-07-26 | Auditoria Enterprise:** Auditoria integral (`documentacion/AUDITORIA_ENTERPRISE_2026-07-26.md`, ~158 hallazgos, 6 tracks en paralelo). Reemplazo por `documentacion/PLAN_UNICO_CORRECCIONES.md` como plan operativo (el §8 original de la auditoria queda como referencia historica, el plan unico tiene cobertura del 100% de los hallazgos trazables a una fase).
*   **2026-07-26/08-03 | Fases 1-4 (CRITICOS + ARQ-A + SEC-A/M + PERF-A/M) — COMPLETADAS:** `DJANGO_DEBUG` falla-cerrado por defecto; IDOR cerrado en `ItemFacturaViewSet`/`NotaCreditoViewSet`; `UniqueConstraint` en `AsientoContable` + `select_for_update()` en consecutivo de `Factura`; UUID corrompido por `parseInt()` corregido en `inventario_editor.js`; colision de `http.js` (anulaba JWT) corregida; `facturas/models.py` ya no importa `contabilidad.Retencion` directo; 3 ViewSets migrados a `lookup_field='uuid'`; XSS/XXE cerrados; N+1 de Facturas resuelto (~140→~10 queries/pagina); `ventas` con test de aislamiento (antes sin tests); CI real conectado (`ci-quality-gate.yml`). Detalle: `REPORTE_FASE_{1,2,3,4}.md`.
*   **2026-08-03/04 | Fase 5-BIS (piloto Tabulator→django-tables2, PARCIAL):** `gastos`, `facturas`, `compras` migrados a tablas server-rendered (`django-tables2`+HTMX), reemplazando Tabulator. `contabilidad` migrado 5/8 grillas (`cuenta`, `periodo`, `asiento`, `retencion`, `plantilla`) — las 3 restantes (`pendientes`, `libro-diario`, `reportes`) quedan deliberadamente fuera de este patron por ser vistas agregadas cross-app, no listados CRUD de un solo modelo (ver `REPORTE_FASE_5_BIS_CONTABILIDAD.md` §2). `ventas` migrado 1/1 grilla real (`venta_list.js`) — los otros 2 archivos que el plan le asignaba (`resolucion_list.js`, `orden_list.js`) resultaron ser codigo no conectado al DOM actual; **no se borraron** porque `orden_list.js`/`orden_editor.js` son parte de trabajo reciente en progreso ("OrdenVenta v3.10.5", commits mas nuevos del repo), no arquitectura abandonada — su destino queda para que el usuario decida (ver `REPORTE_FASE_5_BIS_VENTAS.md` §0). `bancos` migrado 2/2 grillas reales (`cuenta`, `extracto`) — el tercer archivo del plan (`transaccion_list.js`) nunca existió (las transacciones ya se renderizan server-side dentro del offcanvas de detalle de extracto). Particularidad de `bancos`: usa un orquestador centralizado (`bancos.main.js`) que maneja toda la delegacion de acciones de fila via `document.body` — no se tocó, los botones nuevos conservan el mismo atributo `data-id`/clases que usaba Tabulator. `empleados` migrado 5/5 grillas (`empleado`, `contrato`, `resolucion`, `nomina`, `liquidacion`) — las 2 ultimas (`nomina`, `liquidacion`) usan layout Master-Detail (grilla de empleados + historial del seleccionado), resuelto con `Meta.row_attrs` de django-tables2 (inyecta `hx-get`/`hx-target` por fila del master, sin JS de terceros) — ver `REPORTE_FASE_5_BIS_EMPLEADOS.md` §3 para el diseño completo. `nomina_historial.js` (un 6to archivo del inventario original) resultó ser codigo muerto (cargado pero sin boton que lo invoque, superado por el Master-Detail) — no tocado. Particularidad de `empleados`: su orquestador (`empleados.module.js`) ya tenia lazy-loading real por sub-tab (`shown.bs.tab`), preservado usando `hx-trigger="shown.bs.tab from:#tab-X once"` en vez del `hx-trigger="load"` usado en el resto de apps (evita cargar Contratos/Resoluciones si el usuario nunca visita esas pestañas). Nota especifica de `contabilidad`/`ventas`/`bancos`/`empleados`: su UI vive como sub-tabs/paneles dentro de `workspace.html` (no paginas propias como gastos/facturas/compras), pero el patron HTMX funciono sin problemas mayores. Decision del usuario: no gatear la expansion con validacion en runtime — se acumula todo el trabajo y se valida una sola vez al final (pendiente, requiere Docker/venv). Detalle: `REPORTE_FASE_5_PILOTO_TABLAS.md`, `REPORTE_FASE_5_BIS_CONTABILIDAD.md`, `REPORTE_FASE_5_BIS_VENTAS.md`, `REPORTE_FASE_5_BIS_BANCOS.md`, `REPORTE_FASE_5_BIS_EMPLEADOS.md`.
*   **2026-08-03 | Fase 5 (Frontend FE-A/FE-M) — COMPLETADA:** Guard anti-doble-init en 19 `*_editor.js` (varios con bug real de POST duplicado, no solo el hallazgo original); helper centralizado `offcanvas.helper.js` reemplaza 14 reimplementaciones de `mostrarOffcanvasSeguro`; `setData()`→`replaceData()`; CSRF centralizado via `window.getCookie()`; rutas de estaticos de `facturas`/`inventario` normalizadas. Detalle: `REPORTE_FASE_5.md`.
*   **2026-08-03 | Fase 6 (Simplificacion/Dedup/Codigo muerto) — COMPLETADA:** `StandardResultsSetPagination` unificada a 20/200 (encontrado un shadow-import roto en `clientes` que anulaba en silencio un import ya correcto); 50 archivos huerfanos eliminados (un cluster completo de arquitectura "workspace" alternativa abandonada, nunca limpiada); limpieza de raiz. Detalle: `REPORTE_FASE_6.md`.
*   **2026-08-03 | Fase 8 (DevOps/Dependencias) — COMPLETADA:** `.dockerignore` nuevo (antes `.env` se copiaba a cada capa de imagen); usuario no-root en `Dockerfile` (**no verificado en runtime**); `POSTGRES_PASSWORD` sin fallback debil; puertos 5432/6379 restringidos a localhost en dev; healthchecks reales; `pip-audit` agregado; limites de version en 4 dependencias. Detalle: `REPORTE_FASE_8.md`.
*   **2026-08-03 | Fase 9 (Documentacion) — COMPLETADA, incidente resuelto:** Indice de apps y tabla de tests de `arquitectura_general.md` actualizados; referencias rotas (`REFACTORIZAR_DESACOPLAMIENTO_CONTABLE_FRAMEWORK.md`, `AUDITORIA_INVENTARIO.md`) corregidas; `INFORME_AUDITORIA_TENANT_APPS.md` marcado historico; `CLAUDE.md` consolidado para referenciar `AGENTS.md` (decision del usuario) en vez de duplicar contenido. **INCIDENTE (resuelto 2026-08-04):** al limpiar emojis de 46 archivos `.py` (regla `[CRITICAL] 0` de AGENTS.md), un paso de limpieza de espacios colapso la indentacion de Python en los 46 archivos (`SyntaxError`/`IndentationError` confirmado). Todos tenian cambios previos del usuario sin commitear — no se pudo revertir a HEAD sin perder ese trabajo. El usuario restauro los 46 archivos desde dos backups propios (`crm_sintel-01-06-2026` para 45 de ellos; `crm_sintel_antesde_despliegue` para `apps/tenant/core/api/viewsets.py`, validado con diff contra HEAD tras normalizar CRLF — resulto ser evolucion incremental legitima, agrega el endpoint `resend_activation_code` y el flujo dual-schema de `activate_with_code` del ADR-002). **Los 46 archivos compilan limpio (`py_compile`), confirmado 2026-08-04.** Lista completa de archivos afectados en `REPORTE_FASE_9.md` §"Incidente". ARQ-M (naming `.agent/` de ventas, `.all()` sin `.only()` en FK de serializers) quedo documentado pero sin tocar, por precaucion tras el incidente — pendiente para una pasada futura de menor presion.
*   **Fase 7 (Testing) — pendiente, deliberadamente al final** por instruccion explicita del usuario ("deja las pruebas como ultima tarea").

---

## 🚧 3. Estado Activo (Active Context)

*   **Fase Actual:** Plan Único de Correcciones (ver `documentacion/PLAN_UNICO_CORRECCIONES.md`) — Fases 1-6, 8 y 9 completadas. Fase 5-BIS (Tabulator→django-tables2) parcial: `gastos`/`facturas`/`compras` completos, `contabilidad` 5/8 grillas, `ventas` 1/1 grilla real, `bancos` 2/2 grillas reales, `empleados` 5/5 grillas (completo, incluye Master-Detail). **Fase 7 (Testing) queda deliberadamente para el final**, por instrucción explícita del usuario.
*   **Modo:** EN DESARROLLO (Development Mode)
*   **Incidente Fase 9 (corrupcion de 46 archivos .py) — RESUELTO 2026-08-04:** los 46 archivos fueron restaurados desde backups del usuario y compilan limpio. Ya no es un bloqueo. Detalle en `REPORTE_FASE_9.md` §"Incidente".
*   **Bloqueos Conocidos (transversales a todas las fases):** sin Docker/venv funcional en el entorno usado para este plan (red de contenedores rota, puertos ocupados por otro proyecto, `venv` apunta a un intérprete inexistente; confirmado de nuevo 2026-08-04, `manage.py check` falla con `ModuleNotFoundError: No module named 'django'`). Toda corrección se verificó con `py_compile`/`node --check` + lectura manual, **no** con `make dj-check`/`make test` reales. Antes de dar cualquier fase por cerrada en producción: ejecutar esa validación real.
*   **Próximos Pasos:**
    1. `make dj-check && make test` en un entorno funcional — confirma retroactivamente Fases 1-6/8/9, incluida la restauración de los 46 archivos y la migración de `contabilidad`.
    2. Fase 5-BIS: siguiente es el resto (~11 apps: `inventario`, `cotizaciones`, `proveedores`, `empresa`, `proyectos`, `clientes`, `dashboard`, `perfil`, `core`). `contabilidad` quedó con 3 grillas (`pendientes`, `libro-diario`, `reportes`) deliberadamente sin migrar — ver `REPORTE_FASE_5_BIS_CONTABILIDAD.md` §2. `ventas` quedó con 2 archivos sin tocar por ser trabajo en progreso ajeno a esta fase — ver `REPORTE_FASE_5_BIS_VENTAS.md` §0 antes de asumir que son candidatos a limpieza. `empleados` quedó completo (5/5).
    3. Fase 7 (Testing) al final, incluyendo backfill de `test_multitenant_isolation.py` en ~14 apps y decisión sobre los 3 tests de `test_workspace_facturas_*.py` que quedaron referenciando archivos ya eliminados (Fase 6).

---

*Nota para Antigravity: Lee y actualiza este archivo (MEMORY.md) periódicamente a medida que avances en tareas complejas para no perder el hilo lógico de la implementación.*
