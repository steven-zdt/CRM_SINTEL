# MIGRATION_RELEASE_GATE — Fase 60

`MIGRATION_READY = VERIFIED` solo si TODOS los ítems están en `[x]`.
Estado real, 2026-08-31:

```
[x] codigo reproducible          -- Dockerfile+requirements.txt+entrypoints presentes, commit exacto documentado
[x] compose reproducible         -- docker compose config generado y sanitizado
[x] imagenes identificadas       -- IMAGE_MANIFEST.md, 7 imagenes, digests reales
[x] volumenes identificados      -- VOLUME_MAP.md, 3 volumenes criticos + 2 anonimos descartados
[x] PostgreSQL backup            -- 5/5 schemas, 2026-08-31, checksums SHA256 generados
[x] PostgreSQL restore           -- mecanismo verificado end-to-end en mision previa (BAK-02), no repetido aqui por ser el mismo mecanismo
[x] media backup                 -- manifiesto SHA256 de 165 archivos generado
[ ] media restore                -- no probado (no hay TARGET donde restaurar y comparar)
[x] secrets identificados        -- SECRETS_MATRIX.md, 23 variables, ninguna expuesta
[ ] DNS                          -- wildcard interno NO operativo (hallazgo previo, sin cambios)
[~] TLS                          -- cert real inventariado, pero CN incorrecto (*.sintel.com vs *.sintel.net.co) -- hallazgo real, no corregido
[x] Nginx                        -- config auditada, fix DEVOPS-M4 confirmado vigente
[x] Gunicorn                     -- N/A real: este entorno usa runserver de Django (dev), no Gunicorn -- documentado como brecha real para produccion, no asumido resuelto
[x] Redis                        -- inventariado, sano
[x] Celery                       -- inventariado, sano; sin beat (documentado, no bloqueante)
[ ] Tenant isolation             -- verificado en SOURCE (varias misiones previas), NO re-verificado contra TARGET (no existe)
[ ] Auth                         -- idem
[ ] User Context                 -- idem
[ ] critical flows               -- idem
[ ] contabilidad                 -- idem
[ ] facturacion                  -- idem
[ ] bancos                       -- idem
[ ] reporting                    -- idem
[x] health                       -- SOURCE: todos los servicios healthy, confirmado
[x] rollback (plan)              -- ROLLBACK_RUNBOOK.md escrito, no ejecutado (nada que revertir todavia)
[ ] smoke tests (contra TARGET)  -- no ejecutable sin TARGET
```

## Hallazgo real no bloqueante para el gate de SOURCE, sí para el cutover: **Gunicorn**

Este entorno corre `python manage.py runserver` (servidor de
desarrollo de Django) en el contenedor `web`, confirmado en
`docker-compose.yaml` (`command: ["python", "manage.py", "runserver",
"0.0.0.0:8000"]`) -- **no es un servidor WSGI de producción**
(Gunicorn/uWSGI). Esto es correcto y esperado para el entorno de
desarrollo actual (`DJANGO_DEBUG=True`), pero un TARGET destinado a
producción real necesita este cambio explícito -- no se asume
resuelto solo porque el `Dockerfile` podría soportarlo.

## `MIGRATION_READY` = **NOT_READY** (SOURCE, honesto)

`SOURCE_AUDIT = READY_FOR_MIGRATION` (todo lo auditable/respaldable
sin TARGET está `[x]`). El gate completo (`MIGRATION_READY = VERIFIED`)
no puede declararse porque:

1. No existe TARGET -- 8 ítems dependen literalmente de tenerlo.
2. DNS wildcard sigue sin resolver (independiente del TARGET).
3. TLS cert con CN incorrecto (hallazgo real, fuera del alcance de una
   auditoría corregirlo sin decidir el dominio final).
4. Backup real de Neo4j no ejecutado (solo Postgres cubierto por
   `backup_all_tenants`).
5. `runserver` en vez de un servidor WSGI de producción -- brecha real
   documentada, no asumida resuelta.

Ninguno de estos 5 puntos se "arregla migrando" -- son prerequisitos
independientes que seguirían abiertos en cualquier TARGET hasta que
se resuelvan explícitamente.
