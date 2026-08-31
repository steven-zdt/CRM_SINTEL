# BACKUP_RESTORE_RUNBOOK

## Mecanismo real (ya existente, verificado por lectura de código)

`apps/public/tenants/management/commands/`:
- `backup_tenant.py` — backup de un schema individual vía `pg_dump`
  (formato custom).
- `backup_all_tenants.py` — todos los tenants.
- `restore_tenant.py` — restauración desde backup.

```bash
docker compose exec web python manage.py backup_tenant <schema_name> --output-dir /backups
docker compose exec web python manage.py backup_all_tenants --output-dir /backups
docker compose exec web python manage.py restore_tenant <schema_name> --input <archivo>
```

## Estado real (Fase 16-17) — BLOCKER activo

**`BAK-02-restore-tested` = BLOCKER** (confirmado por
`manage.py production_readiness`). Los comandos existen y su código fue
leído y confirmado coherente, pero **no hay evidencia documentada de
una restauración end-to-end ejecutada y verificada** en esta sesión ni
en el historial de `MEMORY.md` revisado.

## Procedimiento de prueba de restauración (a ejecutar para cerrar el blocker)

```
1. backup_tenant de un tenant QA de prueba (ej. qa_verify_20260831090942,
   ya existente de la misión de onboarding E2E — identificable, no
   productivo)
       ↓
2. Modificar deliberadamente un dato conocido en ese tenant (ej. razon_social)
       ↓
3. restore_tenant desde el backup del paso 1 (a un schema DISTINTO para
   no destruir el original mientras se verifica, o documentar que se
   sobrescribe el mismo)
       ↓
4. Verificar: el dato modificado en el paso 2 vuelve al valor original
   del backup
       ↓
5. Verificar: Client/Domain/TenantMembership/Empresa/TenantProfile
   siguen coherentes tras la restauración
       ↓
6. Medir tiempo total (RTO) y punto de datos perdidos si el backup no
   era el más reciente (RPO)
       ↓
7. Documentar el resultado aquí, con evidencia (timestamps, comandos
   ejecutados, verificación de datos) — reemplaza este blocker por PASS
   solo con esa evidencia, nunca por inferencia
```

**No se ejecutó este drill en esta pasada** — requiere una ventana
dedicada (crear backup real, modificar datos, restaurar, verificar) que
excede el alcance de "auditar y construir el marco de verificación" de
esta misión. Queda como el blocker `BAK-02` explícito en
`PRODUCTION_BLOCKERS.md`.

## Retención, cifrado, ubicación (Fase 16) — sin definir, requiere decisión de negocio

No se encontró política de retención/cifrado/ubicación externa para
backups en la documentación existente. **No se inventa una política**
sin evidencia del negocio — se marca como pendiente de decisión, no se
asume un valor arbitrario (ej. "30 días", "AES-256") sin que alguien lo
haya decidido.
