# PLAN MAESTRO — LLM PROVIDER HUB MULTIMODELO PARA SINTEL ERP

**Fecha:** 2026-09-24  
**Objetivo:** desacoplar completamente SINTEL ERP y Google ADK de cualquier LLM concreto y crear en `/console/` una UI para administrar proveedores, conexiones, modelos, capacidades, estado, selección manual y auditoría.

## 1. DECISIÓN ARQUITECTÓNICA

El estado objetivo es:

```text
SINTEL ERP
   ↓
Google ADK / AI Engine
   ↓
LLM Provider Gateway
   ↓
Provider Adapter
   ├── Ollama
   ├── LM Studio
   ├── OpenAI-compatible REST
   ├── OpenAI
   ├── Gemini
   ├── Anthropic
   └── futuros adapters
       ↓
     modelo elegido
```

**Regla:** el LLM es intercambiable; SINTEL mantiene conocimiento, seguridad, tenancy, herramientas, reglas y ejecución.

ADK orquesta. El LLM razona/propone. `AIToolRegistry` controla capacidades. Policy autoriza. Service Layer ejecuta. SINTEL verifica.

## 2. PROVIDER ≠ TRANSPORTE ≠ MODELO ≠ MCP

No mezclar conceptos:

- **Provider:** Ollama, LM Studio, OpenAI, Gemini, Anthropic, etc.
- **Transport:** REST, OpenAI-compatible REST, SDK, streaming, etc.
- **Model:** identificador concreto del modelo.
- **MCP:** frontera de herramientas/contexto, no un LLM provider.

MCP debe integrarse como mecanismo de tools cuando aporte valor, sin convertirlo en sustituto de `AIProvider`.

## 3. PRINCIPIO DE NO BLOQUEO

Ningún proveedor ni modelo puede convertirse en dependencia única del ERP.

Si falla un provider:

```text
READ → puede usar fallback según policy
WRITE/financiero → detener y requerir retry explícito
```

Si un modelo no soporta una capacidad requerida, se marca como incompatible para ese workload, pero no se bloquea todo el sistema.

## 4. CONSOLA PÚBLICA

Implementar dentro de la consola existente en:

```text
https://sintel.net.co/console/
```

No crear un segundo admin.

Menú propuesto:

```text
⚙ Configuración
  └── 🤖 Inteligencia Artificial
      ├── Proveedores IA
      ├── Modelos
      ├── Modelo activo
      ├── Salud y capacidades
      └── Auditoría
```

La IA editora debe descubrir primero el layout, sidebar, rutas, permisos, API client, componentes y estilos existentes y reutilizarlos.

## 5. UX PRINCIPAL

La primera pantalla debe responder inmediatamente:

```text
MODELO ACTUALMENTE EN USO

🟢 Ollama
Qwen3.5:9b

Conexión: Local / REST
Estado: Operativo

Uso:
✓ Asistente ERP
✓ RAG
✓ Agentes ADK
✓ Tool Calling

[ Cambiar modelo ] [ Probar conexión ]
```

Cada provider se muestra como card con:

- nombre
- modelo activo
- local/remoto/cloud
- estado
- capacidades
- último health check
- acciones

## 6. MODELO DE DATOS

Antes de crear entidades, buscar y reutilizar cualquier estructura existente como:

```text
AIProvider
AIModel
AIProviderConfig
AIEngineConfig
AISettings
LLMConfig
AIProviderFactory
```

Si no existe un contrato adecuado, crear una capa central.

### `LLMProvider`

Conceptualmente:

```text
id
name
slug
provider_type
transport_type
description
enabled
is_local
base_url
secret_ref
organization
default_timeout
created_at
updated_at
```

### `LLMModel`

```text
id
provider_id
name
display_name
model_identifier
enabled
context_window
max_output_tokens
supports_tools
supports_streaming
supports_structured_output
supports_vision
supports_reasoning
status
last_health_check
metadata
```

### `LLMConnection`

Debe representar local, remoto, cloud o self-hosted.

