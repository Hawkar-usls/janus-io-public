$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUNBUFFERED = "1"
$env:PYTHONIOENCODING = "utf-8:replace"

$Root = $PSScriptRoot
$Miner = Join-Path $Root "RBLGANUL_A10_ENCODING_ARCHAEOLOGY_V32_ACTIVE_TRIUNE_50_50_IO_SINGLE.py"
$Sidecar = Join-Path $Root "A10_GLYPH_ECOLOGY_SECRET_BACKFORTH_SIDECAR.py"
$RunName = "A10_ENCODING_ARCHAEOLOGY_THE_AVENGERS"

# Logs stay directly in I0\sidecar, not inside janus_io_o1_runs.
$OutDir = Join-Path $Root "sidecar"

if (-not $env:AVENGERS_RESUME_CORPUS) { $env:AVENGERS_RESUME_CORPUS = "1" }
if (-not $env:AVENGERS_NAS_MIRROR_INTERVAL) { $env:AVENGERS_NAS_MIRROR_INTERVAL = "60" }
if (-not $env:AVENGERS_NAS_JANUS_ROOT -and (Test-Path "J:\")) { $env:AVENGERS_NAS_JANUS_ROOT = "J:\" }

Set-Location -LiteralPath $Root
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

Write-Host ""
Write-Host "JANUS A10 ENCODING ARCHAEOLOGY - THE SECRET BACK/FORTH [I0 LOGS]" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "Root:     $Root"
Write-Host "Miner:    $Miner"
Write-Host "Sidecar:  $Sidecar"
Write-Host "Run:      $RunName"
Write-Host "Output:   $OutDir"
Write-Host ""
Write-Host "WIRE / HASH / SUBMIT: FROZEN" -ForegroundColor Yellow
Write-Host "Scheduler effect: SHADOW ONLY in this build" -ForegroundColor Yellow
Write-Host "The Secret model: goal -> attention filter -> belief/resistance -> back/forth intention" -ForegroundColor Yellow
Write-Host "Randomized mirror control: untouched" -ForegroundColor Yellow
Write-Host "Logs are written directly to I0\sidecar" -ForegroundColor Yellow
Write-Host "Public safety: set JANUS_PUBLIC_LIVE_ACK=YES and RBLGANUL_USER before any live run." -ForegroundColor Yellow
if ($env:AVENGERS_NAS_JANUS_ROOT) {
    Write-Host "NAS corpus mirror: $env:AVENGERS_NAS_JANUS_ROOT"
} else {
    Write-Host "NAS corpus mirror: OFF - map NAS Janus share to J: or set AVENGERS_NAS_JANUS_ROOT"
}
Write-Host ""

if (-not (Test-Path -LiteralPath $Miner)) {
    Write-Host "ERROR: Miner file not found:" -ForegroundColor Red
    Write-Host $Miner -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}
if (-not (Test-Path -LiteralPath $Sidecar)) {
    Write-Host "ERROR: Sidecar file not found:" -ForegroundColor Red
    Write-Host $Sidecar -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

if ($env:JANUS_PUBLIC_LIVE_ACK -ne "YES") {
    Write-Host "This public launcher can connect to a Stratum pool." -ForegroundColor Yellow
    Write-Host "Set JANUS_PUBLIC_LIVE_ACK=YES and RBLGANUL_USER before running it live." -ForegroundColor Yellow
    Read-Host "Press Enter to close"
    exit 2
}

if (-not $env:RBLGANUL_USER) {
    Write-Host "ERROR: RBLGANUL_USER is not set." -ForegroundColor Red
    Write-Host "Example: `$env:RBLGANUL_USER='YOUR_WORKER_NAME'" -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 2
}

python --version
Write-Host ""
Write-Host "Starting Secret Back/Forth sidecar wrapper..." -ForegroundColor Green
Write-Host "Press Ctrl+C in this WT window to stop." -ForegroundColor Green
Write-Host ""

& python -u $Sidecar run `
  --target $Miner `
  --run-name $RunName `
  --output-dir $OutDir `
  -- `
  --io-run-name $RunName `
  --janus-glyph-accepted-link-min-z 28 `
  --tail-z 28

$code = $LASTEXITCODE
Write-Host ""
Write-Host "Process ended with code $code. Press Enter to close." -ForegroundColor Yellow
Read-Host
exit $code
