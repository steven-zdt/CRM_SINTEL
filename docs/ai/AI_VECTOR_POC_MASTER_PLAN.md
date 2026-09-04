# AI_VECTOR_POC_MASTER_PLAN — AI-VECTOR-00

Plan técnico ejecutable y verificable para un futuro POC de
**PostgreSQL 16 + pgvector + Vector/Retrieval Layer multi-tenant**,
integrado dentro de `apps/services/ai/`, probado sobre un único tenant.
Este documento **diseña**, no implementa. Toda la evidencia que sustenta
cada decisión vive en `AI_VECTOR_POC_AUDIT.md` — este plan no repite esa
evidencia, la referencia.

---

## 1. Executive Summary

SINTEL ERP corre sobre PostgreSQL 16 (`postgres:16-alpine`) con
`django-tenants` (schema-per-tenant real, ya auditado en `TEN-01`) y un
AI Engine (`apps/services/ai/`) con 4 fases `VERIFIED`/`PARCIAL`
(contexto, EKG parcial, 12 tools READ/SUGGEST, Form Assistant parcial) y
**cero** infraestructura vectorial hoy: `pgvector` no está declarado,
instalado, habilitado ni usado en ningún punto del repositorio
(`AI_VECTOR_POC_AUDIT.md` FASE 0).

La arquitectura del propio AI Engine ya advierte explícitamente, en su
propia documentación, contra introducir "un mecanismo de embeddings/
vector search nuevo sin necesidad demostrada" — no hay hoy ningún flujo
de conversación libre en producción que lo requiera (Form Assistant sigue
sin frontend). Esta auditoría no encontró esa necesidad demostrada, pero
tampoco encontró ninguna razón técnica para descartar pgvector si esa
necesidad llega a existir — la recomendación es **preparar el terreno
(POC controlado, un tenant) sin comprometerse a un rollout general**.

**Veredicto**: `POC_GO_WITH_BLOCKERS`. La arquitectura propuesta
(pgvector + tabla vectorial por schema de tenant, Opción B de
`AI_VECTOR_POC_AUDIT.md` FASE 4) encaja sin fricción en lo que ya existe.
2 bloqueadores concretos (imagen sin pgvector, mecanismo de
`CREATE EXTENSION` no probado en `migrate_schemas`) tienen rutas de
resolución de bajo riesgo y deben cerrarse en AI-VECTOR-01/02 antes de
cualquier código de POC real. Un tercer bloqueador candidato (permisos
del rol de conexión) **ya se verificó y descartó** en esta misma
auditoría con una query real de solo lectura contra el Postgres en
ejecución: el rol `sintel` es `rolsuper=true`.

---

## 2. Estado actual

- PostgreSQL 16 (`postgres:16-alpine`), sin pgvector.
- django-tenants 3.9.x, aislamiento real por schema, middleware maduro.
- AI Engine: `AIContext`/`build_context` (AI-01 VERIFIED), 19 tools
  registradas, `AIEngine.run_tool()` como único punto de entrada, EKG vía
  snapshots offline (no Neo4j en tiempo de consulta), Form Assistant con
  endpoint HTTP real pero sin frontend.
- `apps/services/ai/` es una **capa de servicio, no una app Django** —
  sin `models.py`, sin migraciones propias.
- Celery + Redis ya operativos, con 2 pipelines reales (`maildigester`,
  `document_ingest`) que ya resuelven multi-tenancy async vía
  `schema_context()`.
- Búsqueda existente en el repo: OpenSearch, pero **solo** para el
  catálogo público DIAN (`apps/public/impuestos/`, schema `public`,
  keyword search) — no hay precedente de búsqueda semántica tenant-scoped.

Detalle completo con evidencia: `AI_VECTOR_POC_AUDIT.md` FASE 0-1, 5.

---

## 3. Evidencia encontrada

Ver `AI_VECTOR_POC_AUDIT.md` completo. Resumen de los hallazgos con mayor
peso en las decisiones de este plan:

- `PGVECTOR_PRESENT/INSTALLED/ENABLED/USED` = **false** en las 4
  dimensiones (HECHO, `git grep` exhaustivo).