### `LLMActiveConfig`

Debe representar provider/modelo activo, scope, versión, fecha y usuario que lo activó.

### Auditoría

Guardar quién, cuándo, provider/modelo anterior, nuevo provider/modelo, resultado y motivo. Nunca secretos.

## 7. SECRET MANAGEMENT

Nunca guardar API keys en texto plano en DB, frontend, logs, session state, EKG o RAG.

Usar el mecanismo de secrets existente: environment secret, Docker secret, vault o secret manager.

En DB guardar solo:

```text
secret_ref
```

La UI debe mostrar:

```text
API Key: ••••••••••••9F3A
[Actualizar]
```

Nunca la clave completa.

## 8. CONTRATO ÚNICO DE PROVIDER

Crear o evolucionar un contrato similar a:

```python
class LLMProvider(Protocol):
    def chat(...): ...
    def stream(...): ...
    def health(...): ...
    def list_models(...): ...
    def get_capabilities(...): ...
    def validate_connection(...): ...
```

Y contratos normalizados:

```text
LLMResponse
LLMCapabilities
LLMHealth
LLMModelDescriptor
```

ADK y los agentes no deben conocer detalles de Ollama, LM Studio u otro provider.

## 9. ADAPTERS

Implementar progresivamente:

```text
OllamaProvider
LMStudioProvider
OpenAICompatibleProvider
OpenAIProvider
GeminiProvider
AnthropicProvider
CustomRESTProvider
```

El mínimo inicial es:

```text
Ollama
LM Studio
OpenAI-compatible REST
```

El adapter universal OpenAI-compatible permitirá conectar endpoints como Ollama, LM Studio, gateways y servidores propios sin escribir un adapter por servicio cuando el contrato sea compatible. Ollama documenta una API compatible con OpenAI. citeturn0search9

## 10. OLLAMA

Registrar como provider:

```text
Provider: Ollama
Transport: REST
Endpoint interno: http://ollama:11434
Modelo inicial: qwen3.5:9b
```

El modelo no debe quedar hardcoded en agentes ni prompts.

Ollama soporta tool calling y structured outputs, por lo que puede participar en el flujo agentic cuando sus capacidades hayan sido verificadas. citeturn0search0turn0search1

## 11. LM STUDIO

Mantenerlo como provider independiente:

```text
LM Studio
OpenAI-compatible REST
endpoint configurable
modelo configurable
```

No eliminarlo.

## 12. RESOLVER CENTRAL

Crear/evolucionar una única función:

```python
resolve_active_llm(tenant_context, agent_context, workload)
```

Debe devolver:

```text
provider
model
connection
capabilities
policy
```

Ejemplo:

```json
{
  "provider": "ollama",
  "model": "qwen3.5:9b",
  "transport": "openai_compatible_rest",
  "capabilities": {
    "tools": true,
    "streaming": true,
    "structured_output": true
  }
}
```

No permitir que cada agente resuelva el modelo por su cuenta.

## 13. MODELO GLOBAL Y POR WORKLOAD

Primera versión:

```text
Global default model
```

Preparar arquitectura para overrides posteriores:

```text
ERP Assistant → modelo A
Customer Support → modelo B
Document Extraction → modelo C
Vision → modelo D
```

Los agentes deben declarar capacidades requeridas, no un modelo fijo.

## 14. NO CAMBIAR MODELO DESDE EL PROMPT

Nunca permitir:

```text
usuario: usa GPT...
LLM: cambia provider
```

La selección proviene de configuración/policy autenticada.

El LLM nunca decide tenant, permisos, provider, secrets o autorización.

## 15. NORMALIZACIÓN

Crear `LLMResponseNormalizer` para convertir Ollama, LM Studio, OpenAI, Gemini, Anthropic y REST compatible a un contrato común:

```text
content
tool_calls
finish_reason
usage
model
provider
capabilities
metadata
```

Esto evita provider-specific code en ADK.

## 16. STRUCTURED OUTPUT

