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

**AI-VECTOR-02 = PASS.** NEXT: **AI-VECTOR-03** — nueva app `TENANT_APPS`
`apps/tenant/ai_knowledge/` con `AIKnowledgeDocument` / `AIKnowledgeChunk`
(`SintelTenantBaseModel`), `crud_service.py`, añadir `pgvector` a
`requirements.txt`, migración aplicada **solo al tenant `aipoc`**;
actualizar `DEPLOYMENT_RUNBOOK.md` con la precondición de la extensión.
