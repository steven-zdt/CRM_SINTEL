# Script helper para limpiar datos de cotizaciones en Docker (PowerShell)
#
# Uso:
#   .\scripts\limpiar_cotizaciones.ps1 <schema_name> [-Confirm]
#   .\scripts\limpiar_cotizaciones.ps1 all [-Confirm]
#
# Ejemplos:
#   # Ver qué se eliminaría (simulación)
#   .\scripts\limpiar_cotizaciones.ps1 tenant1
#
#   # Eliminar datos de un tenant específico
#   .\scripts\limpiar_cotizaciones.ps1 tenant1 -Confirm
#
#   # Eliminar datos de todos los tenants
#   .\scripts\limpiar_cotizaciones.ps1 all -Confirm

param(
    [Parameter(Mandatory=$true)]
    [string]$SchemaName,
    
    [switch]$Confirm
)

if ([string]::IsNullOrWhiteSpace($SchemaName)) {
    Write-Host "❌ Error: Debe especificar el nombre del schema o 'all'" -ForegroundColor Red
    Write-Host ""
    Write-Host "Uso:"
    Write-Host "  .\scripts\limpiar_cotizaciones.ps1 <schema_name> [-Confirm]"
    Write-Host "  .\scripts\limpiar_cotizaciones.ps1 all [-Confirm]"
    Write-Host ""
    Write-Host "Ejemplos:"
    Write-Host "  # Simulación (ver qué se eliminaría)"
    Write-Host "  .\scripts\limpiar_cotizaciones.ps1 tenant1"
    Write-Host ""
    Write-Host "  # Eliminar datos de un tenant"
    Write-Host "  .\scripts\limpiar_cotizaciones.ps1 tenant1 -Confirm"
    Write-Host ""
    Write-Host "  # Eliminar datos de todos los tenants"
    Write-Host "  .\scripts\limpiar_cotizaciones.ps1 all -Confirm"
    exit 1
}

# Determinar el comando según el schema
if ($SchemaName -eq "all") {
    if ($Confirm) {
        Write-Host "⚠️  Eliminando datos de cotizaciones en TODOS los tenants..." -ForegroundColor Yellow
        docker compose -f infra/compose/docker-compose.yml exec -T app python manage.py all_tenants_command limpiar_cotizaciones --confirm
    } else {
        Write-Host "ℹ️  Modo simulación: Mostrando qué se eliminaría en todos los tenants..." -ForegroundColor Cyan
        docker compose -f infra/compose/docker-compose.yml exec -T app python manage.py all_tenants_command limpiar_cotizaciones --dry-run
    }
} else {
    if ($Confirm) {
        Write-Host "⚠️  Eliminando datos de cotizaciones en tenant: $SchemaName..." -ForegroundColor Yellow
        docker compose -f infra/compose/docker-compose.yml exec -T app python manage.py tenant_command limpiar_cotizaciones --schema="$SchemaName" --confirm
    } else {
        Write-Host "ℹ️  Modo simulación: Mostrando qué se eliminaría en tenant: $SchemaName..." -ForegroundColor Cyan
        docker compose -f infra/compose/docker-compose.yml exec -T app python manage.py tenant_command limpiar_cotizaciones --schema="$SchemaName" --dry-run
    }
}
