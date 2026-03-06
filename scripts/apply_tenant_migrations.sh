#!/bin/bash
# Script para aplicar migraciones pendientes a todos los tenants
# Uso: ./scripts/apply_tenant_migrations.sh

set -e

echo "🔄 Aplicando migraciones a todos los esquemas de tenant..."

# Aplicar migraciones al esquema public (shared) primero
echo "📦 Aplicando migraciones al esquema public (shared)..."
python manage.py migrate_schemas --shared --fake-initial || {
    echo "❌ ERROR: Fallo al aplicar migraciones al esquema public"
    exit 1
}

# Aplicar migraciones a todos los tenants
echo "🏢 Aplicando migraciones a todos los esquemas de tenant..."
python manage.py migrate_schemas --tenant --fake-initial || {
    echo "❌ ERROR: Fallo al aplicar migraciones a los tenants"
    exit 1
}

echo "✅ Migraciones aplicadas correctamente"
