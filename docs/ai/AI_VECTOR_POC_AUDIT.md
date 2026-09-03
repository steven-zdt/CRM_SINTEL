# AI_VECTOR_POC_AUDIT — AI-VECTOR-00

Auditoría exhaustiva, **solo lectura**, del repositorio real de SINTEL ERP
para determinar si un POC de PostgreSQL 16 + pgvector + Vector/Retrieval
Layer (multi-tenant, integrado en `apps/services/ai/`) es viable. Ningún
archivo de producción fue modificado durante esta misión. Solo se crean
`docs/ai/AI_VECTOR_POC_AUDIT.md` (este documento) y
`docs/ai/AI_VECTOR_POC_MASTER_PLAN.md`.

> **Implementación en curso (2026-09-03+):** la bitácora fase por fase del
> LOOP de implementación real vive en `AI_VECTOR_POC_EXECUTION.md`.
> AI-VECTOR-01 (`vector` disponible en el contenedor) = **PASS**.

Cada afirmación está etiquetada:
- **HECHO** — verificado leyendo código/config real de este repositorio.
- **INFERENCIA** — deducido de HECHOs + conocimiento general de PostgreSQL/
  pgvector/Django, no verificado ejecutando nada en este entorno.
- **PROPUESTA** — diseño recomendado por esta auditoría, no implementado.
- **BLOQUEADOR** — impide `POC_GO` sin antes resolverse o mitigarse.

---

## FASE 0 — Control de alcance y estado base

| Variable | Valor | Clasificación |
|---|---|---|
| `POSTGRES_SERVER_VERSION` | `16` (imagen `postgres:16-alpine`) | HECHO — [docker-compose.yaml:26](../../docker-compose.yaml) |
| `POSTGRES_IMAGE` | `postgres:16-alpine` (Alpine, no Debian) | HECHO |
| `POSTGRES_CLIENT_VERSION` | `16` (`postgresql-client-16` instalado explícitamente desde el repo PGDG en el `Dockerfile`, pineado a propósito para que coincida con el servidor v16 — un incidente real de BAK-02 con `pg_restore` v17 forzó este pin) | HECHO — [Dockerfile:19-43](../../Dockerfile) |
| `POSTGRES_VOLUME` | `crm_sintel_postgres_data` (named volume, persiste entre `docker compose down`, se borra solo con `make down-full`) | HECHO — [docker-compose.yaml:194-197](../../docker-compose.yaml) |
| `PGVECTOR_PRESENT` (declarado en dependencias) | **false** — cero menciones de `pgvector`/`vector` en `requirements.txt`, `Dockerfile`, `docker-compose*.yaml` | HECHO — `git grep -i "pgvector"` sobre todo el repo → 0 resultados |
| `PGVECTOR_INSTALLED` (extensión disponible en el binario de Postgres) | **false** — `postgres:16-alpine` oficial no empaqueta `pgvector`; ningún paso de build lo instala | HECHO (imagen) + INFERENCIA (pgvector no viene en la imagen oficial `postgres:*-alpine` de Docker Hub) |
| `PGVECTOR_ENABLED` (`CREATE EXTENSION vector`) | **false** — ninguna migración, script o comando ejecuta `CREATE EXTENSION` | HECHO — sin resultados para `CREATE EXTENSION` en todo el repo |
| `PGVECTOR_USED` (código que importa/usa tipos vector) | **false** | HECHO — sin resultados para `pgvector`/`VectorField`/`vector(` en `.py` |

**Backups/restore de la base**: ya existe un runbook real y probado
(`docs/production/BACKUP_RESTORE_RUNBOOK.md`), con comandos operativos
`make backup-tenant SCHEMA=...` / `make restore-tenant FILE=...`
(`manage.py backup_tenant` / `restore_tenant`, vía `pg_dump`/`pg_restore`
**por schema**, no por base completa). Un drill real de restore (BAK-02) ya
encontró y resolvió una incompatibilidad real de versión cliente/servidor.
HECHO.

**Configuración de test**: `pytest`/`pytest-django` locales (no Docker,
ver `feedback_no_docker_for_tests` en memoria de proyecto), mismo Postgres
16 que dev (no hay un Postgres de test separado con otra versión). HECHO.

**Configuración de producción**: `docker-compose.prod.yaml` es solo un
override (`gunicorn` en vez de `runserver`, sin bind-mount de código, sin
puertos publicados de `db`/`redis`/`neo4j`) — **no cambia la imagen del
servicio `db`**, sigue siendo `postgres:16-alpine` (hereda del
`docker-compose.yaml` base vía `-f docker-compose.yaml -f
docker-compose.prod.yaml`). No hay ninguna consideración de producción
distinta a la de desarrollo respecto a Postgres/pgvector. HECHO —
[docker-compose.prod.yaml:12-16](../../docker-compose.prod.yaml).

**Verificación real contra el Postgres en ejecución (2026-09-03, lectura
únicamente, permitida por §26 del mandato — `docker compose ps` confirma
`crm_sintel-db-1` corriendo, healthy):**

```sql
-- SELECT name, default_version, comment FROM pg_available_extensions WHERE name ILIKE '%vector%';
 name | default_version | comment
------+------------------+---------
(0 rows)

-- SELECT rolname, rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname = current_user;
 rolname | rolsuper | rolcreatedb | rolcreaterole
---------+----------+-------------+---------------
 sintel  | t        | t           | t

-- SELECT current_user, version();
 sintel | PostgreSQL 16.14 on x86_64-pc-linux-musl, compiled by gcc (Alpine 15.2.0) 15.2.0, 64-bit

-- SELECT extname FROM pg_extension;
 plpgsql
 uuid-ossp
```

Esto confirma con evidencia real (no inferencia) dos cosas:
1. **`pgvector` no está disponible como extensión instalable hoy** en el
   Postgres real de este entorno (`pg_available_extensions` la listaría
   si el archivo `.control` existiera en el filesystem del contenedor —
   no existe). `PGVECTOR_INSTALLED = false` queda confirmado como HECHO,
   no como inferencia.
2. **El rol `sintel` SÍ tiene privilegio para crear extensiones**
   (`rolsuper=true`, además `rolcreatedb`/`rolcreaterole=true`) — el
   riesgo de permisos insuficientes para `CREATE EXTENSION vector`
   señalado más abajo (FASE 3) **queda descartado**, no es un
   bloqueador real.

