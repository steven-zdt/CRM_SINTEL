# SERVER_MIGRATION_BASELINE — Fase 0

Levantamiento real ejecutado 2026-08-31. **Estado: `AUDITING`.**

## Alcance real de esta misión (decisión de scoping, explícita)

Esta misión pide preparar una migración `SOURCE → TARGET`. **No existe
un servidor TARGET real disponible** en este momento — solo esta
máquina (SOURCE). Sin un segundo servidor, las Fases 27+ (rebuild en
staging, restore en TARGET, cutover, DNS switch, post-cutover) no son
ejecutables con evidencia real; no se simulan.

Alcance ejecutado con evidencia real: Fases 0-26 (auditoría e
inventario completo de SOURCE) + Fases 14-17/52 (backups reales,
verificables, restaurables — el activo que "no se puede reconstruir",
regla #3 de la misión). Resultado: **`READY_FOR_MIGRATION`** (SOURCE
completamente auditado y respaldado), no `MIGRATION = VERIFIED` (eso
requiere un TARGET real).

## Documentación leída

`AGENTS.md`, `documentacion/arquitectura_general.md`,
`documentacion/INFRA_RED_LOCAL_MULTI_TENANT.md`,
`docs/production/*` (mission previa de esta sesión — reutilizado, no
duplicado: `BACKUP_RESTORE_RUNBOOK.md`, `DEPLOYMENT_RUNBOOK.md`,
`ROLLBACK_RUNBOOK.md` ya existen y siguen vigentes),
`docs/network/*` (mission LAN previa — IP real del servidor,
`192.168.2.17`), `Dockerfile`, `docker-compose.yaml`, `nginx/nginx.conf`.

## Arquitectura (resumen, detalle completo en cada doc dedicado)

```
Cliente
  -> DNS (sintel.net.co publico via Cloudflare; *.sintel.net.co LAN sin wildcard operativo)
  -> Nginx (Docker, 0.0.0.0:80/443, catch-all server_name _)
  -> Django/Gunicorn-dev (web, 127.0.0.1:8000 -- restringido esta sesion)
  -> TenantMainMiddleware (django-tenants) -> Domain -> schema Postgres
  -> PostgreSQL 16 (esquema public + N esquemas tenant)
  -> Redis (cache + broker Celery)
  -> Celery worker (sin beat -- ningun entorno de este proyecto lo tiene)
  -> Neo4j (biblioteca tributaria/impuestos)
  -> Cloudflare Tunnel (cloudflared, dominio publico sintel.net.co)
```

## Servicios reales (`docker compose ps`, 2026-08-31)

| Servicio | Imagen | Estado | Puertos publicados |
|---|---|---|---|
| `web` | `crm_sintel-web:latest` (build local) | healthy | `127.0.0.1:8000` |
| `nginx` | `crm_sintel-nginx:latest` (build local) | healthy | `0.0.0.0:80`, `0.0.0.0:443` |
| `celery` | `crm_sintel-celery:latest` (build local) | healthy | ninguno (interno) |
| `db` | `postgres:16-alpine` | healthy | `127.0.0.1:5432` |
| `redis` | `redis:7.2-alpine` | healthy | `127.0.0.1:6379` |
| `neo4j` | `neo4j:5.24-community` | healthy | `127.0.0.1:7474/7687` |
| `cloudflared` | `cloudflare/cloudflared:2025.5.0` | up (sin healthcheck) | ninguno |

No hay servicio `celery-beat` -- confirmado ausente en `docker-compose.yaml`
(hallazgo ya documentado en la mision de produccion previa, `INFRA-02`).

## Dependencias entre servicios

`web`/`celery` dependen de `db` y `redis` (healthy). `nginx` depende de
`web` (implícito via `proxy_pass http://web:8000`). `cloudflared`
depende de `nginx` (`depends_on: nginx: service_started`). `neo4j` es
independiente (usado por `apps/public/impuestos/search`).

## Puertos

Ver tabla de servicios arriba. `db`/`redis`/`neo4j` correctamente
acotados a `127.0.0.1` (no LAN-alcanzables) -- confirmado en la misión
de producción previa (`BAK`) y LAN previa de esta sesión.

## Volúmenes (detalle en `VOLUME_MAP.md`)

`crm_sintel_postgres_data` (173.9 MB), `crm_sintel_neo4j_data`
(543.5 MB), `crm_sintel_nginx_certs` (3 kB). `media/`/`staticfiles/`
**no son volúmenes Docker** -- bind-mount directo (`.:/app`) al
filesystem del host, ya sincronizado por OneDrive.

## Datos (detalle en `DATABASE_MIGRATION.md`)

PostgreSQL 16.14. 5 schemas reales: `public` + 4 tenants
(`home`, `qaisotest`, `qa_verify_20260831090942`, `admin`).

## Secretos (detalle en `SECRETS_MATRIX.md`)

Todos en `.env` (no versionado, confirmado `git status` limpio para
ese archivo) + `docker-compose.yaml` los inyecta como variables de
entorno de cada contenedor. Ningún secreto se imprime en este documento
ni en ningún otro de `docs/migration/`.

## Dominios (detalle en `DNS_MIGRATION.md`)

`sintel.net.co` público real (Cloudflare). `*.sintel.net.co` interno
LAN -- wildcard DNS no operativo (hallazgo ya documentado en la misión
LAN previa, sin cambios). IP real del servidor: `192.168.2.17`
(reasignada durante esta sesión tras un conflicto de IP real en `.15`).

**No se modificó infraestructura en esta fase** -- solo lectura y
registro.
