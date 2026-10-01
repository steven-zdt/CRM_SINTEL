# Pinneado explicito (2026-09-24) -- "nginx:alpine" era un tag flotante, no
# reproducible (mismo criterio de pin que el resto de los servicios del
# proyecto: db por digest, redis/neo4j/n8n/cloudflared por version exacta).
# 1.30.5-alpine3.24 es la version estable mas reciente al momento del pin.
FROM nginx:1.30.5-alpine3.24

# openssl necesario para generar el cert en el entrypoint
RUN apk add --no-cache openssl

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# El cert se genera en /etc/nginx/certs/ SOLO si no existe (entrypoint).
# El directorio es un volumen Docker persistente → sobrevive rebuilds.
ENTRYPOINT ["/docker-entrypoint.sh"]
