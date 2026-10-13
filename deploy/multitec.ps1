<#
.SYNOPSIS
  Arranca, detiene y revisa Multitec (backend + web) sin dejar procesos huérfanos.

.DESCRIPTION
  El problema de arrancar con "uvicorn --reload" en ventanas sueltas: al cerrar la ventana queda un
  proceso hijo vivo ocupando el puerto 8000 con el código viejo, y el servidor "nuevo" nunca llega a
  escuchar. Aquí se detiene por PUERTO (quien escuche en 8000/5173, con todo su árbol) y se arranca
  sin --reload, en segundo plano y con logs en backend\logs.

  Uso:   powershell -ExecutionPolicy Bypass -File deploy\multitec.ps1 -Action start|stop|restart|status
  Tras cambiar código del backend hay que hacer "restart" (sin --reload no se recarga solo).
#>
param(
    [ValidateSet('start', 'stop', 'restart', 'status', 'tunnel', 'tunnel-stop')]
    [string]$Action = 'status',
    [int]$BackendPort = 8000,
    [int]$WebPort = 5173
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $Root 'backend'
$WebDir = Join-Path $Root 'frontend'
$LogDir = Join-Path $BackendDir 'logs'
$Python = Join-Path $BackendDir 'venv\Scripts\python.exe'

function Get-ListenerPids([int]$Port) {
    @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique)
}

function Stop-Port([int]$Port, [string]$Label) {
    $pids = Get-ListenerPids $Port
    if ($pids.Count -eq 0) {
        Write-Host "  $Label (puerto $Port): ya estaba detenido"
        return
    }
    foreach ($procId in $pids) {
        # /T mata también a los hijos (el worker de uvicorn, node bajo npm...).
        & taskkill.exe /PID $procId /T /F | Out-Null
    }
    # Un hijo huérfano puede tardar un instante en soltar el puerto.
    for ($i = 0; $i -lt 20 -and (Get-ListenerPids $Port).Count -gt 0; $i++) { Start-Sleep -Milliseconds 250 }
    $left = Get-ListenerPids $Port
    if ($left.Count -gt 0) {
        foreach ($procId in $left) { & taskkill.exe /PID $procId /F | Out-Null }
        Start-Sleep -Milliseconds 500
    }
    if ((Get-ListenerPids $Port).Count -gt 0) { throw "No se pudo liberar el puerto $Port." }
    Write-Host "  $Label (puerto $Port): detenido"
}

function Test-Health([string]$Url) {
    try { (Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3).StatusCode -eq 200 } catch { $false }
}

function Wait-Health([string]$Url, [int]$Seconds) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Health $Url) { return $true }
        Start-Sleep -Milliseconds 700
    }
    return $false
}

function Stop-Multitec {
    Write-Host 'Deteniendo Multitec...'
    Stop-Port $WebPort 'Web'
    Stop-Port $BackendPort 'Backend'
}

