# ADK_BASELINE — Fase 0 (Inspección)

**Fecha:** 2026-09-22 (actualizado el mismo día tras simplificar la arquitectura y recibir `documentacion/PLAN_MAESTRO_ADK_SINTEL_AGENTIC_ERP_LOOP_20260922.md`)
**Fuente:** `PLAN_MAESTRO_INTEGRACION_GOOGLE_ADK_ASISTENTE_IA_SINTEL.md` (raíz del repo), §58. Ver también `docs/adk/ADK_GAPS.md` para el contraste con el plan de evolución más reciente.

## Actualización 2026-09-22 (tarde) — arquitectura simplificada, sin servicio aparte

La primera pasada de esta fase (más abajo) documentó un aislamiento de ADK en `ai_adk_service/` (proceso/imagen separados) por un conflicto real con `cryptography` (usada por la firma XAdES-EPES de facturación electrónica). **El usuario revirtió esa decisión** (2026-09-22): no se generan/firman facturas nuevas en este momento (solo se importan XML ya firmados por su emisor, lectura de CUFE) — el riesgo de subir `cryptography` no aplica hoy. Se simplificó:

- `requirements.txt`: `cryptography` subido a `>=45.0.1,<51.0`; `google-adk==2.9.2` agregado directo, mismo entorno que Django.
- `ai_adk_service/` **eliminado** por completo.
- `apps/services/ai/adk_gateway/` (HTTP + secreto compartido) **eliminado**, reemplazado por `apps/services/ai/adk/` — el agente y sus tools llaman a `AIEngine.run_tool()` **directamente en Python** (mismo proceso), sin HTTP ni autenticación de servicio a servicio.
- `docker-compose.yaml`: servicio `adk-agent` eliminado.
- Verificado: `google-adk` importa limpio en el entorno principal, `XadesSignerService`/`Fernet` (usuarios reales de `cryptography`) siguen importando sin error con la versión nueva.
- Bug real encontrado y corregido en esta simplificación: las tools de ADK son `async def` (convención de la librería) pero llamaban al ORM de Django de forma síncrona directamente -- Django lo bloquea (`SynchronousOnlyOperation`). Corregido envolviendo la parte síncrona con `asgiref.sync.sync_to_async`.
**Regla aplicada (§1 del plan):** código real actual > documentación histórica. Todo lo listado abajo se verificó leyendo el código, no solo la documentación existente.

STATUS FASE 0: **PASS** (auditoría completa, sin cambios de código en esta fase — igual que exige el plan).

---

## Hallazgo central: la mayor parte de la "Fase 0" del plan ya está hecha

El plan asume (§1) que existe un núcleo AI transversal en `apps/services/ai/` con provider abstraction, `AIContext`, tool registry, `RetrievalTool` y `AIEngine`, y que ya hay una tool real `buscar_cliente`. Verificado: es exacto, y el estado real va **más allá** de lo que el plan supone — no es un prototipo aislado, es un sistema con 18 tools reales, 83 tests, un orquestador con endpoint HTTP, y un widget de frontend ya en producción (apagado por flags). El propio proyecto ya mantiene 20 documentos vivos en `docs/ai/` con este historial fase por fase; este documento no los reemplaza, los referencia como fuente de verdad y solo añade la lectura específica que pide el plan de ADK.

## Auditoría ítem por ítem (checklist §58)

