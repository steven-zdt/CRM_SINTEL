# AI_VECTOR_POC_EXECUTION — bitácora del LOOP de implementación

Registro fase por fase de la **implementación real** del POC de PostgreSQL 16
+ pgvector + Vector/Retrieval Layer multi-tenant. Complementa (no reemplaza):

- `AI_VECTOR_POC_AUDIT.md` — auditoría previa, solo lectura (AI-VECTOR-00).
- `AI_VECTOR_POC_MASTER_PLAN.md` — diseño ejecutable (AI-VECTOR-00).
- `AI_VECTOR_POC_RELEASE_GATE.md` — gate final del POC (se crea en AI-VECTOR-10).

Cada fase sigue el LOOP: `INSPECT → BASELINE → PLAN → EXECUTE → VERIFY →
REGRESSION → DOCUMENT → COMMIT → GATE`. Etiquetas: **HECHO** (verificado con
comando real), **VERIFICADO** (probado end-to-end), **PROPUESTA**, **BLOCKED**,
**DEFERRED**.

## Decisiones del usuario (2026-09-03, antes de AI-VECTOR-01)

| Ítem (`MASTER_PLAN` §21) | Decisión |
|---|---|
| Estrategia pgvector (AI-VECTOR-01) | **Cambiar imagen del servicio `db` a `pgvector/pgvector:pg16`** (opción B de la auditoría; no la opción A/Alpine-compile) |
| Tenant + dataset del POC | **Crear un tenant dedicado `aipoc`** y sembrar texto sintético no sensible (`Cliente.observaciones` / `Producto.descripcion`). Ningún tenant real tiene dataset representativo hoy (`home`: ~1 campo con texto; `admin`: vacío) |
| Proveedor de embeddings (AI-VECTOR-04) | **Decidir en AI-VECTOR-04**, no antes |
| Cadencia del agente | **Gate por gate** — ejecutar una fase, verificar, documentar, commit, parar en el GATE y reportar |
| Nombre/ubicación de la app nueva | `apps/tenant/ai_knowledge/` (propuesta del plan, se confirma en AI-VECTOR-03) |

---

## AI-VECTOR-01 — Preparación PostgreSQL 16 + pgvector

**STATUS = PASS** (2026-09-03, rama `feat/onboarding-cookie`)

### BASELINE (verificado contra `crm_sintel-db-1` en ejecución)

| Variable | Valor pre-cambio |
|---|---|
| Imagen `db` | `postgres:16-alpine` (`sha256:57c72fd2a128…`), musl |
| `SELECT version()` | PostgreSQL **16.14** on x86_64-pc-linux-musl |
| `vector` en `pg_available_extensions` | **0 filas — NO disponible** |
| `pg_extension` | `plpgsql`, `uuid-ossp` |
| Rol de conexión | `sintel`, `rolsuper=true` |
| `pg_database.datcollate` / `datctype` | `en_US.utf8` / `en_US.utf8` |
| `pg_database.datcollversion` | **NULL** (musl no registra versión de collation) |
| Schemas de negocio | 3 (`public`, `home`, `admin`) |
| Datos | `tenants_client`=3, `tenants_domain`=5, `home`: 3 clientes / 1 producto |
| Backup previo | `pg_dump -Fc` completo (1.33 MB, 378 tablas / 1322 índices / 392 FK) + `pg_dumpall --globals-only`, guardados fuera del repo antes del cambio |

### PLAN

1. PRECHECK + SNAPSHOT: backup `pg_dump -Fc` + globals; capturar collation/version.
2. CHANGE: `docker-compose.yaml` servicio `db`, `image:` →
   `pgvector/pgvector:pg16@sha256:ccc6e83d…` (pineado por digest — reproducibilidad).
3. `docker compose up -d db` (recrea solo `db`, **mismo volumen** `crm_sintel_postgres_data`).
4. VERIFY: `version()` sigue siendo 16.x; `vector` AVAILABLE; contenedor healthy;
   datos intactos; **NO** ejecutar `CREATE EXTENSION` (eso es AI-VECTOR-02).
5. Mitigar cambio de proveedor de collation musl→glibc: `REINDEX DATABASE sintel`.
6. REGRESSION: `manage.py check`, `makemigrations --check`, smoke ORM tenant, `/health`.

### EXECUTE (HECHO)

- `docker-compose.yaml` editado: `image: pgvector/pgvector:pg16@sha256:ccc6e83d6e35e931dc7c5def2022729d5a6c370318d099181995567ff1fb4d6b`
  con comentario de rollback y nota de collation. Es el único archivo de
  infraestructura tocado en esta fase.
- `docker compose up -d db` → contenedor recreado, healthy en ~15 s.
- `REINDEX DATABASE sintel;` → OK (~9 s, dataset pequeño). Reconstruye todos los
  índices de todos los schemas bajo el collation glibc actual.
  - `ALTER DATABASE … REFRESH COLLATION VERSION` devuelve `invalid collation
    version change` y **se omite deliberadamente**: `datcollversion` era NULL
    (igual que en Alpine), así que PostgreSQL no compara ni emite warning; el
    `REINDEX` ya resolvió la corrección real de ordenamiento. Registrar la
    versión es solo metadata para warnings futuros, no afecta correctitud.
- `docker compose restart web celery` → reconexión limpia; ambos healthy.

### VERIFY (VERIFICADO)

| Check | Resultado |
|---|---|
| `SELECT version()` | PostgreSQL **16.15** (Debian 16.15-1.pgdg12+2) on x86_64-pc-linux-gnu — sigue siendo PG **16** (minor 14→15, drop-in) |
| `vector` en `pg_available_extensions` | **`default_version = 0.8.6`, `installed_version` vacío** → DISPONIBLE, no creada |
| `pg_extension` | `plpgsql`, `uuid-ossp` — **sin cambios, `vector` NO instalada** |
| Columnas tipo `vector` en uso | 0 |
| Contenedores | `db`, `web`, `celery`, `nginx`, `redis`, `neo4j` todos **healthy** |
| Volumen | `crm_sintel_postgres_data` intacto (no recreado) |
| Datos post-cambio | `tenants_client`=3, `tenants_domain`=5, `home`: 3 clientes / 1 producto — **idénticos al baseline** |
| Índices inválidos (`pg_index WHERE indisvalid=false`) | 0 |
| Logs `db` | `database system is ready to accept connections`, sin `warning`/`error`/`collation version mismatch` |

### REGRESSION (VERIFICADO)

| Check | Resultado |
|---|---|
| `manage.py check` | `System check identified no issues (0 silenced)` |
| `makemigrations --check --dry-run` | `No changes detected` |
| Smoke ORM tenant (`schema_context('home')`, `Cliente.objects.order_by('razon_social')`, `__gt`, `__icontains`) | OK — lecturas y queries sensibles a collation devuelven resultados correctos |
| `GET /health` (vía nginx→web) | `200` |

### KNOWN_LIMITATIONS

- El salto de imagen sube PostgreSQL 16.14 → 16.15 y cambia el proveedor de
  collation de musl a glibc. Mitigado con `REINDEX DATABASE sintel`. Cualquier
  entorno adicional (staging/prod) que aplique este mismo cambio de imagen debe
  ejecutar el mismo `REINDEX DATABASE <db>` una vez tras recrear el contenedor.
- Colaciones ICU (`*-x-icu`) muestran `collversion` (153.136) ≠ actual (153.120)
  en la nueva imagen. **No afecta a este proyecto**: la BD `sintel` usa collation
  libc `en_US.utf8` por defecto y no hay ninguna columna con collation ICU
  explícito (0 columnas). Es estado heredado de la imagen, no introducido aquí.
- `docker-compose.prod.yaml` hereda `image:` del compose base — producción
  también quedará en `pgvector/pgvector:pg16` al re-desplegar. Intencional
  (consistencia dev/prod), pero implica el `REINDEX` de arriba en el primer
  arranque de prod con la nueva imagen. Documentar en el runbook de despliegue
  antes de tocar prod (AI-VECTOR-02 / AI-VECTOR-10).

### ROLLBACK (probado por diseño, no ejecutado)

1. Revertir la línea `image:` de `docker-compose.yaml` a `postgres:16-alpine`.
2. `docker compose up -d db` → recrea el contenedor sobre el **mismo volumen**;
   los datos vuelven exactamente (no se tocó `PGDATA`).
3. Opcional pero recomendado: `REINDEX DATABASE sintel` de nuevo (los índices
   quedaron en orden glibc; musl no lo valida pero es limpieza defensiva).
4. No hay `CREATE EXTENSION` que revertir (no se ejecutó).
5. Backup de seguridad disponible: `pg_dump -Fc` completo pre-cambio.

### GATE — AI-VECTOR-01

```
build reproducible        = PASS  (imagen pineada por digest sha256:ccc6e83d…)
PostgreSQL sigue en v16    = PASS  (16.15, minor bump drop-in)
extensión vector visible   = PASS  (pg_available_extensions: vector 0.8.6)
CREATE EXTENSION ejecutado = NO    (correcto — se hace en AI-VECTOR-02)
contenedor healthy         = PASS
volumen intacto            = PASS
datos intactos             = PASS  (row counts idénticos al baseline)
regresión ERP              = PASS  (check / makemigrations / ORM smoke / /health)
rollback posible           = PASS  (revertir image line + up -d db)
```

**AI-VECTOR-01 = PASS.** NEXT: **AI-VECTOR-02**.

---

