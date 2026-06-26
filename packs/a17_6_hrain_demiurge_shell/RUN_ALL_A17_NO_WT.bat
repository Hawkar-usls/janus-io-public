@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"
powershell.exe -NoExit -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_ALL_A17.ps1"
