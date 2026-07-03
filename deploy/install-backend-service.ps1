#Requires -RunAsAdministrator
<#
Instala el backend de Multitec (uvicorn) como servicio de Windows "MultitecBackend"
usando NSSM. Corre en 127.0.0.1:8000 (Caddy hace de reverse proxy hacia afuera — el
backend nunca debe quedar expuesto directamente a la red).

Requisitos antes de correr esto:
  - venv creado e instalado en backend\venv (ver README, sección "Backend — arrancar en
    desarrollo").
  - backend\.env configurado para producción (DATABASE_URL a Postgres real, JWT_SECRET
    y ADMIN_PASSWORD cambiados, CORS_ORIGINS con el dominio real).
  - NSSM instalado: winget install --id NSSM.NSSM -e
#>

param(
    [string]$RepoRoot = (Resolve-Path "$PSScriptRoot\..").Path,
    [string]$ServiceName = "MultitecBackend"
)

$nssm = (Get-Command nssm -ErrorAction SilentlyContinue).Source
if (-not $nssm) {
    throw "nssm no está en el PATH. Instálalo con: winget install --id NSSM.NSSM -e (y abre una terminal nueva)."
}

$backendDir = Join-Path $RepoRoot "backend"
$uvicorn = Join-Path $backendDir "venv\Scripts\uvicorn.exe"
if (-not (Test-Path $uvicorn)) {
    throw "No se encontró $uvicorn — crea el venv e instala requirements.txt primero."
}

$logDir = Join-Path $backendDir "logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

& $nssm install $ServiceName $uvicorn "app.main:app --host 127.0.0.1 --port 8000"
& $nssm set $ServiceName AppDirectory $backendDir
& $nssm set $ServiceName AppStdout (Join-Path $logDir "backend.out.log")
& $nssm set $ServiceName AppStderr (Join-Path $logDir "backend.err.log")
& $nssm set $ServiceName AppRotateFiles 1
& $nssm set $ServiceName AppRotateBytes 10485760
& $nssm set $ServiceName Start SERVICE_AUTO_START
& $nssm set $ServiceName AppExit Default Restart
& $nssm set $ServiceName AppRestartDelay 5000

Start-Service $ServiceName
Start-Sleep -Seconds 3
Get-Service $ServiceName | Format-List Name, Status, StartType

Write-Output ""
Write-Output "Prueba: Invoke-WebRequest http://127.0.0.1:8000/api/health"
