$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker CLI was not found. Install Docker Desktop and reopen PowerShell."
}
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Engine is not running. Start Docker Desktop, wait until it is ready, then rerun scripts\start.ps1."
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example. Review secrets before exposing this service."
}

docker compose up --build -d
if ($LASTEXITCODE -ne 0) { throw "Docker Compose failed. Inspect the output above." }

Write-Host "Waiting for API readiness..."
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    try {
        $response = Invoke-RestMethod "http://localhost:8000/health/ready" -TimeoutSec 3
        if ($response.status -eq "ready") { $ready = $true; break }
    } catch {}
    Start-Sleep -Seconds 3
}
if (-not $ready) {
    docker compose ps
    docker compose logs --tail=100 api migrate seed
    throw "API did not become ready. Review the logs above."
}

Write-Host ""
Write-Host "SignalFlow AI is running:"
Write-Host "  Dashboard: http://localhost:3000"
Write-Host "  API docs:  http://localhost:8000/docs"
Write-Host "  API health: http://localhost:8000/health/ready"
Write-Host ""
docker compose ps
