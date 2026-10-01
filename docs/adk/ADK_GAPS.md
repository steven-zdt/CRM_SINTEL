# ADK_GAPS — Fase 0 (Baseline Forense) del plan de evolución

**Fecha:** 2026-09-22
**Fuente:** `documentacion/PLAN_MAESTRO_ADK_SINTEL_AGENTIC_ERP_LOOP_20260922.md` §30 ("FASE 0 — BASELINE FORENSE", uno de los 3 entregables pedidos junto con `ADK_BASELINE.md` y `ADK_DEPENDENCY_MAP.md")
**Regla aplicada (la que el propio documento exige en su §64):** "INSPECCIONA EL CÓDIGO REAL... NO INVENTES..." — este documento existe precisamente para separar lo que el plan de evolución ASUME que ya existe de lo que realmente existe, verificado archivo por archivo.

---

## Hallazgo crítico: la sección "Estado Actual Real Detectado" (§1) del plan de evolución NO es exacta

El documento `PLAN_MAESTRO_ADK_SINTEL_AGENTIC_ERP_LOOP_20260922.md` afirma en su §1.3 ("Estado ADK existente") que ya existe:

```text
ai_engine_adk/          <- como "proceso FastAPI independiente"
sintel_root_workflow.py
routing determinista
perfiles de agentes
RAG hibrido y memoria persistente en el runtime ADK existente
DatabaseSessionService
```

y en su §26 ("LM Studio Local") afirma que *"el proyecto ya corrigió un problema real donde `reasoning_content` de Qwen3.5 se filtraba a la respuesta pública"*.

**Verificado con `grep` exhaustivo sobre todo el repo (`apps/`, `config/`, `requirements.txt`, `.env`, `.env.example`) el 2026-09-22: ninguno de estos elementos existe.**

| Afirmación del plan | Estado real |
|---|---|
| `ai_engine_adk/` como proceso FastAPI independiente | **No existe.** No hay ningún directorio `ai_engine_adk/` en el repo. |
| `sintel_root_workflow.py` | **No existe.** `grep -r sintel_root_workflow` → 0 resultados. |
| Routing determinista entre dominios | **No existe.** No hay ningún router de intents/dominios implementado — el único "routing" real es el `form_assistant.py` eligiendo UNA tool por JSON (Fase AI-06, ver `docs/ai/AI_RELEASE_GATE.md`). |
| Perfiles de agentes | **No existe.** Un solo `root_agent` (2 tools, `saludar`/`buscar_cliente`), construido en esta misma sesión (Fase 4 del plan original de ADK). |
| RAG híbrido + memoria persistente en el runtime ADK | **No existe.** `AI_MEMORY_POLICY.md` documenta la memoria como diseñada, no implementada. RAG cubre 2/12 dominios (ver `ADK_KNOWLEDGE_MAP.md`), sin ninguna integración con ADK todavía (el `root_agent` no tiene `buscar_conocimiento` entre sus tools). |
| `DatabaseSessionService` | **No existe.** Ningún `SessionService` de ADK está en uso — el `root_agent` nunca se ha ejecutado en una conversación real (no hay LLM conectado). |
| LM Studio + Qwen3.5 con bug de `reasoning_content` ya corregido | **No existe.** `grep -rl "LM Studio\|LM_STUDIO\|reasoning_content\|Qwen\|LiteLLM\|litellm"` sobre todo el repo → 0 resultados reales (un único falso positivo en un XML de factura, coincidencia de substring). LM Studio no está corriendo ni en el host (`127.0.0.1:1234`) ni alcanzable desde el contenedor (`host.docker.internal:1234`) -- probado en vivo el 2026-09-22, ambos "connection refused"/timeout. |

**Conclusión:** el plan de evolución describe un estado "ya construido" que no corresponde a este repositorio. Puede ser una descripción aspiracional (el destino, no el punto de partida), o haber sido redactado con referencia a documentos que tampoco existen aquí (`arquitectura_general(20260922-175425).md`, `IMPLEMENTATION_SUMMARY(20260922-173458).md`, `MEMORY(4).md` — ninguno de los 3 existe en `documentacion/`, solo `arquitectura_general.md` sin fecha). Este documento (`ADK_GAPS.md`) es la corrección forense que el propio plan exige en su Fase 0 antes de construir nada nuevo.

---

## Lo que SÍ existe hoy (real, verificado, evidencia enlazada)

Ver `docs/adk/ADK_BASELINE.md` (Fase 0 del plan original) para el detalle completo. Resumen:

- `apps/services/ai/` — AIContext, AIEngine, AIToolRegistry (18 tools reales, 12 dominios), providers (Anthropic real, OpenAI/local solo diseñados).
- `apps/services/ai/adk/` — `root_agent` (ADK real, `google-adk==2.9.2`, mismo proceso que Django), 2 tools (`saludar`, `buscar_cliente`), sin LLM conectado. Tests reales en `apps/services/ai/tests/test_adk_tools.py`.
- `apps/tenant/ai_knowledge/` — pgvector real, RAG cubre 2/12 dominios (clientes, inventario).
- `tools/ekg/` — grafo estático de código, real, sin IA.
- `docs/ai/` (20 documentos) + `docs/adk/` (este directorio) — documentación viva con estado real.

## Gaps reales frente al plan de evolución (lo que falta, no lo que ya está)

| Elemento pedido por el plan de evolución | Estado |
|---|---|
| `DomainRegistry` / `DomainDefinition` por app (§31, Fase 1) | **No existe** — se construye en esta pasada (ver `apps/services/ai/domain_registry/`). |
| `DomainKnowledgeService` (§32, Fase 2, `get_domain_map()`/`get_rules()`/etc. sobre el EKG) | **No existe.** `ai_project_map` (tool ya real) es el precursor directo -- construir `DomainKnowledgeService` como una capa fina sobre él es trabajo futuro, no de esta pasada. |
| `IntentAgent`/`PlannerAgent`/`PolicyAgent`/`SpecialistAgents`/`SupervisorAgent` (§6-9) | **No existen.** Solo el `root_agent` mínimo. Construir estos requiere primero tener un LLM real conectado (sin eso, no hay forma de probar que el routing/planning funciona) — bloqueado en la práctica por la disponibilidad de LM Studio. |
| `Domain Knowledge Contract` por app (YAML conceptual, §4) | **No existe** como artefacto formal — `ADK_DOMAIN_INVENTORY.md` (Fase 1 del plan original) ya cubre buena parte de este contenido en formato tabla; el plan de evolución pide generarlo "desde código real", lo mismo que ya se hizo ahí. |
| LM Studio como provider local (§26-27) | **No configurado, no alcanzable.** Bloqueante real — ver "Decisión pendiente" abajo. |
| Memoria/sesión persistente (`DatabaseSessionService` o similar) | **No implementado.** El `root_agent` no tiene ningún `SessionService` conectado todavía (no hace falta sin LLM real). |
| Write pipeline (preview/approval/idempotencia/verificación, §18-22) | **Especificado, no implementado** — ya cubierto en `ADK_TOOL_CONTRACT.md` Parte B (Fase 3 del plan original), sigue vigente, ningún cambio aquí. |
| Evaluación (`eval` datasets por dominio, §29) | **No existe.** Depende de tener agentes reales con LLM para generar casos de evaluación con sentido. |

## Decisión pendiente (bloqueante real para el próximo paso del plan de evolución)

El plan de evolución (§26) asume LM Studio corriendo en `http://127.0.0.1:1234/v1`. **Probado en vivo (2026-09-22): no está corriendo** ni en el host de este entorno de desarrollo ni alcanzable desde el contenedor Docker (`curl` a ambas direcciones falla). Antes de avanzar a conectar un LLM real (que desbloquearía Fase 5+ del plan original Y todo el plan de evolución), hace falta que el usuario confirme:

1. ¿LM Studio está instalado y corriendo en esta máquina, en otro puerto, o en otra máquina de la red?
2. Si corre en el host (fuera de Docker), la URL correcta desde dentro del contenedor `web` es `http://host.docker.internal:<puerto>/v1` (no `127.0.0.1`, que dentro del contenedor apunta al propio contenedor) — confirmar si Docker Desktop en este entorno resuelve `host.docker.internal` (usualmente sí en Windows/Mac, requiere configuración extra en Linux puro).
3. ¿Qué modelo está cargado en LM Studio (para fijar `ADK_LLM_MODEL` correctamente)?

Sin esa confirmación, no se puede completar el spike de conectividad LLM sin adivinar una configuración que probablemente esté mal.

## Conclusión de Fase 0 (plan de evolución)

```
FASE 0 — BASELINE FORENSE (plan de evolución) = PASS (con hallazgo critico documentado)
```

Gate cumplido: "baseline reproducible" (§30, "PASS: baseline reproducible"). El hallazgo de que la sección §1 del plan de evolución no es precisa no es un `FAIL` de esta fase -- es exactamente el resultado esperado de ejecutarla honestamente (el propio plan pide "auditar el estado real ANTES de tocar código", y eso es lo que se hizo). No se construyó ningún agente nuevo más allá de lo ya existente, consistente con §69 ("NO comenzar creando más agentes" hasta que Fase 0 y Fase 1 estén PASS).