---

## FASE 1 — Django + django-tenants (matriz real)

| Mecanismo | Estado real | Evidencia | Riesgo para pgvector |
|---|---|---|---|
| `TenantMainMiddleware` | Activo, resuelve tenant por `HTTP_HOST` normalizado (`ForceNoPortMiddleware` corre antes) | HECHO — [config/settings.py:198-226](../../config/settings.py) | Ninguno directo — una tabla vectorial en un schema de tenant hereda automáticamente el aislamiento que ya provee este middleware, sin código nuevo |
| `search_path` | Gestionado por `django_tenants.postgresql_backend` (`DATABASES['default']['ENGINE']`) + `DATABASE_ROUTERS = ('django_tenants.routers.TenantSyncRouter',)` | HECHO — [config/settings.py:254-268](../../config/settings.py) | La extensión `vector` se instala **una sola vez a nivel de base de datos** (no por schema — las extensiones de Postgres son globales a la DB, `CREATE EXTENSION` no es schema-scoped salvo que se fije `SCHEMA` explícito). El **tipo** `vector` queda disponible en todos los schemas automáticamente una vez creada la extensión; las **tablas** que lo usan sí son por-schema, igual que cualquier otra tabla tenant |
| Migraciones tenant | `migrate_schemas --tenant` (todas), `migrate_schemas --schema=<x>` (una), ambas con `--fake-initial` disponible para adopción. Comando operativo propio `migrate_tenant_if_needed` (idempotente, usado en post-deploy) | HECHO — [Makefile:39-51](../../Makefile), [migrate_tenant_if_needed.py](../../apps/public/tenants/management/commands/migrate_tenant_if_needed.py) | Una migración que agrega un modelo vectorial se aplicaría igual que cualquier otra migración tenant — **sin mecanismo nuevo** — pero si `CREATE EXTENSION vector` no existe aún en la base, la migración fallaría en el primer tenant que la ejecute (ver FASE 3) |
| Provisioning de tenant nuevo | `make crear-empresa` → `manage.py crear_empresa` (no auditado línea por línea en esta pasada, pero referenciado en `Makefile:74-77` y `AGENTS.md`) | HECHO (comando existe y está documentado como flujo operativo estándar) | Un tenant nuevo correría `migrate_schemas --tenant` (todas las apps, incluida la futura app vectorial) como parte del flujo normal — no hay bifurcación especial hoy para "apps opcionales" |
| Migraciones sobre todos los tenants | `migrate_schemas --tenant` itera todos los `Client` registrados en `public.tenants_client` | HECHO | Mismo mecanismo, sin cambios necesarios |
| Background jobs (Celery) fuera de request HTTP | **Patrón real y maduro**: todo task usa `django_tenants.utils.schema_context(tenant_schema)` explícito antes de tocar el ORM — verificado en 2 pipelines productivos reales (`apps/services/maildigester/tasks.py`, `apps/services/document_ingest/tasks.py`) | HECHO — ver código citado abajo | Generación de embeddings en background (FASE 16) reutilizaría exactamente este patrón, sin inventar uno nuevo |
| `schema_context()`/`tenant_context()` | `schema_context` es el patrón real y ya extendido (107 archivos lo referencian); no se encontró uso real de `tenant_context()` (variante que recibe el objeto `Client`, no el string) en esta pasada | HECHO (schema_context) / **no verificado** (tenant_context) | Ninguno — usar `schema_context(schema_name)` en cualquier tarea de embeddings es el patrón ya validado |
| Mecanismos anti fuga cross-tenant | Aislamiento por **schema real de Postgres** (no `WHERE tenant_id=`), ya verificado en otra misión de esta sesión (`TEN-01`, referenciado en `AI_SECURITY_MODEL.md`); `SintelTenantBaseModel` fuerza FK a `Empresa` + índice en todos los modelos tenant | HECHO | Una tabla vectorial dentro de un schema de tenant hereda la misma garantía estructural — **no requiere un segundo control de aislamiento** si vive como tabla tenant normal (ver FASE 4) |

**Conclusión de FASE 1**: una futura tabla vectorial encaja de forma
natural en el schema del tenant **si y solo si** se modela como una app
`TENANT_APPS` normal, heredando `SintelTenantBaseModel`. INFERENCIA basada
en los HECHOs anteriores.

---

## FASE 2 — PostgreSQL 16 + pgvector, compatibilidad

### Extensión
- `postgres:16-alpine` (Docker Hub oficial) **no** incluye `pgvector`
  preinstalado. **Confirmado con evidencia real** contra el contenedor
  `crm_sintel-db-1` en ejecución: `pg_available_extensions` no lista
  `vector` (0 filas), ver FASE 0. HECHO, ya no inferencia.
- pgvector es compatible con PostgreSQL 13+ según su propia documentación
  pública (`pgvector/pgvector`, licencia PostgreSQL). **No verificado
  ejecutando nada en este entorno** — debe confirmarse en AI-VECTOR-01
  compilando/instalando la extensión contra un Postgres 16 real antes de
  declarar `COMPATIBLE`. INFERENCIA, no HECHO.
- Dos rutas reales para instalarla, ninguna ejecutada en esta auditoría
  (PROPUESTA, evaluar en AI-VECTOR-01):
  1. **Cambiar la imagen base del servicio `db`** a `pgvector/pgvector:pg16`
     (imagen oficial del proyecto pgvector, basada en Debian, no Alpine) —
     cambio de imagen con impacto en el volumen existente si difieren
     versiones de `initdb`/collation (mismo tipo de riesgo que cualquier
     cambio de imagen de Postgres).
  2. **Compilar pgvector dentro de la imagen Alpine actual** añadiendo un
     paso `RUN` al `Dockerfile` (`apk add postgresql16-dev build-base git`
     + `make && make install` sobre el código fuente de pgvector) — mismo
     patrón ya usado en este `Dockerfile` para instalar
     `postgresql-client-16` desde PGDG (capa de build reproducible).
  - Ambas opciones son técnicamente plausibles; ninguna fue probada. La
    opción 2 preserva la imagen Alpine actual (menor blast radius sobre el
    volumen existente) y sigue el patrón ya establecido en este
    `Dockerfile` de compilar/instalar paquetes adicionales sobre la imagen
    base — se recomienda como primera opción a validar en AI-VECTOR-01.
    **BLOQUEADOR hasta que se pruebe con un build real.**

