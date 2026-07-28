@echo off
setlocal
cd /d "%~dp0"
title ARIA Language Laboratory

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0aria.ps1" doctor -Strict
if errorlevel 1 goto :failed

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0aria.ps1" run "%~dp0examples\hello.aria" -Strict
if errorlevel 1 goto :failed

echo.
echo   ARIA is ready. Use aria.cmd help for the command lattice.
echo.
pause
exit /b 0

:failed
echo.
echo   ARIA gate rejected the launch. Re-run with -VerboseOutput for raw diagnostics.
echo.
pause
exit /b 1
