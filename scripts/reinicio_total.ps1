# ============================================================================
# Script de Reinicio Total (Nuclear Reset) - SINTEL - PowerShell
# ============================================================================
# 
# Este script realiza un reinicio completo del proyecto SINTEL:
# 1. Limpia y reconstruye contenedores Docker
# 2. Elimina archivos de migración
# 3. Inicializa el proyecto desde cero
#
# ⚠️ ADVERTENCIA: Este script elimina TODOS los datos de la base de datos.
# Solo ejecutar en desarrollo o cuando se necesite un reinicio completo.
#
# Uso:
#   .\scripts\reinicio_total.ps1
# ============================================================================

$ErrorActionPreference = "Stop"

Write-Host "🚀 INICIANDO REINICIO TOTAL (NUCLEAR RESET) DE SINTEL" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# PASO 1: LIMPIAR Y RECONSTRUIR DOCKER
# ============================================================================

Write-Host "📦 Paso 1: Limpiando y reconstruyendo Docker..." -ForegroundColor Yellow
Write-Host ""

Write-Host "   1.1. Deteniendo servicios y eliminando volúmenes..." -ForegroundColor Gray
docker compose down -v --remove-orphans
if ($LASTEXITCODE -ne 0) {
    Write-Host "   ❌ Error al detener servicios" -ForegroundColor Red
    exit 1
}
Write-Host "   ✅ Servicios detenidos y volúmenes eliminados" -ForegroundColor Green
Write-Host ""

Write-Host "   1.2. Limpiando sistema Docker..." -ForegroundColor Gray
$cleanSystem = Read-Host "   Ejecutar 'docker system prune -f'? [s/N]"
if ($cleanSystem -eq "s" -or $cleanSystem -eq "S" -or $cleanSystem -eq "y" -or $cleanSystem -eq "Y") {
    docker system prune -f
    Write-Host "   ✅ Sistema Docker limpiado" -ForegroundColor Green
} else {
    Write-Host "   ⏭️  Limpieza del sistema omitida" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "   1.3. Reconstruyendo imágenes Docker sin caché..." -ForegroundColor Gray
Write-Host "   (Esto puede tardar varios minutos...)" -ForegroundColor Gray
docker compose build --no-cache
if ($LASTEXITCODE -ne 0) {
    Write-Host "   ❌ Error al reconstruir imágenes" -ForegroundColor Red
    exit 1
}
Write-Host "   ✅ Imágenes reconstruidas" -ForegroundColor Green
Write-Host ""

# ============================================================================
# PASO 2: ELIMINAR ARCHIVOS DE MIGRACIÓN
# ============================================================================

Write-Host "🗑️  Paso 2: Eliminando archivos de migración..." -ForegroundColor Yellow
Write-Host ""

# Ejecutar script Python
Write-Host "   Ejecutando reset_migrations.py..." -ForegroundColor Gray
python scripts/reset_migrations.py --yes
if ($LASTEXITCODE -ne 0) {
    Write-Host "   ⚠️  Advertencia: Error al ejecutar reset_migrations.py" -ForegroundColor Yellow
    Write-Host "   Continuando con eliminación manual..." -ForegroundColor Yellow
    
    # Eliminación manual como fallback
    Get-ChildItem -Path "apps\public\*\migrations\*.py" -Exclude "__init__.py" -Recurse | Remove-Item -Force
    Get-ChildItem -Path "apps\tenant\*\migrations\*.py" -Exclude "__init__.py" -Recurse | Remove-Item -Force
    Write-Host "   ✅ Archivos de migración eliminados manualmente" -ForegroundColor Green
} else {
    Write-Host "   ✅ Archivos de migración eliminados" -ForegroundColor Green
}
Write-Host ""

# ============================================================================
# PASO 3: LEVANTAR CONTENEDORES
# ============================================================================

Write-Host "🚀 Paso 3: Levantando contenedores..." -ForegroundColor Yellow
Write-Host ""

docker compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "   ❌ Error al levantar contenedores" -ForegroundColor Red
    exit 1
}
Write-Host "   ✅ Contenedores levantados" -ForegroundColor Green
Write-Host ""

Write-Host "   Esperando a que los servicios estén listos..." -ForegroundColor Gray
Start-Sleep -Seconds 30

# Verificar que los servicios estén corriendo
Write-Host "   Verificando estado de servicios..." -ForegroundColor Gray
docker compose ps
Write-Host ""

# ============================================================================
# PASO 4: INICIALIZAR PROYECTO
# ============================================================================

Write-Host "🌱 Paso 4: Inicializando proyecto..." -ForegroundColor Yellow
Write-Host ""

Write-Host "   Ejecutando script de inicialización dentro del contenedor..." -ForegroundColor Gray
docker compose exec -T web bash scripts/init_project.sh
if ($LASTEXITCODE -ne 0) {
    Write-Host "   ❌ Error al inicializar proyecto" -ForegroundColor Red
    Write-Host "   Revisa los logs: docker compose logs web" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# ============================================================================
# RESUMEN FINAL
# ============================================================================

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "✅ REINICIO TOTAL COMPLETADO" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "📋 Resumen:" -ForegroundColor Cyan
Write-Host "   ✅ Docker limpiado y reconstruido" -ForegroundColor Green
Write-Host "   ✅ Migraciones eliminadas" -ForegroundColor Green
Write-Host "   ✅ Proyecto inicializado desde cero" -ForegroundColor Green
Write-Host ""

Write-Host "🔑 Credenciales por defecto:" -ForegroundColor Cyan
Write-Host "   Usuario: admin" -ForegroundColor White
Write-Host "   Email: admin@sintel.net.co" -ForegroundColor White
Write-Host "   Contraseña: admin" -ForegroundColor White
Write-Host ""

Write-Host "🌐 URLs:" -ForegroundColor Cyan
Write-Host "   Admin: http://localhost:8000/admin/" -ForegroundColor White
Write-Host "   Consola: http://localhost:8000/console/" -ForegroundColor White
Write-Host ""

Write-Host "🎉 El sistema está listo para usar!" -ForegroundColor Green
Write-Host ""
