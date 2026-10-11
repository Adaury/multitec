@echo off
REM Doble clic: pide permiso de administrador (aviso azul/amarillo de Windows -> "Si") y deja
REM PostgreSQL funcionando como servicio de Windows, para que arranque solo al encender la PC.
REM Hace lo mismo que enable-postgres-service.ps1, sin tener que abrir PowerShell a mano.
REM La ventana que se abre se queda abierta para que puedas leer el resultado.

set "SCRIPT=%~dp0enable-postgres-service.ps1"
if not exist "%SCRIPT%" (
  echo No se encontro %SCRIPT%
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile -ExecutionPolicy Bypass -NoExit -File \"%SCRIPT%\"'"