Normalizar JSON Schema/Pydantic/provider-specific output a un contrato interno.

Si un provider no soporta structured output:

```text
capability=false
```

y solo se deshabilitan los workflows que lo requieren.

Ollama soporta structured outputs mediante JSON Schema. citeturn0search0

## 17. TOOL CALLING

Cadena obligatoria:

```text
LLM
 ↓
tool proposal
 ↓
normalizer
 ↓
AIToolRegistry
 ↓
Policy
 ↓
Service / Command
 ↓
Verification
```

Nunca:

```text
LLM → ORM
LLM → SQL
LLM → Python arbitrario
```

El soporte nativo de tool calling del provider es una capacidad técnica, no una autorización. Ollama documenta tool calling vía API. citeturn0search1

## 18. RAG Y EKG

No cambiar por esta migración:

```text
AIContext
EKG
ai_project_map
AIKnowledgeDocument
AIKnowledgeChunk
FastEmbed
jina embeddings
pgvector
RetrievalService
RetrievalTool
```

El LLM es intercambiable; embeddings y vector DB siguen independientes.

Flujo:

```text
Usuario
 ↓
ADK
 ↓
Active LLM
 ↓
RetrievalTool
 ↓
FastEmbed
 ↓
pgvector
 ↓
RAG context
 ↓
Active LLM
```

No reindexar por cambiar de LLM.

## 19. UI — CAMBIAR MODELO

Botón:

```text
[ Cambiar modelo ]
```

Modal/wizard:

```text
Proveedor
Modelo
Estado
Conexión
Capacidades
Uso

[Cancelar] [Probar] [Activar]
```

No activar si falla health/capability check.

## 20. WIZARD DE PROVIDER

Pasos:

```text
1. Tipo de proveedor
2. Conexión
3. Credenciales
4. Descubrir/seleccionar modelos
5. Capacidades
6. Prueba
7. Activación
```

Tipos:

```text
Local
Servidor remoto
Cloud
OpenAI-compatible
Custom REST
```

## 21. CAPABILITY PROBE

Al registrar modelo ejecutar, cuando sea soportado:

```text
basic chat
streaming
structured output
tool call
vision
reasoning metadata
```

Guardar:

```text
verified
verified_at
verification_version
```

No asumir capacidades por nombre de modelo.

## 22. CAPABILITY MATRIX

La UI debe mostrar:

| Capacidad | Estado |
|---|---|
| Chat | 🟢/🔴 |
| Streaming | 🟢/🔴 |
| Tool Calling | 🟢/🔴 |
| Structured Output | 🟢/🔴 |
| Thinking/Reasoning | 🟢/🔴 |
| Vision | 🟢/🔴 |
| Embeddings | 🟢/🔴 |

RAG debe aparecer como **capacidad del sistema**, no como capacidad nativa del LLM.

## 23. WORKLOAD POLICY

Cada workload define requisitos:

```text
ERP Assistant:
  tools=true
  structured_output=true

Support:
  chat=true
  streaming=recommended

Vision:
  vision=true
```

Resolver valida:

```text
model capabilities >= workload requirements
```

## 24. ACTIVE MODEL

Endpoint conceptual:

```text
GET /api/v1/ai/active/
```

Debe devolver provider, modelo, conexión no secreta, estado, capacidades y workloads. Nunca API keys ni headers secretos.

## 25. CAMBIO SIN REINICIAR

Siempre que el runtime lo permita:

```text
UI
 ↓
API
 ↓
validate
 ↓
health
 ↓
capabilities
 ↓
persist
 ↓
invalidate cache
 ↓
new request uses new model
```

No reiniciar Django/ERP innecesariamente.

## 26. CACHE Y CONCURRENCIA

DB es fuente persistente; Redis puede cachear la configuración validada.

Al cambiar:

```text
DB transaction
 ↓
cache invalidation
```

Usar optimistic locking/versioning para evitar activaciones simultáneas inconsistentes.

## 27. ROLLBACK

Guardar `last_known_good_config`.