- `apps/services/ai/` no puede hoy alojar modelos Django — cualquier
  tabla vectorial necesita una app `TENANT_APPS` nueva o existente
  (HECHO + BLOQUEADOR de diseño, resuelto en §7 abajo).
- `backup_tenant`/`restore_tenant` ya son schema-scoped — compatibles con
  Opción B sin cambios, siempre que la extensión exista en el destino
  (HECHO + riesgo documentado).
- El propio `AI_CONTEXT_MODEL.md` documenta explícitamente que no debe
  introducirse vector search "sin necesidad demostrada" (HECHO, cita
  textual en la auditoría FASE 6).
- `ToolRisk.SENSITIVE_READ` es solo metadata hoy, sin enforcement
  automático — un futuro `RetrievalTool` no hereda protección automática
  de campos sensibles, debe implementarla explícitamente (HECHO,
  `AI_SECURITY_MODEL.md`).

---

## 4. Compatibilidad PostgreSQL 16

`COMPATIBLE PERO REQUIERE CAMBIO`. pgvector soporta PostgreSQL 13+
(INFERENCIA, documentación pública del proyecto, no verificada
ejecutando nada en este entorno). La imagen `postgres:16-alpine` actual
no lo incluye. Dos rutas viables, ninguna probada:
1. Compilar pgvector dentro de la imagen Alpine actual (mismo patrón ya
   usado en `Dockerfile` para `postgresql-client-16` vía PGDG).
2. Migrar el servicio `db` a `pgvector/pgvector:pg16` (Debian, imagen
   oficial del proyecto pgvector).

Detalle y trade-offs: `AI_VECTOR_POC_AUDIT.md` FASE 2.

## 5. Compatibilidad Django

`psycopg[binary]>=3.1,<4.0` ya en uso — `pgvector-python` soporta
psycopg3 nativamente y expone `pgvector.django.VectorField`. Ningún
cambio a `DATABASES`/`DATABASE_ROUTERS` necesario. Requiere añadir
`pgvector-python` a `requirements.txt` (dependencia nueva, pineada igual
que el resto). No verificado ejecutando código real en este entorno.

## 6. Compatibilidad django-tenants

Sin conflicto conocido: `django-tenants` gestiona `search_path`/routing
de conexión, no el tipo de columna. El único punto real de fricción es
que `CREATE EXTENSION` es a nivel de base de datos (una sola vez), no de
schema — mecanismo a construir en AI-VECTOR-02 (§18/24, `AI-VECTOR-02`),
no algo que django-tenants resuelva automáticamente. Detalle:
`AI_VECTOR_POC_AUDIT.md` FASE 1, FASE 3.

---

## 7. Arquitectura propuesta

```
PostgreSQL 16
   + extensión vector (CREATE EXTENSION, una vez, a nivel de base de datos)
   ↓
apps/tenant/ai_knowledge/          <- NUEVA app TENANT_APPS (propuesta, no creada aun)
   models.py        AIKnowledgeDocument, AIKnowledgeChunk (SintelTenantBaseModel)
   services/
     crud_service.py       persistencia (@transaction.atomic)
     chunking_service.py    parte texto de origen en chunks, EXCLUYE campos FORBIDDEN/MASKED
     embedding_service.py    llama al AIEmbeddingProvider, escribe embedding_model/version
     retrieval_service.py     tenant-scoped vector search + filtros sede/area
   tasks.py            Celery, schema_context(), idempotente por source_version
   ↓
apps/services/ai/tools/retrieval_tools.py   <- RetrievalTool delgado (mismo patron que ai_project_map)
   ↓
AIEngine.run_tool()   <- MISMO punto de entrada, sin cambios estructurales
```

Por qué esta forma y no otra: es la única de las 4 opciones evaluadas en
`AI_VECTOR_POC_AUDIT.md` FASE 4 que no introduce un segundo mecanismo de
aislamiento multi-tenant en paralelo al ya auditado (schema real de
Postgres), y sigue exactamente el patrón FSD (`services/crud_service.py`
+ `business_service.py`/`selectors.py`) que usan las 17 apps
`TENANT_APPS` existentes — cero abstracciones nuevas inventadas.

