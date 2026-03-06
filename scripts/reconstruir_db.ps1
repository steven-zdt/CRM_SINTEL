# Script de Reconstrucción Total de Base de Datos para SINTEL (PowerShell)
# ⚠️ ADVERTENCIA: Este script elimina TODAS las migraciones y recrea la base de datos desde cero
# Uso: .\scripts\reconstruir_db.ps1

$ErrorActionPreference = "Stop"

Write-Host "🚀 Iniciando reconstrucción total de la base de datos..." -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
Write-Host ""

# PASO 1: Limpieza de Archivos de Migración
Write-Host "📁 PASO 1: Limpiando archivos de migración..." -ForegroundColor Yellow
Write-Host "--------------------------------------------" -ForegroundColor Yellow

# Buscar y eliminar todos los archivos .py en carpetas migrations/, excepto __init__.py
Get-ChildItem -Path . -Recurse -Filter "*.py" | 
    Where-Object { $_.FullName -match "\\migrations\\.*\.py$" -and $_.Name -ne "__init__.py" } | 
    Remove-Item -Force

Write-Host "✅ Archivos de migración eliminados (excepto __init__.py)" -ForegroundColor Green

# También eliminar archivos .pyc si existen
Get-ChildItem -Path . -Recurse -Filter "*.pyc" | 
    Where-Object { $_.FullName -match "\\migrations\\" } | 
    Remove-Item -Force -ErrorAction SilentlyContinue

Write-Host "✅ Archivos .pyc de migraciones eliminados" -ForegroundColor Green
Write-Host ""

# PASO 2: Recreación de Migraciones (Orden Estricto)
Write-Host "📦 PASO 2: Recreando migraciones en orden estricto..." -ForegroundColor Yellow
Write-Host "---------------------------------------------------" -ForegroundColor Yellow

# 2.1: Migraciones de accounts (Usuario global - DEBE IR PRIMERO)
Write-Host "✅ Creando migraciones de accounts (Usuario global)..." -ForegroundColor Cyan
python manage.py makemigrations accounts
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Error al crear migraciones de accounts" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Migraciones de accounts creadas" -ForegroundColor Green

# 2.2: Migraciones de tenants (Depende de accounts)
Write-Host "✅ Creando migraciones de tenants (Modelo de tenant)..." -ForegroundColor Cyan
python manage.py makemigrations tenants
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Error al crear migraciones de tenants" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Migraciones de tenants creadas" -ForegroundColor Green

# 2.3: Resto de aplicaciones
Write-Host "✅ Creando migraciones del resto de aplicaciones..." -ForegroundColor Cyan
python manage.py makemigrations
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Error al crear migraciones del resto de aplicaciones" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Migraciones del resto de aplicaciones creadas" -ForegroundColor Green
Write-Host ""

# PASO 3: Aplicación de Migraciones al Esquema Compartido
Write-Host "🗄️  PASO 3: Aplicando migraciones al esquema compartido (public)..." -ForegroundColor Yellow
Write-Host "-------------------------------------------------------------------" -ForegroundColor Yellow

python manage.py migrate_schemas --shared
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Error al aplicar migraciones del esquema compartido" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Migraciones del esquema compartido aplicadas" -ForegroundColor Green
Write-Host ""

# PASO 4: Bootstrapping (Semilla)
Write-Host "🌱 PASO 4: Bootstrapping del sistema (Semilla inicial)..." -ForegroundColor Yellow
Write-Host "--------------------------------------------------------" -ForegroundColor Yellow

# 4.1: Crear tenant público
Write-Host "✅ Creando tenant público..." -ForegroundColor Cyan
python manage.py setup_public_tenant
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  El tenant público ya existe o hubo un error (continuando...)" -ForegroundColor Yellow
} else {
    Write-Host "✅ Tenant público creado" -ForegroundColor Green
}

# 4.2: Crear superusuario por defecto
Write-Host ""
Write-Host "✅ Creando superusuario por defecto..." -ForegroundColor Cyan
Write-Host "Username: admin"
Write-Host "Email: admin@sintel.com"
Write-Host "Password: admin"

# Usar Python para crear el superusuario de forma no interactiva
$pythonScript = @"
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()

try:
    # Intentar obtener el usuario existente
    user = User.objects.get(username='admin')
    print('⚠️  El usuario admin ya existe. Actualizando contraseña...')
    user.set_password('admin')
    user.email = 'admin@sintel.com'
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print('✅ Usuario admin actualizado correctamente')
except User.DoesNotExist:
    # Crear nuevo usuario
    user = User.objects.create_superuser(
        username='admin',
        email='admin@sintel.com',
        password='admin'
    )
    print('✅ Usuario admin creado correctamente')
except IntegrityError as e:
    print(f'⚠️  Error de integridad al crear usuario: {e}')
    print('   Intentando actualizar usuario existente...')
    try:
        user = User.objects.get(email='admin@sintel.com')
        user.username = 'admin'
        user.set_password('admin')
        user.is_staff = True
        user.is_superuser = True
        user.save()
        print('✅ Usuario actualizado correctamente')
    except Exception as e2:
        print(f'❌ Error al actualizar usuario: {e2}')
"@

$pythonScript | python
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Superusuario creado/actualizado" -ForegroundColor Green
} else {
    Write-Host "⚠️  Hubo un problema al crear el superusuario (puede que ya exista)" -ForegroundColor Yellow
}
Write-Host ""

# PASO 5: Verificación Final
Write-Host "🔍 PASO 5: Verificación final..." -ForegroundColor Yellow
Write-Host "--------------------------------" -ForegroundColor Yellow

$verificationScript = @"
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from apps.public.tenants.models import Client, Domain
from django.contrib.auth import get_user_model

User = get_user_model()

print('\n📊 Estado del Sistema:')
print('=' * 50)

# Verificar tenant público
try:
    public_tenant = Client.objects.get(schema_name='public')
    print(f'✅ Tenant público existe: {public_tenant.nombre}')
except Client.DoesNotExist:
    print('❌ Tenant público NO existe')

# Verificar dominios del tenant público
domains = Domain.objects.filter(tenant__schema_name='public')
print(f'✅ Dominios del tenant público: {domains.count()}')
for domain in domains:
    print(f'   - {domain.domain} (primary: {domain.is_primary})')

# Verificar superusuario
try:
    admin = User.objects.get(username='admin')
    print(f'✅ Superusuario existe: {admin.username} ({admin.email})')
    print(f'   - Staff: {admin.is_staff}')
    print(f'   - Superuser: {admin.is_superuser}')
except User.DoesNotExist:
    print('❌ Superusuario NO existe')

print('=' * 50)
"@

$verificationScript | python
Write-Host ""

Write-Host "==================================================" -ForegroundColor Green
Write-Host "🎉 Reconstrucción completada exitosamente!" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Próximos pasos:" -ForegroundColor Cyan
Write-Host "   1. Ejecutar tests: python manage.py test tests.general.test_system_health"
Write-Host "   2. Crear un tenant de prueba: python manage.py crear_empresa 'Mi Empresa' 'admin@miempresa.com'"
Write-Host "   3. Acceder al admin: http://localhost:8000/admin/ (admin/admin)"
Write-Host ""