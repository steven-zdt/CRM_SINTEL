# AI_CURRENT_STATE — Fase 0

Auditoría real de la IA existente en SINTEL, 2026-08-31, antes de
diseñar el AI Engine transversal. **No se modificó código en esta
fase.**

## Único feature de IA real hoy: Asistente Contable (sugerencia de líneas de asiento)

Cadena completa, verificada archivo por archivo:

| Capa | Archivo | Rol |
|---|---|---|
| Config | `requirements.txt:42` | `anthropic>=0.40.0,<1.0` |
| Config | `.env.example:59-61` | `ANTHROPIC_API_KEY` |
| Docs | `AGENTS.md` §20 "[AI-AGENTS]" (líneas 654-751) | Diseño canónico documentado |
| Serializer | `apps/tenant/contabilidad/api/serializers.py:471` `AsistenteIAInputSerializer` | Valida input |
| ViewSet | `apps/tenant/contabilidad/api/viewsets.py:1109` `DocumentosPendientesViewSet.asistente_ia()` | `POST /api/v1/contabilidad/pendientes/asistente-ia/`, `IsTenantMember`+`IsTenantAdminOrReadOnly` |
| Service | `apps/tenant/contabilidad/services/business_service.py:1164` `sugerir_lineas_asiento_ia()` | Llamada real a Anthropic |
| Frontend | `.../pendiente_offcanvas_contabilizar.html:156-937` | Botón "Diligenciar con IA", inyecta sugerencia en formulario manual |

**Cómo funciona:** `anthropic.Anthropic(api_key=...)`, modelo
`claude-haiku-4-5-20251001`, una sola llamada sin streaming, sin
`tools=`/function-calling (el "system prompt" va concatenado dentro
del mensaje de usuario, no como parámetro `system=` separado). La
respuesta JSON se re-valida contra `CuentaContable` real del tenant
(nivel 6, activa, `empresa_id`) antes de devolverse — **nunca escribe
nada por sí sola**, el usuario debe pulsar "Generar Asiento" aparte.

- **Read-only / suggestion-only.** No puede crear `AsientoContable`/`MovimientoContable`.
- **Contexto de tenant:** sí — permisos DRF + `empresa_id` en cada query + cuentas filtradas al tenant.
- **Tests:** **ninguno** (`grep` en `apps/tenant/contabilidad/tests/` para `asistente_ia`/`sugerir_lineas_asiento_ia` → 0 resultados).
- **"Agentes" (`FacturacionAgent`, `GastosAgent`, etc.):** **no son clases reales** — son solo etiquetas en una tabla de `AGENTS.md` §20.2 y un dict Python (`_APP_TIPO_LABEL`) que parametriza el mismo texto de prompt según `app_label`. No existe `class FacturacionAgent` en ningún archivo (`grep -r "class \w*Agent\b" apps/` → 0 resultados).

## OpenAI SDK

**No usado en ningún lugar.** Sin dependencia en `requirements.txt`, sin `OPENAI_API_KEY` referenciada en código.

## MCP — dos superficies distintas, no confundir

**A) `django-rest-framework-mcp`** (`requirements.txt:17`) — instalado,
montado en `config/urls_tenant.py:166` y `config/urls_public.py:117`
(`/mcp/` en ambos), configurado para preservar auth/permisos de cada
ViewSet (`BYPASS_VIEWSET_AUTHENTICATION=False`,
`BYPASS_VIEWSET_PERMISSIONS=False`, `config/settings.py:677-692`).
**Cero ViewSets decorados** (`grep -r "mcp_viewset\|mcp_tool" apps/` →
0 resultados) — el servidor está montado pero no expone ninguna
herramienta hoy. Andamiaje inerte, no una integración funcionando.

**B) `.antigravity/`** — MCP de *tooling de desarrollo* (Antigravity
IDE ayudando a Claude Code/Antigravity a auditar/editar este mismo
repo: `list_available_skills`, `sintel_app_quality_plan`,
`audit_bridge_isolation`, etc.). El servidor real
(`sintel_agent_unified.py`, referenciado en `AGENTS.md`/`MEMORY.md`)
**no vive dentro de este repo** — es infraestructura externa del
propio editor. **No tiene nada que ver con datos de tenants ni
usuarios finales** — no confundir con (A).

## Tool/function-calling registry

**No existe.** La única llamada real a Anthropic no usa `tools=` — es
un completion de texto plano, no tool-use nativo del SDK.

## EKG (`tools/ekg/`) — grafo de código, no IA

Herramienta madura de análisis estático (Tree-sitter + Neo4j) del
propio código fuente (Models/Services/ViewSets/Serializers/
Endpoints/Templates/Tests/Docs), **sin SDK de IA ninguno**. Su propio
`PILOT_REPORT.md` documenta "No GraphRAG/embeddings/semantic search —
fuera de alcance del piloto" como limitación conocida — candidato
real a fuente de contexto para el AI Engine (Fase 9-10), pero hoy es
100% estática, no LLM.

## Prompts

Sin sistema de templates de prompt. El único prompt vive inline como
f-string en `sugerir_lineas_asiento_ia()`, con su forma "canónica"
duplicada como referencia en `AGENTS.md` §20.4.

## Persistencia de sesión/conversación

**Ninguna.** Sin modelo `ChatSession`/`AIConversation`. Cada llamada al
Asistente Contable es stateless — nada se audita ni se persiste sobre
la interacción de IA en sí (ni prompt, ni respuesta, ni decisión).

## Conclusión para el diseño del AI Engine

1. Hay **un** feature de IA real, acotado a contabilidad, sin tests,
   sin tool-calling, sin memoria. El AI Engine transversal no
   "reemplaza agentes" (regla explícita de la misión) porque **no
   existen agentes reales que reemplazar** — solo una función.
2. MCP (`django-rest-framework-mcp`) es la superficie natural para
   exponer tools en el futuro (Fase 31-33) — ya preserva auth/permisos
   por diseño — pero **no se usa en esta primera implementación**: el
   AI Engine de esta fase se invoca directamente desde vistas/backend,
   no vía MCP, para mantener el alcance acotado y verificable.
3. Nada que auditar como "riesgo MCP" (Fase 2-3) porque no hay
   herramientas MCP publicadas todavía — la clasificación de riesgo
   (`AI_TOOL_REGISTRY.md`) aplica desde ya al `AIToolRegistry` nuevo,
   que es real, no al MCP inerte.