`apps/services/ai/` permanece **sin modelos**, consistente con su
diseño documentado ("capa de servicio, no una app de negocio") — la app
nueva (`apps/tenant/ai_knowledge/` o el nombre que se decida en
AI-VECTOR-03) es quien posee los datos, igual que `contabilidad`,
`facturas`, etc. poseen los suyos.

## 8. Modelo vectorial

Ver `AI_VECTOR_POC_AUDIT.md` FASE 7 para el diseño de campos completo y
su justificación (`AIKnowledgeDocument`/`AIKnowledgeChunk`, trazabilidad
`vector -> chunk -> source -> modelo original`). No repetido aquí.

## 9. Tenant isolation strategy

**Opción B**: una tabla por schema de tenant, vía `TENANT_APPS` +
`migrate_schemas --tenant` (mecanismo ya existente, cero código nuevo de
provisioning). Rechaza explícitamente Opción A (`public.ai_chunks` +
`tenant_id`) por debilitar el modelo de aislamiento ya auditado
(`TEN-01`) y ser incompatible con `backup_tenant`/`restore_tenant`
schema-scoped. Matriz completa de comparación: `AI_VECTOR_POC_AUDIT.md`
FASE 4.

## 10. Security model

Reutilizar `AIContext` tal cual (empresa_id/schema_name ya garantizan
tenant; sede_ids/area_ids ya garantizan alcance organizacional, mismo
patrón NULL-safe que `consultar_compra`/`consultar_cotizacion`). No se
crea un segundo RBAC. La responsabilidad nueva y real es del
`ChunkingService`: nunca indexar texto proveniente de campos
`FORBIDDEN`/`MASKED` según `AI_SECURITY_MODEL.md` (salarios, saldos
bancarios, `eps`/`afp`/`arl`, `notas_conciliacion`, etc.) — esto se
decide en el momento de construir el chunk, no en el momento de la
consulta. Detalle: `AI_VECTOR_POC_AUDIT.md` FASE 10.

**Respuesta obligatoria confirmada por diseño**: un usuario no puede
obtener por similitud semántica información de otro tenant — el
aislamiento de schema real de Postgres lo impide estructuralmente con la
Opción B, igual que ya impide cualquier otra fuga cross-schema en el
resto del ERP.

## 11. Embedding strategy

Sin proveedor seleccionado (mandato: no elegir arbitrariamente). Hallazgo
crítico: el `AIProvider` actual solo expone `complete()`, no `embed()` —
Anthropic no ofrece embeddings nativos — se necesita un contrato nuevo
(`AIEmbeddingProvider`, mismo patrón ABC que `AIProvider`) y una
implementación real a decidir en AI-VECTOR-04 con los ejes: compatibilidad
con español, coste, latencia (solo relevante si no es 100% async), y
riesgo de lock-in. Detalle: `AI_VECTOR_POC_AUDIT.md` FASE 8.

## 12. Retrieval strategy

`RetrievalService` tenant-scoped, invocado únicamente cuando la pregunta
del usuario no mapea a una tool determinística existente (el EKG
`ai_project_map` ya resuelve "quién es dueño de qué" sin vectores).
Cualquier dato transaccional exacto (montos, saldos, estados) sigue
viniendo de la tool estructurada correspondiente, nunca del texto
recuperado por similitud — el vector solo aporta **candidatos de
contexto**, no la fuente de verdad del dato. Diagrama completo:
`AI_VECTOR_POC_AUDIT.md` FASE 6.

## 13. Index strategy

Empezar **sin índice ANN** (exact search, `ORDER BY embedding <=> query`)
para el dataset pequeño del POC de un tenant — añadir HNSW solo si el
benchmark (§16) muestra que la latencia exacta ya es un problema medido,
nunca "porque es más rápido" sin medir primero (mandato explícito). Con
Opción B, el filtro de tenant ya no requiere índice compuesto especial —
solo quedan filtros normales de sede/área/document_type. Detalle:
`AI_VECTOR_POC_AUDIT.md` FASE 9.

## 14. Celery strategy

