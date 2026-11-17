$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
docker compose ps
try { Invoke-RestMethod "http://localhost:8000/health/ready" -TimeoutSec 3 | Format-List } catch {
    Write-Warning "API is not ready. Run: docker compose logs --tail=150 api db migrate seed"
}
