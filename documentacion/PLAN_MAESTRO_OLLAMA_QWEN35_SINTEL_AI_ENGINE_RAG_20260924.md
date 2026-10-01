# PLAN MAESTRO — OLLAMA + QWEN3.5 PARA AI ENGINE / RAG SINTEL

**Fecha:** 2026-09-24  
**Base:** `arquitectura_general(20260924-164923).md`  
**Objetivo:** agregar un servicio Docker independiente de Ollama, incorporar Qwen3.5:9b y convertir Ollama en el proveedor principal de inferencia del asistente ERP, conservando LM Studio como fallback/laboratorio.

## 1. Decisión arquitectónica

Estado objetivo:

```text
SINTEL ERP
   ↓
Google ADK / AI Engine
   ↓
AIProvider Factory
   ├── PRIMARY → Ollama → Qwen3.5:9b
   └── FALLBACK → LM Studio → modelo actual
```

Ollama será el proveedor principal. LM Studio no se elimina.

**Regla:** ADK orquesta; Qwen razona/propone; AIContext aporta contexto; EKG aporta conocimiento estructural; RAG recupera conocimiento; AIToolRegistry controla capacidades; Service Layer ejecuta negocio.

## 2. No confundir LLM con embeddings

La arquitectura actual separa `AIEmbeddingProvider` de `AIProvider.complete()` y utiliza FastEmbed con `jinaai/jina-embeddings-v2-base-es`, 768 dimensiones, para pgvector. Mantenerlo.

```text
Qwen3.5 = LLM / reasoning / tool calling / planning
FastEmbed + jina = embeddings / retrieval
PostgreSQL + pgvector = vector store
```

No sustituir el modelo de embeddings por Qwen.

La arquitectura existente ya documenta `AIKnowledgeDocument`, `AIKnowledgeChunk`, aislamiento por schema y `RetrievalService` solo lectura. fileciteturn6file1

## 3. Modelo recomendado

Modelo inicial:

```text
qwen3.5:9b
```

Ollama publica actualmente Qwen3.5 con variantes 0.8B–122B; la variante 9B ronda 6.6 GB y dispone de texto, imagen, tools y thinking, con contexto publicado de 256K. citeturn0search0

Para el hardware indicado del proyecto —RTX 4060 y ~30 GB RAM— empezar con 9B permite priorizar estabilidad, tool calling, latencia y consumo. **Debe confirmarse mediante benchmark real antes del cutover productivo.**

Ollama también soporta structured outputs mediante JSON Schema, útil para Intent, Plan, Tool Arguments, ValidationResult y PolicyResult. citeturn0search1

## 4. Servicio Docker

Agregar un servicio independiente:

```text
ollama
 └── qwen3.5:9b
```

con volumen persistente:

```text
sintel_ollama_models
```

El AI Engine debe acceder internamente mediante:

```text
http://ollama:11434
```

No usar `localhost` entre contenedores.

No exponer `11434` públicamente en producción salvo necesidad explícita.

Topología:

```text
web
db
redis
celery
ai_engine_adk
ollama
```

## 5. Provider abstraction

Inspeccionar primero el contrato real existente.

Objetivo:

```python
get_ai_provider()
```

que resuelva:

```text
AI_PROVIDER=ollama   → OllamaProvider
AI_PROVIDER=lmstudio → LMStudioProvider
```

No acoplar ADK, agentes o tools directamente a Ollama.

El provider debe normalizar:

```text
content
tool_calls
finish_reason
usage
model
provider
metadata
errors
```

Si el contrato existente ya cubre parte de esto, extenderlo mínimamente.

## 6. Configuración

Adaptar los nombres a la configuración real; no duplicar settings:

```env
AI_PROVIDER=ollama
AI_OLLAMA_BASE_URL=http://ollama:11434
AI_OLLAMA_MODEL=qwen3.5:9b

AI_FALLBACK_PROVIDER=lmstudio
AI_LMSTUDIO_BASE_URL=<actual>
AI_LMSTUDIO_MODEL=<actual>

AI_PROVIDER_TIMEOUT_S=120
AI_PROVIDER_MAX_RETRIES=1
```

La IA editora debe descubrir los nombres actuales antes de modificarlos.

## 7. OllamaProvider

Responsabilidades:

```text
API communication
timeouts
retry
structured output
tool calling
response normalization
health
error normalization
```

No debe conocer modelos de negocio.

Nunca:

```text
OllamaProvider → Cliente ORM
OllamaProvider → Factura ORM
OllamaProvider → SQL
```

## 8. ADK + Ollama

Mantener:

```text
Google ADK
   ↓
AIContext
   ↓
OllamaProvider
   ↓
Qwen3.5
```

El modelo continúa usando:

```text
AIToolRegistry
EKG
ai_project_map
RetrievalTool
Service Layer
```