Reutilizar el patrón ya maduro y probado en producción
(`maildigester`/`document_ingest`): `schema_context()` explícito,
idempotencia vía `source_version` (equivalente al CUFE de facturas),
`autoretry_for` acotado a errores transitorios de red (nunca errores de
programación), clasificación de excepciones
(`transient`/`security`/`programming`/`domain`/`validation`), cola
`default` (nunca `high_priority`, reservada para onboarding/facturas
críticas). Cero mecanismo nuevo inventado. Detalle:
`AI_VECTOR_POC_AUDIT.md` FASE 16.

## 15. Backup/restore

`backup_tenant`/`restore_tenant` ya incluyen la tabla vectorial "gratis"
(schema-scoped) — la única precondición nueva es que `CREATE EXTENSION
vector` ya exista en el Postgres **destino** antes de cualquier restore,
paso manual a documentar en el runbook (no automatizado hoy). Riesgo bajo
para el POC (mismo servidor origen/destino), alto si se restaura a un
servidor nuevo sin ese paso — a resolver antes de ir más allá del POC de
un tenant. Detalle: `AI_VECTOR_POC_AUDIT.md` FASE 14.

## 16. Performance benchmark

**Baseline** (sin vector, camino actual): T-query (tiempo de la tool
determinística existente, ej. `buscar_cliente`), T-context (tiempo de
`build_context`), T-total, número de queries a la DB, tokens (si aplica
LLM), memoria, CPU.

**POC** (con vector): exactamente las mismas métricas, más T-retrieval
(tiempo del `RetrievalService`) y T-embedding (tiempo de embeber la
consulta del usuario, si se hace on-the-fly).

**Criterios de aceptación propuestos** (a validar con el usuario antes de
ejecutar el POC, no valores inventados sin revisión):
- `no tenant leaks = 0` — no negociable, ya garantizado estructuralmente
  por Opción B, pero debe probarse con un test explícito (2 tenants
  reales, igual que `test_build_context_usuario_a_tenant_a_difiere_de_usuario_b_tenant_b`
  ya prueba para `AIContext`).
- `ERP regression = 0` — medido comparando latencia de queries
  transaccionales normales antes/después de que exista el índice
  vectorial en el mismo Postgres.
- `retrieval relevance` y `latency improvement`: **no se proponen cifras
  arbitrarias en este documento** — deben fijarse en AI-VECTOR-09 una vez
  exista el dataset real del POC (mandato: "no inventar X arbitrariamente").

**[AI-VECTOR-09, 2026-09-03 — MEDIDO sobre `aipoc`, 24 docs/24 chunks]**
Ver `AI_VECTOR_POC_EXECUTION.md` §AI-VECTOR-09 para el detalle. Valores del
gate fijados con evidencia (no umbrales inventados):
`TOKEN_REDUCTION = 0.775` (baseline "mandar todo" ~1003 tok → vector top-k
~225 tok); `QUERY_REDUCTION = 0.50`; `RELEVANCE` top-1 coseno medio 0.595,
precision@1 = 0.625 (match exacto de keyword, cota inferior);
`LATENCY_GAIN = -24.7` (NEGATIVO a escala de POC: el `embed_query` local
~41 ms supera el fetch ~3.4 ms — honesto, sin proyeccion);
`MEMORY_IMPACT` ~357 MB (modelo ONNX; tablas 608 KB);
**ERP regression = 0** (lecturas transaccionales sub-4 ms, busqueda
vectorial 0.5 ms sin indice ANN).

## 17. POC scope

Un único tenant (a seleccionar por el usuario — no una elección técnica
de esta auditoría). Dataset pequeño pero representativo: **2 campos de
texto libre reales y no sensibles ya confirmados en el modelo** (HECHO,
verificado leyendo código):

- `Cliente.observaciones` (`apps/tenant/clientes/models.py:49`,
  `TextField(blank=True)`, "Observaciones adicionales").
- `Producto.descripcion` (`apps/tenant/inventario/models.py:164`,
  `TextField(blank=True, null=True)`).

