[CmdletBinding()]
param(
    [double]$DurationSeconds = 15,
    [double]$IntervalSeconds = 0.5
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = (Get-Command python -ErrorAction Stop).Source
$Output = Join-Path $Root 'output'
New-Item -ItemType Directory -Force -Path $Output | Out-Null
Write-Host ''
Write-Host 'JANUS A18.43 — HARDWARE PRESERVATION PREFLIGHT' -ForegroundColor Cyan
Write-Host 'READ-ONLY: no miner launch, no fan control, no voltage or clock changes.' -ForegroundColor Yellow
Write-Host 'OpenHardwareMonitor must be running as Administrator.' -ForegroundColor Yellow
Write-Host ''
& $Python (Join-Path $Root 'a18_43_preflight.py') `
  --output $Output `
  --duration-seconds $DurationSeconds `
  --interval-seconds $IntervalSeconds
$ExitCode = $LASTEXITCODE
Write-Host ''
Write-Host ('A18_43_PREFLIGHT_EXIT=' + $ExitCode)
Write-Host ('Report: ' + (Join-Path $Output 'A18_43_PREFLIGHT_REPORT.json')) -ForegroundColor Cyan
Write-Host ('Inventory: ' + (Join-Path $Output 'SENSOR_INVENTORY.json')) -ForegroundColor Cyan
Write-Host ('Samples: ' + (Join-Path $Output 'HARDWARE_SAMPLES.jsonl')) -ForegroundColor Cyan
exit $ExitCode
