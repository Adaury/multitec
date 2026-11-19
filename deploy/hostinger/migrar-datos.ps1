<#
.SYNOPSIS
  Migra los datos REALES del sistema original (Python + PostgreSQL) a MySQL, los verifica y deja listo el paquete.

.DESCRIPTION
  Repite de principio a fin lo que se hizo a mano, y SE DETIENE en cuanto algo no coincide:
    1. Enciende PostgreSQL si está apagado.
    2. Exporta TODAS las tablas (solo lectura: el sistema original no se modifica).
    3. Recrea la base MySQL «real», importa y VERIFICA campo por campo (y que no haya filas huérfanas).
    4. Genera con el sistema original y con Laravel los reportes DGII 606/607/608 de 24 meses, márgenes y seguimientos,
       y exige que sean IDÉNTICOS.
    5. Crea la copia depurada (multitec_deploy), quitando las empresas de prueba indicadas.
    6. Construye el paquete para Hostinger con los datos (build.ps1 -ConDatos).

  PARA UNA FOTO CONSISTENTE: detén el sistema original (detener-multitec.bat) antes de empezar, y no lo vuelvas a encender
  hasta que Multitec nuevo esté funcionando. Todo lo que se escriba en el original después de la exportación se pierde.

.EXAMPLE
  .\migrar-datos.ps1 -QuitarEmpresas 2
#>
param(
    [int[]]$QuitarEmpresas = @(),
    [string]$Exportacion = (Join-Path $env:USERPROFILE 'MultitecBackups\laravel-import'),
    [switch]$SinPreguntar
)

$ErrorActionPreference = 'Stop'
$raiz = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$php = 'C:\laragon\bin\php\php-8.3.31-Win32-vs16-x64\php.exe'
$mysql = 'C:\laragon\bin\mysql\mysql-8.0.30-winx64\bin\mysql.exe'
$py = 'C:\laragon\www\multitec\backend\venv\Scripts\python.exe'
$herr = Join-Path $raiz 'deploy\tools'
$tmp = Join-Path ([IO.Path]::GetTempPath()) ('migracion-' + (Get-Date -Format 'yyyyMMddHHmm'))
New-Item -ItemType Directory -Force $tmp | Out-Null

function Paso($n, $t) { Write-Host ""; Write-Host "[$n] $t" -ForegroundColor Cyan }
# Ejecuta un comando externo; este PHP imprime avisos «MIB» por stderr, que no son errores.
function Ejecutar([string]$exe, [string[]]$args_, [switch]$MostrarSalida) {
    $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    $out = & $exe @args_ 2>&1 | ForEach-Object { "$_" } | Where-Object { $_ -notmatch 'MIB search|Cannot find module' }
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev
    if ($MostrarSalida) { $out | ForEach-Object { Write-Host "   $_" } }
    return [pscustomobject]@{ Codigo = $code; Salida = ($out -join "`n") }
}
function Artisan([string[]]$a, [switch]$Mostrar) { Ejecutar $php (@((Join-Path $raiz 'artisan')) + $a) -MostrarSalida:$Mostrar }

if (-not $SinPreguntar) {
    Write-Host "Esto lee tu base real (sin modificarla) y reconstruye las bases MySQL 'multitec_real' y 'multitec_deploy'." -ForegroundColor Yellow
    Write-Host "¿Detuviste el sistema original (detener-multitec.bat) para una foto consistente?" -ForegroundColor Yellow
    if ((Read-Host 'Escribe SI para continuar') -ne 'SI') { throw 'Cancelado.' }
}

Paso 1 'PostgreSQL'
if (-not (Get-NetTCPConnection -LocalPort 5432 -State Listen -ErrorAction SilentlyContinue)) {
    Start-ScheduledTask -TaskName 'PostgreSQL17-Autostart'
    1..40 | ForEach-Object { if (-not (Get-NetTCPConnection -LocalPort 5432 -State Listen -ErrorAction SilentlyContinue)) { Start-Sleep -Seconds 2 } }
    Start-Sleep -Seconds 8   # acepta conexiones unos segundos después de abrir el puerto
}
if (-not (Get-NetTCPConnection -LocalPort 5432 -State Listen -ErrorAction SilentlyContinue)) { throw 'PostgreSQL no arrancó (puerto 5432).' }
Write-Host '   escuchando en 5432'

