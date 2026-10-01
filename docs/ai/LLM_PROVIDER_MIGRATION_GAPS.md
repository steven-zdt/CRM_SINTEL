# LLM_PROVIDER_MIGRATION_GAPS — FASE 0 (PLAN_MAESTRO_LLM_PROVIDER_HUB_SINTEL_CONSOLE_20260924.md)

**Fecha:** 2026-09-24 · **Base:** `LLM_PROVIDER_BASELINE.md` / `LLM_PROVIDER_DEPENDENCY_MAP.md`

STATUS: **PASS** (inventario de gaps; ninguno bloquea el arranque de Fase 1)

## GAP-1 (plan §8) — `AIProvider` no tiene `stream()`/`health()`/`list_models()`/`get_capabilities()`/`validate_connection()`

Hoy el contrato (`apps/services/ai/providers/base.py`) solo exige `complete()`. El plan pide un `Protocol` con 5 métodos más. Los 3 providers reales (`AnthropicProvider`, `OllamaProvider`, `OpenAICompatibleProvider`) tendrían que implementarlos -- factible (Ollama expone `/api/tags` para `list_models()`, `/api/chat` con `stream:true` ya soportado por el protocolo nativo; Anthropic SDK soporta streaming y tiene endpoint de modelos; OpenAI-compat expone `/models` estándar), pero es trabajo real de Fase 1, no hecho todavía.

## GAP-2 (plan §12) — No existe `resolve_active_llm()` (resolver central único)

Confirmado en `LLM_PROVIDER_DEPENDENCY_MAP.md`: dos caminos de resolución paralelos (`get_ai_provider()` para `form_assistant.py`, `agent.py::_build_model()` inline para ADK). Ninguno lee "workload"/"tenant_context"/"agent_context" como pide el plan -- ambos son globales, sin ese concepto todavía.

## GAP-3 (plan §6, modelo de datos) — Todo vive en variables de entorno, no en DB

`LLMProvider`, `LLMModel`, `LLMConnection`, `LLMActiveConfig` no existen como modelos Django. Hoy "cambiar de provider" es editar `.env` + reiniciar `web` -- viola directamente el §25 del plan ("Cambio sin reiniciar"). Ningún historial de cambios, ninguna UI, ningún `last_known_good_config` para rollback (§27).

## GAP-4 (plan §7) — Secret management: hoy texto plano en `.env`, sin `secret_ref`

Confirmado: `ANTHROPIC_API_KEY`, `ADK_LLM_API_KEY`, futuras keys de Gemini/OpenAI/custom REST -- todas en `.env` plano, nunca en DB. **Hallazgo positivo real:** `apps/services/security/crypto.py` (Fernet, `MAILCFG_FERNET_KEY`) ya existe y ya se usa en producción para otro secreto (password de buzones de correo) -- es el candidato natural para implementar `secret_ref` sin inventar un mecanismo nuevo. Falta: decidir si se reusa tal cual (renombrar conceptualmente, misma clave Fernet) o se crea una clave dedicada para secretos de IA (aislamiento de blast radius si una clave se compromete) -- decisión de Fase 9, no de esta fase.

## GAP-5 (plan §31) — Sin permisos granulares (`ai.providers.*`)

Console usa `IsAdminUser` (DRF, binario: staff o no) en TODAS sus vistas hoy. El plan pide separar ver/modificar/probar/activar/gestionar-secretos/auditar en 6 permisos distintos. No existe ningún sistema de permisos granular en `apps/public/console/` para replicar -- habría que construirlo desde cero (posiblemente reutilizando el patrón de `apps.tenant.api.permissions` del lado tenant, que sí tiene roles ADMIN/OPERADOR/VISOR, pero console es del lado PÚBLICO/staff, dominio distinto).

## GAP-6 (plan §32) — Multitenancy: hoy 100% system-wide, sin decisión explícita tomada

