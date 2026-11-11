@echo off
REM Instalador de Multitec para el servidor. Se pide permiso de administrador solo.
cd /d "%~dp0"
net session >nul 2>&1
if errorlevel 1 (
  echo Pidiendo permiso de administrador...
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy\instalar-servidor.ps1" %*
echo.
pause