Paso 2 'Exportando la base real (solo lectura)'
if (Test-Path $Exportacion) { Get-ChildItem $Exportacion -File | Remove-Item -Force }
$r = Ejecutar $py @('-I', (Join-Path $herr 'pg_export.py'), $Exportacion)
if ($r.Codigo -ne 0) { throw "La exportación falló:`n$($r.Salida)" }
Write-Host "   $($r.Salida)"

Paso 3 'Importando a MySQL (base multitec_real) y verificando campo por campo'
$null = Ejecutar $mysql @('-uroot', '-e', 'DROP DATABASE IF EXISTS multitec_real; CREATE DATABASE multitec_real CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;')
$r = Artisan @('migrate', '--database=real', '--force'); if ($r.Codigo -ne 0) { throw "migrate falló:`n$($r.Salida)" }
$r = Artisan @('multitec:import-real', $Exportacion); if ($r.Codigo -ne 0) { throw "La importación falló:`n$($r.Salida)" }
$r = Artisan @('multitec:verify-import', $Exportacion)
($r.Salida -split "`n" | Select-Object -Last 5) | ForEach-Object { Write-Host "   $_" }
if ($r.Codigo -ne 0) { throw 'La verificación encontró diferencias o filas huérfanas: NO sigo.' }

Paso 4 'Reportes DGII, márgenes y seguimientos: sistema original vs Laravel'
$a = Join-Path $tmp 'original'; $b = Join-Path $tmp 'laravel'
$r = Ejecutar $py @('-I', (Join-Path $herr 'py_reports.py'), $a); if ($r.Codigo -ne 0) { throw "Los reportes del original fallaron:`n$($r.Salida)" }
$r = Artisan @('multitec:dump-reports', $b); if ($r.Codigo -ne 0) { throw "Los reportes de Laravel fallaron:`n$($r.Salida)" }
$r = Ejecutar $py @('-I', (Join-Path $herr 'cmp.py'), $a, $b)
Write-Host "   $($r.Salida -replace "`n", "`n   ")"
if ($r.Codigo -ne 0) { throw 'Los reportes NO coinciden entre el original y Laravel: NO sigo.' }

Paso 5 'Copia depurada para el servidor (multitec_deploy)'
$null = Ejecutar $mysql @('-uroot', '-e', 'DROP DATABASE IF EXISTS multitec_deploy; CREATE DATABASE multitec_deploy CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;')
$dump = Join-Path $tmp 'real.sql'
$r = Ejecutar (Join-Path (Split-Path $mysql) 'mysqldump.exe') @('-uroot', '--single-transaction', '--skip-comments', '--result-file', $dump, 'multitec_real')
if ($r.Codigo -ne 0) { throw "mysqldump falló:`n$($r.Salida)" }
$prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
cmd /c "`"$mysql`" -uroot multitec_deploy < `"$dump`"" 2>$null
$ErrorActionPreference = $prev
Remove-Item $dump -Force
foreach ($id in $QuitarEmpresas) {
    Write-Host "   quitando la empresa $id de la copia:"
    $r = Artisan @('multitec:delete-company', "$id", '--connection=deploy', '--yes') -Mostrar; if ($r.Codigo -ne 0) { throw "No pude quitar la empresa $id" }
}
$r = Ejecutar $mysql @('-uroot', 'multitec_deploy', '-N', '-e', "select concat('empresas=',(select count(*) from companies),' usuarios=',(select count(*) from users),' clientes=',(select count(*) from clients),' proyectos=',(select count(*) from projects),' facturas=',(select count(*) from invoices))")
Write-Host "   copia depurada: $($r.Salida)"

Paso 6 'Construyendo el paquete con los datos'
& (Join-Path $PSScriptRoot 'build.ps1') -ConDatos
Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
Write-Host ""
Write-Host "MIGRACIÓN COMPLETA Y VERIFICADA. Sigue la guía HOSTINGER.md." -ForegroundColor Green
