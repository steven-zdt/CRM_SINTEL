# AI_UI_01_AUDIT — Fase 0 (auditoria real, previa a implementar)

Mision: SINTEL-AI-UI-01 (2026-09-09). Auditoria exhaustiva del estado real
del Asistente IA antes de tocar codigo -- ningun cambio de produccion se
hizo antes de completar este documento.

## Resumen ejecutivo

**El backend transversal del Asistente IA ya existe y esta completo.**
AI-06 (Form Assistant, cerrado como PARCIAL el 2026-09-01) ya construyo:
un orquestador real que llama al LLM (`apps/services/ai/orchestrator/`),
un endpoint HTTP real y probado (`POST /api/v1/ai/ask/`), 20 tools
registradas (14 READ/SUGGEST + 6 VALIDATE, `AI_TOOL_REGISTRY.md`), y
retrieval semantico real conectado (`buscar_conocimiento`, AI-VECTOR-07,
ya incluido en el catalogo que ve el orquestador). La unica pieza
genuinamente faltante, confirmada por `AI_RELEASE_GATE.md` linea 253/275-277
("Lo que falta para que AI-06 sea VERIFIED no es backend: es integracion
en el frontend/UI"), es exactamente el objeto de esta mision: la UI.

Por lo tanto esta mision **NO crea backend nuevo** (Fase 1/2 de la mision
se resuelven por reutilizacion, no por implementacion) -- se enfoca
enteramente en Fase 3+ (UI, JS, tests de esa capa, documentacion).

## A. Que endpoint ya puede utilizarse

`POST /api/v1/ai/ask/` -- registrado en `config/api_urls.py:103`
(`path('ai/', include('apps.services.ai.api.urls'))`), incluido solo
desde `config/urls_tenant.py:159` (nunca desde `urls_public.py` -- no
aplica ADR-002/dual-registration, es un endpoint solo para usuarios
autenticados de un tenant, no reachable desde `home.sintel.net.co`
estatico).

- **ViewSet**: `apps/services/ai/api/viewsets.py` — `AIAssistantViewSet`,
  `viewsets.ViewSet` (no `BaseTenantViewSet`, mismo patron que
  `ReportingViewSet` -- no expone CRUD de un modelo Django).
- **Auth**: `[RelaxedJWTAuthentication, SessionAuthentication]` +
  `IsTenantMember` -- ningun permiso nuevo, reutiliza Dual-Auth existente.
- **Input**: `AIAskSerializer` (`message: str, screen: {app, entity,
  entity_id, operation}` opcional).
- **Output real** (no el ejemplo literal del mission brief -- adaptado a
  la convencion real del proyecto, ver seccion C mas abajo):
  ```json
  {"status": "OK|NO_TOOL|VALIDATION_ERROR|PERMISSION_DENIED|NOT_FOUND|CONFLICT|DOMAIN_ERROR|INTERNAL_ERROR",
   "tool_used": "buscar_cliente" | null,
   "data": [...] | null,
   "message": "..."}
  ```
- **Flags que gatean todo, en False por defecto en este entorno de
  desarrollo** (confirmado: `.env` no define ninguna variable `AI_*`, ni
  `docker-compose.yaml`): `AI_ENABLED`, `AI_READ_ENABLED`,
  `AI_RETRIEVAL_ENABLED`. Exponer la UI no habilita nada por si sola.
- **Tests HTTP ya existentes y en verde**: `test_ai06_http_endpoint.py`
  (5 tests: 403 deshabilitado, 400 mensaje vacio, 401 sin autenticar, 200
  flujo completo con tool real, `screen` se acepta y propaga).

## B. Que endpoint debe crearse

**Ninguno.** El brief de la mision sugeria `POST /api/v1/ai/assistant/`
como preferencia, pero su propia Fase 1 exige verificar rutas reales antes
de crear una nueva y evitar duplicar -- `/api/v1/ai/ask/` cumple
exactamente el contrato pedido (autentica, resuelve tenant, construye
AIContext, valida permisos/alcance, ejecuta el AI Engine, usa solo tools
autorizadas, usa retrieval cuando corresponde, responde apto para UI). Los
nombres de campo de la respuesta se adaptaron a la convencion real
(`tool_used`/`data`/`message` en vez de `sources`/`read_only` literales,
ver seccion C) en vez de forzar un segundo contrato paralelo.

## C. Que parte del backend ya puede reutilizarse sin modificacion

Todo. Especificamente:

1. **AIContext** (`apps/services/ai/context/ai_context.py`) — SSoT real,
   deriva `empresa_id`/`schema_name`/`rol`/`alcance` siempre de
   `request.user.tenant_profile`, nunca de lo que el cliente mande.
2. **AIEngine.run_tool()** (`apps/services/ai/engine/ai_engine.py`) —
   unico punto de ejecucion. Estructuralmente bloquea WRITE
   (`AUTO_APPROVED_KINDS` nunca incluye `ToolKind.WRITE`, sin excepcion
   aunque `AI_WRITE_ENABLED=True`) y nunca propaga tracebacks/SQL/secretos
   (`except Exception` generico -> `INTERNAL_ERROR`).
3. **AIToolRegistry** (`apps/services/ai/tools/registry.py`) — 20 tools ya
   registradas, semanticas (nunca `execute_sql`/`update_model` genericos).
4. **RetrievalTool / RetrievalService / pgvector** (AI-VECTOR-01..11A,
   `docs/ai/AI_VECTOR_POC_*`) — `buscar_conocimiento` ya esta en el
   catalogo que ve el orquestador (`tool_metadata()`), doble gate
   (`AI_RETRIEVAL_ENABLED` global + `AIKnowledgeSettings.retrieval_enabled`
   por tenant). Piloto real activo hoy solo en el tenant `home` (1
   documento real indexado, `AI-VECTOR-11.1`).
5. **Orquestador** (`apps/services/ai/orchestrator/form_assistant.py`) —
   decide 1 tool via LLM (prompt de texto plano + JSON, no tool-use nativo
   de Anthropic), guardrail de prompt injection ya implementado (el
   mensaje del usuario se pasa como dato, nunca concatenado a `system`).

**Limitacion real encontrada (no arreglada en esta mision, documentada
honestamente):** `buscar_producto` (`apps/services/ai/tools/
inventario_tools.py`) envuelve `ProductoSelector.get_list(empresa_id,
search)`, que **no acepta un parametro de ordenamiento** (verificado:
ningun `ProductoSelector`/`ClienteSelector`/etc. en
`apps/tenant/inventario/services/selectors.py` acepta `ordering`). Una
pregunta como "¿que productos tienen menor stock?" (ejemplo literal del
mission brief) devuelve productos con su `stock_actual` real, pero **no
ordenados por stock ascendente** — el usuario ve datos reales, solo no
pre-ordenados por el campo que pidio. No se modifico el selector de
`inventario` para esto (fuera del alcance minimo de una mision de UI,
tocaria una app de dominio distinta) — queda **DEFERRED**, ver
`AI_UI_01_EXECUTION.md`.

## D. Que parte de UI existe

**Ninguna para el asistente transversal.** Grep exhaustivo
(`asistente-ia`, `Sintel.AI`, `AIEngine`, `/ai/ask/`) antes de esta mision
no encontro ningun boton, offcanvas, ni modulo JS para el Asistente IA
global -- confirma `AI_RELEASE_GATE.md`: "PARCIAL... falta integracion en
el frontend/UI".

**Existe, pero es un feature distinto (no confundir, mandato explicito de
la mision):** el "Asistente Contable" puntual dentro de
`apps/tenant/contabilidad/` (`pendiente_offcanvas_contabilizar.html`,
boton "Diligenciar con IA", icono `bi-stars`) — llama a
`/api/v1/contabilidad/pendientes/asistente-ia/` (un endpoint de dominio
especifico, no el AI Engine transversal), usa el patron viejo de
`fetch()`+meta-tag CSRF. Se reutilizo su icono (`bi-stars`, unico
precedente real de "icono de IA" en este codebase) para el boton nuevo,
pero **no se copio su codigo JS** (usa `Sintel.Core.Http` en su lugar, ver
seccion E).

## E. Que parte falta (lo que esta mision construye)

Infraestructura frontend reutilizable identificada antes de escribir
codigo (auditoria delegada, verificada archivo por archivo):

| Pieza | Ubicacion real | Uso en esta mision |
|---|---|---|
| Offcanvas seguro | `core/js/common/offcanvas.helper.js` -> `Sintel.Core.mostrarOffcanvasSeguro` | Unico mecanismo permitido para abrir el panel (AGENTS.md Sec.26 prohibe `getOrCreateInstance()` directo) |
| Cliente HTTP | `core/js/lib/core-http.js` -> `Sintel.Core.Http` | CSRF (cookie) + JWT (`getValidAccessToken()`) automaticos, nunca manejados a mano |
| Errores/feedback | `core/js/lib/ui-manager.js` -> `window.showError`/`UIManager` | Convencion del proyecto: no crear un toast propio |
| Header/navbar | `tenant/partials/_header.html` | Punto de insercion del boton global, junto al dropdown de cuenta |
| Namespace transversal | `core/js/common/` (precedente directo: `reporting.api.js` -> `Sintel.Reporting.API`) | Ubicacion del modulo nuevo (no un `<app>.api.js` por app) |
| Icono | `bi-stars` (Bootstrap Icons, ya cargado globalmente) | Unico precedente real de "icono de asistente IA" en el codebase |

Construido en esta mision (ver `AI_UI_01_EXECUTION.md` para el detalle
completo): el boton global, el panel offcanvas, el modulo
`window.Sintel.AI`, y los tests focalizados (backend HTTP de seguridad +
frontend Playwright).

## Riesgos/limitaciones encontrados durante la auditoria (no inventados, documentados)

1. **Este entorno de desarrollo no tiene `AI_ENABLED`/`ANTHROPIC_API_KEY`
   configurados** (`.env` sin ninguna variable `AI_*`). Un flujo E2E con
   respuesta real del LLM requiere que el usuario decida habilitarlo y
   provea una API key -- accion que esta sesion no puede tomar por si
   sola (entrada de credenciales), ver `AI_UI_01_EXECUTION.md` Fase 10.
2. **El sandbox del Browser tool de esta sesion bloquea
   `net::ERR_BLOCKED_BY_CLIENT` cualquier peticion a `/api/v1/core/*`**
   (confirmado con las 2 rutas que el login real necesita:
   `/api/v1/core/landing/info/` y `/api/v1/core/auth/login/`), incluso
   con credenciales reales provistas por el usuario. No es un bug de esta
   mision -- impide la verificacion manual interactiva en este entorno
   especifico.
3. **Node.js/npm no esta instalado en esta maquina** (`npm`/`node` no
   resueltos en PATH de Bash ni PowerShell) -- la suite Playwright
   existente (`tests/e2e/`) no pudo ejecutarse en esta sesion. El spec
   nuevo (`70-ai-ui-01-assistant.spec.js`) se escribio siguiendo el patron
   real ya establecido (`_helpers.js`, specs existentes) pero queda sin
   ejecutar hasta que el usuario corra `npm install && npx playwright
   install chromium && npm test` (README ya documenta el flujo).
4. **`buscar_producto` no soporta ordenar por stock ascendente** (item C
   arriba) -- DEFERRED, no se toco `apps/tenant/inventario/`.
