#!/bin/sh
# Genera el certificado SSL solo si no existe en el volumen persistente.
# Esto garantiza que reconstruir la imagen nginx no invalida los certificados
# ya aceptados por los clientes de la red local.
set -e

CERT_DIR=/etc/nginx/certs
KEY="$CERT_DIR/sintel.key"
CRT="$CERT_DIR/sintel.crt"

mkdir -p "$CERT_DIR"

if [ ! -f "$KEY" ] || [ ! -f "$CRT" ]; then
    echo "[sintel-nginx] Generando certificado SSL wildcard..."
    openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
        -keyout "$KEY" -out "$CRT" \
        -subj "/CN=*.sintel.net.co/O=Sintel/C=CO" \
        -addext "subjectAltName=DNS:localhost,IP:127.0.0.1,IP:192.168.2.15,DNS:sintel.net.co,DNS:*.sintel.net.co"
    echo "[sintel-nginx] Certificado generado: $CRT"
    echo "[sintel-nginx] SHA1: $(openssl x509 -noout -fingerprint -sha1 -in $CRT 2>/dev/null | cut -d= -f2)"
else
    echo "[sintel-nginx] Reutilizando certificado existente (reconstruccion segura)."
    echo "[sintel-nginx] SHA1: $(openssl x509 -noout -fingerprint -sha1 -in $CRT 2>/dev/null | cut -d= -f2)"
    echo "[sintel-nginx] Valido hasta: $(openssl x509 -noout -enddate -in $CRT 2>/dev/null | cut -d= -f2)"
fi

exec nginx -g "daemon off;"
