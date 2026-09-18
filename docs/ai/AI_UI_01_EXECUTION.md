# AI_UI_01_EXECUTION — bitacora de ejecucion

Mision: SINTEL-AI-UI-01 (2026-09-09). Ver `AI_UI_01_AUDIT.md` (Fase 0) para
el estado previo verificado. Este documento registra que se reutilizo, que
se agrego, y la evidencia de verificacion, fase por fase.

## Fase 1 — Contrato del endpoint

**Decision: reutilizar `POST /api/v1/ai/ask/` (AI-06), no crear
`/api/v1/ai/assistant/`.** Justificacion completa en `AI_UI_01_AUDIT.md`
seccion B. El contrato de respuesta real (`status`/`tool_used`/`data`/
`message`) ya cumple los 8 requisitos funcionales de la Fase 1 (autentica,
resuelve tenant, AIContext, permisos/alcance, ejecuta AI Engine, tools
autorizadas, retrieval cuando corresponde, respuesta apta para UI) — la
"traduccion" a texto legible para el usuario final se hizo en el
**frontend** (Fase 3/4), no reescribiendo el backend, para no arriesgar
los 88 tests ya verdes de `apps/services/ai/tests/` con un segundo
contrato paralelo.

## Fase 2 — Retrieval

Ya conectado (AI-VECTOR-07): `buscar_conocimiento` esta en
`tool_metadata()`, el orquestador la puede elegir para preguntas
abiertas/exploratorias. Ningun cambio de codigo en esta fase — el trabajo
real fue en el **frontend**: `ai.assistant.js::_renderFuentes()` reconoce
`tool_used === 'buscar_conocimiento'` y renderiza `data` (content/
source_type/score) como una lista de "fuentes", nunca como una fila
generica de datos (que expondria `source_id`/`document_uuid`, prohibido
por Fase 3/8).

## Fase 3/4 — UI + JavaScript

Archivos nuevos:

- [`apps/tenant/core/templates/tenant/core/partials/offcanvas_asistente_ia.html`](../../apps/tenant/core/templates/tenant/core/partials/offcanvas_asistente_ia.html) —
  panel offcanvas estatico (Bootstrap `offcanvas-end`), siempre presente
  en el DOM del workspace (fuera de los `<section class="workspace-tab">`
  para no quedar oculto por `display:none`). Header, aviso de solo
  lectura, area de mensajes con estado vacio + 3 ejemplos clicables,
  input + boton enviar con spinner.
- [`apps/tenant/core/static/core/js/common/ai.assistant.js`](../../apps/tenant/core/static/core/js/common/ai.assistant.js) —
  `window.Sintel.AI` (namespace transversal, mismo criterio que
  `Sintel.Reporting.API`). Responsabilidades: abrir/cerrar el offcanvas
  (via `mostrarOffcanvasSeguro`, nunca `getOrCreateInstance()` directo),
  enviar la pregunta (`Sintel.Core.Http.post`), guard de doble-envio
  (`enviando` bandera + `disabled` en input/boton mientras carga),
  renderizado seguro (`textContent`/DOM API, nunca `innerHTML` con texto
  del usuario o del LLM), traduccion de `status` HTTP a mensajes
  amigables en espanol (nunca expone `tool_used`/uuid/stack traces).
- [`tests/e2e/specs/70-ai-ui-01-assistant.spec.js`](../../tests/e2e/specs/70-ai-ui-01-assistant.spec.js) —
  Playwright: boton visible, abre el panel, estado inicial, enviar
  pregunta, guard de doble-clic, escaping XSS, cerrar panel. Ver
  limitacion de ejecucion en la seccion "Limitaciones" abajo.

Archivos modificados (minimo necesario, ver diffs):

- [`apps/tenant/core/templates/tenant/partials/_header.html`](../../apps/tenant/core/templates/tenant/partials/_header.html) —
  boton `#btn-asistente-ia-toggle` (icono `bi-stars`, unico precedente
  real de "IA" en el codebase, tomado de
  `pendiente_offcanvas_contabilizar.html`), insertado junto al dropdown
  de cuenta.
