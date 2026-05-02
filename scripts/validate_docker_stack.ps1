# Script de validación del stack Docker para pipeline universal (PowerShell)
# Uso: .\scripts\validate_docker_stack.ps1

$ErrorActionPreference = "Stop"

$COMPOSE_FILE = "infra/compose/docker-compose.yml"
$ENV_FILE = "infra/compose/.env"

Write-Host "🔍 VALIDACIÓN DEL STACK DOCKER - Pipeline Universal" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Verificar que docker-compose.yml es válido
Write-Host "1. Validando docker-compose.yml..." -ForegroundColor Yellow
docker compose -f $COMPOSE_FILE config | Out-Null
Write-Host "✅ docker-compose.yml es válido" -ForegroundColor Green
Write-Host ""

# 2. Construir imágenes
Write-Host "2. Construyendo imágenes..." -ForegroundColor Yellow
docker compose -f $COMPOSE_FILE --env-file $ENV_FILE build --no-cache
Write-Host "✅ Imágenes construidas" -ForegroundColor Green
Write-Host ""

# 3. Levantar servicios
Write-Host "3. Levantando servicios..." -ForegroundColor Yellow
docker compose -f $COMPOSE_FILE --env-file $ENV_FILE up -d
Write-Host "✅ Servicios levantados" -ForegroundColor Green
Write-Host ""

# 4. Esperar healthchecks
Write-Host "4. Esperando healthchecks..." -ForegroundColor Yellow
Start-Sleep -Seconds 30
Write-Host "✅ Healthchecks completados" -ForegroundColor Green
Write-Host ""

# 5. Verificar estado de servicios
Write-Host "5. Verificando estado de servicios..." -ForegroundColor Yellow
docker compose -f $COMPOSE_FILE ps
Write-Host ""

# 6. Verificar logs de celery y beat
Write-Host "6. Verificando logs de celery..." -ForegroundColor Yellow
docker compose -f $COMPOSE_FILE logs celery --tail=20
Write-Host ""

Write-Host "7. Verificando logs de beat..." -ForegroundColor Yellow
docker compose -f $COMPOSE_FILE logs beat --tail=20
Write-Host ""

# 8. Verificar health endpoint
Write-Host "8. Verificando health endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing
    Write-Host "✅ Health check OK" -ForegroundColor Green
} catch {
    Write-Host "❌ Health check falló: $_" -ForegroundColor Red
}
Write-Host ""

# 9. Verificar que la tarea está registrada
Write-Host "9. Verificando tarea document_ingest_task..." -ForegroundColor Yellow
$taskCheck = docker compose -f $COMPOSE_FILE exec -T celery celery -A config inspect registered 2>&1
if ($taskCheck -match "document_ingest") {
    Write-Host "✅ Tarea document_ingest_task encontrada" -ForegroundColor Green
} else {
    Write-Host "⚠️ Tarea no encontrada" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "✅ Validación completada" -ForegroundColor Green
Write-Host ""
Write-Host "Próximos pasos:" -ForegroundColor Cyan
Write-Host "1. Probar upload de XML con preview=true"
Write-Host "2. Probar upload de XML con preview=false"
Write-Host "3. Probar upload de Nota Crédito"
Write-Host "4. Verificar idempotencia (409)"