Confirmado en Baseline: el provider/modelo activo es el mismo proceso Django para TODO el deployment (no hay override por tenant). El plan pide que Fase 0 "determine" esto -- **ya determinado**: es SYSTEM/PUBLIC hoy, sin excepción. Si en el futuro se quiere permitir preferencia por tenant, es una decisión de producto nueva (¿un tenant paga por su propio modelo? ¿es solo para desarrollo interno?) que el usuario debe tomar explícitamente antes de construir `Tenant preferred provider/model` (Fase 1+).

## GAP-7 (plan §33) — `ConsoleActionLog` existe pero con `ACTION_CHOICES` cerrado

Reutilizable como patrón (actor, timestamp, acción), pero es un `CharField` con `choices` fijos -- agregar `AI_PROVIDER_ACTIVATE`/`AI_PROVIDER_TEST`/etc. requiere migración sobre un modelo compartido con auditoría de tenants/usuarios (acoplamiento de dominios no relacionados). Alternativa: modelo de auditoría propio para IA (`AIProviderAuditLog`), seguridad Regla Absoluta del plan de no duplicar innecesariamente -- decisión de Fase 1/8, no tomada aquí.

## GAP-8 (plan §21/§22) — Sin capability probing ni matrix hoy

Ningún provider reporta hoy si soporta streaming/structured output/vision/tool calling de forma verificada -- son capacidades ASUMIDAS por el código que los llama (ej. `form_assistant.py` asume que cualquier provider puede hacer JSON via texto plano). El plan exige verificación real (`verified`/`verified_at`), no nombres de modelo. Trabajo nuevo completo, Fase 1/2.

## GAP-9 (heredado del plan Ollama anterior, sigue abierto) — Sin fallback real

`docs/ai/OLLAMA_MIGRATION_GAPS.md` GAP-5/GAP-9 ya lo documentó: no hay provider health, no hay `AI_FALLBACK_PROVIDER` real, `AIResponse` no normaliza `tool_calls`/`finish_reason`. Este plan lo retoma en sus Fases 1 (contrato)/10 (fallback+health) -- mismo gap, no uno nuevo.

## GAP-10 (plan §17, heredado) — Tool argument accuracy sin garantía

`docs/ai/OLLAMA_STATUS.md` Fase 7 ya documentó en vivo: el modelo puede alucinar nombres de argumentos porque `AIToolRegistry.tool_metadata()` no expone schema de parámetros. El plan de este Hub (§17) exige la misma cadena `LLM -> tool proposal -> normalizer -> AIToolRegistry -> Policy -> Service`, pero el "normalizer" no existe todavía (GAP-1 arriba, `LLMResponseNormalizer` del §15) -- cerrar GAP-1 no resuelve automáticamente este, son gaps relacionados pero distintos (uno es de contrato de respuesta, otro es de que el modelo conozca el schema real de la tool).

## GAP-11 (plan §30, seguridad Custom REST) — Sin validación SSRF hoy

`OpenAICompatibleProvider` (recién creado) acepta cualquier `AI_OPENAI_COMPAT_BASE_URL` sin validar scheme/rangos privados/redirects -- aceptable hoy porque es una variable de entorno que solo un admin de infraestructura puede tocar (no input de usuario final). Si la Fase 8 de este plan expone un formulario donde un STAFF pueda pegar una URL arbitraria, ahí sí se vuelve una superficie real de SSRF que necesita la validación que pide el §30 -- no implementado, correctamente fuera de alcance mientras la única forma de cambiarlo sea editar `.env`.

## Ningún gap bloquea el arranque de Fase 1

Como con el plan de Ollama: los 11 gaps de arriba son trabajo real pendiente, no bloqueos -- Fase 1 (contrato `LLMProvider`/`LLMResponse`/etc.) puede arrancar apoyándose en lo que ya existe (`AIProvider` actual, `get_ai_provider()`, `crypto.py`, `ConsoleActionLog` como referencia).
