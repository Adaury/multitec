<#
Backup diario de la base de datos Postgres de Multitec. Guarda un dump comprimido con
fecha en el nombre y borra los backups mas viejos que -RetentionDays.

Uso manual (credenciales explicitas):
  .\backup-postgres.ps1 -PgBinPath "C:\Program Files\PostgreSQL\17\bin" `
    -PgHost 127.0.0.1 -PgUser multitec -PgDatabase multitec -PgPassword "..." `
    -BackupDir "D:\MultitecBackups"

Uso recomendado (credenciales tomadas de backend\.env, sin repetir la contrasena):
  .\backup-postgres.ps1 -EnvFile "C:\laragon\www\multitec\backend\.env" -BackupDir "D:\MultitecBackups"

Para automatizarlo: register-backup-task.ps1 (como administrador, cuenta SYSTEM) o
register-backup-task-user.ps1 (sin administrador, con tu usuario de Windows).
#>

param(
    [string]$PgBinPath = "C:\Program Files\PostgreSQL\17\bin",
    [string]$PgHost = "127.0.0.1",
    [string]$PgPort = "5432",
    [string]$PgUser = "multitec",
    [string]$PgDatabase = "multitec",
    [string]$PgPassword,
    # Si se indica, usuario, host, puerto, base y contrasena salen de DATABASE_URL en ese .env
    # (asi la contrasena no queda escrita en la definicion de la tarea programada).
    [string]$EnvFile,
    [string]$BackupDir = (Join-Path $PSScriptRoot "backups"),
    # Segunda copia fuera de este disco (disco externo, carpeta sincronizada de OneDrive personal,
    # unidad de red...). Si no esta disponible en ese momento, el backup local igual se conserva y
    # el script termina con error para que se note.
    [string]$CopyTo,
    # Carpeta de fotos, audios y firmas que sube la app. Vacia = no se respalda.
    [string]$UploadsDir = (Join-Path $PSScriptRoot "..\backend\uploads"),
    [int]$RetentionDays = 14
)

if ($EnvFile) {
    if (-not (Test-Path $EnvFile)) { throw "No se encontro el archivo $EnvFile" }
    $line = Select-String -Path $EnvFile -Pattern '^\s*DATABASE_URL\s*=\s*(.+?)\s*$' | Select-Object -First 1
    if (-not $line) { throw "DATABASE_URL no esta definida en $EnvFile" }
    $url = $line.Matches[0].Groups[1].Value
    $pattern = '^[\w+]+://(?<user>[^:@/]+)(:(?<pass>[^@]*))?@(?<host>[^:/]+)(:(?<port>\d+))?/(?<db>[^?]+)'
    if ($url -notmatch $pattern) { throw "DATABASE_URL no es una URL de PostgreSQL valida" }
    $PgUser = [uri]::UnescapeDataString($Matches['user'])
    $PgHost = $Matches['host']
    if ($Matches['port']) { $PgPort = $Matches['port'] }
    $PgDatabase = $Matches['db']
    if ($Matches['pass']) { $PgPassword = [uri]::UnescapeDataString($Matches['pass']) }
}
if (-not $PgPassword) { throw "Falta la contrasena: usa -PgPassword o -EnvFile" }

$pgDump = Join-Path $PgBinPath "pg_dump.exe"
if (-not (Test-Path $pgDump)) {
    throw "No se encontro pg_dump.exe en $PgBinPath"
}

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$outFile = Join-Path $BackupDir "multitec_$timestamp.dump"

$env:PGPASSWORD = $PgPassword
& $pgDump -h $PgHost -p $PgPort -U $PgUser -d $PgDatabase -F custom -f $outFile
$exitCode = $LASTEXITCODE
Remove-Item Env:\PGPASSWORD

if ($exitCode -ne 0) {
    if (Test-Path $outFile) { Remove-Item $outFile -Force }  # no dejar un dump a medias
    throw "pg_dump termino con codigo $exitCode"
}

Write-Output "Backup creado: $outFile"

# Un dump que no se puede leer no sirve el dia que se necesite: se comprueba que pg_restore lo abra y liste su contenido.
$pgRestore = Join-Path $PgBinPath "pg_restore.exe"
if (Test-Path $pgRestore) {
    $entradas = & $pgRestore --list $outFile
    if ($LASTEXITCODE -ne 0 -or -not ($entradas | Select-String -Pattern 'TABLE DATA' -Quiet)) {
        Remove-Item $outFile -Force
        throw "El backup no se pudo verificar con pg_restore --list; se descarto"
    }
    Write-Output "Backup verificado: $(@($entradas | Select-String -Pattern 'TABLE DATA').Count) tablas con datos"
}

# Las fotos, audios y firmas viven en archivos, no en la base: sin esta copia, restaurar la base dejaria los levantamientos sin fotos.
$uploadsFile = $null
if ($UploadsDir -and (Test-Path $UploadsDir)) {
    $uploadsFile = Join-Path $BackupDir "multitec_uploads_$timestamp.zip"
    Compress-Archive -Path (Join-Path $UploadsDir '*') -DestinationPath $uploadsFile -Force
    Write-Output "Archivos subidos respaldados: $uploadsFile"
}

function Remove-OldBackups([string]$dir) {
    $cutoff = (Get-Date).AddDays(-$RetentionDays)
    Get-ChildItem -Path $dir -Include "multitec_*.dump", "multitec_uploads_*.zip" -File |
        Where-Object { $_.LastWriteTime -lt $cutoff } |
        ForEach-Object {
            Remove-Item $_.FullName -Force
            Write-Output "Backup viejo eliminado: $($_.Name)"
        }
}

Remove-OldBackups $BackupDir

$copyFailed = $false
if ($CopyTo) {
    try {
        New-Item -ItemType Directory -Path $CopyTo -Force -ErrorAction Stop | Out-Null
        foreach ($origen in @($outFile, $uploadsFile) | Where-Object { $_ }) {
            Copy-Item -Path $origen -Destination $CopyTo -Force -ErrorAction Stop
            $copied = Join-Path $CopyTo (Split-Path $origen -Leaf)
            if ((Get-Item $copied).Length -ne (Get-Item $origen).Length) {
                throw "La copia no coincide en tamano con el original"
            }
            Write-Output "Copia externa creada: $copied"
        }
        Remove-OldBackups $CopyTo
    } catch {
        $copyFailed = $true
        Write-Output "ATENCION: no se pudo copiar a '$CopyTo': $($_.Exception.Message)"
    }
}

if ($copyFailed) { exit 2 }
