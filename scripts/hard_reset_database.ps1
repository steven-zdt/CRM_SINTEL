# ⚠️ HARD RESET DATABASE - SINTEL v2.40 (PowerShell)
# Script para limpiar completamente la base de datos y regenerar migraciones desde cero
# 
# ⚠️ ADVERTENCIA: Este script eliminará TODOS los datos de tenants y regenerará migraciones
# Solo ejecutar en desarrollo o cuando se requiera un reset completo

$ErrorActionPreference = "Stop"

Write-Host "🚨 HARD RESET DATABASE - SINTEL v2.40" -ForegroundColor Red
Write-Host "======================================" -ForegroundColor Red
Write-Host ""
Write-Host "⚠️  ADVERTENCIA: Este script eliminará:" -ForegroundColor Yellow
Write-Host "   - Todos los esquemas de tenants (excepto public e information_schema)"
Write-Host "   - Todas las tablas de Client y Domain en el esquema public"
Write-Host "   - Todos los archivos de migración (excepto __init__.py)"
Write-Host ""
$confirmacion = Read-Host "¿Estás seguro de continuar? (escribe 'SI' para confirmar)"

if ($confirmacion -ne "SI") {
    Write-Host "❌ Operación cancelada." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "📋 Paso 1: Limpiando archivos de migración..." -ForegroundColor Cyan
# Eliminar todos los archivos .py en carpetas migrations excepto __init__.py
Get-ChildItem -Path . -Recurse -Filter "*.py" | 
    Where-Object { $_.FullName -match "migrations" -and $_.Name -ne "__init__.py" } | 
    Remove-Item -Force

Get-ChildItem -Path . -Recurse -Filter "*.pyc" | 
    Where-Object { $_.FullName -match "migrations" } | 
    Remove-Item -Force

Get-ChildItem -Path . -Recurse -Directory | 
    Where-Object { $_.FullName -match "migrations.*__pycache__" } | 
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "✅ Archivos de migración eliminados" -ForegroundColor Green

Write-Host ""
Write-Host "📋 Paso 2: Limpiando base de datos PostgreSQL..." -ForegroundColor Cyan
# SQL para limpiar esquemas y tablas
$cleanupSQL = @"
-- ⚠️ CRÍTICO: Eliminar todos los esquemas de tenants (excepto public e information_schema)
DO \$\$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (SELECT schema_name FROM information_schema.schemata 
              WHERE schema_name NOT IN ('public', 'information_schema', 'pg_catalog', 'pg_toast', 'pg_temp_1', 'pg_toast_temp_1')
              AND schema_name NOT LIKE 'pg_%')
    LOOP
        EXECUTE 'DROP SCHEMA IF EXISTS ' || quote_ident(r.schema_name) || ' CASCADE';
        RAISE NOTICE 'Eliminado esquema: %', r.schema_name;
    END LOOP;
END \$\$;

-- Truncar tablas de tenants en el esquema public
TRUNCATE TABLE IF EXISTS tenants_client CASCADE;
TRUNCATE TABLE IF EXISTS tenants_domain CASCADE;

-- Verificar que las tablas estén vacías
SELECT 'Client count: ' || COUNT(*)::text FROM tenants_client;
SELECT 'Domain count: ' || COUNT(*)::text FROM tenants_domain;
"@

$cleanupSQL | docker-compose exec -T db psql -U sintel -d sintel
Write-Host "✅ Base de datos limpiada" -ForegroundColor Green

Write-Host ""
Write-Host "📋 Paso 3: Regenerando migraciones..." -ForegroundColor Cyan
docker-compose exec web python manage.py makemigrations
Write-Host "✅ Migraciones regeneradas" -ForegroundColor Green

Write-Host ""
Write-Host "📋 Paso 4: Aplicando migraciones al esquema público..." -ForegroundColor Cyan
docker-compose exec web python manage.py migrate_schemas --shared
Write-Host "✅ Migraciones del esquema público aplicadas" -ForegroundColor Green

Write-Host ""
Write-Host "📋 Paso 5: Verificando integridad de migraciones..." -ForegroundColor Cyan
docker-compose exec web python manage.py showmigrations --plan | Select-Object -First 20
Write-Host "✅ Verificación completada" -ForegroundColor Green

Write-Host ""
Write-Host "✅ HARD RESET COMPLETADO" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Próximos pasos:" -ForegroundColor Cyan
Write-Host "   1. Crear superusuario: docker-compose exec web python manage.py createsuperuser"
Write-Host "   2. Crear tenant público: docker-compose exec web python manage.py setup_public_tenant"
Write-Host "   3. Probar onboarding de un tenant desde la consola"
Write-Host ""
