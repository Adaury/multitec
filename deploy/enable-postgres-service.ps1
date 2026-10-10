#Requires -RunAsAdministrator
<#
Deja PostgreSQL corriendo como servicio de Windows (arranca con la PC, sin depender de que alguien
inicie sesion). Sirve cuando el servicio esta deshabilitado y la base se levanto a mano con
pg_ctl o con la tarea programada "PostgreSQL17-Autostart".

Que hace, en orden:
  1. Apaga la instancia manual de PostgreSQL (si hay una) de forma limpia.
  2. Pone el servicio en inicio Automatico y lo arranca.
  3. Comprueba que el puerto 5432 responde.
  4. Deshabilita la tarea programada de arranque manual, para que no choque con el servicio.

Uso: clic derecho en PowerShell -> "Ejecutar como administrador", y luego:
  cd C:\laragon\www\multitec\deploy
  powershell -ExecutionPolicy Bypass -File .\enable-postgres-service.ps1

Si algo falla, la base sigue intacta: solo se apaga y se vuelve a encender. Para volver al metodo
anterior: Set-Service postgresql-x64-17 -StartupType Disabled y
Enable-ScheduledTask -TaskName PostgreSQL17-Autostart.
#>

param(
    [string]$ServiceName = "postgresql-x64-17",
    [string]$PgBinPath = "C:\Program Files\PostgreSQL\17\bin",
    [string]$DataDir = "C:\Program Files\PostgreSQL\17\data",
    [string]$AutostartTask = "PostgreSQL17-Autostart",
    [int]$Port = 5432
)

$ErrorActionPreference = "Stop"
$pgCtl = Join-Path $PgBinPath "pg_ctl.exe"

function Test-PgPort {
    try {
        $c = New-Object System.Net.Sockets.TcpClient
        $c.Connect("127.0.0.1", $Port)
        $c.Close()
        return $true
    } catch { return $false }
}

$svc = Get-Service -Name $ServiceName -ErrorAction Stop
Write-Output "Servicio ${ServiceName}: estado=$($svc.Status)"

# 1) Apagar la instancia manual, si la hay (dos servidores no pueden compartir la misma carpeta de datos).
if ($svc.Status -ne "Running" -and (Test-PgPort)) {
    Write-Output "Hay una instancia manual de PostgreSQL corriendo; se apaga de forma limpia..."
    & $pgCtl stop -D $DataDir -m fast -w -t 60
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo apagar la instancia manual (pg_ctl codigo $LASTEXITCODE). Cierrala y repite."
    }
}

# 2) Servicio automatico y arranque.
Set-Service -Name $ServiceName -StartupType Automatic
if ((Get-Service $ServiceName).Status -ne "Running") {
    Start-Service -Name $ServiceName
}
$null = (Get-Service $ServiceName).WaitForStatus("Running", [TimeSpan]::FromSeconds(60))

# 3) Verificacion.
$ok = $false
for ($i = 0; $i -lt 20 -and -not $ok; $i++) {
    $ok = Test-PgPort
    if (-not $ok) { Start-Sleep -Seconds 1 }
}
if (-not $ok) { throw "El servicio arranco pero el puerto $Port no responde. Revisa $DataDir\log." }

# 4) Evitar el doble arranque.
$task = Get-ScheduledTask -TaskName $AutostartTask -ErrorAction SilentlyContinue
if ($task) {
    Disable-ScheduledTask -TaskName $AutostartTask | Out-Null
    Write-Output "Tarea '$AutostartTask' deshabilitada (el servicio ya arranca solo)."
}

$final = Get-Service $ServiceName
Write-Output ""
Write-Output "LISTO: $ServiceName -> estado=$($final.Status), inicio=$($final.StartType), puerto $Port respondiendo."
