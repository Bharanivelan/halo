# Starts the local stack in separate windows: database, API, worker, and the classic frontend if it's
# next to this repo (../halo-web-classic). The Lovable app (halo-web) runs on Lovable and reaches the API via scripts\tunnel.ps1.
# Usage (from the repo root):  powershell -ExecutionPolicy Bypass -File scripts\dev.ps1
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env"; Write-Host "Created .env from .env.example. Add GEMINI_API_KEY for AI research." }

Write-Host "Starting database..."
docker compose up -d db | Out-Null

$py = Join-Path $root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
  Write-Host "Creating backend virtualenv..."
  python -m venv backend\.venv
  & backend\.venv\Scripts\pip.exe install -r backend\requirements.txt
}
Push-Location backend
& $py -m alembic upgrade head
Pop-Location

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\backend'; & '$py' -m uvicorn app.main:app --port 8000 --reload --reload-dir app"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\backend'; & '$py' -m app.worker"
$web = Join-Path (Split-Path -Parent $root) "halo-web-classic"
if (Test-Path $web) {
  Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$web'; if (-not (Test-Path node_modules)) { npm install }; npm run dev"
}

Write-Host ""
Write-Host "API:      http://localhost:8000/api/v1/docs"
if (Test-Path $web) { Write-Host "App:      http://localhost:5173  (classic UI)" }
Write-Host "Tunnel:   powershell -ExecutionPolicy Bypass -File scripts\tunnel.ps1   (for the Lovable app)"