UI:

```text
Modelo actual
Modelo anterior
[Restaurar anterior]
```

Un provider nuevo no debe dejar al sistema sin configuración válida.

## 28. FALLBACK

Definir una policy, no una cadena hardcoded:

```text
PRIMARY
SECONDARY
TERTIARY
```

Para READ/support puede haber fallback automático.

Para WRITE/financiero:

```text
provider failure
 ↓
STOP
 ↓
retry explícito
```

Esto evita duplicación de operaciones.

## 29. HEALTH

Mostrar:

```text
DNS/connectivity
HTTP
Authentication
Model availability
Tools
Structured output
Latency
Última comprobación
```

No mostrar secretos ni stack traces.

## 30. SEGURIDAD CUSTOM REST

Validar contra SSRF:

```text
scheme allowlist
HTTPS para remoto
DNS policy
blocked private ranges según deployment
redirect policy
timeout
host allowlist cuando corresponda
```

Nunca aceptar URL arbitraria que pueda alcanzar metadata endpoints o servicios internos sensibles.

## 31. PERMISOS

Crear o reutilizar permisos equivalentes a:

```text
ai.providers.view
ai.providers.manage
ai.providers.test
ai.providers.activate
ai.providers.secrets.manage
ai.providers.audit
```

Separar ver, modificar, probar, activar y administrar secretos.

## 32. MULTITENANCY

Fase 0 debe determinar si el provider activo es:

```text
SYSTEM / PUBLIC
```

o:

```text
TENANT-SCOPED
```

No asumirlo.

Si es infraestructura global, el tenant común no debe poder cambiarla.

Si existe preferencia por tenant, debe existir:

```text
System allowed providers/models
Tenant preferred provider/model
```

La identidad autenticada y `AIContext` siempre determinan el tenant.

## 33. AUDITORÍA

Registrar:

```text
user
scope/tenant
when
previous provider/model
new provider/model
reason
result
trace/request id
```

No registrar secrets, tokens ni datos sensibles innecesarios.

## 34. OBSERVABILIDAD

Métricas descriptivas:

```text
request_count
success_rate
error_rate
fallback_rate
TTFT
total_latency
tokens_in
tokens_out
tokens_per_second
tool_call_success
structured_output_success
RAG grounding
resource usage
```

No crear un ranking político/comercial ni un score global engañoso; la UI debe presentar métricas y estados verificables.

## 35. FASE 0 — BASELINE FORENSE

Inspeccionar:

```text
ai_engine_adk/
apps/services/ai/
apps/tenant/ai_knowledge/
EKG
RAG
AIToolRegistry
LM Studio
Ollama
settings
Docker
Redis
Postgres
public schema
console
permissions
secrets
```

Buscar también:

```text
AI_MODEL_PROVIDER
AI_MODEL
LOCAL_MODEL_CHAIN
OLLAMA_BASE_URL
LMSTUDIO_BASE_URL
OPENAI_API_KEY
GEMINI_API_KEY
ANTHROPIC_API_KEY
```

Entregar:

```text
docs/ai/LLM_PROVIDER_BASELINE.md
docs/ai/LLM_PROVIDER_DEPENDENCY_MAP.md
docs/ai/LLM_PROVIDER_MIGRATION_GAPS.md
docs/ai/LLM_PROVIDER_SECURITY_BASELINE.md
```

Gate: no avanzar sin saber exactamente provider/modelo/endpoint/transport/secret storage/ADK integration/UI actual.

## 36. FASE 1 — CONTRATO

Crear/evolucionar:

```text
LLMProvider
LLMResponse
LLMCapabilities
LLMHealth
LLMModelDescriptor
LLMProviderResolver
```

Tests unitarios y de contrato.

Gate: `LLM_CONTRACT=PASS`.

## 37. FASE 2 — OLLAMA

Implementar adapter y probar:

```text
chat
stream
tools
structured output
health
model discovery
```

No cambiar RAG.

Gate: `OLLAMA=PASS`.

