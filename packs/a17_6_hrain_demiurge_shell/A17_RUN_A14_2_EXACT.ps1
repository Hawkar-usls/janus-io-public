param([Parameter(Mandatory=$true)][string]$PackRoot)
$ErrorActionPreference="Continue"
try{[Console]::OutputEncoding=[System.Text.Encoding]::UTF8}catch{}
$host.UI.RawUI.WindowTitle="A17 :: A14.2 MINER EXACT"
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " A17 :: A14.2 PURE ROUTE MINER EXACT" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "[A17.5] Embedded miner-only. Sidecar OFF in miner tab." -ForegroundColor Green
Write-Host "[A17.5] WIRE/HASH/SUBMIT frozen. Mirror untouched." -ForegroundColor Yellow
$A14Dir=Join-Path $PackRoot "A14_2_PURE_ROUTE_LOCK_PACK"
$Miner=Join-Path $A14Dir "Yaksa_A14_2_PURE_ROUTE_LOCK_MINER.ps1"
if(-not(Test-Path -LiteralPath $Miner)){Write-Host "[A17.5] ERROR missing miner launcher:" -ForegroundColor Red;Write-Host $Miner -ForegroundColor Red;Read-Host "Enter";exit 1}
Set-Location -LiteralPath $A14Dir
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Miner
$ExitCode=$LASTEXITCODE
Write-Host "[A17.5] A14.2 exit code: $ExitCode" -ForegroundColor Yellow
Read-Host "Press Enter to close A14.2 tab"
exit $ExitCode
