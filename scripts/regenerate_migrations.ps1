# Script PowerShell para regenerar migraciones después de ejecutar fix_migrations.py
# 
# ⚠️ CRÍTICO: Este script DEBE ejecutarse en el orden exacto especificado
# para evitar errores de dependencias.

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "REGENERACION DE MIGRACIONES" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar que estamos en el directorio correcto
if (-not (Test-Path "manage.py")) {
    Write-Host "ERROR: No se encontro manage.py en el directorio actual." -ForegroundColor Red
    Write-Host "   Ejecuta este script desde la raiz del proyecto." -ForegroundColor Red
    exit 1
}

Write-Host "Paso 1/4: Creando migraciones para accounts (CRITICO - debe ser primero)..." -ForegroundColor Yellow
python manage.py makemigrations accounts
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Fallo al crear migraciones de accounts" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Migraciones de accounts creadas" -ForegroundColor Green
Write-Host ""

Write-Host "Paso 2/4: Creando migraciones para tenants (puede depender de accounts)..." -ForegroundColor Yellow
python manage.py makemigrations tenants
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Fallo al crear migraciones de tenants" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Migraciones de tenants creadas" -ForegroundColor Green
Write-Host ""

Write-Host "Paso 3/4: Creando migraciones para el resto de apps..." -ForegroundColor Yellow
python manage.py makemigrations
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Fallo al crear migraciones del resto de apps" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Migraciones del resto de apps creadas" -ForegroundColor Green
Write-Host ""

Write-Host "Paso 4/4: Aplicando migraciones al esquema public (shared)..." -ForegroundColor Yellow
python manage.py migrate_schemas --shared
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Fallo al aplicar migraciones al esquema public" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Migraciones aplicadas al esquema public" -ForegroundColor Green
Write-Host ""

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "REGENERACION COMPLETADA" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "✅ Todas las migraciones han sido regeneradas y aplicadas correctamente." -ForegroundColor Green
Write-Host ""
