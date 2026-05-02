#!/usr/bin/env bash
# wait-for-it.sh - Espera a que un servicio esté disponible
# Uso: wait-for-it.sh host:port [-- command args]
# Ejemplo: wait-for-it.sh db:5432 -- python manage.py migrate

set -e

hostport="$1"
shift
cmd="$@"

if [ -z "$hostport" ]; then
    echo "Usage: wait-for-it.sh host:port [-- command args]"
    exit 1
fi

host=$(echo $hostport | cut -d: -f1)
port=$(echo $hostport | cut -d: -f2)

echo "⏳ Esperando $host:$port..."

until nc -z "$host" "$port" 2>/dev/null; do
    echo "   Esperando $host:$port..."
    sleep 1
done

echo "✅ $host:$port está disponible"

if [ -n "$cmd" ]; then
    exec $cmd
fi
