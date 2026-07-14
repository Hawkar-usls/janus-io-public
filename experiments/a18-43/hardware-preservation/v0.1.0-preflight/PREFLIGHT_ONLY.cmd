@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_A18_43_PREFLIGHT.ps1"
echo.
pause
