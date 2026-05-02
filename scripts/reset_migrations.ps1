# Script de Limpieza Total de Migraciones y Base de Datos (PowerShell)
# ⚠️ ADVERTENCIA: Este script elimina todas las migraciones y la base de datos.
# Solo ejecutar en desarrollo o cuando se necesite un reset completo.

Write-Host "🔴 ADVERTENCIA: Este script eliminará todas las migraciones y la base de datos." -ForegroundColor Red
Write-Host "Presiona Ctrl+C para cancelar, o Enter para continuar..."
Read-Host

Write-Host "📦 Deteniendo contenedores..." -ForegroundColor Yellow
docker-compose down -v

Write-Host "🗑️  Eliminando carpetas de migraciones..." -ForegroundColor Yellow

# Buscar y eliminar todas las carpetas migrations
Get-ChildItem -Path . -Recurse -Directory -Filter "migrations" | Where-Object {
    $_.FullName -notmatch "venv" -and $_.FullName -notmatch "__pycache__"
} | ForEach-Object {
    Write-Host "  Eliminando: $($_.FullName)" -ForegroundColor Gray
    # Mantener __init__.py pero eliminar todo lo demás
    Get-ChildItem -Path $_.FullName -File | Where-Object { $_.Name -ne "__init__.py" } | Remove-Item -Force
    Get-ChildItem -Path $_.FullName -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "🗑️  Eliminando archivos de base de datos..." -ForegroundColor Yellow
# Eliminar archivos .db, .sqlite, .sqlite3
Get-ChildItem -Path . -Recurse -File | Where-Object {
    $_.Extension -in @(".db", ".sqlite", ".sqlite3") -and $_.FullName -notmatch "venv"
} | Remove-Item -Force

Write-Host "📁 Creando directorio estático si no existe..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "static" | Out-Null
New-Item -ItemType Directory -Force -Path "media" | Out-Null

Write-Host "✅ Limpieza completada." -ForegroundColor Green
Write-Host ""
Write-Host "📝 Próximos pasos:" -ForegroundColor Cyan
Write-Host "1. Reconstruir contenedores: docker-compose up -d --build"
Write-Host "2. Crear migraciones: docker-compose exec web python manage.py makemigrations"
Write-Host "3. Aplicar migraciones: docker-compose exec web python manage.py migrate"
Write-Host "4. Crear superusuario (opcional): docker-compose exec web python manage.py createsuperuser"
