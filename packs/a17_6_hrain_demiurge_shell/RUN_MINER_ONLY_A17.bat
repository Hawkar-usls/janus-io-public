@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"
where wt.exe >nul 2>nul
if %errorlevel%==0 (
  start "" wt.exe -w 0 nt powershell.exe -NoExit -NoProfile -ExecutionPolicy Bypass -File "%~dp0A17_RUN_A14_2_EXACT.ps1" -PackRoot "%~dp0"
  exit /b 0
)
powershell.exe -NoExit -NoProfile -ExecutionPolicy Bypass -File "%~dp0A17_RUN_A14_2_EXACT.ps1" -PackRoot "%~dp0"
