#!/bin/bash
# docker/start-neo4j.sh -- arranca Neo4j (paquete Debian oficial, no la
# imagen Docker oficial) dentro del contenedor unico. Volumen `neo4j_data`
# montado en /var/lib/neo4j/data -- mismo path que usaba la imagen anterior
# via su propio volumen, para reusar los datos existentes sin migrar.
set -e

NEO4J_CONF="/etc/neo4j/neo4j.conf"
DATA_DIR="/var/lib/neo4j/data"
PASSWORD="${NEO4J_PASSWORD:?NEO4J_PASSWORD debe estar definido}"

# Config real (equivalente a los NEO4J_server_memory_* que pasaba
# docker-compose.yaml a la imagen oficial via env vars).
grep -q "^server.default_listen_address" "$NEO4J_CONF" 2>/dev/null || \
    echo "server.default_listen_address=0.0.0.0" >> "$NEO4J_CONF"
grep -q "^server.memory.pagecache.size" "$NEO4J_CONF" 2>/dev/null || \
    echo "server.memory.pagecache.size=256m" >> "$NEO4J_CONF"
grep -q "^server.memory.heap.max_size" "$NEO4J_CONF" 2>/dev/null || \
    echo "server.memory.heap.max_size=512m" >> "$NEO4J_CONF"

if [ ! -d "$DATA_DIR/databases" ]; then
    echo "neo4j: primer arranque -- fijando password inicial..."
    neo4j-admin dbms set-initial-password "$PASSWORD" || true
fi

exec neo4j console
