FROM nginx:alpine

# Generar certificado autofirmado para desarrollo local
RUN apk add --no-cache openssl && \
    mkdir -p /etc/nginx/certs && \
    openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
      -keyout /etc/nginx/certs/sintel.key \
      -out /etc/nginx/certs/sintel.crt \
      -subj "/CN=*.sintel.com/O=Sintel/C=CO" \
      -addext "subjectAltName=DNS:localhost,IP:127.0.0.1,IP:192.168.2.15,DNS:sintel.com,DNS:*.sintel.com"

COPY nginx.conf /etc/nginx/conf.d/default.conf
