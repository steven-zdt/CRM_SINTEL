# DEPLOYMENT_RUNBOOK

**Estrategia (Fase 32-34):** rolling restart vía Docker Compose — NO se
implementa blue/green ni Kubernetes; la infraestructura real es Compose
y forzar un patrón de orquestador ajeno sería sobre-ingeniería no
solicitada. Un release identificable = un commit + tag de imagen.

## Procedimiento de despliegue

1. **Pre-check (obligatorio, no opcional):**
   ```bash
   python manage.py production_readiness --json /tmp/pr_pre_deploy.json
   ```
   Si `OVERALL STATUS` es `NOT_READY` con blockers `P0` reales (no
   `EXTERNAL_DEPENDENCY` ya aceptados), **detener el despliegue**.

2. **Backup previo (obligatorio antes de cualquier migración):**
   ```bash
   docker compose exec web python manage.py backup_all_tenants
   ```
   Ver `BACKUP_RESTORE_RUNBOOK.md`.

3. **Build + pull de la imagen** del release identificado (commit/tag).

4. **Migraciones — NUNCA automáticas sin supervisión:**
   ```bash
   docker compose exec web python manage.py makemigrations --check --dry-run  # confirmar 0 pendientes de generar
   docker compose exec web python manage.py migrate_schemas --shared
   docker compose exec web python manage.py migrate_schemas --tenant
   ```

   > **Precondición pgvector (AI-VECTOR-01/02/03).** El servicio `db` debe
   > correr una imagen con la extensión `vector` compilada
   > (`pgvector/pgvector:pg16`, ver `docker-compose.yaml`) — la imagen
   > `postgres:16-alpine` **no** la tiene. `migrate_schemas --shared`
   > incluye `db_extensions.0001_vector_extension` (`CREATE EXTENSION`), que
   > **debe** correr antes de `--tenant` (el orden de arriba ya lo
   > garantiza). Una restauración a un servidor nuevo requiere la extensión
   > ya presente en la BD destino **antes** de `pg_restore` de cualquier
   > schema con columnas `vector` — ver `BACKUP_RESTORE_RUNBOOK.md`.
   > Migrar de `postgres:16-alpine` (musl) a `pgvector/pgvector:pg16`
   > (Debian/glibc) sobre un volumen existente exige un
   > `REINDEX DATABASE <db>` una sola vez tras recrear el contenedor
   > (cambio de proveedor de collation). Detalle:
   > `docs/ai/AI_VECTOR_POC_EXECUTION.md`.

5. **Static assets:**
   ```bash
   docker compose exec web python manage.py collectstatic --noinput
   ```

6. **Restart controlado:**
   ```bash
   docker compose up -d --no-deps web celery nginx
   ```

7. **Health check post-restart:**
   ```bash
   curl -f http://localhost:8000/health || echo "FALLO — ver INCIDENT_RUNBOOK.md"
   ```

8. **Smoke tests** (Fase 36) — ver `PRODUCTION_CHECKLIST.md` §Smoke.

9. **Registrar el release** (Fase 33): commit, fecha, migraciones
   aplicadas, resultado de `production_readiness`, punto de rollback
   (imagen/commit anterior).

## Punto de rollback

Antes del paso 6, conservar: la imagen Docker anterior (tag previo,
nunca sobrescribir `latest` sin conservar el tag anterior) y el backup
del paso 2. Ver `ROLLBACK_RUNBOOK.md`.
