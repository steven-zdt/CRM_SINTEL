# Script PowerShell para aplicar migraciones pendientes a todos los tenants
# Uso: .\scripts\apply_tenant_migrations.ps1

$ErrorActionPreference = "Stop"

Write-Host "🔄 Aplicando migraciones a todos los esquemas de tenant..." -ForegroundColor Cyan

# Aplicar migraciones al esquema public (shared) primero
Write-Host "📦 Aplicando migraciones al esquema public (shared)..." -ForegroundColor Yellow
python manage.py migrate_schemas --shared --fake-initial
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ERROR: Fallo al aplicar migraciones al esquema public" -ForegroundColor Red
    exit 1
}

# Aplicar migraciones a todos los tenants
Write-Host "🏢 Aplicando migraciones a todos los esquemas de tenant..." -ForegroundColor Yellow
python manage.py migrate_schemas --tenant --fake-initial
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ERROR: Fallo al aplicar migraciones a los tenants" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Migraciones aplicadas correctamente" -ForegroundColor Green