| Ítem del plan | Estado real | Evidencia |
|---|---|---|
| `apps/services/ai/` | **PASS** | `engine/ai_engine.py` (fachada única `run_tool()`), `context/ai_context.py` (`AIContext`/`build_context()`), `tools/registry.py` (`AIToolRegistry`), `tools/base.py` (`BaseTool`/`ToolKind`/`ToolRisk`), `providers/base.py` (`AIProvider` ABC) + `anthropic_provider.py` (única implementación real hoy), `orchestrator/form_assistant.py` (`ask()`), `api/` (`AIAssistantViewSet`, `POST /api/v1/ai/ask/`). |
| `apps/tenant/ai_knowledge/` | **PARCIAL** | pgvector real (`models.py`: `AIKnowledgeDocument`/`AIKnowledgeChunk`), `services/retrieval_service.py` (búsqueda semántica tenant-scoped vía schema de PostgreSQL, nunca por `tenant_id` explícito), `services/indexing_service.py`/`chunking_service.py`/`embedding_service.py`. **Hallazgo real, no documentado como tal en el plan:** `services/sources.py::INDEXABLE_SOURCES` (la allowlist real de qué se indexa) hoy solo tiene **2 orígenes**: `cliente_observaciones` (Cliente.observaciones) y `producto_descripcion` (Producto.descripcion). El plan (§3) asume un vector store "ya scoped por los 11 dominios de negocio" — eso NO existe todavía; hoy es un POC de 2 dominios, el resto (proveedores, facturas, ventas, compras, cotizaciones, gastos, empleados, proyectos, bancos, contabilidad) no tiene ningún documento indexado. Esto es una entrada real para la Fase 2 (Mapa de Conocimiento) del plan de ADK, no una corrección de este documento. |
| `tools/ekg/` | **PASS (no-IA)** | Grafo estático de código (Tree-sitter + Neo4j), sin SDK de IA, snapshots reales en `tools/ekg/out/*.json` por app. Su propio `PILOT_REPORT.md` documenta "sin embeddings/semantic search" como límite conocido. `apps/services/ai/tools/ekg_tools.py::ProjectMapTool` ya lo envuelve como tool `READ` real (owner/rules/docs/fk por dominio) — este es el candidato natural a "Context provider" que pide el plan §4, no hace falta crear otro grafo. |
| `AIContext` | **PASS** | `apps/services/ai/context/ai_context.py`. Inmutable (`@dataclass(frozen=True)`), construido SIEMPRE desde `request.user.tenant_profile` (nunca del payload/lenguaje natural — cumple §12 del plan tal cual), incluye `user_id/empresa_id/schema_name/rol/alcance/sede_ids/area_ids` + contexto de pantalla opcional. Satisface literalmente el requisito del plan de reutilizar `OrganizationalContext`/`OrganizationalScope` en vez de crear un segundo RBAC. |
| `AIEngine` | **PASS** | `apps/services/ai/engine/ai_engine.py::AIEngine.run_tool()` — punto único de ejecución. Ya implementa, de forma **estructural** (no solo documentada): feature flags por `ToolKind` (`AI_READ_ENABLED`/`AI_SUGGEST_ENABLED`/`AI_VALIDATE_ENABLED`/`AI_WRITE_ENABLED`), y el bloqueo incondicional de WRITE (`AUTO_APPROVED_KINDS` excluye `WRITE` siempre, sin importar el flag) hasta que exista un flujo de aprobación real — exactamente la evolución READ→VALIDATE→SUGGEST→APPROVAL→WRITE que pide el plan §1. |
| `AIToolRegistry` | **PASS** | `apps/services/ai/tools/registry.py`. Registro explícito a mano (nunca introspección automática de ViewSets — cumple la Regla Absoluta 4 del propio motor de IA, coherente con la prohibición del plan de tools genéricas tipo `execute_sql`/`update_model`). `tool_metadata()` expone name/description/domain/kind/risk/confirmation_required/idempotent — serializable, es exactamente el "Tool Manifest" que el plan pide en su §30. |
| `RetrievalTool` | **PASS** | `apps/services/ai/tools/retrieval_tools.py::RetrievalTool`, envuelve `RetrievalService` (arriba). Kind=`READ`, así que además requiere `AI_RETRIEVAL_ENABLED` como sub-flag independiente (rollout/rollback granular). |
| `EmbeddingService` | **PASS** | `apps/tenant/ai_knowledge/services/embedding_service.py` + `apps/services/ai/providers/fastembed_provider.py` (`FastEmbedProvider`, ONNX local, sin torch — AI-VECTOR-04) + `query_embedding_cache.py` (cache Redis, TTL vía `AI_EMBED_CACHE_TTL_S`). |
| `RetrievalService` | **PASS** | `apps/tenant/ai_knowledge/services/retrieval_service.py`. Solo lectura (docstring lo declara como regla), aislamiento por schema de PostgreSQL (no por filtro `tenant_id` — más fuerte, estructural). Devuelve candidatos de contexto, nunca la fuente de verdad de montos/saldos/estados (esos siguen viniendo de las tools READ deterministas) — esto es exactamente la regla §42 del plan de ADK ("Regla de autoridad de datos"), ya implementada sin que el plan lo supiera. |
| providers | **PARCIAL** | `AIProvider` (ABC, `providers/base.py`) + `AnthropicProvider` (única implementación real, usa `anthropic>=0.40.0,<1.0` de `requirements.txt`, clave `ANTHROPIC_API_KEY`). **No existe** implementación OpenAI-compatible ni local — están diseñadas en `docs/ai/AI_PROVIDER_MATRIX.md` pero sin código. Esto es directamente relevante para el plan de ADK: §25 pide que el LLM detrás de ADK sea "local/OpenAI-compatible cuando esté disponible" — hoy el único provider real y probado en producción es Anthropic. Ver "Decisión pendiente" al final de este documento. |
| settings | **PASS** | `config/settings.py:1007-1024`. Flags server-side únicamente (nunca desde `request.data`, verificado en `ai_engine.py::_flag()`): `AI_ENABLED`, `AI_READ_ENABLED`, `AI_VALIDATE_ENABLED`, `AI_SUGGEST_ENABLED`, `AI_WRITE_ENABLED`, `AI_RETRIEVAL_ENABLED`, `AI_EMBED_CACHE_TTL_S`. Todos `False`/valores seguros por defecto — el AI Engine no se activa solo porque el código exista. |
| URLs | **PASS** | `apps/services/ai/api/urls.py` → `POST /api/v1/ai/ask/` (`AIAssistantViewSet`, no hereda `BaseTenantViewSet` — no expone CRUD de un modelo, mismo patrón que `ReportingViewSet`). Reutiliza `[RelaxedJWTAuthentication, SessionAuthentication]` + `IsTenantMember` existentes, sin permisos nuevos. |
| frontend AI | **PASS (con nota)** | `apps/tenant/core/static/core/js/common/ai.assistant.js` (`window.Sintel.AI`) + `apps/tenant/core/templates/tenant/core/partials/offcanvas_asistente_ia.html`, cargado globalmente desde `assets_core.html`/`workspace.html`/`_header.html` — ya es un menú "Asistente IA" real y visible en el shell del ERP, tal como pide el plan §47. **Nota:** este widget habla con el orquestador `form_assistant.py` (Anthropic, JSON de una sola tool), NO con ADK — es el punto de partida que el plan de ADK debe envolver/reemplazar como orquestador, sin tener que rehacer la UI. |

