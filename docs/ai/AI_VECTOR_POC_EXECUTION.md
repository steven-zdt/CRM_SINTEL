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

**AI-VECTOR-01 = PASS.** NEXT: **AI-VECTOR-02** — migración `RunSQL` en
`SHARED_APPS` (`CREATE EXTENSION IF NOT EXISTS vector;`), ejecutada vía
`migrate_schemas --shared` una sola vez; verificar que `migrate_schemas
--tenant` sigue intacto; actualizar el runbook de provisioning con la
precondición de la extensión.
