# toggle_db_host.ps1
# Script para alternar DATABASE_HOST en .env entre 'db' (Docker) y 'localhost' (desarrollo local)

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("docker", "local")]
    [string]$mode
)

$envPath = "./.env"

if (!(Test-Path $envPath)) {
    Write-Host ".env file not found at $envPath" -ForegroundColor Red
    exit 1
}

$content = Get-Content $envPath

if ($mode -eq "docker") {
    $newContent = $content -replace "^DATABASE_HOST=.*$", "DATABASE_HOST=db"
    Write-Host "Set DATABASE_HOST=db for Docker usage" -ForegroundColor Green
} elseif ($mode -eq "local") {
    $newContent = $content -replace "^DATABASE_HOST=.*$", "DATABASE_HOST=localhost"
    Write-Host "Set DATABASE_HOST=localhost for local usage" -ForegroundColor Green
}

$newContent | Set-Content $envPath
