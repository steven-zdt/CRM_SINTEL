# LLM_PROVIDER_SECURITY_BASELINE — FASE 0 (PLAN_MAESTRO_LLM_PROVIDER_HUB_SINTEL_CONSOLE_20260924.md)

**Fecha:** 2026-09-24 · **Base:** `LLM_PROVIDER_BASELINE.md` / `LLM_PROVIDER_MIGRATION_GAPS.md`

STATUS: **PASS**

## 1. Secretos -- estado real hoy

- **Almacenamiento:** texto plano en `.env` (no versionado, `.gitignore` lo excluye -- verificado, patrón ya establecido en todo el proyecto). Ningún secreto de IA pasa por DB hoy.
- **Exposición:** ninguna ruta actual devuelve `ANTHROPIC_API_KEY`/`ADK_LLM_API_KEY` al frontend, logs o auditoría -- confirmado leyendo `form_assistant.py`, `adk_router.py`, `ollama_provider.py`, `openai_compatible_provider.py` (ninguno hace `logger.info`/`print` de `self.api_key`).
- **Mecanismo reutilizable ya en producción:** `apps/services/security/crypto.py` (Fernet, clave `MAILCFG_FERNET_KEY`) -- cifra/descifra, nunca expone la clave misma. Candidato real para `secret_ref` (plan §7) sin construir nada nuevo desde cero.
- **Riesgo real hoy, ya mitigado:** `AI_OPENAI_COMPAT_API_KEY` (recién agregado) solo es editable por quien tiene acceso al `.env` del servidor (nadie más) -- no hay superficie de ataque nueva mientras no exista una UI que la acepte de un usuario.

## 2. SSRF (Server-Side Request Forgery) -- `OpenAICompatibleProvider`/`OllamaProvider`

Ambos providers REST (`ollama_provider.py`, `openai_compatible_provider.py`) construyen la URL de destino a partir de `base_url` configurada **solo por variable de entorno** (`AI_OLLAMA_BASE_URL`, `AI_OPENAI_COMPAT_BASE_URL`) -- **no** desde input de request/usuario. Esto significa:

- **Hoy: sin superficie de SSRF explotable por un usuario final** -- solo quien controla el proceso `web` (acceso de infraestructura) puede cambiar esas URLs.
- **Riesgo futuro real, condicionado**: si la Fase 8 de este plan expone un formulario donde un STAFF autenticado (vía consola) puede pegar una URL arbitraria para "Custom REST" (§20, wizard de provider), ESE es el momento en que aplica el §30 del plan (allowlist de scheme, HTTPS obligatorio para remoto, bloqueo de rangos privados/metadata endpoints tipo `169.254.169.254`, política de redirects, timeout). **No implementado -- correctamente, no hace falta todavía** mientras la única forma de cambiar esas URLs sea editar `.env` directamente (fuera del alcance de un atacante remoto o incluso de un STAFF sin acceso al servidor).

## 3. Aislamiento tenant

Confirmado en `LLM_PROVIDER_BASELINE.md`: el provider/modelo activo es SYSTEM-wide, no tenant-scoped. Esto tiene una implicación de seguridad real a favor: **un tenant nunca puede, hoy, hacer que sus prompts/datos se enruten a un provider distinto del resto del deployment** -- no hay vector donde un tenant malicioso o comprometido pueda exfiltrar datos de OTRO tenant a un LLM externo de su elección, porque no controla esa configuración en absoluto. Si el plan avanza a "Tenant preferred provider/model" (§32), este análisis debe repetirse -- un tenant eligiendo su propio endpoint remoto SÍ sería una superficie nueva de exfiltración de datos (mismo patrón que el punto 2, pero con datos reales de negocio en juego, no solo la URL).

## 4. Autenticación/autorización de la futura UI de consola

- **Hoy:** `IsAdminUser` (DRF) en todas las vistas de `apps/public/console/api/` -- binario, staff sí/no. Coherente con que hoy console ya administra acciones sensibles (tenants, usuarios) con ese mismo nivel.
- **Gap real (ver GAP-5 en Migration Gaps):** el plan pide separar `ai.providers.secrets.manage` de `ai.providers.view` -- hoy CUALQUIER staff con acceso a consola vería/administraría secretos de IA igual que ve tenants. No es una regresión (nada de esto existe todavía), pero es un requisito real de Fase 8/9 antes de exponer gestión de secretos vía UI.

## 5. Tool calling -- enforcement ya existente, no depende de qué provider esté activo

`AUTO_APPROVED_KINDS` (`apps/services/ai/tools/base.py`) bloquea WRITE estructuralmente en `AIEngine.run_tool()` **sin importar qué LLM propuso la tool ni qué provider respondió** -- verificado en las pruebas reales de Ollama/ADK de hoy (ningún camino nuevo bypasea este check, porque todos convergen en el mismo `AIEngine.run_tool()`, ver `LLM_PROVIDER_DEPENDENCY_MAP.md`). El Hub de providers, aunque agregue N proveedores más, hereda esta garantía gratis mientras todos sigan pasando por `AIEngine` (regla que el propio plan exige en su §17 y Reglas Absolutas §50).

## 6. Reasoning/pensamiento privado -- ya verificado real, no solo prometido

`OllamaProvider.complete()` lee únicamente `message.content`, nunca `message.thinking` (verificado con Ollama real, Qwen3.5 -- ver `docs/ai/OLLAMA_STATUS.md` Fase 3). Mismo principio debe aplicar a cualquier provider nuevo que el Hub agregue (regla explícita §93 "NO EXPONER REASONING PRIVADO" del plan Ollama, heredada por este plan en su §50 "NO EXPONER REASONING PRIVADO").

## Conclusión de la fase

Ningún hallazgo de seguridad bloquea el arranque de Fase 1. El riesgo real más alto identificado (SSRF en Custom REST) está correctamente **fuera de superficie de ataque hoy** porque no existe todavía la UI que lo expondría -- debe resolverse ANTES (no después) de construir esa UI en Fase 8, no como parche posterior.
