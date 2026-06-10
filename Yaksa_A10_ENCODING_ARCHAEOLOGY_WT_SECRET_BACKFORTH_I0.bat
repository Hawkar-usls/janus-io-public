@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "BRIDGE=%~dp0Yaksa_A10_ENCODING_ARCHAEOLOGY_WT_SECRET_BACKFORTH_I0_BRIDGE.ps1"
set "SIDECAR=%~dp0A10_GLYPH_ECOLOGY_SECRET_BACKFORTH_SIDECAR.py"
set "MINER=%~dp0RBLGANUL_A10_ENCODING_ARCHAEOLOGY_V32_ACTIVE_TRIUNE_50_50_IO_SINGLE.py"

if not exist "%MINER%" (
    echo ERROR: Miner file not found:
    echo %MINER%
    pause
    exit /b 1
)

if not exist "%SIDECAR%" (
    echo ERROR: Secret Back/Forth sidecar file not found:
    echo %SIDECAR%
    pause
    exit /b 1
)

if not exist "%BRIDGE%" (
    echo ERROR: Bridge file not found:
    echo %BRIDGE%
    pause
    exit /b 1
)

if /I "%YAKSA_NO_WT%"=="1" goto direct_powershell

where wt >nul 2>&1
if errorlevel 1 goto direct_powershell

wt -w 0 powershell -NoExit -NoProfile -ExecutionPolicy Bypass -File "%BRIDGE%"
exit /b 0

:direct_powershell
powershell -NoExit -NoProfile -ExecutionPolicy Bypass -File "%BRIDGE%"
exit /b 0
