<#
.SYNOPSIS
  Construye el paquete de Multitec para subir a Hostinger (hosting compartido, PHP 8.3 + MySQL).

.DESCRIPTION
  Genera, en la carpeta de salida:
    multitec-app.zip          La aplicación (código + vendor de producción). Va FUERA de public_html.
    multitec-public_html.zip  La carpeta web (public_html): app compilada, index.php adaptado, .htaccess.
    requisitos.php            Verificador de requisitos del servidor (se sube solo y se borra).
    .env.production.example   Plantilla de configuración (se copia como .env y se rellena).
    LEEME.txt                 Pasos y sumas de comprobación.
  Con -ConDatos agrega además (DATOS REALES; no los subas a ningún repositorio ni nube de trabajo):
    base-de-datos.sql         Volcado de la base depurada (multitec_deploy).
    archivos-subidos.zip      Fotos y archivos reales (carpeta uploads/).

  No sube nada a ningún sitio: solo escribe archivos en la carpeta de salida.

.EXAMPLE
  .\build.ps1                      # solo el código
  .\build.ps1 -ConDatos            # código + datos reales depurados
#>
param(
    [string]$Salida = (Join-Path $env:USERPROFILE 'MultitecBackups\despliegue-hostinger'),
    [string]$NombreApp = 'multitec',
    [string]$BaseDeploy = 'multitec_deploy',
    [string]$UploadsOriginal = 'C:\laragon\www\multitec\backend\uploads',
    # Instalación limpia (sin -ConDatos): empresa y primer administrador que trae la base vacía.
    [string]$Empresa = 'Multitec',
    [string]$NombreAdmin = 'Administrador',
    [string]$CorreoAdmin = 'admin@cambia-esto.com',
    [switch]$ConDatos
)

$ErrorActionPreference = 'Stop'
$raiz = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$php = 'C:\laragon\bin\php\php-8.3.31-Win32-vs16-x64\php.exe'
$composer = 'C:\laragon\bin\composer\composer.phar'
$mysqlBin = 'C:\laragon\bin\mysql\mysql-8.0.30-winx64\bin'
foreach ($f in @($php, $composer)) { if (-not (Test-Path $f)) { throw "No encuentro $f" } }

$fecha = Get-Date -Format 'yyyyMMdd-HHmm'
$destino = Join-Path $Salida $fecha
$stage = Join-Path ([IO.Path]::GetTempPath()) "multitec-build-$fecha"
$app = Join-Path $stage $NombreApp
$web = Join-Path $stage 'public_html'
if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
New-Item -ItemType Directory -Force $app, $web, $destino | Out-Null

Write-Host "1/6 Copiando el código (sin pruebas, sin .env, sin datos)..." -ForegroundColor Cyan
# robocopy devuelve 0-7 cuando todo salió bien
$null = robocopy $raiz $app /MIR /NFL /NDL /NJH /NJS /NP `
    /XD '.git' 'node_modules' 'tests' 'deploy' 'vendor' 'public' (Join-Path $raiz 'storage') (Join-Path $raiz 'bootstrap\cache') `
        (Join-Path $raiz 'resources\js') (Join-Path $raiz 'resources\css') `
    /XF '.env' '.env.*' 'phpunit.xml' '*.sqlite' '*.log' '.phpunit.result.cache' 'AGENTS.md' 'CLAUDE.md' 'README.md' `
        'package.json' 'package-lock.json' 'vite.config.js' 'pint.json' '.editorconfig' '.gitattributes' '.gitignore'
if ($LASTEXITCODE -ge 8) { throw "robocopy falló ($LASTEXITCODE)" }

# Estructura de carpetas que Laravel necesita y que no viajan en el paquete (deben existir ANTES de instalar: composer
# ejecuta «artisan package:discover» al terminar y escribe en bootstrap/cache).
foreach ($d in 'storage\app\private', 'storage\framework\cache\data', 'storage\framework\sessions', 'storage\framework\views', 'storage\logs', 'bootstrap\cache') {
    $p = Join-Path $app $d
    New-Item -ItemType Directory -Force $p | Out-Null
    Set-Content -Path (Join-Path $p '.gitkeep') -Value '' -Encoding ASCII
}

