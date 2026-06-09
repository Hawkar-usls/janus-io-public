@echo off
chcp 65001 >nul
title JANUS A10 ENCODING ARCHAEOLOGY ISOLATED [YAKSA]
color 0A

cd /d "%~dp0"

set "MINER=%~dp0RBLGANUL_A10_ENCODING_ARCHAEOLOGY_V32_ACTIVE_TRIUNE_50_50_IO_SINGLE.py"
set "RUNNAME=A10_ENCODING_ARCHAEOLOGY_THE_AVENGERS"

if not defined AVENGERS_RESUME_CORPUS set "AVENGERS_RESUME_CORPUS=1"
if not defined AVENGERS_NAS_MIRROR_INTERVAL set "AVENGERS_NAS_MIRROR_INTERVAL=60"

echo.
echo JANUS A10 ENCODING ARCHAEOLOGY - ISOLATED LIVE RUN
echo =====================================================
echo Entry: Yaksa A10 Encoding Archaeology
echo Miner: %MINER%
echo Run name: %RUNNAME%
echo Resume corpus: %AVENGERS_RESUME_CORPUS%
echo Encoding probe: ON
echo Entropy baseline: ON
echo Glyph classifier: ON
echo Rare glyph accepted link floor: z28
echo Wire/header/submit: FROZEN
echo Public safety: set RBLGANUL_USER before any live run.
if defined AVENGERS_NAS_JANUS_ROOT (
    echo NAS corpus mirror: %AVENGERS_NAS_JANUS_ROOT%
) else (
    echo NAS corpus mirror: OFF - set AVENGERS_NAS_JANUS_ROOT explicitly
)
echo.

if not defined JANUS_PUBLIC_LIVE_ACK (
    echo This public launcher can connect to a Stratum pool.
    echo Set JANUS_PUBLIC_LIVE_ACK=YES and RBLGANUL_USER before running it live.
    echo.
    pause
    exit /b 2
)

if not defined RBLGANUL_USER (
    echo ERROR: RBLGANUL_USER is not set.
    echo Example: set RBLGANUL_USER=YOUR_WORKER_NAME
    echo.
    pause
    exit /b 2
)

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH.
    pause
    exit /b 1
)

if not exist "%MINER%" (
    echo ERROR: Miner file not found:
    echo %MINER%
    echo.
    echo Put this .bat in the same folder as:
    echo RBLGANUL_A10_ENCODING_ARCHAEOLOGY_V32_ACTIVE_TRIUNE_50_50_IO_SINGLE.py
    pause
    exit /b 1
)

echo Starting JANUS A10 Encoding Archaeology isolated run...
echo.

if /I "%YAKSA_NO_WT%"=="1" goto direct_run

where wt >nul 2>&1
if errorlevel 1 (
    goto direct_run
) else (
    wt -w 0 powershell -NoExit -NoProfile -ExecutionPolicy Bypass -Command "& python '%MINER%' --io-run-name '%RUNNAME%' --janus-glyph-accepted-link-min-z 28 --tail-z 28 %*"
    exit /b 0
)

:direct_run
    python "%MINER%" --io-run-name "%RUNNAME%" --janus-glyph-accepted-link-min-z 28 --tail-z 28 %*
    pause
    exit /b %ERRORLEVEL%