Cualquiera de los dos (o ambos) es un candidato razonable para el
dataset del POC — texto libre real, generado por operación normal del
ERP, sin tocar nómina/bancos/contabilidad/fiscal. La selección final
(cuál de los dos, o ambos, y sobre qué tenant) sigue siendo decisión del
usuario, no de esta auditoría — este documento solo reduce el universo de
opciones a candidatas ya verificadas en código real. Explícitamente fuera
de alcance del POC: cualquier campo `FORBIDDEN`/`MASKED` de
`AI_SECURITY_MODEL.md` — evita mezclar la validación técnica del POC con
la complejidad de seguridad de datos sensibles.

## 18. Migration strategy

1. Migración `RunSQL` en una app `SHARED_APPS` (`CREATE EXTENSION IF NOT
   EXISTS vector;`), aplicada vía `migrate_schemas --shared` — una sola
   vez, antes de cualquier `--tenant`.
2. Migración normal de Django en la nueva app `TENANT_APPS`
   (`AIKnowledgeDocument`/`AIKnowledgeChunk`), aplicada vía
   `migrate_schemas --tenant` — igual que cualquier otro modelo.
3. Verificar con `SELECT * FROM pg_extension WHERE extname='vector'`
   (lectura, permitido por el mandato de esta misión) que la extensión
   quedó realmente activa antes de aplicar el paso 2 en cualquier
   ambiente.

Ninguno de estos 3 pasos fue ejecutado en esta misión (prohibido por
mandato) — quedan como el contenido exacto de AI-VECTOR-02.

## 19. Rollback strategy

- Extensión: `DROP EXTENSION IF EXISTS vector;` (falla si hay columnas
  `vector` dependientes — por eso el orden de rollback es primero
  `migrate_schemas --tenant` hacia atrás en la app nueva, luego
  `--shared` hacia atrás).
- App nueva: `migrate_schemas --tenant --schema=<x>` con el número de
  migración anterior (mecanismo estándar de Django, sin nada especial).
- Dato: mientras el POC sea de un único tenant, un `restore_tenant` desde
  el backup pre-POC de ese schema es suficiente para revertir
  completamente sin afectar a ningún otro tenant (consecuencia directa de
  Opción B).

## 20. Risk matrix

Ver `AI_VECTOR_POC_AUDIT.md` FASE 18 (matriz completa, 12 riesgos
evaluados). Ningún riesgo P0 sin mitigación conocida.

## 21. Acceptance criteria

`READY_TO_IMPLEMENT` requiere, antes de iniciar AI-VECTOR-01:
- [x] Confirmar con el usuario el tenant seleccionado para el POC —
      **2026-09-03: crear tenant dedicado `aipoc`** (ningún tenant real
      tiene dataset representativo). Se materializa en AI-VECTOR-03/08.
- [x] Confirmar con el usuario cuál de los 2 campos candidatos reales
      (§17: `Cliente.observaciones` / `Producto.descripcion`) usar como
      dataset — **2026-09-03: ambos, con texto sintético no sensible
      sembrado en el tenant `aipoc`**.
- [x] Validar en un build real que pgvector se instala sobre PostgreSQL 16
      **— 2026-09-03: el usuario eligió cambiar de imagen a
      `pgvector/pgvector:pg16` (opción B); verificado end-to-end en
      AI-VECTOR-01, ver `AI_VECTOR_POC_EXECUTION.md`**.
- [x] **Verificar privilegios reales del rol `DATABASE_USER` para
      `CREATE EXTENSION`** — hecho en la auditoría: `sintel` es
      `rolsuper=true`. Ver `AI_VECTOR_POC_AUDIT.md` FASE 0.
- [x] Decidir nombre y ubicación exacta de la nueva app `TENANT_APPS` —
      **2026-09-03: `apps/tenant/ai_knowledge/`** (propuesta del plan
      aceptada; estructura definitiva se fija en AI-VECTOR-03).
- [ ] Decidir proveedor de embeddings (§11) — **diferido a AI-VECTOR-04
      por decisión del usuario** (no se elige antes de llegar a la capa
      de embeddings).

