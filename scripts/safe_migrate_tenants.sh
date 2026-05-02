#!/usr/bin/env bash
# Wrapper seguro para ejecutar migraciones de tenants.
#
# Acepta variable de entorno TENANTS o primer argumento:
# - TENANTS=all (default) → ejecuta `migrate_schemas --tenant --fake-initial`
# - TENANTS=<schema_name> → ejecuta `migrate_schemas --schema=<schema_name> --fake-initial`
#
# Uso:
#   ./scripts/safe_migrate_tenants.sh
#   TENANTS=mi_empresa ./scripts/safe_migrate_tenants.sh
#   ./scripts/safe_migrate_tenants.sh mi_empresa

set -euo pipefail

# Determinar modo: usar primer argumento o variable de entorno TENANTS
TENANTS="${1:-${TENANTS:-all}}"

if [ "$TENANTS" = "all" ]; then
    echo "🏢 Aplicando migraciones a todos los tenants..."
    python manage.py migrate_schemas --tenant --fake-initial || {
        echo "❌ Error aplicando migraciones de tenants"
        exit 1
    }
    echo "✅ Migraciones de tenants aplicadas"
else
    echo "🏢 Aplicando migraciones al schema: $TENANTS ..."
    python manage.py migrate_schemas --schema="$TENANTS" --fake-initial || {
        echo "❌ Error aplicando migraciones del schema $TENANTS"
        exit 1
    }
    echo "✅ Migraciones aplicadas para $TENANTS"
fi
