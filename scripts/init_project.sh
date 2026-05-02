#!/bin/bash
# ============================================================================
# Script de Inicialización Secuencial - SINTEL
# ============================================================================
# 
# Este script ejecuta la inicialización completa del proyecto en el orden
# correcto: migraciones, esquema público, y datos base.
#
# ⚠️ IMPORTANTE: Este script debe ejecutarse DENTRO del contenedor 'web'
# o vía 'docker compose exec web bash scripts/init_project.sh'
#
# Uso:
#   docker compose exec web bash scripts/init_project.sh
#   o
#   docker compose up -d
#   docker compose exec web bash scripts/init_project.sh
# ============================================================================

set -e  # Salir si cualquier comando falla

echo "🚀 INICIANDO INICIALIZACIÓN SECUENCIAL DEL PROYECTO"
echo "=================================================="
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Verificar que estamos en el contenedor o con acceso a manage.py
if ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Error: Python no encontrado. Asegúrate de ejecutar este script dentro del contenedor 'web'.${NC}"
    exit 1
fi

if [ ! -f "manage.py" ]; then
    echo -e "${RED}❌ Error: manage.py no encontrado. Asegúrate de estar en el directorio raíz del proyecto.${NC}"
    exit 1
fi

# ============================================================================
# PASO 1: CREAR MIGRACIONES (Orden de Dependencia)
# ============================================================================

echo -e "${BLUE}📦 Paso 1: Creando migraciones (orden de dependencia)...${NC}"
echo ""

# 1.1: Migraciones de accounts (PRIMERO - usuarios globales)
echo -e "${YELLOW}   1.1. Creando migraciones para accounts...${NC}"
python manage.py makemigrations accounts
if [ $? -eq 0 ]; then
    echo -e "${GREEN}   ✅ Migraciones de accounts creadas${NC}"
else
    echo -e "${RED}   ❌ Error al crear migraciones de accounts${NC}"
    exit 1
fi
echo ""

# 1.2: Migraciones del resto de apps (tenants, impuestos, etc.)
echo -e "${YELLOW}   1.2. Creando migraciones para el resto de apps...${NC}"
python manage.py makemigrations
if [ $? -eq 0 ]; then
    echo -e "${GREEN}   ✅ Migraciones del resto de apps creadas${NC}"
else
    echo -e "${RED}   ❌ Error al crear migraciones${NC}"
    exit 1
fi
echo ""

# ============================================================================
# PASO 2: APLICAR ESQUEMA PÚBLICO
# ============================================================================

echo -e "${BLUE}🗄️  Paso 2: Aplicando esquema público (shared)...${NC}"
python manage.py migrate_schemas --shared
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Esquema público aplicado${NC}"
else
    echo -e "${RED}❌ Error al aplicar esquema público${NC}"
    exit 1
fi
echo ""

# ============================================================================
# PASO 3: SEMILLA DE DATOS (Bootstrapping)
# ============================================================================

echo -e "${BLUE}🌱 Paso 3: Semilla de datos (bootstrapping)...${NC}"
echo ""

# 3.1: Setup del tenant público
echo -e "${YELLOW}   3.1. Configurando tenant público...${NC}"
# Usar sintel.com como dominio base (configurable vía .env)
python manage.py setup_public_tenant --domain sintel.com
if [ $? -eq 0 ]; then
    echo -e "${GREEN}   ✅ Tenant público configurado${NC}"
else
    echo -e "${YELLOW}   ⚠️  Advertencia: setup_public_tenant falló (puede que ya exista)${NC}"
fi
echo ""

# 3.2: Poblar catálogo DIAN
echo -e "${YELLOW}   3.2. Poblando catálogo DIAN...${NC}"
if python manage.py poblar_catalogo_dian &> /dev/null; then
    echo -e "${GREEN}   ✅ Catálogo DIAN poblado${NC}"
else
    echo -e "${YELLOW}   ⚠️  Advertencia: poblar_catalogo_dian falló o no existe (continuando...)${NC}"
fi
echo ""

# 3.3: Crear superusuario por defecto
echo -e "${YELLOW}   3.3. Creando superusuario por defecto...${NC}"
# Verificar si el superusuario ya existe
if python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); print('EXISTS' if User.objects.filter(email='admin@sintel.com').exists() else 'NOT_EXISTS')" | grep -q "EXISTS"; then
    echo -e "${BLUE}   ℹ️  Superusuario admin@sintel.com ya existe (omitiendo creación)${NC}"
else
    # Crear superusuario sin interacción
    python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='admin@sintel.com').exists():
    User.objects.create_superuser(
        username='admin',
        email='admin@sintel.com',
        password='admin'
    )
    print('Superusuario creado: admin / admin@sintel.com / admin')
else:
    print('Superusuario ya existe')
EOF
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}   ✅ Superusuario creado${NC}"
    else
        echo -e "${YELLOW}   ⚠️  Advertencia: Error al crear superusuario${NC}"
    fi
fi
echo ""

# ============================================================================
# RESUMEN FINAL
# ============================================================================

echo "=================================================="
echo -e "${GREEN}✅ INICIALIZACIÓN COMPLETA${NC}"
echo "=================================================="
echo ""
echo -e "${BLUE}📋 Resumen:${NC}"
echo "   ✅ Migraciones creadas y aplicadas"
echo "   ✅ Esquema público configurado"
echo "   ✅ Tenant público creado"
echo "   ✅ Superusuario: admin / admin@sintel.com / admin"
echo ""
echo -e "${BLUE}🚀 El sistema está listo para usar${NC}"
echo ""
echo -e "${YELLOW}📝 Notas:${NC}"
echo "   - Accede al admin en: http://localhost:8000/admin/"
echo "   - Credenciales: admin / admin"
echo "   - Para crear tenants privados, usa el admin o la API"
echo ""
