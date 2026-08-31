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

## Estado real (Fase 16-17) — `BAK-02-restore-tested` = **PASS**

Drill end-to-end ejecutado y verificado el 2026-08-31 (ver evidencia
completa abajo). Reemplaza el `BLOCKER` anterior, con evidencia real —
no por inferencia.

### Hallazgo critico encontrado y corregido durante el drill

El PRIMER intento de restauración falló:

```
pg_restore: error: could not execute query: ERROR:  unrecognized configuration parameter "transaction_timeout"
Command was: SET transaction_timeout = 0;
```

Causa raíz: la imagen `web` (`FROM python:3.12-slim`, Debian 13
"trixie") instalaba `postgresql-client` sin fijar versión, y el repo
default de trixie solo empaqueta el cliente v17. El servicio `db` corre
`postgres:16-alpine` (servidor v16). `pg_restore` v17 antepone
`SET transaction_timeout = 0;` (GUC introducido en PG17) a cualquier
restauración, y un servidor v16 lo rechaza. **Esto significa que
CUALQUIER restauración real habría fallado en este entorno desde que la
imagen se reconstruyó sobre Debian trixie** — exactamente la razón por
la que nunca había evidencia de un restore exitoso.

Fix aplicado (`Dockerfile`): se agregó el repositorio oficial PGDG
(`apt.postgresql.org`, distribución `trixie-pgdg`) y se fijó
`postgresql-client-16` explícitamente, para que el cliente coincida con
la versión real del servidor. Imagen reconstruida
(`docker compose build web`), contenedor recreado, verificado
`pg_restore --version` → `16.15 (Debian 16.15-1.pgdg13+2)`.

### Evidencia del drill (post-fix, tenant QA desechable `bak_drill_20260831120616`)

```
1. Tenant QA creado vía crear_tenant_con_owner() (desechable, no productivo,
   eliminado al final del drill)
2. Empresa.razon_social = "BAK Drill Test" (estado limpio conocido)
3. backup_tenant bak_drill_20260831120616 --output-dir /tmp/bak_drill
   -> bak_drill_20260831120616_20260831_121532.dump (1.23 MB) -- 8.4s
4. Empresa.razon_social corrompido deliberadamente ->
   "DATO CORRUPTO PARA PRUEBA DE RESTORE V3"
5. restore_tenant <dump> --schema-name bak_drill_20260831120616 --clean
   -> "OK: Restauración completada exitosamente" (exit 0, sin warnings)
   -- RTO medido: 16.86s
6. Verificado post-restore:
   - Empresa.razon_social == "BAK Drill Test" (revertido correctamente)
   - Client.is_active == True, Domain coincide, TenantMembership.count() == 1
   - TenantProfile.count() == 1, owner User sigue existiendo
7. Tenant QA eliminado (hard_delete_tenant) tras verificar -- limpieza,
   no queda residuo en la base de datos
```

### Alcance real de `backup_tenant`/`restore_tenant` (documentado, no asumido)

Ambos comandos operan **únicamente sobre el schema Postgres del tenant**
(`--schema=<schema_name>` en `pg_dump`/`pg_restore`). `Client`, `Domain`
y `TenantMembership` viven en el **schema `public`** y NO son
respaldados ni restaurados por estos comandos — el backup del schema
`public` (cuenta de usuarios, registro de tenants) requeriría un
mecanismo separado, no existente hoy. Esto no invalida el `PASS` de
`BAK-02` (el drill prueba exactamente lo que el comando promete: el
schema del tenant), pero es una limitación real a tener en cuenta para
un plan de DR completo — no se infla el alcance del blocker cerrado.

### RTO/RPO medidos

- **RTO** (tiempo de restauración de un tenant individual): ~17s para un
  schema de ~1.2 MB recién migrado (sin datos operativos reales). No es
  extrapolable linealmente a un tenant productivo con años de datos —
  requiere una medición dedicada contra un volumen representativo antes
  de comprometerse a un SLA de RTO real.
- **RPO**: determinado por la frecuencia de `backup_tenant`/
  `backup_all_tenants` programada — **no hay `celery beat` en ningún
  entorno de este proyecto** (`INFRA-02`, ya documentado), por lo que hoy
  no hay backups automáticos recurrentes; el RPO real es "desde el
  último backup manual", indefinido hasta que se programe.

### Procedimiento (referencia, ya ejecutado arriba)

```
1. backup_tenant de un tenant QA desechable
2. Modificar deliberadamente un dato conocido
3. restore_tenant --clean (mismo schema -- el comando no soporta
   restaurar bajo un nombre de schema distinto al que quedó grabado en
   el dump, confirmado leyendo restore_tenant.py: --schema-name solo
   filtra/etiqueta, no renombra el destino)
4. Verificar que el dato vuelve al valor del backup
5. Verificar Client/Domain/TenantMembership/Empresa/TenantProfile
6. Medir RTO/RPO
7. Documentar con evidencia real (hecho arriba)
```

## Retención, cifrado, ubicación (Fase 16) — sin definir, requiere decisión de negocio

No se encontró política de retención/cifrado/ubicación externa para
backups en la documentación existente. **No se inventa una política**
sin evidencia del negocio — se marca como pendiente de decisión, no se
asume un valor arbitrario (ej. "30 días", "AES-256") sin que alguien lo
haya decidido.
