$ErrorActionPreference="Continue"
try{[Console]::OutputEncoding=[System.Text.Encoding]::UTF8}catch{}
$PackRoot=Split-Path -Parent $MyInvocation.MyCommand.Path
$host.UI.RawUI.WindowTitle="A17 FULL STACK ORCHESTRATOR"
Write-Host "============================================================" -ForegroundColor Magenta
Write-Host " A17.6 HRAIN DEMIURGE REPO-READY ORCHESTRATOR" -ForegroundColor Magenta
Write-Host "============================================================" -ForegroundColor Magenta
Write-Host "[A17.6] Local/private A14.2 pack -> A17 HRain Demiurge Shell." -ForegroundColor Green
Write-Host "[A17.6] Public pack omits raw runs, proofs, logs, and credentials." -ForegroundColor Green
Write-Host "[A17.5] Sidecar shell is observer-only. WIRE/HASH/SUBMIT frozen. Mirror untouched." -ForegroundColor Yellow
Write-Host "[A17.5] PackRoot: $PackRoot" -ForegroundColor DarkCyan
$A14=Join-Path $PackRoot "A17_RUN_A14_2_EXACT.ps1"
$Shell=Join-Path $PackRoot "A17_RUN_HRAIN_DEMIURGE_SHELL.ps1"
$Required=@(
  (Join-Path $PackRoot "A14_2_PURE_ROUTE_LOCK_PACK\Yaksa_A14_2_PURE_ROUTE_LOCK_MINER.ps1"),
  (Join-Path $PackRoot "A17_HRAIN_DEMIURGE_SHELL\serve_a17_hrain_shell.py"),
  (Join-Path $PackRoot "A17_HRAIN_DEMIURGE_SHELL\a17_sidecar_shell_worker.py"),
  (Join-Path $PackRoot "A17_HRAIN_DEMIURGE_SHELL\index.html"),
  $A14,$Shell
)
$Missing=@()
foreach($p in $Required){if(-not(Test-Path -LiteralPath $p)){$Missing+=$p}}
if($Missing.Count -gt 0){
  Write-Host "[A17.5] ERROR missing embedded files:" -ForegroundColor Red
  foreach($m in $Missing){Write-Host "  $m" -ForegroundColor Red}
  Read-Host "Press Enter"
  exit 1
}
function StartTab([string]$File,[string]$Name){
  $qFile='"'+$File+'"';$qRoot='"'+$PackRoot+'"'
  if(Get-Command wt.exe -ErrorAction SilentlyContinue){
    $args="-w 0 nt powershell.exe -NoExit -NoProfile -ExecutionPolicy Bypass -File $qFile -PackRoot $qRoot"
    Write-Host "[A17.5] WT start ${Name}: $args" -ForegroundColor Cyan
    Start-Process -FilePath "wt.exe" -ArgumentList $args | Out-Null
  }else{
    $args="-NoExit -NoProfile -ExecutionPolicy Bypass -File $qFile -PackRoot $qRoot"
    Write-Host "[A17.5] PowerShell fallback start $Name" -ForegroundColor Yellow
    Start-Process -FilePath "powershell.exe" -ArgumentList $args | Out-Null
  }
}
Write-Host "[A17.5] Starting embedded A14.2 miner-only..." -ForegroundColor Cyan
StartTab $A14 "A14.2"
Write-Host "[A17.5] Waiting 12 seconds so miner creates live files..." -ForegroundColor Cyan
Start-Sleep -Seconds 12
Write-Host "[A17.5] Starting HRain Demiurge Sidecar Shell..." -ForegroundColor Cyan
StartTab $Shell "HRAIN"
Write-Host ""
Write-Host "[A17.5] FULL STACK STARTED." -ForegroundColor Green
Write-Host "[A17.5] Expected windows/tabs:" -ForegroundColor Green
Write-Host "  1) A17 :: A14.2 MINER EXACT"
Write-Host "  2) A17 :: HRAIN DEMIURGE SHELL"
Write-Host ""
Write-Host "[A17.5] Browser:" -ForegroundColor Yellow
Write-Host "  http://127.0.0.1:8797/index.html"
Read-Host "Press Enter to close ORCHESTRATOR tab"