function Start-Multitec {
    if (-not (Test-Path $Python)) { throw "No encuentro el Python del backend: $Python" }
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

    Write-Host 'Iniciando backend...'
    Start-Process -FilePath $Python `
        -ArgumentList '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', $BackendPort `
        -WorkingDirectory $BackendDir -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $LogDir 'uvicorn-out.log') `
        -RedirectStandardError (Join-Path $LogDir 'uvicorn-err.log')
    if (-not (Wait-Health "http://127.0.0.1:$BackendPort/api/health" 45)) {
        throw "El backend no respondió en 45 s. Revisa $LogDir\uvicorn-err.log"
    }
    Write-Host "  Backend listo: http://127.0.0.1:$BackendPort"

    Write-Host 'Compilando la web (unos 30 s)...'
    $build = Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', 'npm run build' -WorkingDirectory $WebDir `
        -WindowStyle Hidden -Wait -PassThru `
        -RedirectStandardOutput (Join-Path $LogDir 'web-build.log') `
        -RedirectStandardError (Join-Path $LogDir 'web-build-err.log')
    if ($build.ExitCode -ne 0) { throw "La compilacion de la web fallo. Revisa $LogDirweb-build.log" }

    Write-Host 'Iniciando web...'
    Start-Process -FilePath 'cmd.exe' `
        -ArgumentList '/c', "npm run preview -- --port $WebPort --strictPort" `
        -WorkingDirectory $WebDir -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $LogDir 'web-out.log') `
        -RedirectStandardError (Join-Path $LogDir 'web-err.log')
    if (-not (Wait-Health "http://127.0.0.1:$WebPort/" 60)) {
        throw "La web no respondió en 60 s. Revisa $LogDir\web-err.log"
    }
    Write-Host "  Web lista: http://localhost:$WebPort"
}

function Show-Status {
    $api = Test-Health "http://127.0.0.1:$BackendPort/api/health"
    $web = Test-Health "http://127.0.0.1:$WebPort/"
    Write-Host 'Estado de Multitec:'
    Write-Host ("  Backend  (:{0}): {1}" -f $BackendPort, $(if ($api) { 'FUNCIONANDO' } else { 'detenido' }))
    Write-Host ("  Web      (:{0}): {1}" -f $WebPort, $(if ($web) { 'FUNCIONANDO' } else { 'detenida' }))
    $ollama = try { (Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 2).models.Count } catch { $null }
    Write-Host ("  IA local (Ollama): {0}" -f $(if ($null -ne $ollama) { "FUNCIONANDO ($ollama modelos)" } else { 'apagada' }))
    $disk = Get-PSDrive -Name C -ErrorAction SilentlyContinue
    if ($disk) { Write-Host ("  Disco C: libres {0:N1} GB" -f ($disk.Free / 1GB)) }
}

function Get-TunnelUrl {
    try {
        ((Invoke-RestMethod -Uri 'http://127.0.0.1:4040/api/tunnels' -TimeoutSec 3).tunnels |
            Where-Object { $_.public_url -like 'https://*' } | Select-Object -First 1).public_url
    } catch { $null }
}

function Start-Tunnel {
    # El tunel publica la web en internet: solo se abre a pedido, nunca junto con "start".
    if (-not (Test-Health "http://127.0.0.1:$WebPort/")) { throw 'La web no esta funcionando. Ejecuta primero iniciar-multitec.bat' }
    $url = Get-TunnelUrl
    if (-not $url) {
        New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
        Start-Process -FilePath 'ngrok' -ArgumentList 'http', $WebPort, '--log=stdout' -WindowStyle Hidden `
            -RedirectStandardOutput (Join-Path $LogDir 'ngrok-out.log') `
            -RedirectStandardError (Join-Path $LogDir 'ngrok-err.log')
        for ($i = 0; $i -lt 30 -and -not $url; $i++) { Start-Sleep -Milliseconds 500; $url = Get-TunnelUrl }
    }
    if (-not $url) { throw "El tunel no abrio. Revisa $LogDir
grok-out.log" }
    Write-Host ''
    Write-Host "  Direccion publica: $url"
    Write-Host '  (La primera vez ngrok muestra un aviso: toca "Visit Site".)'
    Write-Host '  Esta direccion cambia cada vez que se reinicia el tunel.'
}

function Stop-Tunnel {
    Get-Process -Name ngrok -ErrorAction SilentlyContinue | Stop-Process -Force
    Write-Host '  Tunel cerrado: la app ya no es visible desde internet.'
}

switch ($Action) {
    'stop'    { Stop-Multitec }
    'start'   { Stop-Multitec; Start-Multitec; Show-Status }
    'restart' { Stop-Multitec; Start-Multitec; Show-Status }
    'status'  { Show-Status; $t = Get-TunnelUrl; Write-Host ("  Tunel: {0}" -f $(if ($t) { $t } else { 'cerrado' })) }
    'tunnel'  { Start-Tunnel }
    'tunnel-stop' { Stop-Tunnel }
}
