@echo off
REM Exporta los datos de esta PC (base, fotos y configuracion) para llevarlos al servidor. Contiene datos de clientes.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy\exportar-datos.ps1"
echo.
pause
