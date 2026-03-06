# Script PowerShell para resetear el historial de migraciones y reconstruirlo
# ⚠️ SOLO PARA DESARROLLO

Write-Host "⚠️  RESETEANDO HISTORIAL DE MIGRACIONES..." -ForegroundColor Yellow
Write-Host "Esto eliminará todo el historial de migraciones de la base de datos."
Write-Host ""

# Resetear historial
Write-Host "🔄 Eliminando historial de migraciones..." -ForegroundColor Cyan
docker compose exec web python manage.py fix_migration_history --reset

# Aplicar migraciones con fake-initial para reconstruir el historial
Write-Host ""
Write-Host "📦 Aplicando migraciones con --fake-initial..." -ForegroundColor Cyan
docker compose exec web python manage.py migrate_schemas --shared --fake-initial

# Verificar estado
Write-Host ""
Write-Host "🔍 Verificando estado de migraciones..." -ForegroundColor Cyan
docker compose exec web python manage.py showmigrations

Write-Host ""
Write-Host "✅ Proceso completado!" -ForegroundColor Green
