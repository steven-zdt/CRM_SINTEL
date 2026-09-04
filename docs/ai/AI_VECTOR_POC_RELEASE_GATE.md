# AI_VECTOR_POC_RELEASE_GATE — AI-VECTOR-10

Gate de cierre del POC de **PostgreSQL 16 + pgvector + Vector/Retrieval
Layer multi-tenant** para el AI Engine de SINTEL. Consolida la evidencia de
AI-VECTOR-01 .. AI-VECTOR-09 (bitácora completa fase por fase:
`AI_VECTOR_POC_EXECUTION.md`; auditoría previa `AI_VECTOR_POC_AUDIT.md`;
plan `AI_VECTOR_POC_MASTER_PLAN.md`; arquitectura §8.7 en
`documentacion/arquitectura_general.md`).

Fecha: 2026-09-03. Rama: `feat/onboarding-cookie`. Commits `e593e2e` (01) ..
`fb074c1` (09). Cadencia: gate por gate, con verificación real en cada uno.

---

## Veredicto

```
POC_STATUS = POC_PASS_WITH_LIMITATIONS
```

Las **8 condiciones duras** de `POC_PASS` (mandato §AI-VECTOR-10) se cumplen,
todas con evidencia ejecutada — no diseñada. El calificador
`WITH_LIMITATIONS` refleja que el dataset del POC es **sintético** (no datos
reales de un tenant en producción), que el `LATENCY_GAIN` **medido** es
negativo a escala de POC, y que hay decisiones pendientes antes de un
rollout (índice ANN, trigger de reindexado, proveedor de embeddings). Ver
"Limitaciones conocidas".

| Condición `POC_PASS` | Estado | Evidencia |
|---|---|---|
| pgvector operational | **PASS** | extensión `vector` 0.8.6 en `public`, 1 instancia; columnas `vector(768)`; `EXPLAIN ANALYZE` de `ORDER BY embedding <=> q` = 0.48 ms (AI-VECTOR-01/02/09) |
| tenant isolation proven | **PASS** | 2 tenants reales (`aipoc`/`home`): buscar desde uno nunca devuelve docs del otro; `empresa_id` de A dentro del schema de B → `[]`; tests + smoke (AI-VECTOR-06) |
| retrieval functional | **PASS** | `run_tool("buscar_conocimiento", ...)` sobre el dataset real de `aipoc` → rankings correctos ("perforar concreto" → Taladro 800W, 0.74) (AI-VECTOR-05/07/08) |
| no sensitive leakage | **PASS** | allowlist `INDEXABLE_SOURCES` + `FORBIDDEN_MODEL_FIELDS` (candado en import) + `EmbeddingService` rechaza `source_type` no permitido + proveedor **local** (cero egress) (AI-VECTOR-06) |
| AI Engine integration functional | **PASS** | `RetrievalTool` registrada (20 tools), `AIEngine.run_tool()` **sin cambios** (`git diff` vacío), doble feature flag, routing en el orquestador (AI-VECTOR-07) |
| rollback tested | **PASS** | `migrate_schemas --tenant --schema=home tenant_ai_knowledge zero` **ejecutado**: reverse `0002`→`0001` OK, tablas eliminadas de `home`, **`aipoc` intacto**, re-migración OK (AI-VECTOR-10) |
| benchmark completed | **PASS** | AI-VECTOR-09: `TOKEN_REDUCTION 0.775`, `QUERY_REDUCTION 0.50`, `LATENCY_GAIN -24.7`, `RELEVANCE` top-1 0.595 / p@1 0.625, `MEMORY_IMPACT` ~357 MB — todos medidos |
| ERP regression = 0 | **PASS** | lecturas transaccionales sub-4 ms; `manage.py check` limpio; `makemigrations --check` limpio; `home` con 3 clientes intactos; 156 tests recolectan |

---

## Los 12 ejes

### 1. Infrastructure
- Servicio `db`: `postgres:16-alpine` → **`pgvector/pgvector:pg16`** (pineada
  por digest `sha256:ccc6e83d…`, Debian/glibc). PostgreSQL 16.14 → 16.15
  (minor drop-in). Volumen `crm_sintel_postgres_data` intacto, datos
  intactos. `REINDEX DATABASE sintel` una vez (cambio de collation musl→glibc).
- Named volume `crm_sintel_fastembed_cache` para el modelo ONNX (~0.64 GB).
- **AI-VECTOR-01 = PASS.**

### 2. Extension
- `apps/db_extensions/` (SOLO `SHARED_APPS`, sin modelos). `0001_vector_extension`
  = `RunPython` con **guard por schema** (`CREATE`/`DROP EXTENSION` solo en
  `public`). `pg_extension`: 1 instancia, namespace `public`. El tipo `vector`
  es visible desde cualquier tenant vía `search_path` `<tenant>, public`.
- **AI-VECTOR-02 = PASS.**