Write-Host "2/6 Instalando dependencias de producción (sin herramientas de desarrollo)..." -ForegroundColor Cyan
# Este PHP imprime avisos «MIB» por stderr: PowerShell 5.1 los trataría como error fatal, así que se aíslan aquí.
$ErrorActionPreference = 'Continue'
& $php $composer install --no-dev --optimize-autoloader --classmap-authoritative --no-interaction --no-progress "--working-dir=$app" 2>&1 |
    ForEach-Object { "$_" } | Where-Object { $_ -notmatch 'MIB|Cannot find module|^\s*$' } | Select-Object -Last 4 | ForEach-Object { Write-Host "   $_" }
$ErrorActionPreference = 'Stop'
if (-not (Test-Path (Join-Path $app 'vendor\autoload.php'))) { throw 'composer no generó vendor/autoload.php' }
if (-not (Test-Path (Join-Path $app 'bootstrap\cache\packages.php'))) { throw 'composer no terminó el descubrimiento de paquetes (bootstrap/cache/packages.php)' }
# Nada de rutas de esta PC dentro del paquete: el servidor tiene otras.
$sospechosos = Get-ChildItem (Join-Path $app 'bootstrap\cache') -Filter *.php | Select-String -Pattern 'C:\\\\?(laragon|Users)' -List
if ($sospechosos) { throw "Hay rutas de esta PC dentro de bootstrap/cache: $($sospechosos.Path -join ', ')" }
# Red de seguridad: si por error subieran la aplicación dentro de public_html, el servidor no serviría nada de ella.
Set-Content -Path (Join-Path $app '.htaccess') -Value "Require all denied`n" -Encoding ASCII

Write-Host "3/6 Preparando la carpeta web (public_html)..." -ForegroundColor Cyan
$null = robocopy (Join-Path $raiz 'public') $web /E /NFL /NDL /NJH /NJS /NP /XF 'hot' 'index.php' /XD 'storage'
if ($LASTEXITCODE -ge 8) { throw "robocopy (public) falló ($LASTEXITCODE)" }
# SIN BOM: «Set-Content -Encoding UTF8» de PowerShell 5.1 antepone 3 bytes (EF BB BF) que PHP imprime antes de cada respuesta
# y rompen el JSON de la API y las cabeceras. Por eso se escribe con .NET y una codificación sin BOM.
$indexTexto = (Get-Content (Join-Path $PSScriptRoot 'public-index.php') -Raw -Encoding UTF8) -replace '\{\{APP_DIR\}\}', $NombreApp
[IO.File]::WriteAllText((Join-Path $web 'index.php'), $indexTexto, (New-Object Text.UTF8Encoding($false)))
$cabecera = [IO.File]::ReadAllBytes((Join-Path $web 'index.php'))[0..2]
if ($cabecera[0] -eq 0xEF -and $cabecera[1] -eq 0xBB -and $cabecera[2] -eq 0xBF) { throw 'index.php quedó con BOM' }
if ([Text.Encoding]::ASCII.GetString($cabecera[0..1]) -ne '<?') { throw 'index.php no empieza con <?php' }

Write-Host "4/6 Comprimiendo..." -ForegroundColor Cyan
# tar.exe (Windows 10+) escribe rutas con «/»; Compress-Archive de PowerShell 5.1 usa «\» y rompe la extracción en Linux.
& tar.exe -a -c -f (Join-Path $destino 'multitec-app.zip') -C $stage $NombreApp
& tar.exe -a -c -f (Join-Path $destino 'multitec-public_html.zip') -C $web .
Copy-Item (Join-Path $PSScriptRoot 'requisitos.php') $destino
Copy-Item (Join-Path $PSScriptRoot '.env.production.example') $destino

