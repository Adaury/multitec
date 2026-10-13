@echo off
REM Arranca Multitec (backend + web) en segundo plano, sin ventanas ni procesos huerfanos.
REM Para detenerlo: detener-multitec.bat   |   Para ver el estado: estado-multitec.bat
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy\multitec.ps1" -Action restart
echo.
pause
