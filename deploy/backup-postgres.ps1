<#
Backup diario de la base de datos Postgres de Multitec. Guarda un dump comprimido con
fecha en el nombre y borra los backups más viejos que -RetentionDays.

Uso manual:
  .\backup-postgres.ps1 -PgBinPath "C:\Program Files\PostgreSQL\17\bin" `
    -PgHost 127.0.0.1 -PgUser multitec -PgDatabase multitec -PgPassword "..." `
    -BackupDir "D:\MultitecBackups"

Para automatizarlo, usa register-backup-task.ps1 (registra esto como tarea programada
diaria) — ajusta los mismos parámetros ahí.
#>

param(
    [string]$PgBinPath = "C:\Program Files\PostgreSQL\17\bin",
    [string]$PgHost = "127.0.0.1",
    [string]$PgPort = "5432",
    [string]$PgUser = "multitec",
    [string]$PgDatabase = "multitec",
    [Parameter(Mandatory = $true)][string]$PgPassword,
    [string]$BackupDir = (Join-Path $PSScriptRoot "backups"),
    [int]$RetentionDays = 14
)

$pgDump = Join-Path $PgBinPath "pg_dump.exe"
if (-not (Test-Path $pgDump)) {
    throw "No se encontró pg_dump.exe en $PgBinPath"
}

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$outFile = Join-Path $BackupDir "multitec_$timestamp.dump"

$env:PGPASSWORD = $PgPassword
& $pgDump -h $PgHost -p $PgPort -U $PgUser -d $PgDatabase -F custom -f $outFile
$exitCode = $LASTEXITCODE
Remove-Item Env:\PGPASSWORD

if ($exitCode -ne 0) {
    throw "pg_dump terminó con código $exitCode"
}

Write-Output "Backup creado: $outFile"

$cutoff = (Get-Date).AddDays(-$RetentionDays)
Get-ChildItem -Path $BackupDir -Filter "multitec_*.dump" |
    Where-Object { $_.LastWriteTime -lt $cutoff } |
    ForEach-Object {
        Remove-Item $_.FullName -Force
        Write-Output "Backup viejo eliminado: $($_.Name)"
    }
