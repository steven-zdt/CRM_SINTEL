#!/bin/bash
# Script para resetear el historial de migraciones y reconstruirlo
# ⚠️ SOLO PARA DESARROLLO

echo "⚠️  RESETEANDO HISTORIAL DE MIGRACIONES..."
echo "Esto eliminará todo el historial de migraciones de la base de datos."
echo ""

# Resetear historial
docker compose exec web python manage.py fix_migration_history --reset

# Aplicar migraciones con fake-initial para reconstruir el historial
echo ""
echo "📦 Aplicando migraciones con --fake-initial..."
docker compose exec web python manage.py migrate_schemas --shared --fake-initial

# Verificar estado
echo ""
echo "🔍 Verificando estado de migraciones..."
docker compose exec web python manage.py showmigrations

echo ""
echo "✅ Proceso completado!"