## 38. FASE 3 — LM STUDIO

Integrar mediante adapter existente o OpenAI-compatible adapter.

Gate: `LMSTUDIO=PASS`.

## 39. FASE 4 — OPENAI-COMPATIBLE REST

Permitir:

```text
base_url
secret_ref
model_id
allowed headers
```

Gate: `CUSTOM_REST=PASS`.

## 40. FASE 5 — RESOLVER + ADK

Migrar ADK para resolver provider/modelo centralmente.

Prohibido:

```text
agent.py → Ollama hardcoded
agent.py → LM Studio hardcoded
```

Gate: todos los agentes usan el contrato.

## 41. FASE 6 — RAG/EKG

Probar el mismo caso con distintos LLMs manteniendo:

```text
same embeddings
same pgvector
same RetrievalTool
same EKG
same AIContext
```

Gate: no regresión de grounding ni aislamiento tenant.

## 42. FASE 7 — TOOLS

Ejecutar primero:

```text
buscar_cliente
buscar_producto
buscar_conocimiento
```

Luego toda la suite autorizada.

Validar selección, argumentos, policy, ejecución y verificación.

## 43. FASE 8 — API + UI

Construir/reutilizar:

```text
Proveedores IA
Modelos
Modelo activo
Salud
Capacidades
Auditoría
```

CRUD completo donde corresponda.

El administrador debe poder:

```text
crear
editar
probar
descubrir modelos
seleccionar
activar
desactivar
ver capacidades
ver salud
ver auditoría
rollback
```

## 44. FASE 9 — SECRETS

Implementar secret references, masking, rotación y tests para garantizar que jamás aparezcan completos en:

```text
API
frontend
logs
audit
DB
sessions
```

## 45. FASE 10 — FALLBACK + HEALTH

Implementar policy de fallback y health checks.

Casos obligatorios:

```text
primary unavailable
secondary available
primary timeout
invalid key
model missing
tool unsupported
structured output unsupported
```

## 46. FASE 11 — BENCHMARK

Comparar con los mismos casos:

```text
simple ERP question
RAG question
tool call
multi-tool
structured output
Spanish
ambiguous request
long context
```

Métricas:

```text
TTFT
latency
tokens/sec
tool success
JSON validity
RAG grounding
error rate
fallback rate
resource consumption
cost
```

No declarar un ganador general; usar resultados para configurar por workload.

## 47. FASE 12 — PRODUCCIÓN

Actualizar únicamente lo necesario en:

```text
docker-compose.yml
docker-compose.prod.yml
settings
secrets
nginx
AI Engine
Celery
Redis
```

Verificar red interna, TLS remoto, timeouts, rate limits, health y egress.

## 48. FASE 13 — RELEASE GATE

No liberar si falla:

```text
Provider contract
Ollama
LM Studio
Custom REST
Resolver
ADK
RAG
EKG
Tool Registry
tenant isolation
permissions
secret masking
UI
audit
rollback
fallback
```

## 49. LOOP OBLIGATORIO DE IA EDITORA

```text
INSPECT
 ↓
READ ARCHITECTURE
 ↓
READ REAL CODE
 ↓
MAP PROVIDERS
 ↓
MAP CONSOLE
 ↓
MAP TENANT BOUNDARIES
 ↓
PLAN
 ↓
IMPLEMENT MINIMAL CHANGE
 ↓
UNIT TEST
 ↓
INTEGRATION TEST
 ↓
SECURITY TEST
 ↓
UI TEST
 ↓
PROVIDER TEST
 ↓
RAG REGRESSION
 ↓
ADK REGRESSION
 ↓
AUDIT
 ↓
DOCUMENT
 ↓
GATE
 ├─ FAIL → DIAGNOSE → FIX → LOOP
 ├─ PARTIAL → DOCUMENT → FIX → LOOP
 └─ PASS → NEXT PHASE
```

## 50. REGLAS ABSOLUTAS