La arquitectura actual ya registra `buscar_conocimiento` como `RetrievalTool` y mantiene `AI_READ_ENABLED` + `AI_RETRIEVAL_ENABLED`; esos contratos deben conservarse. fileciteturn6file3

## 9. RAG

Flujo objetivo:

```text
Usuario
 ↓
ADK
 ↓
Qwen3.5
 ↓
Intent
 ↓
RetrievalTool
 ↓
RetrievalService
 ↓
FastEmbed
 ↓
pgvector
 ↓
Context
 ↓
Qwen3.5
 ↓
Tool planning
```

Qwen no ejecuta directamente SQL ni búsquedas vectoriales.

La arquitectura actual ya tiene aislamiento cross-tenant probado y `AI_WRITE_ENABLED=false`; la migración del provider no debe alterar esos gates. fileciteturn6file3

## 10. EKG + RAG

Conservar:

```text
AIContext
+
ai_project_map
+
EKG
+
RAG
+
runtime ERP
```

No crear segundo EKG.

No crear segunda vector DB.

No convertir RAG en autoridad de permisos.

## 11. Structured output

Usar JSON Schema para:

```text
Intent
Plan
ToolCall
ValidationResult
PolicyDecision
WorkflowResult
```

Validar siempre el resultado antes de consumirlo.

No confiar en JSON generado libremente.

## 12. Tool calling

Cadena obligatoria:

```text
Qwen3.5
 ↓
tool proposal
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
Qwen3.5 → ORM
```

## 13. Fallback

LM Studio permanece como proveedor secundario.

Para READ:

```text
Ollama failure
 ↓
LM Studio fallback
```

Para WRITE:

```text
Ollama failure
 ↓
STOP
```

No hacer fallback automático durante una escritura o acción financiera.

## 14. Provider health

Crear o extender el health existente:

```text
provider
model
reachable
latency
loaded/available
error rate
```

Validar:

```text
Ollama
LM Studio
```

sin exponer secretos.

## 15. Modelo persistente y warmup

El modelo no debe descargarse por request.

Usar volumen persistente.

Bootstrap idempotente:

```text
wait Ollama
 ↓
ollama list
 ↓
si falta qwen3.5:9b → pull
 ↓
healthcheck
```

No bloquear indefinidamente el arranque del ERP por una descarga.

## 16. Producción

Fijar de forma reproducible:

```text
Ollama image
model tag
model digest/checksum si está disponible
```

No depender de `latest`.

No exponer públicamente `11434`.

## 17. Context window

Aunque Qwen3.5 soporte contexto amplio, no enviar el ERP completo.

Usar:

```text
EKG
+
RAG top-k
+
runtime state
+
domain context
```

La POC existente ya mostró reducción importante del contexto enviado frente al baseline, aunque la latencia del embedding local todavía quedó como limitación. fileciteturn6file9

## 18. Reasoning

Usar thinking/reasoning para:

```text
multi-step planning
cross-domain workflows
diagnóstico
ambigüedad
```

Nunca enviar `reasoning_content` al usuario.

## 19. Seguridad

Ollama es componente interno, no autoridad.

No darle al LLM:

```text
DB credentials
tenant authority
permission authority
shell
arbitrary SQL
```

El tenant siempre proviene de identidad autenticada y `AIContext`.

## 20. Fases

### FASE 0 — Baseline

Inspeccionar:

```text
AIProvider
AIEngine
ADK
LM Studio
settings
Docker
RAG
RetrievalTool
FastEmbed
pgvector
```

Entregar:

```text
docs/ai/OLLAMA_BASELINE.md
docs/ai/OLLAMA_MIGRATION_GAPS.md
docs/ai/OLLAMA_DEPENDENCY_MAP.md
```

Gate: `PASS`.

### FASE 1 — Ollama Infrastructure

Agregar servicio Docker, red, volumen y healthcheck.

Validar:

```text
container
network
volume
GPU
health
```

Gate:

```text
OLLAMA-INFRA=PASS
```

### FASE 2 — Qwen3.5:9b

Instalar y validar:

```text
inference
Spanish
English
structured JSON
tool calling
reasoning
context
```

Gate:

```text
QWEN35-9B=PASS
```

### FASE 3 — OllamaProvider

Implementar adapter respetando el contrato existente.

No modificar innecesariamente:

```text
AIEngine
AIContext
AIToolRegistry
RAG
```

### FASE 4 — Provider Factory

Configurar:

```text
primary = Ollama
fallback = LM Studio
```

Probar ambos independientemente.

### FASE 5 — ADK

Conectar:

```text
ADK → AIProvider → Ollama → Qwen3.5
```

Validar tools, EKG y contexto.

### FASE 6 — RAG

Validar:

```text
Qwen3.5
+
RetrievalTool
+
FastEmbed
+
pgvector
```

No cambiar el embedding model.

### FASE 7 — Tool Calling

Probar inicialmente:

```text
buscar_cliente
buscar_producto
buscar_conocimiento
```

