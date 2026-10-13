@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy\multitec.ps1" -Action tunnel-stop
echo.
pause
