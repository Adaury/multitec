#Requires -RunAsAdministrator
<#
Registra una Tarea Programada de Windows que corre backup-postgres.ps1 todos los días
a las 2:00 AM. Ajusta -PgPassword (y el resto de parámetros si aplica) a los valores
reales de producción.
#>

param(
    [Parameter(Mandatory = $true)][string]$PgPassword,
    [string]$PgUser = "multitec",
    [string]$PgDatabase = "multitec",
    [string]$BackupDir = (Join-Path $PSScriptRoot "backups"),
    [string]$TaskName = "MultitecPostgresBackup",
    [string]$Time = "02:00"
)

$scriptPath = Join-Path $PSScriptRoot "backup-postgres.ps1"
$argumentList = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" -PgUser `"$PgUser`" -PgDatabase `"$PgDatabase`" -BackupDir `"$BackupDir`" -PgPassword `"$PgPassword`""

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argumentList
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null

Write-Output "Tarea '$TaskName' registrada — corre todos los días a las $Time."
Write-Output "Prueba manual: Start-ScheduledTask -TaskName '$TaskName'"
