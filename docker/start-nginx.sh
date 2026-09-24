#!/bin/bash
# docker/start-nginx.sh -- genera el certificado self-signed (si no existe,
# mismo comportamiento que nginx/docker-entrypoint.sh original) y arranca
# nginx. CERT_DIR sigue siendo /etc/nginx/certs -- mismo path que montaba
# el volumen `nginx_certs` en el servicio nginx separado.
set -e

/app/docker/wait-for.sh tcp localhost 8000

CERT_DIR=/etc/nginx/certs
KEY="$CERT_DIR/sintel.key"
CRT="$CERT_DIR/sintel.crt"

mkdir -p "$CERT_DIR"

if [ ! -f "$KEY" ] || [ ! -f "$CRT" ]; then
    echo "nginx: generando certificado SSL wildcard..."
    openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
        -keyout "$KEY" -out "$CRT" \
        -subj "/CN=*.sintel.net.co/O=Sintel/C=CO" \
        -addext "subjectAltName=DNS:localhost,IP:127.0.0.1,IP:192.168.2.15,DNS:sintel.net.co,DNS:*.sintel.net.co"
    echo "nginx: certificado generado."
else
    echo "nginx: reutilizando certificado existente."
fi

exec nginx -g "daemon off;"
