<#
Prueba de restauracion: un respaldo solo vale si se puede restaurar. Este script restaura un dump en una base
TEMPORAL y compara el numero de filas de cada tabla con la base real; luego borra la temporal. No toca la base real
(solo la lee).

Uso:
  .\restore-test.ps1 -EnvFile "C:\laragon\www\multitec\backend\.env" -DumpFile "C:\Users\Usuario\MultitecBackups\multitec_2026-10-28_020000.dump"

Sin -DumpFile usa el dump mas reciente de -BackupDir. Requiere un usuario con permiso para crear bases
(-AdminUser, por defecto postgres; pide su contrasena en -AdminPassword o en la variable PGPASSWORD).
Como el respaldo de la noche es de unas horas antes, es normal que las tablas muy activas difieran en pocas filas:
el script las marca como "difiere" y solo falla si falta una tabla o la restauracion da error.
#>

param(
    [string]$PgBinPath = "C:\Program Files\PostgreSQL\17\bin",
    [string]$EnvFile,
    [string]$DumpFile,
    [string]$BackupDir = (Join-Path $env:USERPROFILE "MultitecBackups"),
    [string]$AdminUser = "postgres",
    [string]$AdminPassword
)

if (-not $EnvFile -or -not (Test-Path $EnvFile)) { throw "Indica -EnvFile con la ruta de backend\.env" }
$line = Select-String -Path $EnvFile -Pattern '^\s*DATABASE_URL\s*=\s*(.+?)\s*$' | Select-Object -First 1
if (-not $line) { throw "DATABASE_URL no esta definida en $EnvFile" }
$pattern = '^[\w+]+://(?<user>[^:@/]+)(:(?<pass>[^@]*))?@(?<host>[^:/]+)(:(?<port>\d+))?/(?<db>[^?]+)'
if ($line.Matches[0].Groups[1].Value -notmatch $pattern) { throw "DATABASE_URL no es una URL de PostgreSQL valida" }
$dbHost = $Matches['host']; $dbPort = if ($Matches['port']) { $Matches['port'] } else { "5432" }
$dbName = $Matches['db']; $dbUser = [uri]::UnescapeDataString($Matches['user'])
$dbPass = if ($Matches['pass']) { [uri]::UnescapeDataString($Matches['pass']) } else { "" }

if (-not $DumpFile) {
    $DumpFile = (Get-ChildItem -Path $BackupDir -Filter "multitec_*.dump" | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
}
if (-not $DumpFile -or -not (Test-Path $DumpFile)) { throw "No hay dump para probar" }
Write-Output "Probando: $DumpFile"

$psql = Join-Path $PgBinPath "psql.exe"
$pgRestore = Join-Path $PgBinPath "pg_restore.exe"
$tempDb = "multitec_restoretest_" + (Get-Date -Format "yyyyMMddHHmmss")
$sqlConteo = "select table_name, (xpath('/row/c/text()', query_to_xml('select count(*) as c from ' || quote_ident(table_name), false, true, '')))[1]::text::int as filas from information_schema.tables where table_schema='public' and table_type='BASE TABLE' order by 1"

function Get-Conteos([string]$usuario, [string]$clave, [string]$base) {
    $env:PGPASSWORD = $clave
    $out = & $psql -h $dbHost -p $dbPort -U $usuario -d $base -At -F '|' -c $sqlConteo
    Remove-Item Env:\PGPASSWORD
    if ($LASTEXITCODE -ne 0) { throw "No se pudo leer la base $base" }
    $mapa = @{}
    foreach ($fila in $out) { $p = $fila -split '\|'; $mapa[$p[0]] = [int]$p[1] }
    return $mapa
}

$adminClave = if ($AdminPassword) { $AdminPassword } else { $env:PGPASSWORD }
$fallo = $false
try {
    $env:PGPASSWORD = $adminClave
    & $psql -h $dbHost -p $dbPort -U $AdminUser -d postgres -c "create database $tempDb" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "No se pudo crear la base temporal (revisa -AdminUser / -AdminPassword)" }
    & $pgRestore -h $dbHost -p $dbPort -U $AdminUser -d $tempDb --no-owner --no-privileges $DumpFile
    if ($LASTEXITCODE -ne 0) { throw "pg_restore fallo al restaurar el dump" }
    Remove-Item Env:\PGPASSWORD

    $real = Get-Conteos $dbUser $dbPass $dbName
    $restaurada = Get-Conteos $AdminUser $adminClave $tempDb
    foreach ($tabla in ($real.Keys | Sort-Object)) {
        if (-not $restaurada.ContainsKey($tabla)) { Write-Output "FALTA  $tabla"; $fallo = $true; continue }
        $estado = if ($restaurada[$tabla] -eq $real[$tabla]) { "igual  " } else { "difiere" }
        Write-Output ("{0} {1,-40} respaldo={2,7} real={3,7}" -f $estado, $tabla, $restaurada[$tabla], $real[$tabla])
    }
} catch {
    $fallo = $true
    Write-Output "ERROR: $($_.Exception.Message)"
} finally {
    $env:PGPASSWORD = $adminClave
    & $psql -h $dbHost -p $dbPort -U $AdminUser -d postgres -c "drop database if exists $tempDb" | Out-Null
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
}

if ($fallo) { Write-Output "PRUEBA FALLIDA"; exit 1 }
Write-Output "PRUEBA CORRECTA: el respaldo se restaura y tiene todas las tablas"
