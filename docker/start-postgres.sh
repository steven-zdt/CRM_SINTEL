#!/bin/bash
# docker/start-postgres.sh -- inicializa PGDATA en el primer arranque
# (mismo comportamiento que la imagen oficial de postgres/pgvector, pero
# escrito a mano porque aqui Postgres es un proceso mas de supervisord, no
# la imagen base del contenedor). PGDATA apunta a la MISMA ruta que usaba
# el servicio `db` separado (/var/lib/postgresql/data) para que el named
# volume `postgres_data` existente se reconozca tal cual, sin migrar datos.
set -e

PG_BIN="/usr/lib/postgresql/16/bin"
PGDATA="${PGDATA:-/var/lib/postgresql/data}"
DB_USER="${DATABASE_USER:-sintel}"
DB_NAME="${DATABASE_NAME:-sintel}"
DB_PASSWORD="${DATABASE_PASSWORD:?DATABASE_PASSWORD debe estar definido}"

if [ ! -s "$PGDATA/PG_VERSION" ]; then
    echo "postgres: PGDATA vacio -- inicializando ($PGDATA)..."
    "$PG_BIN/initdb" -D "$PGDATA" -U postgres --auth=trust --auth-host=md5 >/tmp/initdb.log 2>&1

    echo "host all all 0.0.0.0/0 md5" >> "$PGDATA/pg_hba.conf"
    echo "host all all ::/0 md5"      >> "$PGDATA/pg_hba.conf"
    echo "listen_addresses = '*'"     >> "$PGDATA/postgresql.conf"

    "$PG_BIN/pg_ctl" -D "$PGDATA" -l /tmp/pg_bootstrap.log -w start

    "$PG_BIN/psql" -U postgres -c "CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASSWORD}' SUPERUSER;"
    "$PG_BIN/psql" -U postgres -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

    # n8n usa su propia base/rol dentro del MISMO servidor Postgres, aislada
    # a nivel de rol (N8N-SINTEL-02: CONNECT revocado sobre la BD de sintel).
    if [ -n "$N8N_DB_USER" ]; then
        "$PG_BIN/psql" -U postgres -c "CREATE ROLE ${N8N_DB_USER} LOGIN PASSWORD '${N8N_DB_PASSWORD}';"
        "$PG_BIN/psql" -U postgres -c "CREATE DATABASE ${N8N_DB_NAME:-n8n} OWNER ${N8N_DB_USER};"
        "$PG_BIN/psql" -U postgres -c "REVOKE CONNECT ON DATABASE ${DB_NAME} FROM ${N8N_DB_USER};"
    fi

    "$PG_BIN/psql" -U postgres -d "${DB_NAME}" -c "CREATE EXTENSION IF NOT EXISTS vector;"

    "$PG_BIN/pg_ctl" -D "$PGDATA" -m fast -w stop
    echo "postgres: inicializacion completa."
else
    echo "postgres: PGDATA existente detectado ($PGDATA) -- arrancando sin reinicializar."
fi

exec "$PG_BIN/postgres" -D "$PGDATA"
