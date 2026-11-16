# Starts the local stack in separate windows: database, API, worker and the web app.
# The web app is taken from ./web (combined repo Bharanivelan/halo), else ../halo-web (Lovable repo clone),
# else the old classic UI in ../halo-web-classic.
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

$parent = Split-Path -Parent $root
$web = @((Join-Path $root "web"), (Join-Path $parent "halo-web")) | Where-Object { Test-Path (Join-Path $_ "package.json") } | Select-Object -First 1
$classic = Join-Path $parent "halo-web-classic"
$app = $null
if ($web) {
  # The web app reads the API address from VITE_HALO_API_URL (a value saved in the browser wins).
  Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$web'; if (-not (Test-Path node_modules)) { bun install }; `$env:VITE_HALO_API_URL='http://localhost:8000'; bun run dev --port 5173"
  $app = "http://localhost:5173"
} elseif (Test-Path $classic) {
  Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$classic'; if (-not (Test-Path node_modules)) { npm install }; npm run dev"
  $app = "http://localhost:5173  (classic UI)"
}

Write-Host ""
Write-Host "API:      http://localhost:8000/api/v1/docs"
if ($app) { Write-Host "App:      $app" }
Write-Host "Tunnel:   powershell -ExecutionPolicy Bypass -File scripts\tunnel.ps1   (lets the Lovable-hosted app reach this API)"
