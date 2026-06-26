param([Parameter(Mandatory=$true)][string]$PackRoot)
$ErrorActionPreference="Continue"
try{[Console]::OutputEncoding=[System.Text.Encoding]::UTF8}catch{}
$host.UI.RawUI.WindowTitle="A17 :: HRAIN DEMIURGE SHELL"
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " A17 :: HRAIN DEMIURGE SIDECAR SHELL" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "[A17.5] HRain bubble/caviar/spore UI + semantic sidecar + Markov memory." -ForegroundColor Green
Write-Host "[A17.5] Observer-only. NOT stratum proxy. Output-only bias." -ForegroundColor Yellow
$ShellDir=Join-Path $PackRoot "A17_HRAIN_DEMIURGE_SHELL"
$Serve=Join-Path $ShellDir "serve_a17_hrain_shell.py"
if(-not(Test-Path -LiteralPath $Serve)){Write-Host "[A17.5] ERROR missing server:" -ForegroundColor Red;Write-Host $Serve -ForegroundColor Red;Read-Host "Enter";exit 1}
$PyExe=$null;$PyPrefix=@()
if(Get-Command py -ErrorAction SilentlyContinue){$PyExe="py";$PyPrefix=@("-3")}
elseif(Get-Command python -ErrorAction SilentlyContinue){$PyExe="python";$PyPrefix=@()}
else{Write-Host "[A17.5] ERROR Python not found." -ForegroundColor Red;Read-Host "Enter";exit 1}
Set-Location -LiteralPath $ShellDir
& $PyExe @PyPrefix $Serve --root $PackRoot
$ExitCode=$LASTEXITCODE
Write-Host "[A17.5] HRain Demiurge exit code: $ExitCode" -ForegroundColor Yellow
Read-Host "Press Enter to close A17 shell tab"
exit $ExitCode
