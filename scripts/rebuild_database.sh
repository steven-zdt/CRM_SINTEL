#!/bin/bash
# Script de Hard Reset y Reconstrucción de Base de Datos para SINTEL v2.9
# Este script regenera migraciones y reconstruye la base de datos desde cero

set -e  # Salir si cualquier comando falla

echo "============================================================"
echo "🚀 Hard Reset y Reconstrucción de Base de Datos SINTEL v2.9"
echo "============================================================"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para imprimir mensajes
print_step() {
    echo -e "${GREEN}▶ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# ============================================================
# TAREA 1: Limpieza Preventiva
# ============================================================
print_step "Tarea 1: Limpieza Preventiva"

# Limpiar archivos Python compilados
print_step "Limpiando archivos .pyc y __pycache__..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true

# Limpiar archivos de migración (excepto __init__.py)
print_step "Limpiando archivos de migración (excepto __init__.py)..."
find . -path "*/migrations/*.py" ! -name "__init__.py" -delete 2>/dev/null || true
find . -path "*/migrations/*.pyc" -delete 2>/dev/null || true

# Verificar que solo queden __init__.py en migrations
print_step "Verificando estructura de migrations..."
for dir in apps/*/migrations apps/public/*/migrations; do
    if [ -d "$dir" ]; then
        if [ ! -f "$dir/__init__.py" ]; then
            touch "$dir/__init__.py"
            echo "  ✓ Creado $dir/__init__.py"
        fi
    fi
done

echo "✅ Limpieza completada"

# ============================================================
# TAREA 2: Generación de Migraciones
# ============================================================
print_step "Tarea 2: Generación de Migraciones"

# Prioridad 1: Modelo de Usuario Personalizado (accounts)
print_step "Generando migraciones para accounts (Prioridad 1)..."
python manage.py makemigrations accounts || {
    print_error "Error al generar migraciones para accounts"
    exit 1
}

# Prioridad 2: Modelo de Tenant (tenants)
print_step "Generando migraciones para tenants (Prioridad 2)..."
python manage.py makemigrations tenants || {
    print_error "Error al generar migraciones para tenants"
    exit 1
}

# Resto de las apps
print_step "Generando migraciones para el resto de las apps..."
python manage.py makemigrations || {
    print_warning "Algunas apps pueden no tener modelos (esto es normal)"
}

echo "✅ Generación de migraciones completada"

# ============================================================
# TAREA 3: Aplicación de Migraciones
# ============================================================
print_step "Tarea 3: Aplicación de Migraciones"

# Ejecutar migraciones del esquema public (shared)
print_step "Ejecutando migraciones del esquema public (shared)..."
python manage.py migrate_schemas --shared || {
    print_error "Error al ejecutar migraciones del esquema public"
    exit 1
}

echo "✅ Migraciones aplicadas"

# ============================================================
# TAREA 4: Bootstrap del Sistema
# ============================================================
print_step "Tarea 4: Bootstrap del Sistema"

# Crear el tenant público
print_step "Creando tenant público..."
python manage.py setup_public_tenant || {
    print_error "Error al crear tenant público"
    exit 1
}

# Crear superusuario por defecto (si no existe)
print_step "Verificando superusuario por defecto..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()

# Verificar si existe el usuario admin
if not User.objects.filter(email='admin@admin.com').exists():
    User.objects.create_superuser(
        email='admin@admin.com',
        password='admin',
        username='admin'
    )
    print("✅ Superusuario creado: admin@admin.com / admin")
else:
    print("ℹ️  Superusuario ya existe: admin@admin.com")
EOF

echo "✅ Bootstrap del sistema completado"

# ============================================================
# TAREA 5: Verificación de Docker y Celery
# ============================================================
print_step "Tarea 5: Verificación Final"

# Verificar que los modelos estén correctos
print_step "Verificando estructura de modelos..."
python manage.py shell << EOF
from apps.public.tenants.models import Client, Domain, TenantMembership
from django.contrib.auth import get_user_model
User = get_user_model()

# Verificar tenant público
public_tenant = Client.objects.filter(schema_name='public').first()
if public_tenant:
    print(f"✅ Tenant público existe: {public_tenant.nombre} (schema: {public_tenant.schema_name})")
    domains = Domain.objects.filter(tenant=public_tenant)
    print(f"✅ Dominios del tenant público: {domains.count()}")
    for d in domains:
        print(f"   - {d.domain} (principal: {d.is_primary})")
else:
    print("❌ Tenant público NO existe")
    exit(1)

# Verificar superusuario
admin = User.objects.filter(email='admin@admin.com').first()
if admin:
    print(f"✅ Superusuario existe: {admin.email}")
else:
    print("❌ Superusuario NO existe")
    exit(1)
EOF

echo ""
echo "============================================================"
echo "✅ Hard Reset y Reconstrucción Completados Exitosamente"
echo "============================================================"
echo ""
echo "📋 Próximos pasos:"
echo "   1. Ejecutar tests CRUD: pytest tests/public/tenants/test_crud_full.py -v"
echo "   2. Ejecutar tests de UI: pytest tests/public/console/test_tenant_ui_flow.py -v"
echo "   3. Verificar que el sistema funciona: python manage.py runserver"
echo ""
