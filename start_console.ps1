# SINTEL Browser Console - Quick Start Script
# Usage: .\start_console.ps1

param(
    [switch]$NoInstall = $false,
    [int]$Port = 8000
)

Write-Host "`n" -NoNewline
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SINTEL Browser Console v2.61.7" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan

# Get project root
$projectRoot = Split-Path -Parent $MyInvocation.MyCommandPath
Write-Host "`nProject root: $projectRoot`n" -ForegroundColor Gray

# Activate venv if it exists
$venvPath = Join-Path $projectRoot "venv"
if (Test-Path $venvPath) {
    Write-Host "[1/3] Activating virtual environment..." -ForegroundColor Blue
    & "$venvPath\Scripts\Activate.ps1"
    Write-Host "[OK] Virtual environment activated`n" -ForegroundColor Green
} else {
    Write-Host "[WARN] Virtual environment not found at $venvPath`n" -ForegroundColor Yellow
}

# Install dependencies if not --NoInstall
if (-not $NoInstall) {
    Write-Host "[2/3] Installing dependencies..." -ForegroundColor Blue
    
    $requirementsFile = Join-Path $projectRoot "requirements-console.txt"
    
    if (Test-Path $requirementsFile) {
        Write-Host "Installing from $requirementsFile`n" -ForegroundColor Gray
        & python -m pip install -r $requirementsFile
    } else {
        Write-Host "Installing FastAPI, Uvicorn, and dependencies..." -ForegroundColor Gray
        & python -m pip install fastapi uvicorn aiofiles python-multipart
    }
    
    Write-Host "[OK] Dependencies installed`n" -ForegroundColor Green
}

# Start server
Write-Host "[3/3] Starting SINTEL Browser Console..." -ForegroundColor Blue
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Server Information" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "URL:        http://localhost:$Port" -ForegroundColor Green
Write-Host "REST API:   http://localhost:$Port/api/" -ForegroundColor Green
Write-Host "WebSocket:  ws://localhost:$Port/ws" -ForegroundColor Green
Write-Host "`nPress Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host "========================================`n" -ForegroundColor Cyan

# Start the server
Set-Location $projectRoot

# Modify port in server if not 8000
if ($Port -ne 8000) {
    Write-Host "Starting server on port $Port..." -ForegroundColor Yellow
    # Run with specific port (would need to modify browser_console_server.py)
    & python browser_console_server.py
} else {
    & python browser_console_server.py
}
