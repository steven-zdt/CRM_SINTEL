# COMPOSE_EFFECTIVE_CONFIG — Fase 8

`docker compose config` (salida efectiva real, tras aplicar
`docker-compose.yaml` + `.env`), sanitizada: **todos los valores de
`environment:` se reemplazaron por `<REDACTED>`** -- se conservan los
NOMBRES de las variables (Fase 9), nunca los valores.

Archivo completo saneado: [`compose_config_sanitized.yml`](compose_config_sanitized.yml)
(324 líneas, generado 2026-08-31 con un script de sanitización
dedicado -- nunca se escribió la salida cruda de `docker compose config`
a ningún archivo de este repositorio; se procesó únicamente en un
directorio de scratch fuera del repo antes de sanitizar).

## Servicio oficial de compose

`docker-compose.yaml` (raíz del repo) -- único archivo compose real,
sin overrides (`docker-compose.override.yaml` no existe). `.env`
(no versionado) provee los valores reales de cada variable.

## Estructura real (7 servicios, ver nombres/imágenes en
`SERVER_MIGRATION_BASELINE.md`)

- `web`, `celery` comparten el ancla `x-app-base` (mismo `build`,
  mismo `env_file`, mismo bind-mount `.:/app`, mismo `depends_on`).
- `nginx`, `db`, `redis`, `neo4j`, `cloudflared` con configuración
  propia.

## Variables de entorno inyectadas por servicio (nombres, Fase 9)

`web`/`celery` reciben las mismas ~28 variables (ver
`SECRETS_MATRIX.md` para el listado completo con clasificación
sensible/no-sensible). `db` recibe solo `POSTGRES_DB`/`POSTGRES_USER`/
`POSTGRES_PASSWORD`. `cloudflared` recibe solo `TUNNEL_TOKEN`.
`nginx`/`redis`/`neo4j` no reciben variables de `.env` (su
configuración vive en archivos montados o en el propio
`docker-compose.yaml`).
