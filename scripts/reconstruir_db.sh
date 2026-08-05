#!/bin/bash
# Script de Reconstrucción Total de Base de Datos para SINTEL
# ⚠️ ADVERTENCIA: Este script elimina TODAS las migraciones y recrea la base de datos desde cero
# Uso: ./scripts/reconstruir_db.sh

set -e  # Salir si hay algún error

echo "🚀 Iniciando reconstrucción total de la base de datos..."
echo "=================================================="

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para imprimir mensajes
print_step() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# PASO 1: Limpieza de Archivos de Migración
echo ""
echo "📁 PASO 1: Limpiando archivos de migración..."
echo "--------------------------------------------"

# Buscar y eliminar todos los archivos .py en carpetas migrations/, excepto __init__.py
find . -path "*/migrations/*.py" -not -name "__init__.py" -type f -delete
print_step "Archivos de migración eliminados (excepto __init__.py)"

# También eliminar archivos .pyc si existen
find . -path "*/migrations/*.pyc" -type f -delete 2>/dev/null || true
print_step "Archivos .pyc de migraciones eliminados"

# PASO 2: Recreación de Migraciones (Orden Estricto)
echo ""
echo "📦 PASO 2: Recreando migraciones en orden estricto..."
echo "---------------------------------------------------"

# 2.1: Migraciones de accounts (Usuario global - DEBE IR PRIMERO)
print_step "Creando migraciones de accounts (Usuario global)..."
python manage.py makemigrations accounts
if [ $? -eq 0 ]; then
    print_step "Migraciones de accounts creadas"
else
    print_error "Error al crear migraciones de accounts"
    exit 1
fi

# 2.2: Migraciones de tenants (Depende de accounts)
print_step "Creando migraciones de tenants (Modelo de tenant)..."
python manage.py makemigrations tenants
if [ $? -eq 0 ]; then
    print_step "Migraciones de tenants creadas"
else
    print_error "Error al crear migraciones de tenants"
    exit 1
fi

# 2.3: Resto de aplicaciones
print_step "Creando migraciones del resto de aplicaciones..."
python manage.py makemigrations
if [ $? -eq 0 ]; then
    print_step "Migraciones del resto de aplicaciones creadas"
else
    print_error "Error al crear migraciones del resto de aplicaciones"
    exit 1
fi

# PASO 3: Aplicación de Migraciones al Esquema Compartido
echo ""
echo "🗄️  PASO 3: Aplicando migraciones al esquema compartido (public)..."
echo "-------------------------------------------------------------------"

python manage.py migrate_schemas --shared
if [ $? -eq 0 ]; then
    print_step "Migraciones del esquema compartido aplicadas"
else
    print_error "Error al aplicar migraciones del esquema compartido"
    exit 1
fi

# PASO 4: Bootstrapping (Semilla)
echo ""
echo "🌱 PASO 4: Bootstrapping del sistema (Semilla inicial)..."
echo "--------------------------------------------------------"

# 4.1: Crear tenant público
print_step "Creando tenant público..."
python manage.py setup_public_tenant
if [ $? -eq 0 ]; then
    print_step "Tenant público creado"
else
    print_warning "El tenant público ya existe o hubo un error (continuando...)"
fi

# 4.2: Crear superusuario por defecto
echo ""
print_step "Creando superusuario por defecto..."
echo "Username: admin"
echo "Email: admin@sintel.net.co"
echo "Password: admin"

# Usar Python para crear el superusuario de forma no interactiva
python << EOF
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
    print("⚠️  El usuario 'admin' ya existe. Actualizando contraseña...")
    user.set_password('admin')
    user.email = 'admin@sintel.net.co'
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print("✅ Usuario 'admin' actualizado correctamente")
except User.DoesNotExist:
    # Crear nuevo usuario
    user = User.objects.create_superuser(
        username='admin',
        email='admin@sintel.net.co',
        password='admin'
    )
    print("✅ Usuario 'admin' creado correctamente")
except IntegrityError as e:
    print(f"⚠️  Error de integridad al crear usuario: {e}")
    print("   Intentando actualizar usuario existente...")
    try:
        user = User.objects.get(email='admin@sintel.net.co')
        user.username = 'admin'
        user.set_password('admin')
        user.is_staff = True
        user.is_superuser = True
        user.save()
        print("✅ Usuario actualizado correctamente")
    except Exception as e2:
        print(f"❌ Error al actualizar usuario: {e2}")
EOF

if [ $? -eq 0 ]; then
    print_step "Superusuario creado/actualizado"
else
    print_warning "Hubo un problema al crear el superusuario (puede que ya exista)"
fi

# PASO 5: Verificación Final
echo ""
echo "🔍 PASO 5: Verificación final..."
echo "--------------------------------"

# Verificar que el esquema public existe
python << EOF
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from apps.public.tenants.models import Client, Domain
from django.contrib.auth import get_user_model

User = get_user_model()

print("\n📊 Estado del Sistema:")
print("=" * 50)

# Verificar tenant público
try:
    public_tenant = Client.objects.get(schema_name='public')
    print(f"✅ Tenant público existe: {public_tenant.nombre}")
except Client.DoesNotExist:
    print("❌ Tenant público NO existe")

# Verificar dominios del tenant público
domains = Domain.objects.filter(tenant__schema_name='public')
print(f"✅ Dominios del tenant público: {domains.count()}")
for domain in domains:
    print(f"   - {domain.domain} (primary: {domain.is_primary})")

# Verificar superusuario
try:
    admin = User.objects.get(username='admin')
    print(f"✅ Superusuario existe: {admin.username} ({admin.email})")
    print(f"   - Staff: {admin.is_staff}")
    print(f"   - Superuser: {admin.is_superuser}")
except User.DoesNotExist:
    print("❌ Superusuario NO existe")

print("=" * 50)
EOF

echo ""
echo "=================================================="
print_step "🎉 Reconstrucción completada exitosamente!"
echo ""
echo "📝 Próximos pasos:"
echo "   1. Ejecutar tests: python manage.py test tests.general.test_system_health"
echo "   2. Crear un tenant de prueba: python manage.py crear_empresa 'Mi Empresa' 'admin@miempresa.com'"
echo "   3. Acceder al admin: http://localhost:8000/admin/ (admin/admin)"
echo ""