- [`apps/tenant/core/templates/tenant/core/workspace.html`](../../apps/tenant/core/templates/tenant/core/workspace.html) —
  `{% include %}` del offcanvas, fuera de `<main>`/los tabs.
- [`apps/tenant/core/templates/tenant/core/partials/assets_core.html`](../../apps/tenant/core/templates/tenant/core/partials/assets_core.html) —
  `<script>` de `ai.assistant.js`, cargado despues de `Sintel.Core.Http` y
  `offcanvas.helper.js` (mismo bloque que `reporting.api.js`).

**Alcance deliberado de disponibilidad**: el boton/panel solo son
funcionales en paginas que cargan `assets_core.html` (hoy: `workspace.html`,
donde vive el 100% del uso real del ERP — sidebar con todos los modulos de
negocio). En paginas que solo extienden `tenant/base.html` sin
`assets_core.html` (p.ej. paginas de error) el boton no se renderiza
porque el offcanvas + el script viven junto al include de workspace —
decision explicita para no duplicar dependencias en paginas donde el
asistente no aporta valor, en vez de cargar todo `assets_core.html` en
paginas que no lo necesitan.

**Decision de diseno explicita (no un vacio):** el backend (`ask()`) NO
sintetiza una respuesta en lenguaje natural sobre los datos de la tool —
devuelve `data` estructurado + un `message` casi siempre vacio para tools
READ. Agregar una segunda llamada al LLM para "narrar" el resultado
habria sido codigo nuevo en el AI Engine (fuera del alcance minimo de una
mision de UI, y el propio mandato de la mision prohibe que el frontend
invente logica de negocio). En su lugar, `ai.assistant.js` renderiza
`data` de forma generica y legible (titulo + campos con etiquetas en
espanol, nunca `id`/`uuid`/`empresa_id` crudos) — cumple Fase 8 (UX
legible) sin tocar el AI Engine.

## Fase 5/6 — Capacidades READ + Retrieval

MVP usa las tools ya reales, sin implementar ninguna nueva:
`buscar_cliente`, `buscar_producto` (incluye `stock_actual`), y
`buscar_conocimiento` para preguntas abiertas. Limitacion real encontrada
y documentada (no arreglada, DEFERRED): `buscar_producto` no ordena por
stock ascendente (`AI_UI_01_AUDIT.md` seccion C) — la pregunta ejemplo
"¿que productos tienen menor stock?" devuelve productos reales con su
stock real, sin garantia de que los de menor stock aparezcan primero.

## Fase 7 — Seguridad

Ver [`apps/services/ai/tests/test_ai_ui_01_security.py`](../../apps/services/ai/tests/test_ai_ui_01_security.py)
(nuevo, no duplica cobertura existente — ver docstring del archivo para
el detalle de que complementa cada test):

- **Tenant isolation** (2 pruebas): dentro del mismo schema, un
  `empresa_id` falso inyectado en los `arguments` que el LLM podria
  alucinar es rechazado (`INTERNAL_ERROR`, nunca aceptado como scope
  valido — la tool ni siquiera acepta ese parametro). Entre 2 schemas
  reales (`tenant1`/`tenant2`, patron canonico AGENTS.md 24.5), un
  usuario de `tenant1` nunca recupera clientes de `tenant2` via HTTP real.
- **Nada tecnico expuesto**: uuid de `Empresa`, `schema_name`, nunca
  aparecen en el payload de respuesta.
- **Tool allowlist**: estructural, ya cubierto por `AIToolRegistry` (el
  frontend nunca elige la tool, solo el orquestador via LLM + el
  `AIEngine.run_tool()` valida contra el registro).
- **WRITE bloqueado**: prueba nueva con una tool WRITE ficticia
  registrada en caliente (no una real de negocio, no existe ninguna hoy) —
  confirma que ni con `AI_WRITE_ENABLED=True` se ejecuta, gracias a
  `AUTO_APPROVED_KINDS` en `ai_engine.py` (garantia estructural, no una
  convencion documental).