if ($ConDatos) {
    Write-Host "5/6 Datos reales depurados (base $BaseDeploy + archivos)..." -ForegroundColor Cyan
    $sql = Join-Path $destino 'base-de-datos.sql'
    $ErrorActionPreference = 'Continue'
    & (Join-Path $mysqlBin 'mysqldump.exe') -uroot --single-transaction --skip-comments --no-tablespaces --default-character-set=utf8mb4 --result-file=$sql $BaseDeploy 2>$null
    $codigo = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if ($codigo -ne 0 -or -not (Test-Path $sql) -or (Get-Item $sql).Length -lt 10000) { throw "El volcado de $BaseDeploy falló o salió vacío" }
    if (Test-Path $UploadsOriginal) {
        $tmp = Join-Path $stage 'datos'
        New-Item -ItemType Directory -Force (Join-Path $tmp 'uploads') | Out-Null
        $null = robocopy $UploadsOriginal (Join-Path $tmp 'uploads') /E /NFL /NDL /NJH /NJS /NP
        & tar.exe -a -c -f (Join-Path $destino 'archivos-subidos.zip') -C $tmp uploads
    }
} else {
    Write-Host "5/6 Base de datos LIMPIA (estructura + primer administrador, sin datos de clientes)..." -ForegroundColor Cyan
    # Se arma dentro de la copia temporal del paquete (que no tiene caché de configuración) con una base temporal;
    # nunca toca tus bases de trabajo. El .env temporal se borra antes de terminar y NO viaja en los zips (ya se crearon).
    $baseLimpia = 'multitec_limpia_build'
    $mysql = Join-Path $mysqlBin 'mysql.exe'
    $ErrorActionPreference = 'Continue'
    & $mysql -uroot -e "DROP DATABASE IF EXISTS $baseLimpia; CREATE DATABASE $baseLimpia CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci" 2>$null
    $envTemporal = "APP_ENV=production`nAPP_DEBUG=false`nAPP_KEY=base64:" + [Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 } | ForEach-Object { [byte]$_ })) +
        "`nDB_CONNECTION=mysql`nDB_HOST=127.0.0.1`nDB_PORT=3306`nDB_DATABASE=$baseLimpia`nDB_USERNAME=root`nDB_PASSWORD=`nCACHE_STORE=file`nSESSION_DRIVER=file`nLOG_CHANNEL=single`n"
    [IO.File]::WriteAllText((Join-Path $app '.env'), $envTemporal, (New-Object Text.UTF8Encoding($false)))
    # Este PHP imprime avisos «MIB» por stderr: se filtran para que el error real (si hay) se vea.
    $ruido = 'MIB|Cannot find module|^\s*$'
    $artisan = Join-Path $app 'artisan'
    if (-not (Test-Path $artisan)) { throw "No encuentro $artisan (¿lo borró el antivirus?). Vuelve a correr build.ps1." }
    $salidaMigrar = & $php $artisan migrate --force 2>&1 | ForEach-Object { "$_" } | Where-Object { $_ -notmatch $ruido }
    $textoMigrar = $salidaMigrar -join "`n"
    if ($textoMigrar -notmatch 'create_quote_comparisons\s*\.+\s*[\d.]+\s*m?s\s+DONE' -and $textoMigrar -notmatch 'Nothing to migrate') {
        throw 'migrate no terminó bien: ' + (($salidaMigrar | Select-Object -Last 6) -join ' | ')
    }
    $salida = & $php $artisan multitec:crear-administrador $CorreoAdmin "--empresa=$Empresa" "--nombre=$NombreAdmin" 2>&1 | ForEach-Object { "$_" } | Where-Object { $_ -notmatch $ruido }
    $claveTemporal = ($salida | Select-String 'CLAVE_TEMPORAL=(\S+)' | Select-Object -First 1).Matches.Groups[1].Value
    Remove-Item (Join-Path $app '.env') -Force
    $sqlLimpia = Join-Path $destino 'base-de-datos-limpia.sql'
    & (Join-Path $mysqlBin 'mysqldump.exe') -uroot --single-transaction --skip-comments --no-tablespaces --default-character-set=utf8mb4 --result-file=$sqlLimpia $baseLimpia 2>$null
    $codigo = $LASTEXITCODE
    & $mysql -uroot -e "DROP DATABASE IF EXISTS $baseLimpia" 2>$null
    $ErrorActionPreference = 'Stop'
    if ($codigo -ne 0 -or -not (Test-Path $sqlLimpia) -or (Get-Item $sqlLimpia).Length -lt 20000) { throw 'No se pudo generar la base de datos limpia' }
    if (-not $claveTemporal) { throw 'No se pudo crear el primer administrador: ' + ($salida -join ' ') }
    $primerAcceso = @"