```text
NO ACOPLAR ERP A UN LLM.
NO ACOPLAR ADK A OLLAMA.
NO ACOPLAR AGENTS A UN PROVIDER.
NO GUARDAR API KEYS EN TEXTO PLANO.
NO DEVOLVER SECRETS AL FRONTEND.
NO CAMBIAR PROVIDER DESDE PROMPT.
NO PERMITIR AL LLM DECIDIR TENANT/PERMISOS.
NO ORM/SQL DIRECTO DESDE EL LLM.
NO DUPLICAR AIContext/EKG/RAG/Tool Registry/Service Layer.
NO CAMBIAR EMBEDDINGS POR CAMBIAR LLM.
NO CREAR SEGUNDA CONSOLA ADMIN.
NO EXPONER OLLAMA DIRECTAMENTE A INTERNET.
NO PERMITIR SSRF EN CUSTOM REST.
NO ACTIVAR SIN HEALTH + CAPABILITY CHECK.
NO FALLBACK AUTOMÁTICO DURANTE WRITE.
NO EXPONER REASONING PRIVADO.
NO REGISTRAR SECRETOS.
NO ASUMIR CAPACIDADES.
MEDIR.
AUDITAR.
DOCUMENTAR.
ROLLBACK SI ES NECESARIO.
```

## 51. CRITERIO DE ÉXITO

Desde `/console/` un administrador puede:

```text
Proveedores IA
 ↓
Agregar provider
 ↓
Configurar conexión
 ↓
Probar
 ↓
Descubrir modelos
 ↓
Seleccionar modelo
 ↓
Ver capacidades
 ↓
Activar
```

y posteriormente:

```text
Cambiar modelo
 ↓
otro provider/modelo
 ↓
probar
 ↓
activar
```

sin editar agentes, RAG, EKG, Tool Registry o Service Layer.

También debe poder conectar un endpoint OpenAI-compatible remoto mediante API key sin que el ERP quede atado a ese proveedor.

## 52. ARQUITECTURA FINAL

```text
                         SINTEL ERP
                              │
                              ▼
                     GOOGLE ADK / AI ENGINE
                              │
                              ▼
                     LLM PROVIDER HUB
                              │
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
          Ollama          LM Studio       Remote APIs
             │                │                │
             └────────────────┼────────────────┘
                              ▼
                    NORMALIZED LLM CONTRACT
                              │
                              ▼
                            ADK
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
           EKG               RAG              TOOLS
                              │                 │
                          pgvector        Tool Registry
                              │                 │
                         FastEmbed        Service Layer
                                                │
                                                ▼
                                           PostgreSQL
```

## 53. PRIMERA MISIÓN

La IA editora **NO debe empezar modificando producción**.

Primero ejecutar FASE 0 y producir los cuatro documentos de baseline. Debe identificar inequívocamente:

```text
CURRENT_PRIMARY_PROVIDER
CURRENT_PRIMARY_MODEL
CURRENT_FALLBACK_PROVIDER
CURRENT_FALLBACK_MODEL
OLLAMA_ENABLED
LM_STUDIO_ENABLED
CURRENT_ADK_MODEL_PATH
CURRENT_RAG_PATH
CURRENT_CONSOLE_PATH
CURRENT_SECRET_STORAGE
CURRENT_TENANT_SCOPE
```

Después continuar secuencialmente por fases y no avanzar con `FAIL`.

## 54. FUENTES TÉCNICAS VERIFICADAS

- Google ADK documenta una abstracción de LLM y soporte para múltiples proveedores, incluyendo Gemini, Claude, LiteLLM y Ollama. citeturn1search0turn1search4
- Ollama documenta compatibilidad con OpenAI API. citeturn0search9
- Ollama documenta tool calling. citeturn0search1
- Ollama documenta structured outputs con JSON Schema. citeturn0search0

**Nota:** la existencia de una capacidad en un proveedor no implica que SINTEL deba confiar en ella sin validación. Todas las capabilities usadas por un workload deben pasar por el capability probe y por las políticas internas de SINTEL.
