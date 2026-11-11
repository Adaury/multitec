@echo off
REM Arma el paquete de instalacion para el servidor (sin datos ni claves) en la carpeta MultitecServidor.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy\empaquetar.ps1"
echo.
pause
