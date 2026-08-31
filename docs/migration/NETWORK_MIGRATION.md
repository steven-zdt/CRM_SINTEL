# NETWORK_MIGRATION — Fases 19, 20

## Redes Docker (Fase 19)

`crm_sintel_default` (bridge, local) -- única red del proyecto,
generada automáticamente por Docker Compose a partir del `name:
crm_sintel` en `docker-compose.yaml`. Todos los servicios (`web`,
`nginx`, `celery`, `db`, `redis`, `neo4j`, `cloudflared`) la comparten;
sin redes adicionales declaradas.

Nombres de servicio (DNS interno de Docker, usados por contrato en
código): `db`, `redis`, `web`, `nginx`, `neo4j`. Confirmado en uso real
-- `DATABASE_HOST=db`, `REDIS_URL=redis://redis:6379/0`,
`NEO4J_URI=bolt://neo4j:7687`, `nginx.conf: set $upstream
http://web:8000`. **Estos nombres deben preservarse literalmente en el
TARGET** -- están hardcodeados en la configuración de aplicación, no
son solo nombres de contenedor cosméticos.

## Nginx (Fase 20)

`nginx/nginx.conf` -- 2 bloques `server`: `listen 80` (entrada
principal, recibe tráfico de Cloudflare Tunnel y LAN sin cert
instalado) y `listen 443 ssl` (acceso directo con el cert
autofirmado). Ambos con `server_name _` (catch-all, correcto para
resolución multi-tenant por `Host` header -- el nombre del servidor no
decide el tenant, el `Host` header sí, vía `TenantMainMiddleware`).

`proxy_set_header Host $host` en ambos bloques -- preserva el hostname
real hacia Django (verificado en vivo en la misión LAN previa).

**Nginx incorpora su configuración en la imagen** (no hay volumen
montado para `nginx.conf` en este `docker-compose.yaml`) -- cualquier
cambio a `nginx/nginx.conf` requiere `docker compose build nginx` +
redeploy, no un simple restart. Esto aplica igual en SOURCE y TARGET.

`/static/` y `/media/` servidos directamente por Nginx desde
`/app/staticfiles`/`/app/media` (alias, no proxy_pass). Confirmado en
`docker-compose.yaml`: `nginx` monta explícitamente
`./staticfiles:/app/staticfiles:ro` y `./media:/app/media:ro` (mismos
paths del host que `web`/`celery` vía `.:/app`, pero como bind-mounts
propios y de solo lectura) -- deben preservarse ambos mounts en el
TARGET, no solo el de `web`.

`nginx` espera correctamente a `web: condition: service_healthy`
(no solo a que el contenedor arranque) -- fix real ya aplicado en este
repo (comentario `DEVOPS-M4` en `docker-compose.yaml`, evita el 502
transitorio que este mismo servidor mostró más de una vez durante
reinicios en sesiones previas de esta jornada). Preservar este
`depends_on` en el TARGET.
