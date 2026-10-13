@echo off
REM Publica Multitec en internet (ngrok) y muestra la direccion. Para cerrarlo: cerrar-tunel-multitec.bat
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy\multitec.ps1" -Action tunnel
echo.
pause