## Lo que el plan de ADK debe evitar duplicar (confirmado, no solo asumido)

- **No crear otro vector store**: `apps/tenant/ai_knowledge/` + pgvector ya existen, con aislamiento real por schema.
- **No crear otro grafo**: `tools/ekg/` + `ProjectMapTool` ya existen.
- **No crear otro RBAC/Access Context**: `AIContext`/`build_context()` ya deriva siempre de `request.user.tenant_profile`.
- **No crear otro Tool Registry**: `AIToolRegistry` ya es el contrato tool-first que pide el plan §8, con exactamente las 3 clases READ/VALIDATE/WRITE que pide §9 (`ToolKind`), más `SUGGEST` que el plan no distingue explícitamente pero que el sistema real sí separa.
- **No crear otro provider abstraction**: `AIProvider` ya existe: ADK necesita un *adaptador* sobre él (o sobre lo que exponga `AnthropicProvider`/futuros providers), no un contrato nuevo.

## Lo que NO existe hoy (gaps reales frente al plan, ninguno resuelto en esta fase)

1. **Google ADK no está instalado.** `requirements.txt` no tiene `google-adk` ni ningún paquete relacionado (`grep` confirmado). Es una dependencia nueva real a decidir (ver "Decisión pendiente" abajo).
2. **Sin tools WRITE.** Cero tools `WRITE` registradas — `AUTO_APPROVED_KINDS` lo hace estructuralmente imposible de saltar. El plan §7/§65 (Fase 7 — primer WRITE controlado) parte de cero aquí, coherente con lo que exige el propio plan (§1: no empezar por WRITE indiscriminado).
3. **RAG cubre solo 2 de 12 dominios** (ver arriba, `INDEXABLE_SOURCES`). El plan §3 da por hecho una cobertura de 11 dominios que no existe — entrada real para la Fase 2 (Mapa de Conocimiento).
4. **Sin sesión/memoria conversacional.** `docs/ai/AI_MEMORY_POLICY.md` la diseña, no hay modelo `ChatSession`/`AIConversation` implementado — el plan §13 (Session) lo exige.
5. **Sin tracing/observabilidad persistente.** Solo logging básico por tool call (`ai_engine.py::run_tool`, un `logger.info`). El plan §37 pide observabilidad real.
6. **MCP está bloqueado, no es una superficie usable hoy.** `django-rest-framework-mcp==0.1.0a4` tiene un defecto real que rompe `IsTenantAdminOrReadOnly` — 0 ViewSets decorados, revertido. No es parte del camino de ADK (el plan no depende de MCP), pero se registra aquí porque el plan podría asumir MCP como una superficie disponible si solo lee la documentación superficial.
7. **Sin evaluación formal (`eval run`).** El plan §79 pide usar el ecosistema oficial de evaluación de ADK — no aplica todavía porque ADK no está integrado.
8. **Providers OpenAI-compatible/local: diseñados, no implementados.** Relevante porque el plan prefiere explícitamente un LLM local/OpenAI-compatible para lo que hable con ADK.

