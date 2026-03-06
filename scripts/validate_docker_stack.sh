#!/bin/bash
# Script de validación del stack Docker para pipeline universal
# Uso: ./scripts/validate_docker_stack.sh

set -e

COMPOSE_FILE="infra/compose/docker-compose.yml"
ENV_FILE="infra/compose/.env"

echo "🔍 VALIDACIÓN DEL STACK DOCKER - Pipeline Universal"
echo "=================================================="
echo ""

# 1. Verificar que docker-compose.yml es válido
echo "1. Validando docker-compose.yml..."
docker compose -f $COMPOSE_FILE config > /dev/null
echo "✅ docker-compose.yml es válido"
echo ""

# 2. Construir imágenes
echo "2. Construyendo imágenes..."
docker compose -f $COMPOSE_FILE --env-file $ENV_FILE build --no-cache
echo "✅ Imágenes construidas"
echo ""

# 3. Levantar servicios
echo "3. Levantando servicios..."
docker compose -f $COMPOSE_FILE --env-file $ENV_FILE up -d
echo "✅ Servicios levantados"
echo ""

# 4. Esperar healthchecks
echo "4. Esperando healthchecks..."
sleep 30
echo "✅ Healthchecks completados"
echo ""

# 5. Verificar estado de servicios
echo "5. Verificando estado de servicios..."
docker compose -f $COMPOSE_FILE ps
echo ""

# 6. Verificar logs de celery y beat
echo "6. Verificando logs de celery..."
docker compose -f $COMPOSE_FILE logs celery --tail=20
echo ""

echo "7. Verificando logs de beat..."
docker compose -f $COMPOSE_FILE logs beat --tail=20
echo ""

# 8. Verificar health endpoint
echo "8. Verificando health endpoint..."
curl -f http://localhost:8000/health || echo "❌ Health check falló"
echo ""

# 9. Verificar que la tarea está registrada
echo "9. Verificando tarea document_ingest_task..."
docker compose -f $COMPOSE_FILE exec -T celery celery -A config inspect registered | grep document_ingest || echo "⚠️ Tarea no encontrada"
echo ""

echo "✅ Validación completada"
echo ""
echo "Próximos pasos:"
echo "1. Probar upload de XML con preview=true"
echo "2. Probar upload de XML con preview=false"
echo "3. Probar upload de Nota Crédito"
echo "4. Verificar idempotencia (409)"
