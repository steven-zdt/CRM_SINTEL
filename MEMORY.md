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
    *   Tabulator para grillas (SSoT de datos en memoria UI).
    *   HTMX para acciones asíncronas y Out-of-Band (OOB) swaps.

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

---

## 🚧 3. Estado Activo (Active Context)

*   **Fase Actual:** 🚧 Desarrollo Activo (Refactorización y Estabilización UI/UX)
**Modo:** EN DESARROLLO (Development Mode)
*   **Tarea en Curso:** Ninguna. (Esperando siguiente directiva).
*   **Bloqueos Conocidos:** Ninguno.
*   **Próximos Pasos Posibles:**
    *   Validar flujos adicionales de otros módulos si presentan el mismo patrón de error 500.
    *   Explorar automatización de DIAN / n8n.

---

*Nota para Antigravity: Lee y actualiza este archivo (MEMORY.md) periódicamente a medida que avances en tareas complejas para no perder el hilo lógico de la implementación.*