PRIMER ACCESO — INSTALACIÓN LIMPIA DE MULTITEC
==============================================

Empresa:        $Empresa
Correo:         $CorreoAdmin     (puedes cambiarlo en phpMyAdmin: UPDATE users SET email='tu@correo.com' WHERE id=1;)
Clave temporal: $claveTemporal

El sistema te pedirá cambiar la clave la primera vez que entres. Esta clave solo sirve una vez.
Cuando termines la instalación BORRA este archivo (y no lo mandes por correo ni lo subas a ningún servidor).
"@
    Set-Content -Path (Join-Path $destino 'PRIMER-ACCESO.txt') -Value $primerAcceso -Encoding UTF8
}
# La guía de instalación viaja con el paquete.
Copy-Item (Join-Path $PSScriptRoot 'HOSTINGER.md') (Join-Path $destino 'GUIA-INSTALACION.md')

Write-Host "6/6 Sumas de comprobación y guía..." -ForegroundColor Cyan
$lineas = Get-ChildItem $destino -File | Where-Object { $_.Name -ne 'LEEME.txt' } | ForEach-Object {
    '{0}  {1,12:N0} bytes  SHA256 {2}' -f $_.Name, $_.Length, (Get-FileHash $_.FullName -Algorithm SHA256).Hash.Substring(0, 16)
}
$leeme = @"
PAQUETE DE MULTITEC PARA HOSTINGER  ($fecha)
==================================================

Lee primero:  GUIA-INSTALACION.md  (en esta misma carpeta; paso a paso con todo el detalle)

Orden resumido:
  1. hPanel: crea la base de datos MySQL y anota usuario / contraseña.
  2. hPanel -> PHP: versión 8.3, y activa las extensiones que pida requisitos.php.
  3. Sube y descomprime  multitec-app.zip  FUERA de public_html (queda la carpeta '$NombreApp' al lado de public_html).
  4. Sube y descomprime  multitec-public_html.zip  DENTRO de public_html.
  5. Copia .env.production.example como  $NombreApp/.env  y rellénalo (APP_URL, APP_KEY, JWT_SECRET, base de datos, correo, GEMINI_API_KEY).
  6. phpMyAdmin: importa  base-de-datos-limpia.sql  (instalación nueva, sin datos; el primer acceso está en PRIMER-ACCESO.txt)
     o  base-de-datos.sql  (si construiste el paquete con -ConDatos).
  7. Si incluiste archivos: descomprime  archivos-subidos.zip  dentro de  $NombreApp/storage/app/private/  (queda ..../private/uploads/).
  8. Con SSH:  cd $NombreApp ; php artisan multitec:check-server
  9. Activa HTTPS (SSL gratis; sin él el micrófono del asistente no funciona) y entra.

Archivos de este paquete:
$($lineas -join "`n")

PRIMER-ACCESO.txt (instalación limpia) trae la clave temporal del administrador: bórralo al terminar.
DATOS REALES: base-de-datos.sql y archivos-subidos.zip (solo con -ConDatos) contienen información de clientes. Guárdalos solo en
lugares privados y bórralos del servidor y de tu PC cuando termines.
"@
Set-Content -Path (Join-Path $destino 'LEEME.txt') -Value $leeme -Encoding UTF8

Remove-Item $stage -Recurse -Force
Write-Host ""
Write-Host "Listo -> $destino" -ForegroundColor Green
Get-ChildItem $destino -File | ForEach-Object { '  {0,-28} {1,10:N1} MB' -f $_.Name, ($_.Length / 1MB) }