### Compatibilidad Django + django-tenants + pgvector
- `psycopg[binary]>=3.1,<4.0` ya es el adaptador en uso (`requirements.txt:9`).
  El paquete oficial `pgvector-python` soporta psycopg3 nativamente
  (`pgvector.psycopg`) y expone un backend Django (`pgvector.django.VectorField`)
  compatible con Postgres genérico — no hay razón conocida para que
  `django-tenants` (que solo envuelve el backend de conexión, no el ORM de
  campos) sea incompatible con un campo `VectorField` de terceros.
  INFERENCIA razonable, **no probada en este entorno**.
- Ningún paquete `pgvector`/`pgvector-python` está en `requirements.txt`
  hoy — sería una dependencia nueva a añadir y pinear (mismo patrón de
  pineo estricto ya usado en todo `requirements.txt`, ej.
  `pgvector-python>=0.3,<0.4`). PROPUESTA.

**Clasificación**: `COMPATIBLE PERO REQUIERE CAMBIO` (imagen base o build
step + dependencia Python nueva). No es `COMPATIBLE` sin cambios, no es
`NO COMPATIBLE`.

---

## FASE 3 — Migraciones: dónde vive `CREATE EXTENSION vector`

**Hallazgo estructural clave (HECHO):** `apps/services/ai/` **no es una
app de Django instalada** — no aparece en `SHARED_APPS` ni `TENANT_APPS`
([config/settings.py:53-126](../../config/settings.py)), no tiene
`models.py`, no tiene carpeta `migrations/`. Esto es una decisión de
diseño explícita y documentada: *"apps/services/ai/ # capa de servicio,
NO una app de negocio"* ([AI_ENGINE_ARCHITECTURE.md:37](AI_ENGINE_ARCHITECTURE.md)).

Consecuencia directa: **hoy no existe ningún lugar dentro de
`apps/services/ai/` donde una migración Django pueda crear una tabla**,
porque Django solo genera/aplica migraciones para apps registradas en
`INSTALLED_APPS`. Cualquier modelo vectorial requiere:

1. `CREATE EXTENSION IF NOT EXISTS vector;` — operación **a nivel de
   base de datos completa**, no de schema. django-tenants no tiene un
   mecanismo nativo documentado para "ejecutar SQL crudo una sola vez
   antes de todas las migraciones tenant"; el patrón real más cercano en
   este repo es una migración de `SHARED_APPS` con `RunSQL`, ejecutada una
   sola vez contra el schema `public` — pero una extensión creada desde
   `public` es visible desde cualquier schema de la misma base (las
   extensiones son a nivel de base de datos, no de schema, salvo
   `CREATE EXTENSION ... SCHEMA x` explícito, que no aplica aquí porque el
   tipo debe ser visible en todos los schemas de tenant). PROPUESTA a
   verificar en AI-VECTOR-02: una migración `0002_create_vector_extension`
   en una app `SHARED_APPS` existente (o una nueva, mínima) con
   `migrations.RunSQL("CREATE EXTENSION IF NOT EXISTS vector;", reverse_sql="DROP EXTENSION IF EXISTS vector;")`,
   ejecutada por `migrate_schemas --shared` (una sola vez, no por tenant).
2. Las **tablas** (`AIKnowledgeDocument`/`AIKnowledgeChunk`, FASE 7) deben
   vivir en una app `TENANT_APPS` real (nueva o existente) para que
   `migrate_schemas --tenant` las cree en cada schema de tenant — mismo
   mecanismo que cualquier otro modelo del ERP.

**Riesgos concretos identificados** (a mitigar en AI-VECTOR-02, no
resueltos aquí):
- Si la migración de extensión se aplica en `--tenant` en vez de
  `--shared`, se reintentaría N veces (una por tenant) — inofensivo con
  `IF NOT EXISTS` pero señal de diseño incorrecto.
- Provisionar un tenant nuevo **antes** de que la extensión exista en la
  base rompería la migración tenant con la tabla vectorial (ver FASE 15).
- `CREATE EXTENSION` requiere privilegios de superusuario o rol con
  `CREATE` sobre la extensión. **Verificado con una query real** (FASE 0):
  `sintel` es `rolsuper=true` — **puede** ejecutar `CREATE EXTENSION
  vector` sin restricciones de permisos. Ya no es un bloqueador, es un
  HECHO resuelto.

---

## FASE 4 — Diseño de multitenancy vectorial

| Opción | Aislamiento | Rendimiento | Migraciones/provisioning | Backup/restore | Encaja con arquitectura actual |
|---|---|---|---|---|---|
| **A — `public.ai_chunks` + columna `tenant_id`** | Débil por diseño: depende de que **cada query** filtre `WHERE tenant_id=`, sin la garantía estructural de schema real que ya tiene el resto del ERP (`TEN-01`) | Un solo índice HNSW/IVFFlat gigante, compartido entre tenants — contención y ruido cruzado en el índice | Una sola tabla, sin relación con `migrate_schemas --tenant` | Un backup del schema `public` mezclaría todos los tenants — **incompatible** con `backup_tenant`/`restore_tenant` actuales (schema-scoped) | **No** — contradice el modelo de aislamiento por schema que la Fase 1 confirma como el mecanismo real vigente |
| **B — una tabla por schema de tenant (`tenant_x.ai_knowledge_chunk`)** | Igual de fuerte que el resto del ERP — aislamiento de Postgres real, mismo mecanismo ya auditado (`TEN-01`) | Índice HNSW/IVFFlat pequeño y propio por tenant — sin ruido cruzado, escala con el tamaño de cada tenant individual | Se crea automáticamente vía `migrate_schemas --tenant`, exactamente igual que cualquier otro modelo — **cero código nuevo de provisioning** | `backup_tenant`/`restore_tenant` ya son schema-scoped — la tabla se incluye gratis (siempre que la extensión `vector` ya exista en el Postgres destino, ver FASE 14) | **Sí** — es el patrón ya usado por las 17 apps `TENANT_APPS` existentes |
| **C — tabla particionada por tenant** | Fuerte si la partición está bien enforced, pero añade una capa (partition key = tenant) que **no existe hoy en ningún modelo de este ERP** | Potencialmente mejor que A a gran escala, pero pgvector con particionamiento nativo de Postgres tiene soporte limitado/reciente y no fue verificado | Requiere lógica de creación de partición por tenant nueva — no reutiliza `migrate_schemas` | Backup por partición no es lo que `pg_dump --schema=` hace hoy — requeriría tooling nuevo | **No** — introduce un segundo modelo de multi-tenancy (partición) en paralelo al ya existente (schema), duplicando el concepto que Fase 1 confirma como ya resuelto |
| **D — otra alternativa (vector DB externo)** | Fuera de alcance salvo evidencia objetiva de que pgvector no basta (Regla del mandato, §2) — no se encontró tal evidencia en esta auditoría | N/A | N/A | N/A | **No** — mandato explícito de la misión: no proponer sustituir Postgres salvo evidencia objetiva, y no se halló ninguna en este repo |

