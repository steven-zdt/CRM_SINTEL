# CUTOVER_RUNBOOK — Fase 54

**No ejecutado en esta pasada** -- no existe TARGET. Este runbook queda
preparado para cuando exista, con los comandos reales ya verificados
en SOURCE durante esta sesión (no genéricos/inventados).

## Orden obligatorio (Fase 54, sin saltos)

```
1. Freeze de escritura en SOURCE
2. Backup final de SOURCE
3. Copiar cambios/datos desde el backup final a TARGET
4. Restore en TARGET
5. Validar (POST_MIGRATION_VALIDATION.md completo)
6. Cambiar DNS
7. Smoke test contra TARGET (por hostname real, no solo por IP)
8. Monitorear (docs/production/PRODUCTION_CHECKLIST.md ya cubre esto)
```

## Paso 1 — Freeze de escritura

No existe hoy un mecanismo de "modo mantenimiento" auditado en este
repo. Opción mínima viable: escalar temporalmente `DEBUG`-equivalente
de solo-lectura no existe -- **acción recomendada, no implementada
aquí:** un middleware de mantenimiento explícito, o detener
`celery`/`web` brevemente durante la ventana de freeze (aceptable para
una migración planificada, no para un rollback de emergencia). Se
documenta como brecha real, no se inventa un mecanismo nuevo a mitad
de una auditoría.

## Paso 2 — Backup final (comando real, ya verificado esta sesión)

```
docker compose exec web python manage.py backup_all_tenants --output-dir /tmp/cutover_final_backup
docker compose cp web:/tmp/cutover_final_backup/. ./backups/cutover_final/
# Generar SHA256SUMS.txt igual que en DATABASE_MIGRATION.md
```

## Paso 3-4 — Transferir y restaurar en TARGET

```
# En TARGET, tras copiar los .dump por un canal seguro:
docker compose exec web python manage.py restore_tenant <archivo>.dump --schema-name <schema> --clean
# Repetir por cada schema (public + cada tenant)
# CRITICO (BAK-02): confirmar antes que pg_dump/pg_restore del TARGET
# coincide en version major con el Postgres del TARGET -- ver
# docs/production/BACKUP_RESTORE_RUNBOOK.md, es el bug real que este
# mismo entorno tuvo y corrigio.
```

## Paso 5 — Validar

Ver `POST_MIGRATION_VALIDATION.md` -- checklist completo, no se repite
aquí.

## Paso 6 — Cambiar DNS

Solo tras `TARGET = VERIFIED` (Fase 56, regla explícita). TTL bajo
recomendado ANTES del cutover (reducir TTL del registro relevante con
suficiente antelación para que la propagación del cambio real sea
rápida cuando se ejecute).

## Paso 7 — Smoke test

Reusar `docs/production/PRODUCTION_CHECKLIST.md` + los checks
automatizados de `apps/public/core/production_readiness/` (framework
ya construido en la misión de producción de esta sesión, reutilizable
tal cual contra TARGET) -- correr
`python manage.py production_readiness` dentro del contenedor `web`
del TARGET como primer paso del smoke test, no al final.

## Split-brain (Fase 55, prevención)

Durante la ventana entre el paso 3 (backup final) y el paso 6 (DNS),
**SOURCE no debe recibir escrituras nuevas** que no queden reflejadas
en TARGET -- de ahí el freeze del paso 1. Sin un mecanismo de
replicación continua (no existe en esta arquitectura), la ventana de
freeze debe ser corta y el equipo debe evitar operar SOURCE durante
ese lapso.
