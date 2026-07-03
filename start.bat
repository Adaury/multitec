@echo off
REM Arranca el backend (FastAPI/uvicorn) y el frontend (Vite) cada uno en su propia ventana.
setlocal
set ROOT=%~dp0

start "Multitec - Backend" cmd /k "cd /d "%ROOT%backend" && venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"
start "Multitec - Frontend" cmd /k "cd /d "%ROOT%frontend" && npm run dev"

echo Backend:  http://localhost:8000/docs
echo Frontend: http://localhost:5173
