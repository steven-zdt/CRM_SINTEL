# VOLUME_MAP — Fase 18

Levantamiento real, 2026-08-31 (`docker system df -v`, `docker volume ls`).

| Volumen | Contenedor(es) | Path en contenedor | Tamaño | Clasificación |
|---|---|---|---|---|
| `crm_sintel_postgres_data` | `db` | `/var/lib/postgresql/data` | 173.9 MB | **CRITICAL_DATA** |
| `crm_sintel_neo4j_data` | `neo4j` | (interno neo4j) | 543.5 MB | **CRITICAL_DATA** (biblioteca tributaria/impuestos) |
| `crm_sintel_nginx_certs` | `nginx` | `/etc/nginx/certs` | 3 kB | **CRITICAL_DATA** (certificado + clave privada -- ver `TLS_MIGRATION.md`) |
| (2 volúmenes anónimos con nombre-hash) | referenciados, 1 link cada uno | -- | 7.3 kB / 5.7 MB | **RECREATABLE** -- sin nombre declarado en `docker-compose.yaml`, no forman parte del contrato de datos oficial; no se migran deliberadamente |

## No son volúmenes Docker (bind-mounts directos al host)

`media/` (281 MB, 165 archivos) y `staticfiles/` (18 MB) -- montados
vía `.:/app` (bind-mount de todo el repo). Viven directamente en
`C:\Users\steve\OneDrive\Documents\crm_sintel\` y ya están
sincronizados por OneDrive. Ver `MEDIA_MIGRATION.md`.

## GENERATED / CACHE (no se copian)

`staticfiles/` es 100% regenerable vía `collectstatic` (ya corre
automáticamente en cada arranque del contenedor `web`, ver
`Dockerfile` líneas 39-47) -- no se trata como fuente de verdad, solo
`nginx/nginx.conf` + los archivos fuente `apps/**/static/` lo son
(Fase 17).

`Build cache usage: 6.59GB` (`docker system df -v`) -- cache de build
de Docker, 100% recreatable, no se migra.

## Estrategia de migración por volumen

| Volumen | Estrategia |
|---|---|
| `crm_sintel_postgres_data` | **No copiar el volumen crudo** -- usar `pg_dump`/`pg_restore` lógico (ya verificado end-to-end, `BAK-02`). Un volumen crudo copiado entre hosts con arquitecturas/versiones de Postgres distintas es frágil; el dump lógico es portable y ya tiene un drill real exitoso. |
| `crm_sintel_neo4j_data` | Backup nativo de Neo4j (`neo4j-admin dump`) recomendado sobre copia cruda de volumen -- **no ejecutado en esta pasada** (fuera del alcance verificado por `BAK-02`, que solo cubrió Postgres); ver `MIGRATION_RELEASE_GATE.md` para este punto abierto. |
| `crm_sintel_nginx_certs` | Copiar el `.crt` (público) sin problema; el `.key` (privado) solo por canal seguro, nunca a este repo ni a chat -- mismo canal recomendado que `.env` en `SECRETS_MATRIX.md`. |
| `media/`/`staticfiles/` | Copia de archivos + manifiesto de checksums ya generado (`MEDIA_MIGRATION.md`) -- no requiere mecanismo de "volumen Docker", es una copia de archivos normal. |
