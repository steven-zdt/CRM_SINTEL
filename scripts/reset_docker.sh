#!/bin/bash
# ============================================================================
# Script de Limpieza y Reconstrucción Docker - SINTEL
# ============================================================================
# 
# Este script realiza un reinicio total (nuclear reset) de los contenedores
# Docker, eliminando volúmenes, redes y reconstruyendo las imágenes desde cero.
#
# ⚠️ ADVERTENCIA: Este script elimina TODOS los datos de la base de datos.
# Solo ejecutar en desarrollo o cuando se necesite un reinicio completo.
#
# Uso:
#   bash scripts/reset_docker.sh
#   o
#   chmod +x scripts/reset_docker.sh && ./scripts/reset_docker.sh
# ============================================================================

set -e  # Salir si cualquier comando falla

echo "🚀 INICIANDO REINICIO TOTAL (NUCLEAR RESET) DE DOCKER"
echo "=================================================="
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Paso 1: Bajar servicios y eliminar volúmenes
echo -e "${YELLOW}📦 Paso 1: Deteniendo servicios y eliminando volúmenes...${NC}"
docker compose down -v --remove-orphans
echo -e "${GREEN}✅ Servicios detenidos y volúmenes eliminados${NC}"
echo ""

# Paso 2: Limpiar sistema Docker (opcional pero recomendado)
echo -e "${YELLOW}🧹 Paso 2: Limpiando sistema Docker (imágenes huérfanas, caché)...${NC}"
read -p "¿Deseas ejecutar 'docker system prune -f'? Esto eliminará imágenes, contenedores y redes no utilizados. (s/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Ss]$ ]]; then
    docker system prune -f
    echo -e "${GREEN}✅ Sistema Docker limpiado${NC}"
else
    echo -e "${YELLOW}⏭️  Limpieza del sistema omitida${NC}"
fi
echo ""

# Paso 3: Reconstrucción controlada sin caché
echo -e "${YELLOW}🔨 Paso 3: Reconstruyendo imágenes Docker sin caché...${NC}"
echo "   Esto puede tardar varios minutos..."
docker compose build --no-cache
echo -e "${GREEN}✅ Imágenes reconstruidas${NC}"
echo ""

# Paso 4: Verificar que las imágenes se crearon correctamente
echo -e "${YELLOW}🔍 Paso 4: Verificando imágenes creadas...${NC}"
docker compose images
echo ""

echo -e "${GREEN}✅ REINICIO DOCKER COMPLETADO${NC}"
echo "=================================================="
echo ""
echo "📋 Próximos pasos:"
echo "   1. Ejecutar: bash scripts/reset_migrations.py"
echo "   2. Ejecutar: docker compose up -d"
echo "   3. Ejecutar: bash scripts/init_project.sh"
echo ""
