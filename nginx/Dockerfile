FROM nginx:alpine

# openssl necesario para generar el cert en el entrypoint
RUN apk add --no-cache openssl

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# El cert se genera en /etc/nginx/certs/ SOLO si no existe (entrypoint).
# El directorio es un volumen Docker persistente → sobrevive rebuilds.
ENTRYPOINT ["/docker-entrypoint.sh"]
