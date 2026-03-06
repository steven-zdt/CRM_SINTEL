#!/bin/bash
# Script helper para limpiar datos de cotizaciones en Docker
#
# Uso:
#   ./scripts/limpiar_cotizaciones.sh <schema_name> [--confirm]
#   ./scripts/limpiar_cotizaciones.sh all [--confirm]
#
# Ejemplos:
#   # Ver qué se eliminaría (simulación)
#   ./scripts/limpiar_cotizaciones.sh tenant1
#
#   # Eliminar datos de un tenant específico
#   ./scripts/limpiar_cotizaciones.sh tenant1 --confirm
#
#   # Eliminar datos de todos los tenants
#   ./scripts/limpiar_cotizaciones.sh all --confirm

set -e

SCHEMA_NAME="${1:-}"
CONFIRM="${2:-}"

if [ -z "$SCHEMA_NAME" ]; then
    echo "❌ Error: Debe especificar el nombre del schema o 'all'"
    echo ""
    echo "Uso:"
    echo "  ./scripts/limpiar_cotizaciones.sh <schema_name> [--confirm]"
    echo "  ./scripts/limpiar_cotizaciones.sh all [--confirm]"
    echo ""
    echo "Ejemplos:"
    echo "  # Simulación (ver qué se eliminaría)"
    echo "  ./scripts/limpiar_cotizaciones.sh tenant1"
    echo ""
    echo "  # Eliminar datos de un tenant"
    echo "  ./scripts/limpiar_cotizaciones.sh tenant1 --confirm"
    echo ""
    echo "  # Eliminar datos de todos los tenants"
    echo "  ./scripts/limpiar_cotizaciones.sh all --confirm"
    exit 1
fi

# Determinar el comando según el schema
if [ "$SCHEMA_NAME" = "all" ]; then
    if [ "$CONFIRM" = "--confirm" ]; then
        echo "⚠️  Eliminando datos de cotizaciones en TODOS los tenants..."
        docker compose -f infra/compose/docker-compose.yml exec -T app python manage.py all_tenants_command limpiar_cotizaciones --confirm
    else
        echo "ℹ️  Modo simulación: Mostrando qué se eliminaría en todos los tenants..."
        docker compose -f infra/compose/docker-compose.yml exec -T app python manage.py all_tenants_command limpiar_cotizaciones --dry-run
    fi
else
    if [ "$CONFIRM" = "--confirm" ]; then
        echo "⚠️  Eliminando datos de cotizaciones en tenant: $SCHEMA_NAME..."
        docker compose -f infra/compose/docker-compose.yml exec -T app python manage.py tenant_command limpiar_cotizaciones --schema="$SCHEMA_NAME" --confirm
    else
        echo "ℹ️  Modo simulación: Mostrando qué se eliminaría en tenant: $SCHEMA_NAME..."
        docker compose -f infra/compose/docker-compose.yml exec -T app python manage.py tenant_command limpiar_cotizaciones --schema="$SCHEMA_NAME" --dry-run
    fi
fi
