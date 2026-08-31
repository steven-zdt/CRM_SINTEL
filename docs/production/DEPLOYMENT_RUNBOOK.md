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
