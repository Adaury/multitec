@echo off
REM Un solo archivo con TODO para el servidor: programa, imagenes, videos y los datos de esta PC.
REM Tiene datos de clientes: llevarlo en USB y borrarlo cuando el servidor funcione.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy\empaquetar.ps1" -ConDatos
echo.
pause
