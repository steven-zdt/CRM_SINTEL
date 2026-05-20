# Script PowerShell para configurar hosts local
# EJECUTAR COMO ADMINISTRADOR

$hostsPath = "C:\Windows\System32\drivers\etc\hosts"
$entry = "192.168.2.15    home.sintel.com"

Write-Host "=== Configurar Hosts Local ===" -ForegroundColor Green
Write-Host "Host File: $hostsPath" -ForegroundColor Cyan
Write-Host "Entrada: $entry" -ForegroundColor Yellow

# Verificar si entrada ya existe
$hosts = Get-Content $hostsPath
if ($hosts -like "*home.sintel.com*") {
    Write-Host "✓ Entrada ya existe en hosts file" -ForegroundColor Green
    Write-Host "Contenido:" -ForegroundColor Cyan
    $hosts | Select-String "home.sintel.com"
} else {
    Write-Host "Agregando entrada a hosts file..." -ForegroundColor Yellow
    Add-Content -Path $hostsPath -Value "`n$entry"
    Write-Host "✓ Entrada agregada correctamente" -ForegroundColor Green
}

# Verificar resolución
Write-Host "`n=== Verificar Resolución ===" -ForegroundColor Green
Write-Host "Ejecutando: ping home.sintel.com" -ForegroundColor Cyan
ping home.sintel.com

Write-Host "`n=== Configuración Completada ===" -ForegroundColor Green
Write-Host "Ahora puedes acceder a:" -ForegroundColor Cyan
Write-Host "  • http://home.sintel.com" -ForegroundColor Yellow
Write-Host "  • http://192.168.2.15" -ForegroundColor Yellow
Write-Host "  • http://192.168.2.15:8000" -ForegroundColor Yellow