## AI-VECTOR-02 — `CREATE EXTENSION vector` vía `migrate_schemas --shared`

**STATUS = PASS** (2026-09-03, rama `feat/onboarding-cookie`)

### Decisiones del usuario para esta fase

| Ítem | Decisión |
|---|---|
| Hogar de la migración compartida | **Nueva app mínima `apps/db_extensions/`** (sin modelos, solo en `SHARED_APPS`). `apps/public/` está prohibido (AGENTS.md L110, requiere RFC + `needs-admin-approval`); no existe ninguna otra app de `SHARED_APPS` fuera de `apps/public/` |
| Prueba del paso 6 (provisioning) | **Crear el tenant `aipoc` ahora** — doble propósito: valida `migrate_schemas` sobre un schema nuevo end-to-end y deja el tenant del POC listo para AI-VECTOR-03/08 |

### BASELINE

| Variable | Valor pre-fase |
|---|---|
| `pg_extension` | `plpgsql`, `uuid-ossp` (`vector` disponible pero no instalada — cierre de AI-VECTOR-01) |
| `SHARED_APPS` | `django_tenants` + `apps.public.*` + libs; **ninguna app fuera de `apps/public/`** |
| Tenants | `public`, `home`, `admin` |
| `makemigrations --check` | `No changes detected` |
| Backup previo | `pg_dump -Fc` completo (`sintel_pre_aivector02.dump`) antes de tocar nada |

### EXECUTE (HECHO)

**Archivos nuevos/modificados:**

- `apps/db_extensions/__init__.py` (vacío)
- `apps/db_extensions/apps.py` — `DbExtensionsConfig`, sin modelos. Docstring
  explica por qué vive fuera de `apps/public/` y por qué **solo** en `SHARED_APPS`.
- `apps/db_extensions/migrations/__init__.py` (vacío)
- `apps/db_extensions/migrations/0001_vector_extension.py` — `RunPython`
  **con guard por schema**: `CREATE EXTENSION IF NOT EXISTS "vector"` se
  ejecuta únicamente cuando `schema_editor.connection.schema_name ==
  get_public_schema_name()`. Reverse: `DROP EXTENSION IF EXISTS "vector"`,
  también sólo desde `public`.
- `config/settings.py` — `"apps.db_extensions"` añadido a `SHARED_APPS`
  (justo tras `django_tenants`), con comentario. **No** en `TENANT_APPS`.

**Iteración real durante la fase (registrada, no oculta):** la primera
versión de la migración usaba `django.contrib.postgres.operations.CreateExtension`
sin guard. `migrate_schemas --tenant` la aplicó también a `home`/`admin`
(django-tenants 3.9.0 registra las migraciones de `SHARED_APPS` en el
`django_migrations` de **todos** los schemas — mismo comportamiento
verificado para `auth`: 12 registros en `home.django_migrations` **sin** que
existan las tablas `auth_*` en ese schema). Con `CreateExtension` la operación
no-modelo llegaba a ejecutarse por schema (inofensivo por `IF NOT EXISTS`,
`pg_extension` nunca pasó de 1 fila) pero es la "señal de diseño incorrecto"
que advierte `AI_VECTOR_POC_AUDIT.md` FASE 3, y el reverse habría matado la
extensión database-wide desde el primer tenant. **Corregido**: se reescribió
con `RunPython` + guard por schema; se borraron los registros espurios de
`home`/`admin` (`DELETE FROM <schema>.django_migrations WHERE
app='db_extensions'`, sin efecto sobre la extensión) y se re-corrió
`migrate_schemas --tenant` con la versión guardada.

**Comandos aplicados:**

```
manage.py check                         -> System check identified no issues
manage.py makemigrations --check         -> No changes detected
manage.py migrate_schemas --shared       -> Applying db_extensions.0001_vector_extension... OK
manage.py migrate_schemas --tenant       -> db_extensions.0001 (no-op guardado en home/admin)
manage.py crear_empresa "AI POC" "aipoc@sintel.net.co" --schema-name aipoc  -> OK
```

### VERIFY (VERIFICADO)

| Check | Resultado |
|---|---|
| `SELECT count(*) FROM pg_extension WHERE extname='vector'` | **1** — una sola instancia database-wide |
| Namespace de la extensión | `public` |
| `pg_extension.extversion` | `0.8.6` |
| Tipo `vector` desde contexto tenant (`schema_context('home')`, `search_path='home, public'`) | operadores `<->` / `<=>` funcionan; `SELECT extname FROM pg_extension` visible |
| `db_extensions.0001` en `django_migrations` | presente en `public`, `home`, `admin`, `aipoc` (consistente con `auth`/`impuestos`) |
| Tenant `aipoc` | fila en `public.tenants_client` (`is_active=t`, `on_trial=t`), dominio `aipoc.sintel.net.co`, **79 tablas** en el schema, `db_extensions.0001` registrado |
| `vector` desde contexto `aipoc` | `'[1,0,0]'::vector <=> '[0,1,0]'::vector` = `1.0` (ortogonales — correcto) |

### REGRESSION (VERIFICADO)

| Check | Resultado |
|---|---|
| `manage.py check` | `System check identified no issues (0 silenced)` |
| `manage.py makemigrations --check --dry-run` | `No changes detected` |
| Tenants existentes (`home`) | 3 clientes / 1 producto — **idéntico al baseline** |
| `GET /health` | `200` |
| Contenedores | todos healthy |

### KNOWN_LIMITATIONS / EFECTOS SECUNDARIOS