### 3. Migrations
- `db_extensions.0001` (shared) + `tenant_ai_knowledge.0001_initial` +
  `0002_pin_embedding_dimension_768` (`vector` → `vector(768)`, tablas
  vacías). Aplicadas por el entrypoint a los 3 tenants. `makemigrations
  --check` limpio. Precondición documentada en `DEPLOYMENT_RUNBOOK.md` §4
  (`--shared` antes de `--tenant`; restore a servidor nuevo exige la
  extensión pre-creada).
- **AI-VECTOR-02/03 = PASS.**

### 4. Tenant isolation
- **Opción B**: una tabla por schema de tenant (`tenant_ai_knowledge_*`),
  nunca `public.ai_chunks + tenant_id`. `public` no tiene ninguna tabla de
  negocio. `RetrievalService` ejecuta dentro de `schema_context` — no filtra
  por `tenant_id` (el schema es la garantía). `cross_tenant_leaks = 0`
  probado con 2 tenants reales.
- **AI-VECTOR-03/06 = PASS.**

### 5. Security
- Allowlist `INDEXABLE_SOURCES` = frontera. `FORBIDDEN_MODEL_FIELDS` (24
  pares) + `_assert_allowlist_safe()` en import. `EmbeddingService.index_text`
  lanza `ValueError` si el `source_type` no está permitido.
- Alcance organizacional: `RetrievalService.search_for_context(context, …)`
  traduce `AIContext.alcance` igual que `compras_tools._scope_kwargs`.
  `unauthorized_retrieval = 0` (SEDE(1) no ve docs de SEDE 2).
- `ToolRisk.SENSITIVE_READ` **no** es enforcement automático — pineado por
  test; el `RetrievalTool` aplica el alcance explícitamente en `run()`.
- Proveedor **local** → cero egress. `forbidden_indexed = 0`.
- Sección dedicada en `AI_SECURITY_MODEL.md`. **AI-VECTOR-06 = PASS.**

### 6. Embeddings
- Contrato `AIEmbeddingProvider` (ABC, separado de `AIProvider.complete()`).
  `FastEmbedProvider` — `fastembed` (ONNX, sin torch), modelo
  `jinaai/jina-embeddings-v2-base-es` (768d, ES/EN). Sin API key, sin coste.
  Guard de timeout, retry de carga, logging seguro (nunca el texto/vector).
- **AI-VECTOR-04 = PASS.**

### 7. Chunking
- `ChunkingService.chunk()` — capa pura de texto (párrafos → oraciones con
  solapamiento → corte duro). No BD, no proveedor, no tenants.
- **AI-VECTOR-05 = PASS.**

### 8. Retrieval
- `RetrievalService.search()` / `search_for_context()` — **solo lectura**,
  `CosineDistance` exact search **sin índice ANN** (plan §13), filtros
  `source_type` + sede/área NULL-safe. `RetrievalHit` con `score`.
- **AI-VECTOR-05 = PASS.**

### 9. AI integration
- `RetrievalTool` (`buscar_conocimiento`, READ/SAFE_READ, domain
  `ai_knowledge`) en `AIToolRegistry`. `AIEngine.run_tool()` **intacto**.
  Doble flag: `AI_READ_ENABLED` + `AI_RETRIEVAL_ENABLED` (default `false`).
  Routing determinista > semántico en el system prompt del orquestador.
  `AI_WRITE_ENABLED` sigue `false`. `AIContext` / EKG / tools existentes sin
  cambios.
- **AI-VECTOR-07 = PASS.**

### 10. Benchmark
- Comando `benchmark_ai_poc.py`. Sobre `aipoc` (24 docs/24 chunks, 9 iter):
  `TOKEN_REDUCTION 0.775` (baseline "mandar todo" ~1003 tok → vector top-k
  ~225), `QUERY_REDUCTION 0.50`, `LATENCY_GAIN -24.7` (negativo a escala
  POC — honesto), `MEMORY_IMPACT` ~357 MB (modelo; tablas 608 KB),
  `RELEVANCE` top-1 coseno 0.595 / p@1 0.625.
- **AI-VECTOR-09 = PASS** (valores fijados con evidencia).

### 11. Rollback
- **Probado (AI-VECTOR-10):** `migrate_schemas --tenant --schema=home
  tenant_ai_knowledge zero` → reverse `0002`→`0001`, tablas eliminadas de
  `home`, `aipoc` intacto (24 chunks), re-migración restaura `vector(768)`.
  El rollback por schema aísla — un tenant no afecta a otro.
- **Diseñado + guardado, no ejecutado** (afectaría DB-wide):
  - imagen: revertir la línea `image:` a `postgres:16-alpine` + `up -d db`
    (volumen intacto; `REINDEX` de nuevo).
  - extensión: `db_extensions 0001 zero` → `DROP EXTENSION IF EXISTS vector`
    solo desde `public` (guard); falla si hay columnas `vector` dependientes
    (correcto: primero revertir `tenant_ai_knowledge`).
