# ============================================================================
# Script de Limpieza de Contenedores Huérfanos - SINTEL
# ============================================================================
# 
# Este script identifica y elimina contenedores Docker que no pertenecen
# al proyecto SINTEL (contenedores con nombres aleatorios o huérfanos).
#
# ⚠️ ADVERTENCIA: Este script elimina contenedores que NO tienen el prefijo
# "crm_sintel-" o que no están definidos en docker-compose.yml.
# Solo ejecutar si estás seguro de que quieres eliminar contenedores huérfanos.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File scripts/limpiar_contenedores_huérfanos.ps1
# ============================================================================

Write-Host "🔍 Buscando contenedores huérfanos..." -ForegroundColor Yellow

# Obtener todos los contenedores
$allContainers = docker ps -a --format "{{.Names}}|{{.Status}}|{{.Image}}"

# Contenedores válidos del proyecto SINTEL
$validContainers = @(
    "crm_sintel-web",
    "crm_sintel-db",
    "crm_sintel-redis",
    "crm_sintel-celery",
    "crm_sintel-beat",
    "crm_sintel-opensearch",
    "crm_sintel-traefik"
)

$orphanContainers = @()

foreach ($line in $allContainers) {
    if ($line) {
        $parts = $line -split '\|'
        $name = $parts[0]
        $status = $parts[1]
        $image = $parts[2]
        
        # Verificar si el contenedor es válido
        $isValid = $false
        foreach ($valid in $validContainers) {
            if ($name -like "$valid*") {
                $isValid = $true
                break
            }
        }
        
        # Si no es válido y la imagen parece ser del proyecto, es huérfano
        if (-not $isValid) {
            # Verificar si la imagen es del proyecto SINTEL
            if ($image -like "*crm_sintel*" -or $image -like "*sintel*") {
                $orphanContainers += @{
                    Name = $name
                    Status = $status
                    Image = $image
                }
            }
        }
    }
}

if ($orphanContainers.Count -eq 0) {
    Write-Host "✅ No se encontraron contenedores huérfanos" -ForegroundColor Green
    exit 0
}

Write-Host "`n⚠️  Se encontraron $($orphanContainers.Count) contenedor(es) huérfano(s):" -ForegroundColor Yellow
Write-Host ""

foreach ($container in $orphanContainers) {
    Write-Host "  - $($container.Name)" -ForegroundColor Red
    Write-Host "    Estado: $($container.Status)" -ForegroundColor Gray
    Write-Host "    Imagen: $($container.Image)" -ForegroundColor Gray
    Write-Host ""
}

$confirm = Read-Host "¿Deseas eliminar estos contenedores? (s/N)"

if ($confirm -eq "s" -or $confirm -eq "S") {
    Write-Host "`n🗑️  Eliminando contenedores huérfanos..." -ForegroundColor Yellow
    
    foreach ($container in $orphanContainers) {
        Write-Host "  Deteniendo: $($container.Name)..." -ForegroundColor Yellow
        docker stop $container.Name 2>$null
        
        Write-Host "  Eliminando: $($container.Name)..." -ForegroundColor Yellow
        docker rm $container.Name 2>$null
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✅ $($container.Name) eliminado" -ForegroundColor Green
        } else {
            Write-Host "  ❌ Error al eliminar $($container.Name)" -ForegroundColor Red
        }
    }
    
    Write-Host "`n✅ Limpieza completada" -ForegroundColor Green
} else {
    Write-Host "`n⏭️  Operación cancelada" -ForegroundColor Yellow
}
