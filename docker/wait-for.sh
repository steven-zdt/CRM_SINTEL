#!/bin/bash
# docker/wait-for.sh — helper de espera reusable para el contenedor unico de
# desarrollo (Postgres/Redis/Nginx/Django/Celery/Celery-beat/Neo4j/n8n/
# cloudflared todos en el mismo namespace de red via supervisord).
#
# Generaliza las funciones wait_for_db/wait_for_redis que ya existian en
# entrypoint.sh (arquitectura multi-contenedor, con depends_on: condition:
# service_healthy) -- dentro de un unico contenedor ese mecanismo de Compose
# no existe, cada programa dependiente debe esperar activamente a los
# programas de los que depende antes de arrancar de verdad.
#
# Uso: docker/wait-for.sh <tcp|postgres> <host> <puerto> [intentos] [-- comando...]
set -e

MODE="$1"; shift
HOST="$1"; shift
PORT="$1"; shift

# INTENTOS es opcional -- solo consumirlo si el siguiente argumento es
# realmente un numero. Sin este chequeo, una llamada sin INTENTOS explicito
# (ej. "wait-for.sh tcp localhost 6379 -- celery ...") hacia que INTENTOS
# se tragara el separador "--" literal, y `seq 1 "--"` fallaba con
# "invalid floating point argument" (confirmado en vivo: los 4 programas de
# supervisord que usan este patron -- celery, celery-beat, n8n, cloudflared
# -- entraban en FATAL de inmediato).
INTENTOS=60
case "$1" in
    ''|*[!0-9]*) ;;
    *) INTENTOS="$1"; shift ;;
esac

if [ "$1" = "--" ]; then shift; fi

wait_tcp() {
    for i in $(seq 1 "$INTENTOS"); do
        if nc -z -w 3 "$HOST" "$PORT" 2>/dev/null; then
            echo "wait-for: $HOST:$PORT disponible."
            return 0
        fi
        echo "wait-for: $HOST:$PORT no disponible, esperando... (intento $i/$INTENTOS)"
        sleep 2
    done
    echo "wait-for: ERROR -- $HOST:$PORT no disponible tras $INTENTOS intentos."
    exit 1
}

wait_postgres() {
    for i in $(seq 1 "$INTENTOS"); do
        if PGPASSWORD="${DATABASE_PASSWORD:?DATABASE_PASSWORD debe estar definido}" \
           psql -h "$HOST" -p "$PORT" -U "${DATABASE_USER:-sintel}" -d "${DATABASE_NAME:-sintel}" \
           -c "SELECT 1;" >/dev/null 2>&1; then
            echo "wait-for: Postgres ($HOST:$PORT) disponible."
            return 0
        fi
        echo "wait-for: Postgres ($HOST:$PORT) no disponible, esperando... (intento $i/$INTENTOS)"
        sleep 2
    done
    echo "wait-for: ERROR -- Postgres ($HOST:$PORT) no disponible tras $INTENTOS intentos."
    exit 1
}

case "$MODE" in
    tcp)      wait_tcp ;;
    postgres) wait_postgres ;;
    *) echo "wait-for: modo desconocido '$MODE' (usar tcp|postgres)"; exit 2 ;;
esac

if [ "$#" -gt 0 ]; then
    exec "$@"
fi