5 de los 6 ítems cerrados (2026-09-03). El único pendiente (proveedor de
embeddings) se decide dentro de AI-VECTOR-04, no antes. Por eso el veredicto de `POC_STATUS` (§23)
sigue siendo `READY_WITH_CONDITIONS`, no `READY_TO_IMPLEMENT`: las
condiciones restantes son decisiones que le corresponden al usuario
(tenant, dataset, proveedor, nombre de app) o requieren un build real
(fuera del alcance de "solo lectura" de esta misión de auditoría) — no
son brechas de investigación que esta auditoría pueda seguir cerrando
por su cuenta sin salirse de su propio mandato.

## 22. Fases posteriores

```
AI-VECTOR-01   Preparacion PostgreSQL/pgvector
               -> build real que instale/verifique pgvector sobre 16-alpine
                  (o decision de cambiar de imagen); verificar privilegios de rol.

AI-VECTOR-02   Extension + migraciones
               -> migracion SHARED_APPS (CREATE EXTENSION), verificada;
                  runbook de provisioning actualizado con la precondicion.

AI-VECTOR-03   Modelo Vector Store
               -> nueva app TENANT_APPS (nombre a confirmar), models.py,
                  crud_service.py, seleccion real del dataset del POC (S17).

AI-VECTOR-04   Embedding Provider
               -> contrato AIEmbeddingProvider + primera implementacion real,
                  proveedor decidido con el usuario (S11).

AI-VECTOR-05   Retrieval Layer
               -> retrieval_service.py, sin indice ANN inicialmente (S13).

AI-VECTOR-06   Tenant Security
               -> ChunkingService con exclusion real de campos FORBIDDEN/MASKED;
                  test explicito de no-fuga cross-tenant (2 tenants reales).

AI-VECTOR-07   AI Engine Integration
               -> RetrievalTool delgado en apps/services/ai/tools/,
                  registrado en AIToolRegistry, sin tocar AIEngine.run_tool().

AI-VECTOR-08   POC unico tenant
               -> indexacion real del dataset elegido, consultas reales.

AI-VECTOR-09   Benchmark
               -> metricas de S16 medidas con datos reales, criterios de
                  aceptacion numericos fijados con el usuario (no antes).

AI-VECTOR-10   Release Gate
               -> declarar AUDIT_STATUS/POC_STATUS finales con evidencia
                  real de ejecucion, no con diseno.
```

Esta secuencia reemplaza cualquier nombre genérico anterior — es la
estructura que esta auditoría demuestra necesaria, no una plantilla fija.

## 23. Release Gate

```
AUDIT_STATUS = PASS_WITH_BLOCKERS
```
`PASS`, no `BLOQUEADO`, porque ningún hallazgo impide seguir avanzando en
diseño/decisión; `WITH_BLOCKERS` porque 3 verificaciones reales (§21)
siguen pendientes de ejecutarse, no de decidirse.

```
POC_STATUS = READY_WITH_CONDITIONS
```
Condiciones exactas: los 6 ítems de §21 (Acceptance criteria). Ninguno
requiere una nueva auditoría — todos son verificaciones puntuales o
decisiones del usuario, ejecutables en AI-VECTOR-01/03/04.

---

## Gobernanza (verificado antes del cierre de esta misión)

- [x] No se creó una nueva business app (solo diseñada, en `apps/tenant/ai_knowledge/` propuesto, no escrito a disco).
- [x] No se creó un RBAC nuevo (§10 reutiliza `AIContext` tal cual).
- [x] No se duplicó el EKG (§6/12 usan `ai_project_map` como está, no se reimplementa).
- [x] No se duplicó `AIContext` (§10, mismo objeto, mismo `build_context`).
- [x] No se duplicó el Service Layer (§7 sigue el patrón FSD existente, no uno nuevo).
- [x] No se modificó `TenantMiddleware`.
- [x] No se modificaron modelos ERP.
- [x] No se habilitó WRITE (esta misión no toca `AI_WRITE_ENABLED` ni ningún flag).
- [x] No se introdujo otra base de datos vectorial (Opción D descartada explícitamente, FASE 4 de la auditoría).
- [x] No se modificó la fuente de verdad transaccional (cero migraciones, cero código de producción tocado).

**Único archivo modificado por error humano previo a esta misión**:
`notas.txt` (una línea sobre el archivo `hosts`, ajena a esta misión, ya
presente en el working tree antes de iniciar esta auditoría — no tocado
por este trabajo).