- `RetrievalTool`: `AI_RETRIEVAL_ENABLED=false` lo apaga sin tocar nada más
  (probado en `test_retrieval_tool.py`).

### 12. Backup
- **Probado (AI-VECTOR-10):** `backup_tenant aipoc` → dump custom 1.21 MB
  que **incluye** `tenant_ai_knowledge_aiknowledgedocument` /
  `_aiknowledgechunk` con `TABLE DATA` (los embeddings) + constraints.
  `pg_dump` captura la columna `vector` sin tratamiento especial.
- Precondición de restore a servidor nuevo: `CREATE EXTENSION vector` debe
  existir **antes** de `pg_restore` — documentado en `DEPLOYMENT_RUNBOOK.md`
  §4 y `BACKUP_RESTORE_RUNBOOK.md` (pendiente de reflejar ahí, DEFERRED a
  AI-VECTOR-11).

---

## Limitaciones conocidas (no bloquean `POC_PASS`, sí condicionan el rollout)

| # | Limitación | Impacto | Dónde se resuelve |
|---|---|---|---|
| L1 | Dataset de `aipoc` **sintético** (12 Cliente + 12 Producto sembrados), no datos reales de un tenant en producción | El benchmark y la relevancia son indicativos, no representativos del volumen/ruido real | AI-VECTOR-11 (piloto sobre un tenant con datos reales) |
| L2 | `LATENCY_GAIN = -24.7` (el `embed_query` local ~41 ms es más caro que el fetch baseline ~3.4 ms con 24 docs) | Con datasets pequeños el vector **no** mejora latencia | Escala (baseline "mandar todo" deja de ser viable) / caché de query-embeddings / proveedor más rápido — decisión de AI-VECTOR-11 |
| L3 | **Sin índice ANN** (exact search) | O(n) por query — 0.5 ms con 24 filas, crece linealmente | Añadir `HnswIndex` cuando el benchmark a escala lo justifique (dimensión ya fija: `vector(768)`) |
| L4 | Reindexado **manual** (`reindex_tenant_knowledge.delay(schema)`), sin trigger automático desde `save()` | El Vector Store puede quedar desactualizado entre corridas | Celery Beat periódico o trigger por dominio — AI-VECTOR-11 |
| L5 | Modelo ONNX ~250–340 MB en RSS del proceso que embebe (worker Celery) | Coste de memoria por worker | Aceptable; alternativa = proveedor hosted (reintroduce egress + coste + latencia de red) |
| L6 | `RELEVANCE` p@1 = 0.625 (métrica de keyword exacto, conservadora) | 3/8 queries no tienen la keyword literal en el top-1 (aunque el top-1 es semánticamente relacionado, 0.51–0.57) | Evaluar con datos reales + métrica menos estricta (p@3, MRR) en AI-VECTOR-11 |
| L7 | `db_extensions` se registra en el `django_migrations` de todos los schemas (comportamiento de django-tenants 3.9) | Cosmético; el guard evita ejecución real por tenant | Ninguna acción; documentado |
| L8 | Backup/restore a **servidor nuevo** exige `CREATE EXTENSION vector` pre-aplicado | Riesgo operativo si se restaura sin ese paso | `BACKUP_RESTORE_RUNBOOK.md` — DEFERRED a AI-VECTOR-11 |

---

## Governance (verificado)

- [x] `AI_WRITE_ENABLED` sigue `false`. Ninguna tool WRITE registrada.
- [x] `AIContext` sin cambios (`git diff` vacío en `ai_context.py`).
- [x] `AIEngine.run_tool()` sin cambios (`git diff` vacío en `ai_engine.py`).
- [x] EKG sin cambios (`ekg_tools.py` / `tools/ekg/`).
- [x] Service Layer: patrón FSD, sin abstracciones nuevas.
- [x] `TenantMiddleware` / `search_path` sin cambios.
- [x] Modelos ERP sin cambios.
- [x] Ninguna Vector DB externa (Opción D descartada).
- [x] `apps/public/` no tocado (`apps/db_extensions/` vive fuera).
- [x] Tests: `apps/services/ai/tests/` + `apps/tenant/ai_knowledge/tests/` =
      **156** recolectan; suites focalizadas verdes (venv local, no Docker).

---

## Siguiente: AI-VECTOR-11 (rollout controlado)

Solo puede iniciar con `POC_PASS` o `POC_PASS_WITH_LIMITATIONS` + decisión
explícita del usuario. Estrategia: tenant piloto (datos reales) → 2 tenants
→ 25 % → 50 % → 100 %, con cada gate en PASS. Antes: resolver L1/L2/L4/L8 y
decidir sobre L3 (índice ANN). Rollback siempre disponible:
`AI_RETRIEVAL_ENABLED=false` (inmediato) / `migrate_schemas … zero` (tablas).
