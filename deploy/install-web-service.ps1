#Requires -RunAsAdministrator
<#
Instala Caddy (frontend estático + reverse proxy hacia el backend) como servicio de
Windows "MultitecWeb" usando NSSM, apuntando a deploy\Caddyfile.

Requisitos antes de correr esto:
  - frontend\dist construido: cd frontend && npm run build
  - Caddy instalado: winget install --id CaddyServer.Caddy -e
  - deploy\Caddyfile ajustado (dominio real, o "tls internal" para red local — ver
    comentarios en el archivo).
  - MultitecBackend ya corriendo (install-backend-service.ps1), ya que Caddy le hace
    proxy a 127.0.0.1:8000.
#>

param(
    [string]$RepoRoot = (Resolve-Path "$PSScriptRoot\..").Path,
    [string]$ServiceName = "MultitecWeb"
)

$nssm = (Get-Command nssm -ErrorAction SilentlyContinue).Source
if (-not $nssm) {
    throw "nssm no está en el PATH. Instálalo con: winget install --id NSSM.NSSM -e (y abre una terminal nueva)."
}

$caddy = (Get-Command caddy -ErrorAction SilentlyContinue).Source
if (-not $caddy) {
    throw "caddy no está en el PATH. Instálalo con: winget install --id CaddyServer.Caddy -e (y abre una terminal nueva)."
}

$deployDir = Join-Path $RepoRoot "deploy"
$distDir = Join-Path $RepoRoot "frontend\dist"
if (-not (Test-Path $distDir)) {
    throw "No se encontró $distDir — corre 'npm run build' en frontend\ primero."
}

$logDir = Join-Path $deployDir "logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

& $nssm install $ServiceName $caddy "run --config Caddyfile"
& $nssm set $ServiceName AppDirectory $deployDir
& $nssm set $ServiceName AppStdout (Join-Path $logDir "web.out.log")
& $nssm set $ServiceName AppStderr (Join-Path $logDir "web.err.log")
& $nssm set $ServiceName AppRotateFiles 1
& $nssm set $ServiceName AppRotateBytes 10485760
& $nssm set $ServiceName Start SERVICE_AUTO_START
& $nssm set $ServiceName AppExit Default Restart
& $nssm set $ServiceName AppRestartDelay 5000

Start-Service $ServiceName
Start-Sleep -Seconds 3
Get-Service $ServiceName | Format-List Name, Status, StartType

Write-Output ""
Write-Output "Recuerda abrir el firewall para 443/80 (o el puerto que definas en el Caddyfile):"
Write-Output '  New-NetFirewallRule -DisplayName "Multitec HTTPS" -Direction Inbound -LocalPort 443 -Protocol TCP -Action Allow'
Write-Output '  New-NetFirewallRule -DisplayName "Multitec HTTP" -Direction Inbound -LocalPort 80 -Protocol TCP -Action Allow'