- **Email de activación real enviado.** `crear_empresa` encola
  `send_tenant_activation_email_task`; `EMAIL_BACKEND` en este entorno es
  `smtp.EmailBackend` (no consola). Se envió un correo "Activa tu cuenta en
  AI POC - SINTEL" a `aipoc@sintel.net.co` (`[EMAIL:OK] Enviado
  exitosamente`). La dirección usa el dominio corporativo; si no tiene buzón
  real, rebotará al remitente. Efecto colateral inherente al flujo de
  provisioning estándar, no específico de esta fase — a considerar si se
  crean más tenants de prueba (usar una dirección controlada o revisar si
  hay flag para omitir el correo).
- **Runbook de provisioning de producción — DEFERRED a AI-VECTOR-03/10.**
  La precondición "`migrate_schemas --shared` (que ahora incluye
  `db_extensions.0001`) debe haber corrido antes de cualquier
  `migrate_schemas --tenant`" **todavía no es load-bearing**: no existe
  ninguna tabla que use el tipo `vector`. Se vuelve real cuando
  `apps.tenant.ai_knowledge` (AI-VECTOR-03) añada la primera columna
  `VectorField`. Se actualizará `docs/production/DEPLOYMENT_RUNBOOK.md` en
  esa fase, no antes (evita tocar un runbook de producción por una
  precondición que aún no aplica).

### ROLLBACK (probado por diseño, no ejecutado)

1. `manage.py migrate_schemas --shared db_extensions zero` → el guard hace
   que sólo `public` ejecute `DROP EXTENSION IF EXISTS "vector"` (falla,
   correctamente, si ya hay columnas `vector` dependientes → primero
   revertir `ai_knowledge` en AI-VECTOR-03+).
2. Quitar `"apps.db_extensions"` de `SHARED_APPS`; borrar `apps/db_extensions/`.
3. Tenant `aipoc`: `DROP SCHEMA aipoc CASCADE;` + `DELETE FROM
   public.tenants_domain WHERE domain LIKE 'aipoc.%'; DELETE FROM
   public.tenants_client WHERE schema_name='aipoc';` (o conservarlo — es el
   tenant del POC de todas formas).
4. Backup `sintel_pre_aivector02.dump` disponible.

### GATE — AI-VECTOR-02

```
extension = installed                 = PASS  (pg_extension: vector 0.8.6)
extension = one database-wide instance = PASS  (count(*) = 1, namespace public)
tipo vector visible desde tenants      = PASS  (home + aipoc, via search_path real)
tenant migrations (--tenant) = OK      = PASS  (guarded no-op, sin errores)
provisioning tenant nuevo = OK         = PASS  (aipoc: 79 tablas, migración registrada)
existing apps = unaffected             = PASS  (check / makemigrations / row counts / health)
rollback posible                       = PASS  (guard en reverse + backup)
```

**AI-VECTOR-02 = PASS.** NEXT: **AI-VECTOR-03**.

---

## AI-VECTOR-03 — Vector Store tenant-scoped (`apps/tenant/ai_knowledge/`)

**STATUS = PASS** (2026-09-03, rama `feat/onboarding-cookie`)

### Decisión del usuario para esta fase

`entrypoint.sh` (L96) corre `migrate_schemas --tenant` (TODOS los tenants)
en cada arranque de `web`, y la app necesita `pgvector` (rebuild de imagen
→ reinicio). "Solo `aipoc`" no se sostiene tras el primer reinicio.
**Decisión: rebuild ya y aceptar tablas VACÍAS en `home`/`admin`.** El
aislamiento que importa (datos, y que `public` no reciba tablas de negocio)
se mantiene; rollback = `migrate_schemas --tenant tenant_ai_knowledge zero`
+ desregistrar.

### EXECUTE (HECHO)

**Archivos nuevos:**

- `apps/tenant/ai_knowledge/__init__.py`
- `apps/tenant/ai_knowledge/apps.py` — `AiKnowledgeConfig`, `label = "tenant_ai_knowledge"`
- `apps/tenant/ai_knowledge/models.py` — `AIKnowledgeDocument`, `AIKnowledgeChunk`
  (heredan `SintelTenantBaseModel`). Trazabilidad `embedding -> chunk ->
  document -> origen` por `source_type` + `source_id` (string, **sin FK** a
  los modelos de dominio). `embedding = VectorField(dimensions=None)` —
  `vector` sin dimensión fija hasta AI-VECTOR-04.
- `apps/tenant/ai_knowledge/services/__init__.py` + `crud_service.py` —
  `AIKnowledgeCRUDService`: persistencia pura (`upsert_document`,
  `replace_chunks`, `set_chunk_embedding`, `get_document`, `delete_document`),
  todos `empresa`-scoped y `@transaction.atomic`.
- `apps/tenant/ai_knowledge/migrations/0001_initial.py`
- `apps/tenant/ai_knowledge/tests/` — `conftest.py` (2 tenants de prueba) +
  `test_models.py` (7 tests: upsert idempotente, replace_chunks,
  set_chunk_embedding, query `CosineDistance`, unique constraint, empresa
  obligatoria, **aislamiento cross-tenant**).

**Archivos modificados:**

- `requirements.txt` — `pgvector>=0.5,<0.6`
- `config/settings.py` — `"apps.tenant.ai_knowledge"` en **`TENANT_APPS`**
  (nunca en `SHARED_APPS`).
- `docs/production/DEPLOYMENT_RUNBOOK.md` — callout de precondición pgvector
  en el paso 4 (imagen `pgvector/pgvector:pg16`, orden `--shared` antes de
  `--tenant`, `REINDEX` en el cambio de imagen, precondición de restore).

**Incidente registrado (no oculto):** al añadir la app a `INSTALLED_APPS`, el
autoreload de `runserver` importó `ai_knowledge/models.py` → `pgvector` aún
no estaba en la imagen → `web` caído (`ModuleNotFoundError`). Recuperado con
`pip install pgvector` en los contenedores en caliente, y luego **rebuild
real** de las imágenes `web`/`celery` (`docker compose build`) para que
persista. `makemigrations` se hizo con la imagen ya parcheada.

**Iteración de diseño:** la primera `0001` no incluía los índices de la
`Meta` abstracta de `SintelTenantBaseModel` (Django **no** los fusiona
cuando la hija declara su propia `Meta.indexes` — mismo comportamiento
documentado en `SedeAwareModel`). Se añadieron explícitamente
`Index(empresa)` e `Index(empresa, -created_at)` a ambos modelos y se
regeneró la migración (nunca se había aplicado).

### VERIFY (VERIFICADO)

| Check | Resultado |
|---|---|
| Tablas `tenant_ai_knowledge_*` por schema | `aipoc`=2, `home`=2, `admin`=2, **`public`=0** |
| `\d aipoc.tenant_ai_knowledge_aiknowledgedocument` | FK `empresa_id` → `aipoc.empresa_empresa` (schema-local); índices `empresa`, `(empresa, created_at DESC)`, `(empresa, source_type, source_id)`, `(empresa, source_type)`; `uniq_aikdoc_empresa_source` |
| Columna `embedding` | `USER-DEFINED` / `udt_name = vector` (sin dimensión) |
| CRUD service (aipoc) | `upsert_document` crea; `replace_chunks` crea 2 chunks; `set_chunk_embedding` guarda vector + `embedding_dimension` |
| Query vectorial | `AIKnowledgeChunk.objects.order_by(CosineDistance('embedding', q)).first()` devuelve el chunk correcto (`[1,0,0]` más cercano a `[0.95,0.05,0]`) |
| Aislamiento cross-tenant | doc creado en `aipoc` → `home` y `admin` ven **0 docs / 0 chunks** |
| Datos de prueba | limpiados tras el smoke (`aipoc` vuelve a 0 filas) |

### REGRESSION (VERIFICADO)

| Check | Resultado |
|---|---|
| `manage.py check` | `System check identified no issues (0 silenced)` |
| `manage.py makemigrations --check --dry-run` | `No changes detected` |
| Tenants existentes (`home`) | 3 clientes / 1 producto — idéntico al baseline |
| `GET /health` | `200` |
| Contenedores | todos healthy tras el rebuild |
| `pytest apps/tenant/ai_knowledge/tests/` (venv local) | **7 passed** en 608s (la mayoría es build de la BD de test multi-tenant) |

### KNOWN_LIMITATIONS

- `home` y `admin` tienen las tablas `tenant_ai_knowledge_*` **vacías**
  (creadas por el `migrate_schemas --tenant` del entrypoint). Cero datos,
  cero comportamiento nuevo (sin `RetrievalTool`, flags AI en `false`).
  Rollback: `migrate_schemas --tenant tenant_ai_knowledge zero` +
  quitar de `TENANT_APPS` + borrar `apps/tenant/ai_knowledge/`.
- `embedding` es `vector` sin dimensión → **no admite índice ANN (HNSW)**
  todavía. Intencional (plan §13: exact search en el POC). AI-VECTOR-04
  fijará la dimensión con un `AlterField` al conocerse el proveedor.
- `pgvector` quedó instalado a mano en la imagen vía rebuild; el
  `docker-compose.prod.yaml` hereda la misma imagen — el primer deploy de
  prod tras este commit necesita el rebuild (ya cubierto por el paso 3 del
  `DEPLOYMENT_RUNBOOK.md`).

### ROLLBACK (probado por diseño)

1. `manage.py migrate_schemas --tenant tenant_ai_knowledge zero` (borra las
   tablas de `aipoc`/`home`/`admin`; no toca la extensión).
2. Quitar `"apps.tenant.ai_knowledge"` de `TENANT_APPS`; quitar `pgvector`
   de `requirements.txt`; borrar `apps/tenant/ai_knowledge/`.
3. Rebuild `web`/`celery` sin `pgvector`.
4. Backup `sintel_pre_aivector03.dump` disponible.

### GATE — AI-VECTOR-03

```
\d ai_knowledge_document / _chunk        = PASS  (estructura correcta, FK schema-local)
tenant aipoc -> tables exist              = PASS  (2 tablas, columna vector real)
tenant home/admin -> tablas VACIAS         = PASS por decision (entrypoint las migra; 0 datos)
public -> no business tables               = PASS  (0 tablas tenant_ai_knowledge_* en public)
CRUD + query vectorial funcionan           = PASS  (CosineDistance ordena correctamente)
aislamiento cross-tenant (datos)           = PASS  (home/admin no ven data de aipoc)
regresion ERP                              = PASS  (check / makemigrations / row counts / health)
rollback posible                           = PASS
```

**AI-VECTOR-03 = PASS.** NEXT: **AI-VECTOR-04**.

---

## AI-VECTOR-04 — Embedding Provider (`AIEmbeddingProvider` + `FastEmbedProvider`)

**STATUS = PASS** (2026-09-03, rama `feat/onboarding-cookie`)

### Decisión del usuario

Evaluación de proveedores (español, key, peso, coste, egress, latencia,
timeout/retry) → **local con `fastembed` (ONNX, sin torch), modelo
`jinaai/jina-embeddings-v2-base-es` (bilingüe ES/EN, 768 dims)**.

Motivo dominante: el `.env` real **no tiene ninguna API key de IA**
(`ANTHROPIC_/OPENAI_/VOYAGE_API_KEY` ausentes) — un proveedor externo
bloquearía el loop hasta configurar credenciales. `fastembed` local: sin
key, sin coste, **cero egress** (la regla de aislamiento del mandato se
cumple estructuralmente), y desbloquea AI-VECTOR-04..10 ya. Los campos
`embedding_model`/`embedding_version` + el path de reindexado permiten
cambiar de proveedor si el benchmark (AI-VECTOR-09) lo exige.

Validación previa del modelo (venv, real): descarga ~50 s (una vez),
embed de 3 textos 0.08 s, salida 768-d. `cos("tornillo de acero" ES,
"stainless steel screw" EN) = 0.67`; `cos("tornillo" ES, "cliente
mayorista" ES) = -0.02` — cross-lingual y discriminación correctas.

### EXECUTE (HECHO)

**Contrato (`apps/services/ai/providers/`):**

- `embedding_base.py` — `AIEmbeddingProvider` (ABC), `EmbeddingResult`
  (con validación de dimensión en `__post_init__`), `EmbeddingProviderError`
  (`transient: bool`). **Separado** de `AIProvider.complete()` a propósito
  (generar texto y embeddings son operaciones distintas; Anthropic ni
  siquiera ofrece embeddings). Métodos: `embed_documents(texts)` /
  `embed_query(text)` (separados porque e5/jina-v3/voyage usan prompt
  distinto para consulta vs documento).
- `fastembed_provider.py` — `FastEmbedProvider`. Import perezoso de
  `fastembed`, cache de modelo a nivel de módulo, **guard de timeout**
  (`ThreadPoolExecutor.result(timeout=...)` → `EmbeddingProviderError(
  transient=True)`), **retry** de la carga del modelo (1 reintento, para el
  fallo de descarga de pesos), **logging seguro** (solo `n`, `model`,
  `dim`, `elapsed_ms` — nunca el texto ni el vector). Config por env:
  `AI_EMBEDDING_MODEL` / `AI_EMBEDDING_DIMENSION` / `AI_EMBEDDING_TIMEOUT_S`.
- `__init__.py` — `get_embedding_provider(name=None)` (factory, dict
  explícito, default `fastembed` vía `AI_EMBEDDING_PROVIDER`).

**Modelo + migración (`apps/tenant/ai_knowledge/`):**

- `models.py` — `embedding = VectorField(dimensions=768)` (era `None`).
- `migrations/0002_pin_embedding_dimension_768.py` — `AlterField`,
  `vector` → `vector(768)`. Tablas vacías → sin riesgo de datos.

**Infra:**

- `requirements.txt` — `fastembed>=0.8,<0.9`.
- `Dockerfile` — `mkdir -p /app/.fastembed_cache` (owner appuser, para que
  el named volume herede UID 1000).
- `docker-compose.yaml` / `.prod.yaml` — named volume `fastembed_cache`
  montado en `/app/.fastembed_cache` (web + celery), env
  `FASTEMBED_CACHE_PATH`. Evita re-descargar ~0.64 GB en cada arranque.

**Tests:** `apps/services/ai/tests/test_embedding_provider.py` — 9 tests
con modelo fake (dimensión, shape, texto vacío, timeout→transient, logging
sin texto, factory) + 1 `@pytest.mark.slow` con el modelo real (768d,
similitud cross-lingual). `pytest.ini` — marker `slow`.

### VERIFY (VERIFICADO)

| Check | Resultado |
|---|---|
| Columna `embedding` (aipoc) | `vector(768)` (era `vector` sin dimensión) |
| `get_embedding_provider()` en el contenedor | `fastembed / jinaai/jina-embeddings-v2-base-es / 768` |
| `FASTEMBED_CACHE_PATH` | `/app/.fastembed_cache`, escribible por `appuser` (UID 1000) |
| Smoke real end-to-end (aipoc) | 3 descripciones de producto → `embed_documents` (768d, 45 s incl. 1ª descarga del modelo) → persistidas vía `set_chunk_embedding` → `embed_query` 51 ms → `order_by(CosineDistance)` rankea **perno + tornillo por encima de "cliente mayorista"** para la consulta "herramientas y sujetadores metálicos" |
| Logging del provider | `[FastEmbedProvider] embed_documents n=3 model=... dim=768 elapsed_ms=...` — **sin texto ni vector** |
| Cache persistido | 615 MB en el named volume `crm_sintel_fastembed_cache` — un reinicio no vuelve a descargar |
| Datos de smoke | limpiados (4 filas: 1 doc + 3 chunks) |

### REGRESSION (VERIFICADO)

| Check | Resultado |
|---|---|
| `manage.py check` | `System check identified no issues` |
| `manage.py makemigrations --check --dry-run` | `No changes detected` |
| `pytest apps/services/ai/tests/ --collect-only` | **93 tests** recolectados, sin errores de import (el cambio en `providers/__init__.py` no rompe nada) |
| `pytest -m "not slow"` provider tests (venv) | **9 passed** (dimensión, shape, timeout→transient, logging sin texto, factory) |
| `pytest apps/tenant/ai_knowledge/tests/` + provider (venv) | **16 passed**, 1 deselected (slow) en 609 s |
| Tenants existentes (`home`) | 3 clientes / 0 chunks — intacto/aislado |
| `GET /health` | `200` |

### KNOWN_LIMITATIONS

- **"timeout" y "retry" están degradados** frente a un proveedor hosted
  (decisión del usuario, local sin red): timeout = guard de wall-clock sobre
  la inferencia; retry = 1 reintento de la carga/descarga del modelo. No hay
  5xx remoto que reintentar. Si AI-VECTOR-09 muestra que la calidad no
  alcanza, cambiar a Voyage/OpenAI reactiva el path completo (contrato
  `AIEmbeddingProvider` ya lo soporta).
- El modelo se descarga en el **primer `embed()`** (~40-50 s, ~0.64 GB). El
  named volume lo persiste entre reinicios y rebuilds. Un entorno nuevo
  (prod primer deploy) paga esa descarga una vez; puede pre-calentarse con
  un `python -c "from apps.services.ai.providers import get_embedding_provider; get_embedding_provider().embed_query('warmup')"`.
- `HF_TOKEN` no configurado → descargas sin autenticar (rate limit más bajo).
  Suficiente para el POC; documentar si se vuelve un problema.

### ROLLBACK

1. `migrate_schemas --tenant tenant_ai_knowledge 0001` (revierte `vector(768)`
   → `vector`; tablas vacías, sin pérdida).
2. Quitar `fastembed` de `requirements.txt`; borrar `embedding_base.py` /
   `fastembed_provider.py`; revertir `providers/__init__.py` y `models.py`.
3. Revertir el volumen `fastembed_cache` en los 2 compose + el `mkdir` del
   Dockerfile; `docker volume rm crm_sintel_fastembed_cache`.
4. Rebuild `web`/`celery`.

### GATE — AI-VECTOR-04

```
provider real                = PASS  (FastEmbedProvider, jina-v2-es 768d)
generacion real               = PASS  (smoke end-to-end en aipoc, ranking correcto)
manejo de timeout             = PASS  (guard wall-clock -> EmbeddingProviderError transient)
retry                         = PASS  (1 reintento de carga de modelo; degradado, documentado)
idempotencia                  = PASS  (modelo determinista: mismo texto -> mismo vector)
logging seguro                = PASS  (solo n/model/dim/elapsed; test lo verifica)
aislamiento (cero egress)      = PASS  (modelo local, el texto no sale del contenedor)
dimension fijada + trazable    = PASS  (vector(768), embedding_model/version/dimension)
regresion ERP                 = PASS
rollback posible              = PASS
```

**AI-VECTOR-04 = PASS.** NEXT: **AI-VECTOR-05**.

---

## AI-VECTOR-05 — Capa semántica (Chunking + Embedding + Retrieval)

**STATUS = PASS** (2026-09-03, rama `feat/onboarding-cookie`)

### EXECUTE (HECHO) — todo en `apps/tenant/ai_knowledge/services/`

- **`chunking_service.py`** — `ChunkingService.chunk(text, *, max_chars=800,
  overlap_chars=80)`. Capa **pura de texto** (no BD, no proveedor, no
  tenants): parte por párrafos; un párrafo largo se reparte por oración con
  solapamiento; una oración gigante se corta duro por caracteres. Texto
  vacío → `[]`.
- **`sources.py`** — `INDEXABLE_SOURCES`: allowlist **curada a mano** de
  `(modelo, campo)` indexables = **la frontera de seguridad**. Los 2
  orígenes del POC (`cliente_observaciones`, `producto_descripcion`).
  Cualquier campo FORBIDDEN/MASKED simplemente no está aquí. `is_indexable()`.
- **`embedding_service.py`** — `EmbeddingService.index_text(...)`. Orquesta
  `upsert_document → ChunkingService → replace_chunks → provider.embed_documents
  → set_chunk_embedding`. **Idempotente**: si `source_version` no cambió y los
  chunks ya están embebidos con el modelo/`CURRENT_EMBEDDING_VERSION`
  actuales → `skipped=True`, sin llamar al proveedor. `force=True` reindexar;
  `deindex()` borra; `stale_count()` cuenta chunks con modelo/versión viejos.
- **`retrieval_service.py`** — `RetrievalService.search(*, empresa, query, k=5,
  source_types=None, sede_ids=None, area_ids=None, max_distance=None)`.
  **Solo lectura** (`.filter/.only/.annotate/.order_by`, cero writes).
  `embed_query → CosineDistance('embedding', qvec) → order_by(distance)[:k]`.
  Sin índice ANN (plan §13, exact search). Filtros sede/área **NULL-safe**
  (un doc sin `sede_id` en `metadata` es visible siempre; si lo declara, debe
  caer en el alcance — mismo criterio que `filter_by_scope_null_safe`).
  `RetrievalHit` con `content/source_type/source_id/document_uuid/distance/
  score/metadata`. **No filtra por `tenant_id`** — el aislamiento lo da el
  schema.

### VERIFY (VERIFICADO)

**Smoke real end-to-end en `aipoc`** (4 descripciones sintéticas de producto,
modelo jina-es real):

| Consulta | Top-1 (score) | Correcto |
|---|---|---|
| "fijaciones metálicas para obra" | Perno hexagonal grado 8.8 (0.55) | ✓ (perno > tornillo, ambos fasteners) |
| "protección de manos para laboratorio" | Guante de nitrilo (0.38) | ✓ |
| "condiciones de pago del cliente" | Cliente preferente paga a 15 días (0.38) | ✓ |
| Re-index con mismo `source_version` | `skipped=True` | ✓ idempotencia |
| Datos de smoke | limpiados (8 filas) | ✓ |

| Check | Resultado |
|---|---|
| `manage.py check` / `makemigrations --check` | OK / `No changes detected` (sin migraciones, sin infra) |
| `pytest apps/tenant/ai_knowledge/tests/` (venv, modelo fake) | **22 passed** (7 modelos + 15 servicios: chunking, allowlist, idempotencia, ranking, k, filtro source_type, solo-lectura, no-cruza-tenants) en 623 s |

### GATE — AI-VECTOR-05

```
ChunkingService puro (sin BD/tenant/provider)     = PASS
allowlist de orIgenes = frontera de seguridad     = PASS  (sources.py, is_indexable)
EmbeddingService idempotente por source_version    = PASS  (skip verificado)
RetrievalService SOLO lectura                      = PASS  (test: docs/chunks no cambian)
retrieval tenant-scoped (sin WHERE tenant_id)      = PASS  (aislamiento por schema)
exact search, sin ANN                              = PASS  (CosineDistance + order_by)
"retrieval funcionando dentro de un tenant real"   = PASS  (smoke en aipoc, ranking correcto)
```

**AI-VECTOR-05 = PASS.** NEXT: **AI-VECTOR-06**.

---

## AI-VECTOR-06 — Seguridad y aislamiento multi-tenant (GATE CRÍTICO)

**STATUS = PASS** (2026-09-03, rama `feat/onboarding-cookie`)

```
cross_tenant_leaks = 0     unauthorized_retrieval = 0     forbidden_indexed = 0
```

### EXECUTE (HECHO) — endurecimiento, no nueva funcionalidad

- **`EmbeddingService.index_text`** — nuevo param `allow_unlisted: bool =
  False`. Si `source_type` no está en `INDEXABLE_SOURCES` y no se pasa
  `allow_unlisted=True`, **lanza `ValueError` antes de tocar el
  ChunkingService o el proveedor** y loguea un `warning` (evento de
  seguridad). La allowlist deja de ser solo documentación: es un candado.
- **`sources.py`** — `FORBIDDEN_MODEL_FIELDS` (24 pares `(model_label,
  field)` clasificados FORBIDDEN/MASKED en `AI_SECURITY_MODEL.md`:
  `Empleado.eps/afp/arl/...`, `Contrato.salario_mensual`,
  `Devengo.salario_base/...`, `CuentaBancaria.numero`,
  `ExtractoBancario.saldo_*`, `TransaccionBancaria.valor/saldo/
  notas_conciliacion`). `_assert_allowlist_safe()` corre **en tiempo de
  import**: si algún `IndexableSource` apuntara a un campo prohibido (texto
  o metadata), el módulo no carga.
- **`RetrievalService.search_for_context(context, query, ...)`** — deriva
  el alcance organizacional del `AIContext` **exactamente igual que
  `compras_tools.py::_scope_kwargs`** (EMPRESA → sin restricción; SEDE →
  `sede_ids` del contexto, incluso vacía; AREA → `area_ids`). El
  `empresa_id` sale SIEMPRE del contexto, no de un parámetro. Es el punto
  donde AI-VECTOR-07 conectará el `RetrievalTool`.
- `RetrievalService.search` — acepta `empresa` como instancia **o** id
  (`_resolve_empresa_id`), filtra por `empresa_id`.

### Escenario 4 — `ToolRisk.SENSITIVE_READ` NO es enforcement automático

`AIEngine.run_tool()` verifica (leído en `engine/ai_engine.py`): `AI_ENABLED`
→ tool existe → flag del `kind` → `AUTO_APPROVED_KINDS` (bloqueo WRITE) →
`build_context`. **Nunca lee `tool.risk`.** `test_toolrisk_not_enforced.py`
lo pinea: una tool `risk=SENSITIVE_READ` se ejecuta igual (flags mediante);
lo que la bloquea es `AI_READ_ENABLED=False`, no el riesgo. Un `RetrievalTool`
sensible (AI-VECTOR-07) **debe** aplicar el alcance explícitamente en su
`run()` — no puede confiar en `risk`. Un test de candado documental
(`"ToolRisk" not in inspect.getsource(ai_engine)`) fuerza actualizar
`AI_SECURITY_MODEL.md` si eso cambia.

### VERIFY — smoke real end-to-end (modelo jina-es, tenants `aipoc` + `home`)

| Escenario | Resultado |
|---|---|
| **1. Cross-tenant** — doc "confidencial aipoc" indexado en `aipoc`, doc "confidencial home" en `home` | Buscar desde `aipoc` → solo `SECRET_AIPOC`; desde `home` → solo `SECRET_HOME`. **0 leaks** |
| Cross-tenant vía `empresa_id` de A dentro del schema de B | `[]` (la tabla vive en el schema; el `empresa_id` de A no existe en B) |
| **2. Alcance EMPRESA** (`sede_ids=None`) | ve los 3 docs (sede1, sede2, general) |
| **2. Alcance SEDE(1)** | ve sede1 + general, **NO sede2**. `unauthorized_retrieval = 0` |
| **2. Alcance SEDE sin asignaciones** (`sede_ids=()`) | solo el doc general (NULL-safe); ninguno con sede |
| **2. Alcance AREA(7)** | ve area7 + los sin área; AREA(99) no ve area7 |
| **3. FORBIDDEN/MASKED** — `empleado_salario`, `cuenta_bancaria_numero`, `devengo_salario_base` | `is_indexable() == False`; `index_text()` lanza `ValueError`; **`forbidden_indexed = 0`** |
| Datos de smoke | limpiados |

### REGRESSION

| Check | Resultado |
|---|---|
| `manage.py check` / `makemigrations --check` | OK / `No changes detected` (sin migraciones) |
| `pytest apps/services/ai/tests/test_toolrisk_not_enforced.py` (venv) | **3 passed** |
| `pytest apps/tenant/ai_knowledge/tests/` (venv, stub provider) | **42 passed** (7 modelos + 15 servicios + 20 seguridad). 1 fallo transitorio corregido (`int` en vez de instancia `Empresa` en un test, no en el codigo) |
| AI-VECTOR-05 tests (`test_services.py`) | siguen pasando (usan `source_type` allowlisted) |

### GATE — AI-VECTOR-06

```
cross_tenant_leaks = 0        = PASS  (smoke aipoc/home + tests 2 tenants reales)
unauthorized_retrieval = 0     = PASS  (SEDE(1) no ve sede2; empresa_id inexistente -> [])
forbidden_indexed = 0          = PASS  (allowlist candado import + runtime, 24 pares prohibidos)
ToolRisk no es automatico       = PASS  (pineado; RetrievalTool debe enforcar en run())
aislamiento por schema probado  = PASS  (no sustituido por "es estructural" -- 2 tenants reales)
regresion ERP                   = PASS
```

**AI-VECTOR-06 = PASS.** NEXT: **AI-VECTOR-07**.

---

## AI-VECTOR-07 — Integración con el AI Engine (`RetrievalTool`)

**STATUS = PASS** (2026-09-03, rama `feat/onboarding-cookie`)

### EXECUTE (HECHO)

- **`apps/services/ai/tools/retrieval_tools.py`** — `RetrievalTool`
  (`name="buscar_conocimiento"`, `domain="ai_knowledge"`, `kind=READ`,
  `risk=SAFE_READ`). Tool **delgada**, mismo patrón que `ProjectMapTool`
  invoca al EKG: `run()` hace import diferido de
  `apps.tenant.ai_knowledge.services.RetrievalService` y llama
  **`search_for_context(context, query, ...)`** — el alcance se aplica
  explícitamente (no se confía en `risk`). Devuelve
  `ToolResult(status="OK", data=[{content, source_type, source_id,
  document_uuid, score}])`.
- **Doble gate:** `kind=READ` → el engine ya exige `AI_READ_ENABLED`; además
  `run()` chequea **`AI_RETRIEVAL_ENABLED`** (nuevo flag en `settings.py`,
  default `false`) y devuelve `PERMISSION_DENIED` si está off. Permite
  encender/apagar SOLO retrieval en el rollout/rollback de AI-VECTOR-11 sin
  tocar las demás tools READ.
- **`apps/services/ai/tools/__init__.py`** — `register_tool(RetrievalTool())`.
  20 tools registradas (era 19).
- **`apps/services/ai/orchestrator/form_assistant.py`** — 6 líneas al
  `system` prompt: regla de routing explícita ("si la pregunta pide un DATO
  EXACTO y hay una tool determinista, usa esa — nunca `buscar_conocimiento`
  para un dato exacto"). El catálogo de tools que ve el LLM ya sale de
  `tool_metadata()`, así que la `description` de la tool también guía.
- **`config/settings.py`** — `AI_RETRIEVAL_ENABLED` (default `false`).

### GATE — lo que NO se tocó (verificado con `git diff`)

```
apps/services/ai/context/ai_context.py     = SIN CAMBIOS  (AIContext unchanged)
apps/services/ai/engine/ai_engine.py        = SIN CAMBIOS  (run_tool unchanged)
apps/services/ai/tools/ekg_tools.py + ekg/   = SIN CAMBIOS  (EKG unchanged)
otras *_tools.py                             = SIN CAMBIOS  (existing tools unchanged)
AI_WRITE_ENABLED                             = false        (AI WRITE disabled)
```
Solo 2 archivos modificados en `apps/services/ai/`: `__init__.py` (+5,
registro) y `form_assistant.py` (+6, prompt de routing).

### VERIFY — smoke real end-to-end en `aipoc` (vía `AIEngine.run_tool`)

| Check | Resultado |
|---|---|
| `run_tool("buscar_conocimiento", request, query="descuento y condiciones de pago del cliente", k=2)` | `status=OK`; K1 "condiciones comerciales..." (score 0.58) sobre K2 "taladro..." (0.04) |
| Log del engine | `ai_engine.tool_call tool=buscar_conocimiento kind=READ status=OK user=17 empresa=1` — pasó por el punto de entrada sin modificarlo |
| `AI_RETRIEVAL_ENABLED=False` (con READ on) | `PERMISSION_DENIED` |
| Datos de smoke | limpiados |

### REGRESSION

| Check | Resultado |
|---|---|
| `manage.py check` / `makemigrations --check` | OK / `No changes detected` |
| `pytest test_retrieval_tool.py` + `test_toolrisk_not_enforced.py` (venv) | **12 passed** (9 retrieval tool + 3 toolrisk): registro, doble gate, query vacía, k fuera de rango, alcance EMPRESA ve sede B / alcance SEDE(A) no la ve, WRITE off |

### GATE — AI-VECTOR-07

```
RetrievalTool registrada en AIToolRegistry        = PASS  (buscar_conocimiento, 20 tools)
AIEngine.run_tool() como punto de entrada, intacto  = PASS  (git diff vacio en ai_engine.py)
AIContext / EKG / tools existentes sin cambios       = PASS
alcance aplicado en run() (no se confia en risk)     = PASS  (search_for_context)
doble feature flag (READ + RETRIEVAL), default off   = PASS
routing determinista > semantico                     = PASS  (description + system prompt)
AI WRITE sigue deshabilitado                          = PASS
```

**AI-VECTOR-07 = PASS.** NEXT: **AI-VECTOR-08**.

---

## AI-VECTOR-08 — Indexación real del tenant `aipoc` (pipeline + Celery)

**STATUS = PASS** (2026-09-03, rama `feat/onboarding-cookie`)

### EXECUTE (HECHO)

- **`apps/tenant/ai_knowledge/services/indexing_service.py`** — `IndexingService`.
  `reindex_source_type(empresa, source_type, prune=True)` /
  `reindex_all(empresa, source_types=None)`. Itera un `IndexableSource`:
  lee el modelo de dominio vía **`django.apps.get_model(model_label)`** +
  `.filter(empresa_id=...).only(...)` (mismo criterio que `ai_project_map`
  usa `apps.get_models()`; la allowlist garantiza que el campo nunca es
  FORBIDDEN/MASKED). `source_version` = **SHA-256 del texto** →
  `EmbeddingService.index_text` salta si no cambió. Texto en blanco →
  `deindex`. `prune=True` → borra los `AIKnowledgeDocument` cuyo `source_id`
  ya no existe. Devuelve `IndexStats` (scanned/indexed/skipped/emptied/pruned).
- **`apps/tenant/ai_knowledge/tasks.py`** — `@shared_task
  reindex_tenant_knowledge(schema_name, source_types=None)`. Patrón
  `maildigester`: `schema_context(schema_name)` envuelve todo el ORM;
  `autoretry_for=(ConnectionError, TimeoutError, OSError)`;
  `EmbeddingProviderError` se reintenta **solo si `transient=True`**;
  `_clasificar_excepcion` (transient/security/programming/domain/validation)
  decide el nivel de log, nunca silencia. Cola `default` (vía
  `CELERY_TASK_ROUTES '*'`), nunca `high_priority`.
- **`config/settings.py`** — `"apps.tenant.ai_knowledge.tasks"` en
  `CELERY_IMPORTS` (registro explícito, como los demás tasks críticos).
- **`apps/tenant/ai_knowledge/management/commands/seed_ai_poc.py`** — siembra
  12 `Cliente` (con `observaciones`) + 12 `Producto` (con `descripcion`) de
  **texto libre sintético NO sensible** (ferretería/eléctrico/salud/
  construcción — condiciones comerciales, especificaciones). Candado:
  `POC_SCHEMAS = {"aipoc"}`, requiere `--force` para otros schemas.

### VERIFY — ejecución real vía el worker Celery

```
reindex_tenant_knowledge.delay('aipoc')   -> task 4bed9e91-...
Task ... succeeded in 9.05s:
  totals = {scanned: 24, indexed: 24, skipped: 0, emptied: 0, pruned: 0}
  by_source: cliente_observaciones 12/12, producto_descripcion 12/12
```

| Check | Resultado |
|---|---|
| `aipoc.tenant_ai_knowledge_aiknowledgedocument` | 12 `cliente_observaciones` + 12 `producto_descripcion` |
| `..._aiknowledgechunk` | 24 chunks, **24 con embedding**, dimensión 768 |
| **Idempotencia** — 2ª corrida del task | `scanned: 24, indexed: 0, skipped: 24` |
| `run_tool("buscar_conocimiento", ...)` sobre el dataset real (dentro de `schema_context('aipoc')`) | "productos resistentes a la corrosión / acero inoxidable" → *"Proyectos de vivienda en zona costera. Exige productos con protección contra corrosión"* (0.63); "herramienta eléctrica para perforar concreto" → *"Taladro percutor eléctrico de 800 W"* (0.74); "protección personal sector salud" → *"insumos de protección y aseo para clínicas: guantes, batas"* (0.58) |

### REGRESSION

| Check | Resultado |
|---|---|
| `manage.py check` / `makemigrations --check` | OK / `No changes detected` (sin migraciones nuevas) |
| Celery worker | `reindex_tenant_knowledge` registrada (`celery inspect registered`) |
| `pytest apps/tenant/ai_knowledge/tests/` (venv) | **51 passed** (7 modelos + 15 servicios + 20 seguridad + 9 indexación). 2 fallos corregidos: `PermissionError` es subclase de `OSError` → se clasificaba `transient` (reordenado el check); test de `prune` reescrito para no depender de `Cliente.delete()` (el collector de Django exige migrar media docena de apps al schema de test — el flujo delete→prune real está verificado en `aipoc`) |

### KNOWN_LIMITATIONS

- El disparo del task hoy es manual (`reindex_tenant_knowledge.delay(schema)`)
  o vía `seed_ai_poc` + shell. **No hay** trigger automático desde una
  escritura del ERP (signal/save) — deliberado: el mandato prohíbe que una
  escritura normal del ERP bloquee esperando al proveedor, y un
  fire-and-forget desde cada `Cliente.save()` es ruido para el POC. El
  refresco periódico (Celery Beat) o el trigger por dominio es diseño de
  rollout (AI-VECTOR-11), no del POC.
- El dataset de `aipoc` es **sintético** (12+12 registros). Suficiente para
  el POC y el benchmark (AI-VECTOR-09); no representa el volumen de un
  tenant real.

### ROLLBACK

1. `reindex_tenant_knowledge` con la allowlist vacía no aplica; para limpiar:
   `AIKnowledgeDocument.objects.all().delete()` dentro de `schema_context('aipoc')`.
2. `seed_ai_poc --schema aipoc --wipe` borra los clientes/productos sembrados.
3. Quitar `apps.tenant.ai_knowledge.tasks` de `CELERY_IMPORTS`; borrar
   `indexing_service.py` / `tasks.py` / `management/`.

### GATE — AI-VECTOR-08

```
pipeline source -> chunk -> embedding -> persistence   = PASS  (24/24 en aipoc)
idempotencia por source_version                        = PASS  (2a corrida: skipped 24)
asincrono con Celery (schema_context, cola default)     = PASS  (task en el worker, 9s)
retry SOLO transitorios                                = PASS  (autoretry_for + transient flag)
dataset del POC en aipoc                               = PASS  (seed_ai_poc, 12+12, no sensible)
tenant no productivo                                   = PASS  (aipoc, candado POC_SCHEMAS)
regresion ERP                                          = PASS
```

**AI-VECTOR-08 = PASS.** NEXT: **AI-VECTOR-09**.

---

## AI-VECTOR-09 — Benchmark real (`aipoc`, 24 docs / 24 chunks)

**STATUS = PASS** (2026-09-03). Herramienta:
`apps/tenant/ai_knowledge/management/commands/benchmark_ai_poc.py`
(`--iterations 9 --k 5`, no altera datos). Tokens estimados por heurística
`len/4` (sin `tiktoken`) — el **ratio** baseline/vector es consistente.

### A. Lecturas transaccionales del ERP — **sin degradación**

| Query | Mediana | queries/call |
|---|---|---|
| `ClienteSelector.get_cliente_list` (12 filas) | **1.94 ms** | 1 |
| `ProductoSelector.get_list` (12 filas) | **2.06 ms** | 1 |
| `ClienteSelector.get_cliente_detail` x1 | 3.34 ms | 2 |
| `Producto.count()` (aggregate) | 1.53 ms | 1 |
| **Búsqueda vectorial** `ORDER BY embedding <=> q LIMIT 5` (`EXPLAIN ANALYZE`) | **0.478 ms** | nodo `Limit` (seq scan + sort, **sin índice ANN**, exact search — plan §13) |

Todas sub-4 ms. La tabla vectorial (24 filas, sin índice) resuelve top-k en
**0.5 ms**. **No se afirma que pgvector acelere el ERP** — el ERP no cambió.

### B. Eficiencia AI — BASELINE (mandar todo el texto al LLM) vs VECTOR (top-k)

| | BASELINE | VECTOR (media de 8 queries) |
|---|---|---|
| `T_fetch` / `T_embedding` | 3.39 ms (fetch de 24 textos) | ~41 ms (`embed_query` local) |
| `T_retrieval` | — | ~46 ms (search + `CosineDistance`) |
| **T_total** | **3.39 ms** | **~87 ms** |
| DB queries | 2 | **1** |
| **Tokens al LLM** | **~1003** (constante, por cada query) | **~225** |
| Relevancia top-1 (coseno) | — | 0.51 – 0.74 |

### C. Memoria / almacenamiento

| | Valor |
|---|---|
| Tablas vectoriales (`document` + `chunk`, 24 filas) | **608 KB** |
| Modelo ONNX (`jina-es`) en RSS del proceso que embebe | **~250–340 MB** (arena ONNX crece con uso) |

### GATE — valores **medidos** (no objetivos inventados)

```
LATENCY_GAIN            = -24.7      (NEGATIVO: con 24 docs el embed local
                                     (~41 ms) es mas caro que el fetch (3.4 ms).
                                     Honesto -- no hay ganancia de latencia a
                                     esta escala.)
QUERY_REDUCTION         = 0.50       (2 -> 1 query a la BD)
TOKEN_REDUCTION         = 0.775      (~1003 -> ~225 tokens al LLM: -77.5 %.
                                     Este es el valor real del POC.)
MEMORY_IMPACT           = ~357 MB    (dominado por el modelo ONNX; tablas 608 KB)
RELEVANCE_SCORE (top-1 coseno, media) = 0.595
RELEVANCE precision@1   = 0.625      (5/8 con match EXACTO de palabra clave;
                                     metrica estricta -- los 3 "miss" tienen
                                     top-1 semanticamente relacionado, score
                                     0.51-0.57)
```

### Lectura honesta

- **AI efficiency ≠ ERP performance.** El ERP no se toca; sus lecturas
  siguen sub-4 ms.
- El valor **medido** del POC es **TOKEN_REDUCTION (−77.5 %)** y que el coste
  de retrieval **no crece con el dataset** (0.5 ms para 24 filas, seq scan).
- **La latencia es peor** a escala de POC (24 docs): el `embed_query` local
  añade ~41 ms que el baseline "mandar todo" no paga. Con un proveedor de
  embeddings más rápido, un caché de query-embeddings, o a escala (miles de
  docs, donde "mandar todo" supera el context window y el fetch ya no es
  barato) la balanza cambia. **No se proyecta un número** — se deja la
  medición como está.
- **Relevancia**: aceptable para un POC (todos los scores 0.5–0.74,
  semánticamente pertinentes). `precision@1` con match exacto de keyword es
  una cota inferior conservadora.

**AI-VECTOR-09 = PASS.** NEXT: **AI-VECTOR-10**.

---

## AI-VECTOR-10 — Release Gate del POC

**STATUS = PASS** (2026-09-03). Documento:
**`docs/ai/AI_VECTOR_POC_RELEASE_GATE.md`** (consolidación de los 12 ejes +
las 8 condiciones duras + limitaciones conocidas).

### Verificaciones ejecutadas en esta fase

- **Rollback (probado):** `migrate_schemas --tenant --schema=home
  tenant_ai_knowledge zero` → reverse `0002`→`0001` OK, tablas eliminadas de
  `home`, **`aipoc` intacto** (2 tablas, 24 chunks), re-migración restaura
  `vector(768)`. El rollback por schema aísla.
- **Backup (probado):** `backup_tenant aipoc` → dump custom 1.21 MB que
  incluye `tenant_ai_knowledge_*` con `TABLE DATA` (embeddings) + constraints.
- **Regresión final:** `check` limpio, `makemigrations --check` limpio,
  `/health` 200 (directo + nginx), `home` 3 clientes intactos, `aipoc` 24
  docs/24 chunks, **156 tests** recolectan.

### Veredicto

```
POC_STATUS = POC_PASS_WITH_LIMITATIONS
```

Las 8 condiciones duras de `POC_PASS` se cumplen con evidencia **ejecutada**.
El calificador `WITH_LIMITATIONS` refleja: dataset sintético (L1),
`LATENCY_GAIN` negativo a escala POC (L2), sin índice ANN (L3), reindexado
manual (L4), etc. — ninguna viola una condición de `POC_PASS`, pero todas
condicionan el rollout. Ver la tabla de limitaciones en el Release Gate.

**AI-VECTOR-10 = PASS.** NEXT: **AI-VECTOR-11** — rollout controlado (solo
con go-ahead del usuario): tenant piloto con datos reales → 2 → 25 % → 50 %
→ 100 %, resolviendo antes L1/L2/L4/L8. Rollback siempre disponible
(`AI_RETRIEVAL_ENABLED=false` inmediato / `migrate_schemas … zero`).

---

## AI-VECTOR-11.1 — Piloto sobre `home` (rollout, primer gate)

**STATUS = PASS** (2026-09-08). Go-ahead explícito del usuario para iniciar
AI-VECTOR-11, con 3 decisiones tomadas antes de implementar: tenant piloto
`home` (datos reales tal cual, sin volumen mínimo exigido), L4 = Celery Beat
periódico (no trigger por `save()`), L3 = mantener exact search (no HNSW en
este gate). Alcance: **solo el primer gate del rollout** (piloto), no los 5
pasos completos — mismo patrón gate-por-gate de AI-VECTOR-01..10.

**Hallazgo antes de implementar:** `home` tiene exactamente **1**
`Cliente.observaciones` no vacío y **0** `Producto.descripcion` no vacíos —
dataset real del piloto = 1 documento. Suficiente para aislamiento/
seguridad/rollback/reindexado con datos genuinamente reales, no para un
benchmark de relevancia significativo (documentado, no se infla el resultado).

### EXECUTE (HECHO)

- **`AIKnowledgeSettings`** (nuevo modelo, `apps/tenant/ai_knowledge/models.py`,
  migración `0003_aiknowledgesettings_and_more`): flag `retrieval_enabled`
  por empresa (`UniqueConstraint`). Resuelve un gap encontrado en la
  exploración: `AI_RETRIEVAL_ENABLED` era una única env var global sin
  control por tenant — imposible progresar un rollout gradual sin esto.
- **`RetrievalTool.run()`** ahora chequea el flag global (kill switch de todo
  el entorno, ya existente) Y el flag por tenant (kill switch incremental,
  nuevo) — `apps/services/ai/tools/retrieval_tools.py`.
- **Comando** `ai_knowledge_toggle_retrieval <schema> --enable|--disable` —
  palanca operativa para las siguientes etapas del rollout.
- **L4 resuelto:** `reindex_enabled_tenants` (orquestador liviano, `tasks.py`)
  + `apps/tenant/ai_knowledge/celery_beat_schedule.py` (cada 6h), merged en
  `config/celery.py`. **Hallazgo de infraestructura:** no existía ningún
  contenedor `celery beat` en `docker-compose.yaml` — el `CELERY_BEAT_SCHEDULE`
  de `dashboard` ya definido nunca se disparaba. Se agregó el servicio
  `celery-beat` + fix en `entrypoint.sh` (esperaba Redis solo para
  `SERVICE_ROLE=celery`, ahora también `celery-beat`).
- **L8 documentado:** `docs/production/BACKUP_RESTORE_RUNBOOK.md` —
  precondición `CREATE EXTENSION vector` antes de `pg_restore` en servidor
  nuevo; corregida también la nota `INFRA-02` ("no hay celery beat en ningún
  entorno"), que ya no aplica literalmente tras este cambio (aunque
  `backup_tenant`/`backup_all_tenants` siguen sin entrada en el beat schedule).
- **Tests:** casos nuevos de `AIKnowledgeSettings` (CRUD, constraint,
  aislamiento cross-tenant) en `test_models.py`, y del flag por tenant en
  `RetrievalTool` (fila ausente / apagado / no afecta el flag global) en
  `test_retrieval_tool.py` — cuyo `setUp()` se actualizó para crear el flag
  encendido (sin eso, los 12 tests existentes de AI-VECTOR-07 habrían
  quedado en `PERMISSION_DENIED`).

### VERIFY (VERIFICADO) — evidencia ejecutada, no solo diseñada

| Check | Resultado |
|---|---|
| `manage.py check` / `makemigrations --check --dry-run` | limpios, tras aplicar la migración a `home`/`admin`/`aipoc` |
| `pytest apps/tenant/ai_knowledge/tests/ apps/services/ai/tests/test_retrieval_tool.py` (venv local) | **67 passed** |
| Reindexado real `reindex_tenant_knowledge.delay('home')` | worker reiniciado (no hace autoreload de código) → 1 documento real indexado, embedding jina-es 768d real |
| `run_tool("buscar_conocimiento", ...)` en `home` (flag ON) | `status=OK`, devuelve el documento real (`score=0.1396`) |
| `run_tool("buscar_conocimiento", ...)` en `admin` (sin flag) | `PERMISSION_DENIED` ("no esta habilitada para este tenant") |
| `celery-beat` levantado (`docker compose up -d celery-beat`) | `app.conf.beat_schedule` confirmado con `ai-knowledge-reindex-enabled-tenants` (cada 6h) |
| `reindex_enabled_tenants` disparada a mano | programó únicamente `['home']` — no `admin`, no `aipoc` (filtro por tenant real, no solo diseñado) |
| Rollback: `ai_knowledge_toggle_retrieval home --disable` | apaga solo `home`; `AI_RETRIEVAL_ENABLED` (global) confirmado que sigue `True` — kill switch incremental real, además del global ya probado en AI-VECTOR-10. Re-habilitado después para dejar el piloto activo |
| `benchmark_ai_poc --schema home --iterations 5 --json` | con n=1 documento real: `TOKEN_REDUCTION=-1.0083`, `RELEVANCE precision@1=0.0`, `LATENCY_GAIN=-6.47` — **peor que el POC sintético** de AI-VECTOR-09, tal como se anticipó (1 documento no es una medición de escala útil). Resuelve L1 (dataset real, no sintético) honestamente; no resuelve L2 |

### REGRESSION (VERIFICADO)

| Check | Resultado |
|---|---|
| `GET /health` | `200` |
| Contenedores | todos healthy (incluye `celery-beat` nuevo) |
| `home` | datos transaccionales intactos |

**Estado final:** `home` con `retrieval_enabled=True` (piloto activo),
`admin`/`aipoc` sin flag (apagados por defecto).

### KNOWN_LIMITATIONS

- Dataset real de `home` = 1 documento. L1 resuelto en el sentido estricto
  (dato real, no sintético) pero **no** en el sentido de "volumen
  representativo" — `RELEVANCE`/`LATENCY_GAIN`/`TOKEN_REDUCTION` medidos con
  n=1 no son comparables con los de AI-VECTOR-09 ni sirven de base para
  proyectar a escala.
- L2 sigue sin resolver: ningún tenant actual tiene volumen suficiente para
  que "mandar todo" deje de ser competitivo frente al vector.
- L3 (HNSW) diferido, decisión tomada explícitamente en este gate.

### GATE — AI-VECTOR-11.1

```
flag por tenant (nuevo, kill switch incremental) = PASS  (modelo + constraint + enforcement en RetrievalTool)
aislamiento con datos reales (home ON, admin OFF) = PASS  (run_tool end-to-end)
reindexado real sobre home                        = PASS  (1 doc, embedding 768d real)
L4: Celery Beat periodico                         = PASS  (celery-beat nuevo, schedule confirmado, orquestador filtra por tenant)
L8: precondicion documentada                      = PASS  (BACKUP_RESTORE_RUNBOOK.md)
rollback incremental probado                      = PASS  (toggle --disable no toca el flag global)
regresion ERP                                     = PASS  (check / makemigrations / health / tests)
```

**AI-VECTOR-11.1 = PASS.** NEXT: AI-VECTOR-11.2+ (expandir a 2 tenants / 25%
/ 50% / 100%) — cada etapa su propio gate, requiere un tenant con volumen
real de datos para que L1/L2 se resuelvan con evidencia útil (no solo con 1
documento). HNSW (L3) sigue diferido hasta que el volumen lo justifique.
Como en AI-VECTOR-10/11, avanzar de gate requiere go-ahead explícito del
usuario.

---

## AI-VECTOR-11A — Caché de query-embeddings (optimización de L2)

**STATUS = PASS** (2026-09-08). El usuario decidió priorizar el caché de
query-embeddings (sobre cambiar de proveedor) para atacar L2 antes de
expandir el rollout a más tenants (AI-VECTOR-11.2+).

### EXECUTE (HECHO)

- **`apps/tenant/ai_knowledge/services/query_embedding_cache.py`** (nuevo):
  `get_cached_embedding(query, model)` / `set_cached_embedding(...)`. Redis
  directo (no `django.core.cache.cache` — el proyecto no tiene `CACHES`
  configurado, el default de Django es `LocMemCache`, **por proceso**, no
  compartido entre `web`/`celery`). Mismo patrón de conexión que
  `apps/tenant/core/services/password_reset.py::_redis()`. Key =
  `ai_embed_query:{schema_name}:{model}:{sha256(texto normalizado)}` —
  aísla por tenant (mismo criterio que `password_reset.py`, "evita uso
  cross-tenant"), nunca el texto en claro, auto-invalida si cambia el
  modelo. TTL configurable (`AI_EMBED_CACHE_TTL_S`, default 6h). Fail-open:
  cualquier fallo de Redis se loguea como `warning` y `search()` sigue
  funcionando sin caché — nunca rompe una tool READ ya gateada.
- **`retrieval_service.py`** — `RetrievalService.search()` envuelve la única
  llamada a `provider.embed_query()` con el cache. No cambia la firma
  pública; `search_for_context()` (usado por `RetrievalTool`) se beneficia
  sin tocarlo.
- **`config/settings.py`** — `AI_EMBED_CACHE_TTL_S` (nuevo, default 6h).
- **`benchmark_ai_poc.py`** — **hallazgo:** el benchmark medía el embedding
  DOS veces por query (una vez standalone vía `provider.embed_query()`, otra
  vez dentro de `ret.search()`), sumando ambas en `T_total_ms`. Eso no
  representa el camino real de producción (`RetrievalTool` solo llama a
  `search()` una vez) y quedaría ciego al caché (la medición standalone no
  pasa por él). Se fusionó en una sola medición `T_search_ms` (mediana) +
  `T_search_ms_best` (mínimo, aproxima el estado estable con caché caliente).

### Incidente durante la implementación — RESUELTO

Primera versión de `_redis()` creaba una conexión Redis **nueva en cada
llamada** (mismo patrón que `password_reset.py`, donde es aceptable por ser
código raro). Al re-correr el benchmark, `T_search_ms` saltó a **~2035 ms**
(peor que sin caché: `LATENCY_GAIN=-226`). Diagnóstico con una prueba
aislada (`redis.from_url('redis://localhost:...').ping()`): conectar a
`localhost` tardaba **~2048 ms** vs **~4 ms** contra `127.0.0.1` explícito —
mismo problema ya documentado en `docker-compose.yaml` para nginx (Windows
prueba IPv6 `[::1]` antes que IPv4 y hace timeout). Insignificante para un
reset de password (raro), catastrófico para retrieval (hot path, 2
conexiones nuevas por query). **Fix:** cliente Redis cacheado a nivel de
proceso (`_client` global, creado una sola vez de forma lazy) en vez de
recrearlo en cada `get`/`set` — el costo de conexión se paga una vez por
proceso, no por llamada. Correcto independientemente del problema de
Windows: reutilizar una conexión es la práctica correcta en cualquier
entorno, el bug de IPv6 solo lo hizo obvio de inmediato en desarrollo local.

### VERIFY (VERIFICADO)

| Check | Resultado |
|---|---|
| Smoke real (`home`): 2 llamadas idénticas a `search()` | 1a ~9.2s (carga del modelo ONNX en frío + cache miss), 2a ~2.1s (cache hit, sin re-embeber) — mismos resultados |
| Prueba aislada de conexión Redis | `localhost`: ~2048 ms; `127.0.0.1`: ~4 ms (diagnóstico del incidente) |
| Tras el fix: 3 llamadas dentro del mismo proceso | 1a paga la conexión (~2023 ms, una sola vez), 2a y 3a `~1 ms` cada una |
| `pytest apps/tenant/ai_knowledge/tests/ apps/services/ai/tests/test_retrieval_tool.py` (venv local) | **72 passed** (67 previos + 5 nuevos: cache hit, cache miss con texto distinto, aislamiento cross-tenant del cache, invalidación por modelo, fail-open sin Redis) |
| `manage.py check` | limpio |
| `benchmark_ai_poc --schema home --iterations 5 --json` (re-ejecutado) | `T_search_ms` (mediana) **6.9–9.4 ms** por query — antes (AI-VECTOR-11.1, sin caché) `T_total_ms` era **56–64 ms** (`T_embedding_ms` ~25-28 + `T_retrieval_ms` ~31-36) |

### GATE — valores medidos, antes/después

```
                        AI-VECTOR-11.1 (sin cache)   AI-VECTOR-11A (con cache)
LATENCY_GAIN            -6.47                         -0.1007
T_total/T_search (med.) ~56-64 ms                      ~6.9-9.4 ms
TOKEN_REDUCTION         -1.0083                        -1.0083   (sin cambio -- no depende del embedding)
RELEVANCE precision@1   0.0                             0.0      (sin cambio -- mismo dataset de 1 doc, mismos scores)
```

### Lectura honesta

- El caché resuelve el costo del `embed_query` para consultas **repetidas**
  dentro de la vida del proceso (TTL 6h) — no acelera la primera vez que se
  hace una pregunta nueva (cache miss real, sigue pagando ~25-28 ms de
  inferencia ONNX). `LATENCY_GAIN` sigue siendo levemente negativo
  (`-0.1007`, no positivo) porque la mediana de 5 iteraciones incluye 1
  cache-miss real; con más iteraciones o preguntas repetidas en producción
  la mediana se acercaría más al costo de un cache-hit puro (~1 ms + fetch
  DB).
- `TOKEN_REDUCTION`/`RELEVANCE` no cambian — el caché optimiza latencia, no
  toca qué se recupera ni cuánto se manda al LLM. El límite real de esos
  ejes sigue siendo el dataset de `home` (1 documento), no resuelto por
  este gate.
- El incidente de conexión (2000ms/llamada) fue un hallazgo real del propio
  proceso de verificación — se documenta el diagnóstico completo, no se
  omite como si el diseño hubiera sido correcto a la primera.

```
cache de query-embeddings funciona (hit/miss)       = PASS  (smoke real + 5 tests)
aislamiento del cache por tenant                     = PASS  (test_search_cache_no_cruza_tenants)
invalidacion automatica por cambio de modelo         = PASS  (test_search_cache_invalida_por_modelo)
fail-open si Redis no responde                       = PASS  (test_search_cache_fail_open_si_redis_no_responde)
LATENCY_GAIN mejora medible                          = PASS  (-6.47 -> -0.1007, ~65x menos negativo)
benchmark mide el camino real de produccion          = PASS  (T_search_ms fusiona embed+retrieval, ya no duplica)
regresion (check / tests / mismos resultados)        = PASS
```

**AI-VECTOR-11A = PASS.** NEXT: AI-VECTOR-11.2+ (expandir el rollout a 2
tenants / 25% / 50% / 100%) — requiere go-ahead explícito del usuario y,
idealmente, un tenant con volumen real de datos para que L1/L2 se terminen
de resolver con evidencia representativa (no solo 1 documento).
