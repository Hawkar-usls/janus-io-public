[CmdletBinding()]
param([double]$DurationSeconds=20,[double]$IntervalSeconds=0.5)
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Python=(Get-Command python -ErrorAction Stop).Source
$Output=Join-Path $Root 'output';New-Item -ItemType Directory -Force -Path $Output|Out-Null
Write-Host ''
Write-Host 'JANUS A18.43 — SYSTEM MONITOR BRIDGE PREFLIGHT' -ForegroundColor Cyan
Write-Host 'OpenHardwareMonitor + NVML/nvidia-smi + psutil' -ForegroundColor Green
Write-Host 'READ-ONLY: no miner, no fan/voltage/clock control.' -ForegroundColor Yellow
Write-Host ''
& $Python (Join-Path $Root 'a18_43_preflight.py') --output $Output --duration-seconds $DurationSeconds --interval-seconds $IntervalSeconds
$Code=$LASTEXITCODE
Write-Host ''
Write-Host ('A18_43_PREFLIGHT_EXIT='+$Code)
Write-Host ('Report: '+(Join-Path $Output 'A18_43_PREFLIGHT_REPORT.json')) -ForegroundColor Cyan
Write-Host ('Baseline: '+(Join-Path $Output 'HARDWARE_BASELINE_SUMMARY.json')) -ForegroundColor Cyan
Write-Host ('Inventory: '+(Join-Path $Output 'SENSOR_INVENTORY.json')) -ForegroundColor Cyan
exit $Code
