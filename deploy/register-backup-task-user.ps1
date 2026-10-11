<#
Registra el backup diario SIN permisos de administrador: una Tarea Programada que corre con tu
usuario de Windows (solo cuando hay una sesion abierta; si la PC estaba apagada a la hora, corre
apenas esta disponible). Las credenciales se leen de backend\.env al ejecutarse: no se guardan
en la tarea.

Si puedes usar administrador, register-backup-task.ps1 (cuenta SYSTEM) es mas robusto.

Uso:
  .\register-backup-task-user.ps1
  .\register-backup-task-user.ps1 -BackupDir "D:\MultitecBackups" -Time "13:00"
#>

param(
    [string]$EnvFile = (Join-Path (Split-Path $PSScriptRoot -Parent) "backend\.env"),
    # Fuera del repositorio a proposito: asi un `git add` nunca sube datos de clientes.
    [string]$BackupDir = (Join-Path $env:USERPROFILE "MultitecBackups"),
    # Segunda copia fuera de este disco (disco externo, OneDrive PERSONAL ya iniciado, unidad de
    # red). Evita la carpeta de OneDrive de una cuenta de trabajo/escuela: los datos de clientes
    # quedarian en la nube de otra organizacion.
    [string]$CopyTo,
    [string]$TaskName = "MultitecPostgresBackup",
    [string]$Time = "02:00"
)

$scriptPath = Join-Path $PSScriptRoot "backup-postgres.ps1"
if (-not (Test-Path $EnvFile)) { throw "No se encontro $EnvFile" }

$argumentList = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptPath`" -EnvFile `"$EnvFile`" -BackupDir `"$BackupDir`""
if ($CopyTo) { $argumentList += " -CopyTo `"$CopyTo`"" }
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argumentList
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
$user = "$env:USERDOMAIN\$env:USERNAME"
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 1)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Backup diario de la base de datos Multitec (pg_dump)" -Force | Out-Null

Write-Output "Tarea '$TaskName' registrada: corre todos los dias a las $Time con el usuario $user."
Write-Output "Respaldos en: $BackupDir"
Write-Output "Prueba manual: Start-ScheduledTask -TaskName '$TaskName'"