**Recomendación de FASE 4 (PROPUESTA)**: **Opción B** — una tabla por
schema de tenant, como una app `TENANT_APPS` normal. Es la única opción
que no introduce un segundo mecanismo de aislamiento en paralelo al que
ya existe y ya fue auditado (`TEN-01`), y es la que el propio mandato de
esta misión pide privilegiar ("la recomendación debe privilegiar la
arquitectura de schemas existente").

---

## FASE 5 — Auditoría del AI Engine existente

Resumen verificado leyendo `docs/ai/AI_ENGINE_ARCHITECTURE.md`,
`AI_CONTEXT_MODEL.md`, `AI_SECURITY_MODEL.md`, `AI_PROVIDER_MATRIX.md`,
`AI_RELEASE_GATE.md` y la estructura real de `apps/services/ai/`:

- **`AIContext`** (`context/ai_context.py`): dataclass inmutable,
  construido exclusivamente desde `request.user.tenant_profile`. **AI-01
  = VERIFIED.** HECHO.
- **`AIToolRegistry`/`BaseTool`/`ToolKind`/`ToolRisk`** (`tools/base.py`,
  `tools/registry.py`): registro real, 19 tools registradas a la fecha de
  esta auditoría (13 READ/SUGGEST de AI-03 + 6 VALIDATE de AI-04). HECHO.
  **`ToolRisk.SENSITIVE_READ` es solo metadata hoy — no hay enforcement
  automático en `AIEngine.run_tool()`** (confirmado explícitamente en
  `AI_SECURITY_MODEL.md` líneas 96-108) — dato crítico para el diseño de
  seguridad del retrieval vectorial (FASE 10): un futuro `RetrievalTool`
  tendría el mismo nivel de enforcement manual que las tools sensibles
  actuales, no uno automático "gratis".
- **`AIEngine.run_tool()`** (`engine/ai_engine.py`): único punto de
  entrada, 4 verificaciones estructurales en orden (flags → kind →
  `AUTO_APPROVED_KINDS` → `build_context`). HECHO.
- **EKG** (`tools/ekg_tools.py`, `ProjectMapTool`): usa **snapshots JSON
  offline** (`tools/ekg/out/*.json`), no una conexión Neo4j viva en el
  flujo de consulta — Neo4j sí corre como contenedor
  (`crm_sintel-neo4j-1`, `docker-compose.yaml:61-81`) pero solo se usa en
  tiempo de **build** del grafo (`make ekg-build`), no en tiempo de
  consulta de una tool. HECHO. Esto es relevante para FASE 6/9: el EKG ya
  resuelve "qué app es dueña de qué modelo" sin vectores — un futuro
  retrieval semántico no debe duplicar esa función.
- **`ai_project_map`** (AI-02, PARCIAL): responde `owner`/
  `rules_for_app`/`docs_for_app`/`fk_relationships`/`endpoints_for_model`
  desde snapshots — no resuelve cadenas de proceso multi-app
  ("¿qué pasa al facturar una venta?", AI-02.4, no implementado). HECHO.
- **`buscar_cliente`/`buscar_producto`**: tools determinísticas, sin LLM,
  envuelven `Selector`s ya existentes del dominio (`ClienteSelector`,
  etc.) — **no hay generación de texto libre en ningún flujo READ real
  hoy**. HECHO.
- **Tests**: 83/83 pasan en la corrida más reciente registrada
  (`AI_RELEASE_GATE.md:190`). HECHO (según el propio documento, no
  re-ejecutado en esta auditoría — Regla 26 de la misión: no correr la
  suite global).
- **Feature flags**: `AI_ENABLED`, `AI_READ_ENABLED`,
  `AI_VALIDATE_ENABLED`, `AI_SUGGEST_ENABLED`, `AI_WRITE_ENABLED` — todas
  `False` por defecto, leídas de `settings`/env, nunca de `request.data`.
  HECHO — [config/settings.py:966-973](../../config/settings.py).
- **`docs/ai/` (documentación vigente)**: 14 documentos, cada uno
  distingue explícitamente implementado vs. diseñado — **no hay ningún
  documento `docs/ai/AI_VECTOR_*` previo a esta misión** (confirmado en
  la conversación previa a esta auditoría). HECHO.
- **`.agent/` de `apps/services/ai/`**: **no existe** — a diferencia de
  otras apps (`apps/public/tenants/.agent/`), `apps/services/ai/` no
  tiene un audit doc `.agent/` propio. HECHO (glob sin resultados). No es
  bloqueador pero es una brecha documental preexistente, fuera del
  alcance de esta misión corregirla.

**Dónde incorporar `EmbeddingService`/`ChunkingService`/
`VectorRepository`/`RetrievalService` sin duplicar servicios existentes**
(PROPUESTA, ver FASE 7/Plan): siguiendo el mismo patrón FSD que el resto
del ERP (`services/crud_service.py`, `business_service.py`,
`selectors.py`) dentro de la **nueva app tenant** propuesta en FASE 4,
con un delgado `RetrievalTool` en `apps/services/ai/tools/` que la invoque
— exactamente el mismo patrón que `ai_project_map` usa hoy para llamar al
EKG sin que `apps/services/ai/` posea la lógica de negocio del EKG.

---

## FASE 6 — Search / Retrieval architecture (diseño conceptual)

Evidencia real relevante ya existente en el propio AI Engine
(`AI_CONTEXT_MODEL.md:96-111`, cita textual):

> "reutilizando selectors ya existentes de cada dominio (mismo patrón que
> `ClienteSelector` en `buscar_cliente`), **nunca un mecanismo de
> embeddings/vector search nuevo sin necesidad demostrada**."

