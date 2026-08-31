# IMAGE_MANIFEST — Fases 2, 5, 6, 7

Levantamiento real, 2026-08-31.

## Imágenes en uso

| Repository | Tag | Image ID | Digest | Tamaño | Origen | Reconstruible |
|---|---|---|---|---|---|---|
| `crm_sintel-web` | `latest` | `ffe34c810237` | `sha256:ffe34c8102370d3259293a1b28cc5107c76417d3ed7f3bfbdcf9f2d1b696d785` | 1.22 GB | build local (`Dockerfile`) | Sí -- `docker compose build web` |
| `crm_sintel-celery` | `latest` | `3c0dbfd190eb` | `sha256:3c0dbfd190eb867a44e1e5f8699ccae3a86fbc3a31ed4a0fd54d2616ca113a31` | 1.22 GB | build local (mismo `Dockerfile`, ancla `x-app-base`) | Sí |
| `crm_sintel-nginx` | `latest` | `0233dd7a3252` | `sha256:0233dd7a3252e941abd02e1a7a72add15c2a58eb0ab167a47483523f6186a87f` | 94.8 MB | build local (`nginx/Dockerfile` o equivalente) | Sí |
| `postgres` | `16-alpine` | `57c72fd2a128` | `sha256:57c72fd2a128e416c7fcc499958864df5301e940bca0a56f58fddf30ffc07777` | 420 MB | registry oficial (Docker Hub) | Pull directo |
| `redis` | `7.2-alpine` | `05a97a479bc7` | `sha256:05a97a479bc73de66f087dc05b569010772880f778cc8671fa6b8aadee32e5c6` | 56.9 MB | registry oficial | Pull directo |
| `neo4j` | `5.24-community` | `2e7e4eea5bc1` | `sha256:2e7e4eea5bc1eec581a3097c018dfeb3747f3638e67a963c10554825c31c1425` | 847 MB | registry oficial | Pull directo |
| `cloudflare/cloudflared` | `2025.5.0` | `f9d5c5b94cd7` | `sha256:f9d5c5b94cd7337c0c939a6dbf5537db34030828c243fca6b589fd85ab25d43b` | 91.2 MB | registry oficial | Pull directo |

## Reproducibilidad (Fase 6)

Confirmado, todos presentes en el repo:

- `Dockerfile` (raíz) -- imagen `web`/`celery` (mismo `Dockerfile`,
  ancla `x-app-base` en `docker-compose.yaml`). **Contiene el fix real
  de esta sesión**: `postgresql-client-16` fijado vía repo oficial
  PGDG (ver `docs/production/BACKUP_RESTORE_RUNBOOK.md`) -- sin este
  fix, cualquier TARGET reconstruido desde este `Dockerfile` habría
  heredado el mismo bug de incompatibilidad `pg_dump`/`pg_restore` ya
  cerrado aquí. El TARGET debe construirse desde el `Dockerfile`
  ACTUAL (post-fix), nunca desde una imagen `crm_sintel-web` antigua
  cacheada de antes del fix.
- `requirements.txt` -- dependencias Python, versiones exactas (ver
  `DEPENDENCIES` abajo).
- `nginx/nginx.conf` -- fuente de la imagen `nginx`, incorporado en
  build (cambios requieren rebuild, no hot-reload).
- `entrypoint.sh`, `entrypoint-celery.sh` -- scripts de arranque.
- Sin `package.json`/pipeline Node -- **confirmado, no se crea uno
  para esta migración**: el frontend carga librerías vía CDN
  (Bootstrap, HTMX, Font Awesome), consistente con
  `CLAUDE.md` ("No build step").

## Dependencias Python (Fase 26)

```
Python 3.12 (base imagen: python:3.12-slim, Debian 13 "trixie")
Django 5.0.14
psycopg2 / django-tenants (ver requirements.txt para version pins exactos)
```

Ver `requirements.txt` (raíz del repo) para el listado completo con
versiones exactas -- no se duplica aquí para evitar que este documento
quede desactualizado respecto a la fuente real.

## Objetivo de reproducibilidad (Fase 7)

`postgres`/`redis`/`neo4j`/`cloudflared`: pull idéntico por tag+digest
en el TARGET -- sin ambigüedad, ya fijados a versiones exactas en
`docker-compose.yaml`.

`web`/`celery`/`nginx`: no se copian imágenes -- se reconstruyen en el
TARGET desde el mismo código fuente (`Dockerfile`, `nginx/nginx.conf`)
al commit exacto documentado en `SOURCE_HOST_INVENTORY.md`, y se
verifican funcionalmente (Fase 27-29), no por comparación binaria de
imagen (una imagen reconstruida desde el mismo `Dockerfile` nunca
produce el mismo digest byte a byte -- timestamps, orden de capas --
la equivalencia real es funcional, no criptográfica).