y las demás tools existentes.

WRITE continúa bloqueado.

### FASE 8 — Benchmark

Comparar LM Studio vs Ollama/Qwen3.5:9b usando los mismos casos:

```text
TTFT
tokens/sec
total latency
VRAM
RAM
CPU
tool-call success
JSON validity
intent accuracy
RAG faithfulness
tool selection
```

No declarar ganador sin medición.

### FASE 9 — Primary Cutover

Solo con gates verdes:

```env
AI_PROVIDER=ollama
AI_FALLBACK_PROVIDER=lmstudio
```

### FASE 10 — Producción

Actualizar `docker-compose.prod.yml` con:

```text
persistent volume
internal network
healthcheck
resource limits/policy
model bootstrap
```

### FASE 11 — Observabilidad

Registrar:

```text
provider
model
latency
TTFT
tokens
tool calls
errors
fallback
```

Nunca registrar:

```text
secrets
reasoning
credenciales
datos sensibles innecesarios
```

### FASE 12 — Release Gate

No liberar si falla:

```text
Ollama
model
tool calling
RAG
tenant isolation
fallback
ERP regression
```

## 21. Loop obligatorio para la IA editora

```text
INSPECT
 ↓
READ ARCHITECTURE
 ↓
READ REAL CODE
 ↓
MAP DEPENDENCIES
 ↓
PLAN
 ↓
IMPLEMENT MINIMAL CHANGE
 ↓
TEST
 ↓
BENCHMARK
 ↓
SECURITY
 ↓
REGRESSION
 ↓
DOCUMENT
 ↓
GATE
 ├── FAIL → DIAGNOSE → FIX → LOOP
 ├── PARTIAL → DOCUMENT → FIX → LOOP
 └── PASS → NEXT PHASE
```

## 22. Reglas absolutas

```text
NO ELIMINAR LM STUDIO.

NO CAMBIAR EL MODELO DE EMBEDDINGS.

NO CREAR OTRA VECTOR DATABASE.

NO CREAR OTRO EKG.

NO CREAR OTRO AIContext.

NO CREAR OTRO TOOL REGISTRY.

NO ACCEDER AL ORM DESDE OLLAMA.

NO PERMITIR QUE QWEN DECIDA EL TENANT.

NO PERMITIR QUE QWEN DECIDA PERMISOS.

NO EJECUTAR SQL GENERADO POR EL LLM.

NO HABILITAR AI_WRITE_ENABLED DURANTE ESTA MIGRACIÓN.

NO HACER FALLBACK AUTOMÁTICO DE WRITE.

NO EXPONER OLLAMA A INTERNET.

NO USAR localhost ENTRE CONTENEDORES.

NO DESCARGAR EL MODELO EN CADA REQUEST.

NO USAR latest COMO DEPENDENCIA PRODUCTIVA.

NO EXPONER reasoning_content.

NO ENVIAR TODO EL ERP AL CONTEXTO.

USAR EKG.

USAR RAG.

USAR AIContext.

USAR AIToolRegistry.

USAR SERVICE LAYER.

VERIFICAR TODA ESCRITURA.

MEDIR ANTES DE DECLARAR MEJORAS.

NO AVANZAR CON FAIL.
```

## 23. Resultado final

```text
                 AI PROVIDER
                     │
          ┌──────────┴──────────┐
          │                     │
       PRIMARY              FALLBACK
          │                     │
       Ollama              LM Studio
          │
    Qwen3.5:9b
          │
       Google ADK
          │
       AI Engine
          │
 ┌────────┼─────────┐
 ▼        ▼         ▼
EKG      RAG       Tools
         │           │
     pgvector      Services
         │           │
     FastEmbed     PostgreSQL
```

El asistente queda preparado para evolucionar:

```text
READ
 ↓
RAG
 ↓
TOOL CALLING
 ↓
VALIDATE
 ↓
PLAN
 ↓
PREVIEW
 ↓
WRITE
 ↓
VERIFY
 ↓
MULTI-AGENT WORKFLOWS
```

sin rediseñar nuevamente el ERP.

## 24. Primera misión

La IA editora **no debe empezar modificando producción**.

Primero ejecutar:

```text
FASE 0
```

y producir los tres documentos de baseline.

Después:

```text
FASE 1 → OLLAMA SERVICE
FASE 2 → QWEN3.5:9B
FASE 3 → PROVIDER
FASE 4 → FACTORY
FASE 5 → ADK
FASE 6 → RAG
FASE 7 → TOOLS
FASE 8 → BENCHMARK
FASE 9 → PRIMARY CUTOVER
```

### GATE MAESTRO

```text
INSPECT
→ MAP
→ IMPLEMENT
→ TEST
→ BENCHMARK
→ SECURITY
→ REGRESSION
→ DOCUMENT
→ PASS
```

No activar `AI_WRITE_ENABLED` como parte de esta migración.