Esta es la propia arquitectura documentada advirtiendo explícitamente
contra lo que esta misión evalúa, **sin que exista todavía ningún caso de
uso real que lo justifique** (no hay flujo de conversación libre en
producción, AI-06 aún `PARCIAL`, sin frontend). HECHO — dato crítico que
debe pesar en la decisión final (FASE 19).

Diseño conceptual (PROPUESTA, condicionado a que exista una necesidad
real demostrada):

```
Usuario (mensaje libre, AI-06 Form Assistant)
   -> AIContext (empresa_id, schema_name, rol, alcance -- ya existe)
   -> ¿la pregunta mapea a un dominio/tool conocido? (EKG owner ya resuelve esto sin vectores)
        SI -> tool determinística existente (ClienteSelector, etc.) -- camino YA IMPLEMENTADO
        NO -> RetrievalService (candidato a construir)
               -> tenant-scoped vector search (schema del tenant, FASE 4 Opción B)
               -> candidate chunks (con source_type/source_id trazable)
               -> re-validación de permisos con AIContext (mismo objeto, no uno nuevo)
               -> si el chunk resuelve a un dominio con READ Tool existente, preferir esa tool para el dato final (evitar alucinación de datos transaccionales)
               -> LLM (AIProvider.complete) solo para redactar la respuesta, nunca para inventar el dato
```

**Qué NUNCA debe recuperarse por vector** (PROPUESTA, alineado con
`AI_SECURITY_MODEL.md`): cualquier campo `FORBIDDEN`/`MASKED` de la
clasificación existente (salarios, saldos bancarios, `notas_conciliacion`,
`eps`/`afp`/`arl`) — un chunk de texto embebido no tiene el mismo control
de campo-por-campo que ya aplican las tools estructuradas
(`ToolResult.data` con campos omitidos). Indexar texto libre de esos
dominios en un vector store sería un vector de fuga nuevo que el `ToolRisk`
actual no cubre (ver FASE 10).

**Qué debe seguir siendo SQL exacto / EKG, nunca vector**: cualquier
pregunta que ya tiene una tool determinística (montos, saldos, estados,
relaciones FK) — el propio `AI_CONTEXT_MODEL.md` ya lo establece como
principio.

---

## FASE 7 — Modelo vectorial propuesto (diseño, no implementado)

PROPUESTA, siguiendo `SintelTenantBaseModel`
([apps/tenant/core/models.py:38-63](../../apps/tenant/core/models.py)) —
FK obligatoria a `Empresa`, índice por `empresa`:

```python
class AIKnowledgeDocument(SintelTenantBaseModel):
    source_type = models.CharField(max_length=50)   # ej. "factura", "cliente", "manual_interno"
    source_id = models.CharField(max_length=64)      # PK/UUID del registro origen (trazabilidad)
    source_version = models.CharField(max_length=64, blank=True)  # hash/updated_at del origen, para invalidacion
    metadata = models.JSONField(default=dict, blank=True)
    # created_at/updated_at ya vienen de SintelTenantBaseModel

class AIKnowledgeChunk(SintelTenantBaseModel):
    document = models.ForeignKey(AIKnowledgeDocument, on_delete=models.CASCADE, related_name="chunks")
    content = models.TextField()
    embedding = VectorField(dimensions=<N>)   # pgvector.django.VectorField, N segun proveedor (FASE 8)
    embedding_model = models.CharField(max_length=100)
    embedding_version = models.PositiveIntegerField(default=1)
    chunk_index = models.PositiveIntegerField()
```

