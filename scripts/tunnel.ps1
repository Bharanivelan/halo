# Exposes the local Halo API on a public HTTPS URL so the Lovable-hosted frontend can reach it (D-37).
# Usage (API must already be running on :8000):
#   powershell -ExecutionPolicy Bypass -File scripts\tunnel.ps1               # ngrok if NGROK_DOMAIN is set in .env, else Cloudflare
#   powershell -ExecutionPolicy Bypass -File scripts\tunnel.ps1 -Provider cloudflare
#
# ngrok (recommended for demos): free account gives ONE fixed domain, so the URL never changes.
#   1. Sign up at https://dashboard.ngrok.com, copy your authtoken, run:  ngrok config add-authtoken <token>
#   2. Claim your free static domain (Dashboard -> Domains) and put it in .env:  NGROK_DOMAIN=your-name.ngrok-free.app
# Cloudflare quick tunnel: no account, but the URL changes on every start, and some ISP/router DNS blocks
#   trycloudflare.com (it does on this machine's Wi-Fi as of 2026-11-10).
#
# Security: anyone with the URL can reach the API's login and docs pages. All data still requires sign-in.
# Stop the tunnel (Ctrl+C) when you're not demoing.
param([ValidateSet("auto", "ngrok", "cloudflare")] [string]$Provider = "auto")

$root = Split-Path -Parent $PSScriptRoot
$domain = $null
if (Test-Path "$root\.env") {
  $line = Select-String -Path "$root\.env" -Pattern '^\s*NGROK_DOMAIN\s*=\s*(\S+)' | Select-Object -First 1
  if ($line) { $domain = $line.Matches[0].Groups[1].Value }
}
if ($Provider -eq "auto") { $Provider = $(if ($domain) { "ngrok" } else { "cloudflare" }) }

try { Invoke-RestMethod http://127.0.0.1:8000/healthz -TimeoutSec 3 | Out-Null }
catch { Write-Host "The Halo API isn't running on http://127.0.0.1:8000. Start it first (scripts\dev.ps1)."; exit 1 }

if ($Provider -eq "ngrok") {
  $exe = (Get-Command ngrok -ErrorAction SilentlyContinue).Source
  if (-not $exe) { Write-Host "ngrok not found. Install it with:  winget install --id Ngrok.Ngrok -e"; exit 1 }
  if ($domain) {
    Write-Host "Halo API will be at: https://$domain   (paste into Halo -> Connection settings)"
    & $exe http --url="https://$domain" 8000
  } else {
    Write-Host "No NGROK_DOMAIN in .env; using a random ngrok URL (shown below as 'Forwarding')."
    & $exe http 8000
  }
} else {
  $exe = (Get-Command cloudflared -ErrorAction SilentlyContinue).Source
  if (-not $exe) { $exe = "C:\Program Files (x86)\cloudflared\cloudflared.exe" }
  if (-not (Test-Path $exe)) { Write-Host "cloudflared not found. Install it with:  winget install --id Cloudflare.cloudflared -e"; exit 1 }
  Write-Host "Look for the https://<something>.trycloudflare.com line, then paste it into Halo -> Connection settings."
  & $exe tunnel --no-autoupdate --url http://127.0.0.1:8000
}