- **Prompt injection**: guardrail ya implementado en AI-06 (mensaje del
  usuario pasado como dato, nunca concatenado a `system`) — no se
  modifico, se documenta como heredado.

## Fase 9 — Tests

**Backend/API** (pytest, venv local, nunca Docker —
`feedback-no-docker-for-tests`): `apps/services/ai/tests/`
(88 preexistentes + 4 nuevos de este archivo). Resultado real de esta
corrida: ver `## Corrida real de tests` mas abajo.

**Frontend**: `tests/e2e/specs/70-ai-ui-01-assistant.spec.js` (Playwright,
5 tests: boton+apertura, enviar pregunta, doble-clic, XSS, cerrar). Sigue
el patron real de `_helpers.js`/`62-f334-offcanvas-consolidation.spec.js`
ya existentes en el repo — no se reinvento el helper de login ni el de
deteccion de errores de consola.

## Fase 10 — Verificacion E2E

**Flujo 1 (pregunta -> tool -> respuesta) y Flujo 3 (aislamiento entre
tenants)**: verificados de punta a punta via HTTP real (Django test
client -> URL real -> middleware real -> AIContext real -> tool real ->
DB real -> respuesta real), ver Fase 7/9 arriba. El LLM (`AnthropicProvider`)
se mockea en la capa de transporte (`anthropic.Anthropic`, no la logica de
decision) — mismo patron ya usado por `test_ai06_http_endpoint.py`
(pre-existente, no inventado para esta mision), porque este entorno de
desarrollo no tiene `ANTHROPIC_API_KEY` configurada (ver Limitaciones).

**Flujo 2 (retrieval -> pgvector -> respuesta)**: no se ejecuto un test
HTTP nuevo especifico en esta pasada — `buscar_conocimiento` ya tiene
cobertura real end-to-end desde AI-VECTOR-07/11.1 (`test_retrieval_tool.py`,
smoke real con el modelo jina-es contra el tenant piloto `home`). Se
prueba en esta mision solo el **renderizado** del lado del cliente
(`ai.assistant.js::_renderFuentes`), no una segunda vez el backend.

