# Script de Hard Reset y Reconstrucción de Base de Datos para SINTEL v2.9 (PowerShell)
# Este script regenera migraciones y reconstruye la base de datos desde cero

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "🚀 Hard Reset y Reconstrucción de Base de Datos SINTEL v2.9" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Función para imprimir mensajes
function Print-Step {
    param([string]$Message)
    Write-Host "▶ $Message" -ForegroundColor Green
}

function Print-Warning {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
}

function Print-Error {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

# ============================================================
# TAREA 1: Limpieza Preventiva
# ============================================================
Print-Step "Tarea 1: Limpieza Preventiva"

# Limpiar archivos Python compilados
Print-Step "Limpiando archivos .pyc y __pycache__..."
Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path . -Recurse -Filter "*.pyc" | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path . -Recurse -Filter "*.pyo" | Remove-Item -Force -ErrorAction SilentlyContinue

# Limpiar archivos de migración (excepto __init__.py)
Print-Step "Limpiando archivos de migración (excepto __init__.py)..."
Get-ChildItem -Path . -Recurse -Filter "*.py" | Where-Object {
    $_.FullName -match "\\migrations\\.*\.py$" -and $_.Name -ne "__init__.py"
} | Remove-Item -Force -ErrorAction SilentlyContinue

Get-ChildItem -Path . -Recurse -Filter "*.pyc" | Where-Object {
    $_.FullName -match "\\migrations\\"
} | Remove-Item -Force -ErrorAction SilentlyContinue

# Verificar que solo queden __init__.py en migrations
Print-Step "Verificando estructura de migrations..."
$migrationDirs = Get-ChildItem -Path . -Recurse -Directory -Filter "migrations" | Where-Object {
    $_.FullName -match "(apps\\public|apps\\tenant)"
}

foreach ($dir in $migrationDirs) {
    $initFile = Join-Path $dir.FullName "__init__.py"
    if (-not (Test-Path $initFile)) {
        New-Item -Path $initFile -ItemType File -Force | Out-Null
        Write-Host "  ✓ Creado $($dir.FullName)\__init__.py" -ForegroundColor Gray
    }
}

Write-Host "✅ Limpieza completada" -ForegroundColor Green
Write-Host ""

# ============================================================
# TAREA 2: Generación de Migraciones
# ============================================================
Print-Step "Tarea 2: Generación de Migraciones"

# Prioridad 1: Modelo de Usuario Personalizado (accounts)
Print-Step "Generando migraciones para accounts (Prioridad 1)..."
try {
    python manage.py makemigrations accounts
    if ($LASTEXITCODE -ne 0) {
        Print-Error "Error al generar migraciones para accounts"
        exit 1
    }
} catch {
    Print-Error "Error al generar migraciones para accounts: $_"
    exit 1
}

# Prioridad 2: Modelo de Tenant (tenants)
Print-Step "Generando migraciones para tenants (Prioridad 2)..."
try {
    python manage.py makemigrations tenants
    if ($LASTEXITCODE -ne 0) {
        Print-Error "Error al generar migraciones para tenants"
        exit 1
    }
} catch {
    Print-Error "Error al generar migraciones para tenants: $_"
    exit 1
}

# Resto de las apps
Print-Step "Generando migraciones para el resto de las apps..."
try {
    python manage.py makemigrations
    if ($LASTEXITCODE -ne 0) {
        Print-Warning "Algunas apps pueden no tener modelos (esto es normal)"
    }
} catch {
    Print-Warning "Algunas apps pueden no tener modelos (esto es normal)"
}

Write-Host "✅ Generación de migraciones completada" -ForegroundColor Green
Write-Host ""

# ============================================================
# TAREA 3: Aplicación de Migraciones
# ============================================================
Print-Step "Tarea 3: Aplicación de Migraciones"

# Ejecutar migraciones del esquema public (shared)
Print-Step "Ejecutando migraciones del esquema public (shared)..."
try {
    python manage.py migrate_schemas --shared
    if ($LASTEXITCODE -ne 0) {
        Print-Error "Error al ejecutar migraciones del esquema public"
        exit 1
    }
} catch {
    Print-Error "Error al ejecutar migraciones del esquema public: $_"
    exit 1
}

Write-Host "✅ Migraciones aplicadas" -ForegroundColor Green
Write-Host ""

# ============================================================
# TAREA 4: Bootstrap del Sistema
# ============================================================
Print-Step "Tarea 4: Bootstrap del Sistema"

# Crear el tenant público
Print-Step "Creando tenant público..."
try {
    python manage.py setup_public_tenant
    if ($LASTEXITCODE -ne 0) {
        Print-Error "Error al crear tenant público"
        exit 1
    }
} catch {
    Print-Error "Error al crear tenant público: $_"
    exit 1
}

# Crear superusuario por defecto (si no existe)
Print-Step "Verificando superusuario por defecto..."
$superuserScript = @"
from django.contrib.auth import get_user_model
User = get_user_model()

# Verificar si existe el usuario admin
if not User.objects.filter(email='admin@admin.com').exists():
    User.objects.create_superuser(
        email='admin@admin.com',
        password='admin',
        username='admin'
    )
    print('✅ Superusuario creado: admin@admin.com / admin')
else:
    print('ℹ️  Superusuario ya existe: admin@admin.com')
"@

$superuserScript | python manage.py shell
if ($LASTEXITCODE -ne 0) {
    Print-Warning "No se pudo crear/verificar superusuario (puede que ya exista)"
}

Write-Host "✅ Bootstrap del sistema completado" -ForegroundColor Green
Write-Host ""

# ============================================================
# TAREA 5: Verificación Final
# ============================================================
Print-Step "Tarea 5: Verificación Final"

# Verificar que los modelos estén correctos
Print-Step "Verificando estructura de modelos..."
$verificationScript = @"
from apps.public.tenants.models import Client, Domain, TenantMembership
from django.contrib.auth import get_user_model
User = get_user_model()

# Verificar tenant público
public_tenant = Client.objects.filter(schema_name='public').first()
if public_tenant:
    print(f'✅ Tenant público existe: {public_tenant.nombre} (schema: {public_tenant.schema_name})')
    domains = Domain.objects.filter(tenant=public_tenant)
    print(f'✅ Dominios del tenant público: {domains.count()}')
    for d in domains:
        print(f'   - {d.domain} (principal: {d.is_primary})')
else:
    print('❌ Tenant público NO existe')
    exit(1)

# Verificar superusuario
admin = User.objects.filter(email='admin@admin.com').first()
if admin:
    print(f'✅ Superusuario existe: {admin.email}')
else:
    print('❌ Superusuario NO existe')
    exit(1)
"@

$verificationScript | python manage.py shell
if ($LASTEXITCODE -ne 0) {
    Print-Error "Error en verificación de modelos"
    exit 1
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "✅ Hard Reset y Reconstrucción Completados Exitosamente" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 Próximos pasos:" -ForegroundColor Yellow
Write-Host "   1. Ejecutar tests CRUD: pytest tests/public/tenants/test_crud_full.py -v"
Write-Host "   2. Ejecutar tests de UI: pytest tests/public/console/test_tenant_ui_flow.py -v"
Write-Host "   3. Verificar que el sistema funciona: python manage.py runserver"
Write-Host ""