## Decisión pendiente (bloqueante para avanzar a Fase 4 — ADK Spike)

El plan (§25-27) pide que el LLM detrás de ADK sea configurable, con preferencia inicial por local/OpenAI-compatible, y nunca hardcodear URL/API key/modelo. Hoy el ERP no tiene ningún LLM local ni endpoint OpenAI-compatible configurado — el único provider real y ya probado en producción (apagado por flags) es Anthropic vía `ANTHROPIC_API_KEY`. Antes de instalar `google-adk` y escribir el `root_agent` mínimo de la Fase 4, hace falta una decisión del usuario que este documento no puede tomar por sí solo: qué LLM va a hablar realmente con ADK en esta primera pasada (reutilizar Anthropic vía un adaptador tipo LiteLLM, apuntar a un LLM local ya corriendo en la infraestructura del usuario, o usar Gemini/Vertex directamente). Se detalla como pregunta explícita en el mensaje de cierre de esta sesión de trabajo.

## Adenda Fase 4 (2026-09-22) — conflicto real de dependencias, encontrado al intentar el spike

Con el usuario ya habiendo decidido dejar el proveedor LLM sin conectar por ahora ("solo dejar la base lista"), se intentó el primer paso mecánico de la Fase 4: verificar que `google-adk` instala limpio en este entorno, vía `pip install --dry-run` dentro del contenedor `web` (sin tocar `requirements.txt` todavía).

**Hallazgo real:** `google-adk` (probado `2.9.2`, `1.9.0`, `1.0.0` — el conflicto es idéntico en las 3) depende de `authlib`, que exige `cryptography>=45.0.1`. El proyecto fija `cryptography>=42.0,<44.0` en `requirements.txt:27`, con un comentario explícito: *"Firma XAdES-EPES (XadesSignerService)"*. Verificado con `grep` que ese pin protege uso real, no incidental:

- `apps/tenant/facturas/services/dian/xades_signer.py`
- `apps/tenant/core/dian/xades_signer.py`
- `apps/services/security/crypto.py`

Esto es firma criptográfica de facturación electrónica ante la DIAN (Colombia) — un componente de cumplimiento fiscal/legal, no una dependencia cualquiera. Subir `cryptography` de 43.0.3 a 50.x (lo que pide `authlib`) es un salto de 7 versiones mayores en una librería de la que depende la validez legal de las firmas electrónicas ya emitidas y las que se emitan después del cambio — no es razonable bumpear ese pin solo para poder instalar un framework de orquestación de IA que ni siquiera va a hablar con ningún LLM todavía.

**Resuelto (2026-09-22):** el usuario eligió la opción 2 (aislar ADK en un proceso/entorno separado). Implementado en `ai_adk_service/` — ver `docs/adk/ADK_STATUS.md` Fase 4 para el detalle completo y la evidencia (imagen construida, contenedor real corrido, `google-adk==2.9.2` importando limpio, `root_agent` construido con sus tools). El pin de `cryptography` del proyecto Django (`requirements.txt:27`, `<44.0`) **no se tocó** — sigue protegiendo la firma XAdES-EPES sin ningún cambio.

Rutas alternativas consideradas y descartadas, por si se revisita esta decisión más adelante:

1. **Verificar y bumpear con evidencia**: subir `cryptography` a `>=45.0.1` en el entorno Django, correr la suite real de firma XAdES contra el nuevo major, y solo si las firmas generadas siguen siendo válidas actualizar el pin con ese respaldo. Descartada por el usuario -- riesgo innecesario sobre código de cumplimiento fiscal para un framework que ni siquiera tiene LLM conectado todavía.
2. **Aislar ADK en un proceso/entorno separado** -- **elegida**, ver arriba.
3. **Esperar una versión de `google-adk`/`authlib` con un rango de `cryptography` compatible** — no se encontró ninguna en las versiones probadas (`2.9.2`, `1.9.0`, `1.0.0`, todo el histórico reciente exige `cryptography>=45.0.1` vía `authlib`).

## Conclusión de Fase 0

```
FASE 0 — INSPECCIÓN = PASS
```

No se modificó código en esta fase (cumple el mandato explícito del plan). El resto de la auditoría (matriz de dominios, mapa de conocimiento, contrato de tools) continúa en `docs/adk/ADK_DOMAIN_INVENTORY.md` y se resume en `docs/adk/ADK_STATUS.md`.
