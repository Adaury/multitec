@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy\multitec.ps1" -Action status
echo.
pause