Cada campo tiene una razón trazable (Regla "no introducir campos sin
justificación"): `source_type`/`source_id`/`source_version` son la cadena
de trazabilidad `vector -> chunk -> source -> modelo original` que la
misión exige explícitamente; `embedding_model`/`embedding_version`
permiten reindexar sin ambigüedad cuando cambie el proveedor (FASE 8);
`metadata` es el único campo "flexible", ya usado como patrón en el resto
del ERP (`ArrayField`/`JSONField` ya presentes en
`apps/tenant/facturas/models.py`, `empleados/models.py`, `perfil/models.py`
— HECHO, no es un patrón nuevo).

**No implementado.** Este bloque es diseño para AI-VECTOR-03, no código
de esta misión.

---

## FASE 8 — Embedding strategy (evaluación, sin selección arbitraria)

**Hallazgo crítico (HECHO):** el `AIProvider` actual
(`apps/services/ai/providers/base.py`) solo expone `complete()`
(generación de texto) — **no expone ni `embed()` ni ningún método de
embeddings**. `AnthropicProvider` es la única implementación real, y la
API de Anthropic (paquete `anthropic>=0.40.0,<1.0` ya usado) **no ofrece
un endpoint de embeddings nativo** — Anthropic recomienda proveedores
externos (ej. Voyage AI) para esa función. Esto significa que el POC
**no puede reutilizar el `AIProvider` existente tal cual** para
embeddings; necesitaría un contrato nuevo (`AIEmbeddingProvider` o
extender `AIProvider`) — decisión de diseño real a tomar en AI-VECTOR-04,
no una elección cosmética. HECHO (lectura de `providers/base.py` +
conocimiento público de la API de Anthropic).

Ejes de evaluación (sin seleccionar proveedor arbitrariamente, según
mandato):

| Eje | Consideración |
|---|---|
| Compatibilidad | El proveedor debe soportar español razonablemente bien (contenido real del ERP: facturas, clientes, descripciones) |
| Coste | Embeddings se cobran por token de entrada, no de salida — el volumen depende de cuántos documentos/chunks se indexen (FASE 12, un único tenant, dataset pequeño) |
| Latencia | Solo relevante en el camino de indexación (async, Celery) si se hace batch; si se hiciera embedding "on-the-fly" de la consulta del usuario, sí es latencia de request |
| Lock-in | Igual que `AIProvider` ya resolvió con una interfaz abstracta, un `AIEmbeddingProvider` debe seguir el mismo contrato para no acoplar `apps/services/ai/` a un SDK concreto |
| Versionado | `embedding_model`/`embedding_version` (FASE 7) son el mecanismo de invalidación cuando cambie el proveedor/modelo |

**No se selecciona proveedor en esta auditoría** (mandato explícito) —
la decisión queda para AI-VECTOR-04 con los criterios de arriba.

---

## FASE 9 — Index strategy

- **HNSW**: mejor recall/latencia en la mayoría de benchmarks públicos de
  pgvector, pero build más lento y más memoria que IVFFlat. INFERENCIA
  (documentación pública de pgvector, no medido en este entorno).
- **IVFFlat**: build más rápido, requiere `lists` bien calibrado y datos
  ya cargados antes de crear el índice (o recall pobre) — peor ajuste
  para un POC iterativo donde el dataset cambia. INFERENCIA.
- **Exact search (sin índice ANN)**: para un **único tenant con dataset
  pequeño y representativo** (mandato explícito de FASE 12/15), un
  `ORDER BY embedding <=> query LIMIT N` sin índice puede ser
  suficientemente rápido y evita la complejidad de calibrar HNSW/IVFFlat
  antes de tener datos reales para medir. PROPUESTA: **empezar sin índice
  ANN en el POC**, añadir HNSW solo si el benchmark (FASE 13) muestra que
  la latencia exacta ya es un problema con el dataset del POC.
- **Filtrado por tenant/empresa/sede/área/document_type/permissions**: con
  la Opción B (FASE 4, tabla por schema), el filtro por tenant/empresa
  **ya no es necesario en la query vectorial** (el schema ya lo garantiza)
  — solo quedan los filtros de sede/área/document_type/permisos, que son
  filtros `WHERE` normales combinables con el operador de distancia de
  pgvector (`WHERE sede_id = X ORDER BY embedding <=> query`), sin
  necesidad de un índice compuesto especial para el POC de un solo
  tenant.

---

## FASE 10 — Seguridad del retrieval

**Pregunta obligatoria: ¿puede un usuario obtener por similitud semántica
información de otro tenant? Respuesta requerida: NO.**

Con la Opción B (FASE 4): la respuesta es estructuralmente **NO** por el
mismo mecanismo ya auditado (`TEN-01`, aislamiento real de schema) — un
query vectorial ejecutado con `schema_context(schema_actual)` físicamente
no puede ver la tabla `ai_knowledge_chunk` de otro schema. Esto es más
fuerte que un `WHERE tenant_id=` (Opción A), que sí podría fugarse por un
bug de filtro olvidado.

**Integración con el `User Access Context` existente (no un segundo
RBAC, mandato explícito)**: reutilizar `AIContext` tal cual —
`empresa_id`/`schema_name` ya resuelven tenant/empresa;
`sede_ids`/`area_ids` ya resuelven sede/área (mismo patrón NULL-safe que
`consultar_compra`/`consultar_cotizacion` usan hoy,
`AI_CONTEXT_MODEL.md:43-77`) — un futuro `RetrievalTool` debe aplicar
`_scope_kwargs()` de la misma forma, no inventar un segundo esquema de
alcance.

**Documentos sensibles (empleados/bancos/contabilidad/fiscal)**: dado que
`ToolRisk` no tiene enforcement automático (FASE 5), la regla real debe
ser **de proceso, no de código heredado**: ningún pipeline de indexación
(`ChunkingService`) debe indexar campos clasificados `FORBIDDEN`/`MASKED`
en `AI_SECURITY_MODEL.md` — esto se aplica en el momento de construir el
chunk (qué texto se manda a embeber), igual que hoy se aplica en el
momento de construir `ToolResult.data`. Es una responsabilidad nueva del
`ChunkingService`, no del motor de retrieval.

---

## FASE 11 — Performance del ERP

### A. Performance AI (a medir en el POC, FASE 13)
Retrieval latency, embedding latency, LLM latency, número de queries a la
DB, tamaño del contexto enviado al LLM, tokens, tiempo total de respuesta
— ninguno medido todavía (no hay POC implementado).

### B. Performance ERP (auditoría de lo ya existente)
**No se hizo una auditoría de N+1/slow queries/`EXPLAIN ANALYZE` del ERP
transaccional en esta pasada** — está fuera del alcance de esta misión
(que es sobre pgvector/AI, no sobre optimización general del ERP) y
requeriría ejecutar queries contra datos reales, lo cual el mandato de
"solo lectura ligera" permite pero no fue priorizado dado el volumen de
las otras 19 fases. **No verificado.**

**No afirmar que pgvector acelera el ERP transaccional** — cumplido: esta
auditoría no hace esa afirmación en ningún punto. Un índice vectorial
adicional en la misma base de datos sí compite por RAM/CPU con las
queries transaccionales normales (mismo servidor Postgres, sin instancia
separada) — riesgo real a monitorear en el POC (ver Matriz de Riesgo,
FASE 18), no cuantificado todavía.

---

## FASE 12-13 — Alcance del POC y benchmark (diseño)

Ver `AI_VECTOR_POC_MASTER_PLAN.md` §17 (POC scope) y §16 (benchmark) —
contenido movido al documento de plan para no duplicar contenido, por
pedido explícito del formato (`ENTREGABLE PRINCIPAL`, mandato §23).

---

## FASE 14 — Backup / Restore

**Ya existe un runbook real** (`docs/production/BACKUP_RESTORE_RUNBOOK.md`,
HECHO): `backup_tenant`/`restore_tenant` operan **por schema**
(`pg_dump --schema=<x>` / `pg_restore --schema=<x>`), no sobre la base
completa. `Client`/`Domain`/`TenantMembership` (schema `public`) **no**
se respaldan por este mecanismo — limitación ya documentada, no
introducida por esta auditoría.

**Impacto de pgvector sobre este runbook (INFERENCIA + riesgo real)**:
1. La extensión `vector` es a nivel de base de datos, no de schema — un
   `pg_restore --schema=tenant_x` de un dump que contiene columnas tipo
   `vector` **fallará** si la base destino no tiene ya
   `CREATE EXTENSION vector` aplicada. Esto es un paso manual/nuevo que
   el runbook actual no contempla — debe documentarse como precondición
   antes de cualquier restore a un servidor nuevo. **BLOQUEADOR para
   producción, no para el POC de un solo tenant** (mismo servidor).
2. Tamaño adicional de backup: embeddings de dimensión N (ej. 1536)
   ocupan `N * 4 bytes` por vector (float4) más overhead — para un
   dataset pequeño de POC (FASE 15, mandato: "no indexar todo el ERP"),
   el impacto es marginal; a escala de producción con miles de documentos
   por tenant, sí sería un incremento medible del tamaño de dump — no
   cuantificado en esta auditoría (no hay datos reales todavía).
3. Reconstrucción de índices (si se usa HNSW/IVFFlat, FASE 9): `pg_restore`
   reconstruye el índice al restaurar — tiempo adicional proporcional al
   tamaño del índice, no medido.

---

## FASE 15 — Impacto sobre nuevos tenants

Con la Opción B (FASE 4): un tenant nuevo (`make crear-empresa`) correría
`migrate_schemas --tenant` como ya hace hoy — la tabla vectorial se
crearía automáticamente, **sin bifurcación especial**, siempre y cuando
la extensión `vector` ya exista a nivel de base de datos (precondición de
FASE 3).

**Qué pasa si**:
- **La extensión no existe**: la migración tenant que crea
  `AIKnowledgeChunk` fallaría con un error de tipo desconocido
  (`type "vector" does not exist`) — rompería el provisioning completo
  del tenant nuevo, no solo la parte de IA. PROPUESTA de mitigación: la
  migración de extensión (FASE 3) debe ser parte de `migrate_schemas
  --shared` y ejecutarse **antes** de cualquier `migrate_schemas
  --tenant`, con un chequeo de precondición documentado en el runbook de
  provisioning.
- **Una migración vectorial falla**: mismo comportamiento que cualquier
  otra migración tenant fallida hoy — `migrate_schemas` se detiene para
  ese tenant, requiere intervención manual (`migrate_tenant_if_needed
  --schema=<x>`). No es un caso especial.
- **Tenant creado mientras pgvector está temporalmente indisponible**: no
  aplica en el modelo propuesto — la extensión vive en la base, no es un
  servicio externo que pueda estar "caído" independientemente de Postgres.
- **Embeddings aún no generados**: comportamiento esperado y normal
  (indexación es asíncrona, FASE 16) — el tenant funciona igual, el
  retrieval simplemente no tiene contenido todavía hasta que corra el
  primer job de indexación.

---

## FASE 16 — Celery / Async (evidencia real, no diseño desde cero)

Dos pipelines Celery reales ya auditados en este repo dan un patrón
maduro y directamente reutilizable:

- **`schema_context(tenant_schema)`** envuelve todo el trabajo de BD
  dentro de la tarea — patrón ya probado en producción
  (`apps/services/maildigester/tasks.py`,
  `apps/services/document_ingest/tasks.py`). HECHO.
- **Idempotencia real, no teórica**: `batch_upload_facturas_task` hace
  una "pre-validación de idempotencia" por CUFE antes de procesar
  completo (`document_ingest/tasks.py:148-163`) — un futuro
  `generate_embeddings_task` debe seguir el mismo principio: usar
  `source_version` (FASE 7) para saltar chunks ya embebidos con la misma
  versión, evitando reembeber sin necesidad. PROPUESTA basada en patrón
  HECHO.
- **`autoretry_for` acotado a errores transitorios** (`ConnectionError`,
  `TimeoutError`, `OSError`) — explícitamente **excluye**
  `AttributeError`/errores de programación del autoretry, para no
  reintentar bugs reales como si fueran fallos de red
  (`maildigester/tasks.py:189-192`, comentario explícito en el código).
  Mismo patrón esperado para llamadas a un proveedor de embeddings
  (fallos de red del proveedor externo → retry; error de programación →
  no retry). HECHO (patrón) + PROPUESTA (aplicación a embeddings).
- **Clasificación de excepciones** (`_clasificar_excepcion`,
  `maildigester/tasks.py:105-124`): `transient`/`security`/`programming`/
  `domain`/`validation`/`unknown`, con logging a nivel `error` para
  `programming`/`security` y `warning` para el resto — patrón reutilizable
  tal cual para la tarea de embeddings.
- **Cola dedicada**: `CELERY_TASK_ROUTES` ya separa `high_priority` de
  `default` (`config/settings.py:871-882`) — una tarea de embeddings NO
  crítica (indexación en background, no bloquea al usuario) debe ir a
  `default`, nunca a `high_priority` (esa cola está reservada hoy para
  onboarding e ingesta de facturas). PROPUESTA.
- **`CELERY_TASK_TIME_LIMIT`/`SOFT_TIME_LIMIT`** ya están en 30/25
  minutos globalmente (`config/settings.py:853-854`) — suficiente para un
  batch de embeddings de un dataset pequeño de POC; a evaluar de nuevo a
  escala de producción (no medido).
- **Dead-letter/failure**: no se encontró un mecanismo explícito de dead
  letter queue en el patrón actual — los fallos quedan registrados vía
  `_update_run(status="FAILED", ...)` (persistencia en BD, consultable),
  no en una cola separada. Mismo patrón esperado para embeddings: un
  modelo de "run" de indexación con estado consultable, no una DLQ nueva.

**Riesgo explícito a evitar (mandato de la misión)**: ninguna
modificación normal de un registro del ERP debe bloquear esperando al
proveedor de embeddings — el patrón Celery ya existente (fire-and-forget
desde la vista/señal de dominio, ejecución async real) ya resuelve esto
si se reutiliza tal cual; el riesgo solo aparece si alguien decide
invocar el embedding de forma síncrona dentro de un request HTTP, lo cual
esta auditoría recomienda prohibir explícitamente en el diseño de
AI-VECTOR-04/05.

---

## FASE 17 — Costo y capacidad (estimación inicial)

| Variable | Nivel estimado | Qué lo dispara |
|---|---|---|
| Almacenamiento adicional | **LOW** para el POC (un tenant, dataset pequeño representativo, mandato explícito) | Crece a **MEDIUM/HIGH** en producción con miles de documentos por tenant × decenas de tenants — no cuantificado (no hay datos reales) |
| RAM (índice HNSW en memoria) | **LOW** en el POC (dataset pequeño, o sin índice ANN según FASE 9) | HNSW completo requiere que el índice quepa en `shared_buffers`/RAM para rendimiento óptimo — a escala, compite con la caché normal de Postgres del ERP transaccional |
| CPU | **LOW** en el POC | El build de índice HNSW es intensivo en CPU una sola vez; en producción, reindexación frecuente (cambios de modelo de embedding) sería el driver de CPU sostenido |
| Coste de proveedor de embeddings | **LOW** en el POC (dataset pequeño) | Volumen de documentos × frecuencia de reembedding en producción — no cuantificable sin elegir proveedor (FASE 8) |
| Coste LLM (generación de respuesta) | Ya existe hoy (Anthropic, Form Assistant) — el retrieval no añade una llamada LLM nueva, solo cambia qué contexto se le pasa | Ninguno nuevo directamente atribuible a pgvector |
| Impacto en PostgreSQL compartido | **MEDIUM** (mismo servidor que el ERP transaccional, sin instancia separada) | Cualquier índice vectorial grande compite por recursos con las queries de negocio — mitigable monitoreando, no cuantificado |

No se estima un número de chunks/documentos porque el mandato de FASE 12
exige seleccionar el dataset del POC **antes** de poder estimar con
evidencia real — cualquier cifra aquí sería inventada.

---

## FASE 18 — Matriz de riesgo

| Riesgo | Probabilidad | Impacto | Mitigación | Bloquea POC |
|---|---|---|---|---|
| Cross-tenant retrieval | Baja (con Opción B, mismo mecanismo que `TEN-01`) | Crítico | Usar tabla por schema (Opción B, FASE 4), nunca `public.ai_chunks + tenant_id` (Opción A) | **Sí, si se elige Opción A** — no bloquea si se sigue la recomendación B |
| `search_path`/schema incorrecto | Baja (patrón `schema_context` ya maduro y probado, FASE 16) | Alto | Reutilizar `schema_context()` tal cual, sin variantes nuevas | No, si se sigue el patrón existente |
| Permisos insuficientes para `CREATE EXTENSION` | **Descartado** — verificado con evidencia real (FASE 0): `sintel` es `rolsuper=true` | N/A | N/A, ya resuelto | No |
| Migraciones (extensión no creada antes que tablas tenant) | Media (mecanismo nuevo, no probado — FASE 3; los permisos del rol ya no son el problema, falta el mecanismo de orquestación en `migrate_schemas`) | Alto (rompe provisioning de tenants nuevos) | Migración de extensión en `SHARED_APPS`, ejecutada antes de cualquier `--tenant`, con chequeo de precondición documentado | **Sí, hasta validarse en AI-VECTOR-02** |
| Imagen base sin pgvector (Alpine) | Alta (confirmado con evidencia real, `pg_available_extensions` vacío, FASE 0/2) | Medio (requiere cambio de Dockerfile/imagen, no de arquitectura) | Compilar pgvector en la imagen Alpine actual o migrar a `pgvector/pgvector:pg16`, validado en un build real | **Sí, hasta validarse en AI-VECTOR-01** |
| Aumento de memoria/CPU en Postgres compartido | Media | Medio (con Opción B y dataset pequeño de POC) | Empezar sin índice ANN (FASE 9), medir antes de optimizar | No para el POC; sí a monitorear en escalado |
| Índices mal calibrados (IVFFlat sin `lists` correcto) | Baja (mitigado evitando IVFFlat en el POC, FASE 9) | Bajo en el POC | Empezar con exact search o HNSW por defecto | No |
| Embeddings obsoletos (contenido cambia, embedding no se regenera) | Media (sin mecanismo construido aún) | Medio | `source_version`/`embedding_version` (FASE 7) + job de reindexación idempotente (FASE 16) | No, es un problema de diseño ya cubierto en el plan, no un bloqueador de arranque |
| Outage del proveedor de embeddings | Baja-Media (depende del proveedor elegido, FASE 8 no decidida) | Bajo (indexación async, no bloquea el ERP si se sigue el patrón Celery de FASE 16) | `autoretry_for` en errores transitorios, cola `default` no crítica | No |
| Backup/restore sin extensión en destino | Media (mecanismo nuevo no documentado, FASE 14) | Alto en producción, bajo en POC (mismo servidor) | Documentar precondición `CREATE EXTENSION` antes de cualquier restore a servidor nuevo | No para el POC de un tenant en el mismo servidor |
| Celery backlog (embeddings) | Baja (cola `default`, no crítica; mismo mecanismo de colas ya en producción) | Bajo | Cola `default`, nunca `high_priority` | No |
| Degradación del ERP transaccional | Media (sin cuantificar, mismo servidor Postgres) | Alto si ocurre | Medir en el benchmark del POC (FASE 13/Plan) antes de cualquier rollout más allá de un tenant | No bloquea el POC; sí bloquearía ir más allá del POC sin medirlo |
| Duplicar el EKG/AIContext/Service Layer | Baja (mandato + gobernanza explícita, FASE 28 del mandato) | Alto si ocurre (violación de arquitectura) | Reutilizar `AIContext`, EKG y selectors existentes tal cual (FASE 5/6/10) | No, si se sigue el diseño propuesto |

---

## FASE 19 — Decisión arquitectónica

```
POC_GO_WITH_BLOCKERS
```

**Justificación**: la arquitectura propuesta (Postgres 16 + pgvector,
tabla vectorial por schema de tenant, integrada como app `TENANT_APPS`
nueva con un `RetrievalTool` delgado en `apps/services/ai/`) es
coherente con todo lo que esta auditoría encontró implementado y
documentado — no requiere alterar `TenantMiddleware`, `search_path`,
Service Layer, EKG ni `AIContext`. No se encontró evidencia de que
pgvector sea insuficiente ni de que se necesite una base de datos
vectorial externa.

Sin embargo, existen **2 bloqueadores reales, no teóricos**, que deben
resolverse en AI-VECTOR-01/02 antes de escribir la primera línea de
código del POC (un tercer bloqueador candidato — permisos del rol de
conexión para `CREATE EXTENSION` — fue verificado con una query real
contra el Postgres en ejecución en esta misma auditoría y **queda
descartado**: `sintel` es `rolsuper=true`, ver FASE 0):

1. La imagen `postgres:16-alpine` actual no incluye `pgvector` —
   confirmado con evidencia real (`pg_available_extensions` vacío para
   `vector`, FASE 0/2) — sin un build real que lo instale y verifique,
   `PGVECTOR_INSTALLED` sigue en `false`.
2. No existe hoy ningún mecanismo verificado para ejecutar
   `CREATE EXTENSION vector` una sola vez a nivel de base de datos dentro
   del flujo de `migrate_schemas` de django-tenants — debe diseñarse y
   probarse, no asumirse (FASE 3).

Ninguno de los 2 es un riesgo P0 sin mitigación conocida — ambos tienen
una ruta de resolución clara y de bajo riesgo (compilar la extensión,
migración `RunSQL` en `SHARED_APPS`). Por eso la decisión es
`POC_GO_WITH_BLOCKERS`, no `POC_NO_GO`.