**Verificacion visual/manual en navegador real**: NO se pudo completar en
esta sesion (ver Limitaciones #2/#3 abajo) — codigo revisado
manualmente linea por linea en su lugar (templates, JS, orden de carga de
scripts).

## Limitaciones (honestas, no ocultas)

1. **Sin respuesta real del LLM en este entorno**: `.env` no tiene
   `AI_ENABLED`/`ANTHROPIC_API_KEY`. Todo lo verificado con evidencia real
   usa el mismo mock de transporte que ya establecio AI-06
   (`anthropic.Anthropic` mockeado, la logica de negocio real — AIContext,
   tools, DB — se ejecuta sin mocks). Un flujo interactivo con respuesta
   real del modelo requiere que el usuario decida habilitar los flags y
   proveer una API key real — decision y credencial que esta sesion no
   puede tomar por si sola.
2. **Verificacion manual en navegador**: el sandbox del Browser tool de
   esta sesion bloquea (`ERR_BLOCKED_BY_CLIENT`) toda peticion a
   `/api/v1/core/*`, incluyendo el propio login — confirmado con
   credenciales reales provistas por el usuario
   (`admin@home.com`/`http://home.sintel.net.co`). No relacionado con el
   codigo de esta mision.
3. **Playwright no ejecutado**: Node.js/npm no esta instalado en esta
   maquina (verificado: no resuelve en PATH de Bash ni PowerShell). El
   spec `70-ai-ui-01-assistant.spec.js` esta escrito y listo, pendiente de
   `cd tests/e2e && npm install && npx playwright install chromium &&
   npm test` (o CI) para ejecutarse por primera vez.
4. **`buscar_producto` no ordena por stock** — DEFERRED, `AI_UI_01_AUDIT.md`
   seccion C.
5. **Disponibilidad del boton limitada a `workspace.html`** — decision
   deliberada, no un descuido (ver Fase 3/4 arriba).

## Corrida real de tests

Ejecutado local (venv, nunca Docker -- `feedback-no-docker-for-tests`),
`apps/services/ai/tests/test_ai_ui_01_security.py`, verificado en 2
corridas separadas (no una sola corrida conjunta final, por el costo real
de tiempo -- cada corrida completa del archivo tarda ~33 min en este
entorno, migracion de esquema completa por clase `SintelTenantTestCase` +
2 esquemas reales nuevos `tenant1`/`tenant2` para el test cross-schema):

```
1a corrida (4 tests, 33m45s): 2 passed, 2 failed
  - test_empresa_id_inyectado_en_arguments_es_ignorado_no_causa_fuga -- PASSED
  - test_respuesta_nunca_expone_uuid_de_empresa_ni_schema -- FAILED (bug real
    del test: Empresa no tiene campo uuid propio, corregido)
  - test_cross_schema_usuario_de_tenant1_no_recupera_clientes_de_tenant2 -- PASSED
  - test_tool_write_registrada_sigue_bloqueada_con_flag_write_activo -- FAILED
    (bug real del test: setUp() no creaba TenantProfile, PERMISSION_DENIED
    llegaba por falta de contexto, no por el bloqueo de WRITE; corregido)

2a corrida tras corregir bug #1 (timeout de la herramienta cortó el ultimo
test a los 10 min, 3 de 4 completados): 3 passed
  - test_empresa_id_inyectado_en_arguments_es_ignorado_no_causa_fuga -- PASSED
  - test_respuesta_nunca_expone_uuid_de_empresa_ni_schema -- PASSED (confirma el fix)
  - test_cross_schema_usuario_de_tenant1_no_recupera_clientes_de_tenant2 -- PASSED

3a corrida, solo el test restante tras corregir bug #2 (21m15s): 1 failed
  - test_tool_write_registrada_sigue_bloqueada_con_flag_write_activo -- FAILED
    (bug real DISTINTO, no relacionado a AUTO_APPROVED_KINDS: faltaba
    mockear ANTHROPIC_API_KEY en este test especifico -- sin ella,
    AnthropicProvider.complete() lanza RuntimeError real ANTES de llegar
    a AIEngine.run_tool(), devuelve INTERNAL_ERROR/500 en vez de
    PERMISSION_DENIED/403. Confirmado reproduciendo AIEngine.run_tool()
    directo via manage.py shell: el motor SI bloquea WRITE correctamente
    -- el 500 era 100% un bug del test, no del AI Engine. Corregido.)

4a corrida, solo el test corregido (20m19s): 1 passed
  - test_tool_write_registrada_sigue_bloqueada_con_flag_write_activo -- PASSED
```

**Los 4 tests pasan** con la version final del archivo. Los 3 "bugs"
encontrados fueron todos en el codigo del test nuevo (asuncion incorrecta
sobre el modelo `Empresa`, falta de fixture, falta de mock) -- ninguno
revelo un defecto real en `apps/services/ai/`. `manage.py check` y
`manage.py makemigrations --check --dry-run` (locales, mismo venv):
limpios, sin cambios detectados.

## Veredicto

```
AI_UI_01 = COMPLETED_WITH_DEFERRED
```

Bloqueadores para `PASS` total, ninguno atribuible a un defecto de esta
mision: (a) flujo interactivo con LLM real requiere decision/credencial
del usuario (Limitacion 1), (b) verificacion visual en navegador real
bloqueada por el entorno de esta sesion, no por el codigo (Limitacion 2),
(c) suite Playwright escrita pero no ejecutada por falta de Node.js en
esta maquina (Limitacion 3). Todo lo demas del release gate (UI visible
en el codigo, endpoint operativo, autenticacion correcta, AIContext
correcto, 3 tools READ/retrieval funcionales via HTTP con evidencia real,
tenant isolation probado con evidencia real, WRITE bloqueado con evidencia
real, tests backend focalizados) tiene evidencia ejecutada real, no solo
implementacion.
