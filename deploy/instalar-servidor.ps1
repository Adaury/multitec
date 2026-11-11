<#
Instalador de Multitec para el servidor (Windows Server 2019+ o Windows 10/11).

Uso normal: clic derecho en INSTALAR.bat → «Ejecutar como administrador» y responder las preguntas.
Revisar sin cambiar nada:  powershell -ExecutionPolicy Bypass -File deploy\instalar-servidor.ps1 -SoloRevisar

Qué hace (en orden):
  1. Revisa que estén Python 3.13+ y PostgreSQL; instala NSSM y Caddy si faltan.
  2. Crea el usuario y la base de datos «multitec» en PostgreSQL (con una clave al azar).
  3. Prepara el backend (entorno de Python y librerías) y su configuración (backend\.env) para producción.
  4. Si se le da el ZIP de datos (EXPORTAR-DATOS.bat de la PC anterior), restaura la base, las fotos y la
     configuración; si no, crea una base nueva con su administrador.
  5. Configura Caddy (dominio con HTTPS, Cloudflare Tunnel o red local) y deja backend y web como servicios.
  6. Programa la copia de seguridad diaria (2:00 a. m.).
Se puede correr otra vez para ACTUALIZAR: conserva backend\.env, la base de datos y las fotos.
#>

param(
    # ZIP que genera EXPORTAR-DATOS.bat en la PC anterior (base de datos, fotos y configuración). Opcional.
    [string]$Datos,
    [ValidateSet('', 'dominio', 'cloudflare', 'red-local')]
    [string]$Modo = '',
    # dominio: p. ej. app.multitec.com.do · red-local: nombre del servidor o su IP
    [string]$Dominio,
    [string]$CarpetaRespaldos = 'C:\MultitecBackups',
    # Segunda copia de los respaldos fuera de este disco (disco externo, unidad de red...). Opcional.
    [string]$CopiaExterna,
    [switch]$ConIA,
    # Restaurar datos encima de una base que ya tiene información (solo si estás seguro).
    [switch]$Sobrescribir,
    # Solo revisa requisitos y muestra qué haría, sin cambiar nada.
    [switch]$SoloRevisar
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Backend = Join-Path $Root 'backend'
$Deploy = Join-Path $Root 'deploy'
$EnvFile = Join-Path $Backend '.env'
$Tools = Join-Path $Root 'tools'
$BackendPort = 8000
$script:Paso = 0

function Paso([string]$texto) { $script:Paso++; Write-Host ''; Write-Host "[$script:Paso] $texto" -ForegroundColor Cyan }
function Ok([string]$texto) { Write-Host "    OK   $texto" -ForegroundColor Green }
function Aviso([string]$texto) { Write-Host "    !!   $texto" -ForegroundColor Yellow }
function Falla([string]$texto) {
    Write-Host ''
    Write-Host "    XX   $texto" -ForegroundColor Red
    Write-Host '    La instalación se detuvo. Corrige lo indicado y vuelve a ejecutar INSTALAR.bat.' -ForegroundColor Red
    if (-not $SoloRevisar) { try { Stop-Transcript | Out-Null } catch {} }
    exit 1
}
function Clave([int]$largo = 32) {
    $chars = 'abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    $bytes = New-Object byte[] $largo
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    -join ($bytes | ForEach-Object { $chars[$_ % $chars.Length] })
}
function Hex([int]$bytes = 32) {
    $b = New-Object byte[] $bytes
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b)
    -join ($b | ForEach-Object { $_.ToString('x2') })
}
function Resto([object[]]$lista) { if ($lista.Length -gt 1) { return $lista[1..($lista.Length - 1)] } return @() }
function Refrescar-Path {
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
    if (Test-Path $Tools) { $env:Path = "$Tools;$env:Path" }
}
function Leer-Env([string]$ruta) {
    $valores = [ordered]@{}
    if (Test-Path $ruta) {
        foreach ($linea in [IO.File]::ReadAllLines($ruta)) {
            if ($linea -match '^\s*([A-Z0-9_]+)\s*=(.*)$') { $valores[$Matches[1]] = $Matches[2] }
        }
    }
    return $valores
}
function Escribir-Env([string]$ruta, [hashtable]$cambios) {
    # Reemplaza o agrega cada clave conservando el resto del archivo. UTF-8 sin BOM (pydantic no lo espera).
    $lineas = New-Object System.Collections.Generic.List[string]
    if (Test-Path $ruta) { $lineas.AddRange([IO.File]::ReadAllLines($ruta)) }
    foreach ($clave in $cambios.Keys) {
        $nueva = "$clave=$($cambios[$clave])"
        $i = -1
        for ($j = 0; $j -lt $lineas.Count; $j++) { if ($lineas[$j] -match "^\s*$clave\s*=") { $i = $j; break } }
        if ($i -ge 0) { $lineas[$i] = $nueva } else { $lineas.Add($nueva) }
    }
    [IO.File]::WriteAllLines($ruta, $lineas, (New-Object Text.UTF8Encoding $false))
}

Write-Host ''
Write-Host '=================================================' -ForegroundColor Cyan
Write-Host '   Instalador de Multitec para el servidor' -ForegroundColor Cyan
if ($SoloRevisar) { Write-Host '   MODO REVISIÓN: no se cambia nada' -ForegroundColor Yellow }
Write-Host '=================================================' -ForegroundColor Cyan

$esAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $esAdmin -and -not $SoloRevisar) { Falla 'Hay que ejecutarlo como administrador: clic derecho en INSTALAR.bat → «Ejecutar como administrador».' }
if (-not $SoloRevisar) {
    New-Item -ItemType Directory -Force (Join-Path $Deploy 'logs') | Out-Null
    Start-Transcript -Path (Join-Path $Deploy "logs\instalacion_$(Get-Date -Format yyyy-MM-dd_HHmmss).log") | Out-Null
}
$actualizar = Test-Path $EnvFile
if ($actualizar) { Write-Host '   Ya hay una instalación: se ACTUALIZA (se conservan datos y configuración).' -ForegroundColor Yellow }
Refrescar-Path

# ------------------------------------------------------------------------------------------------ requisitos
Paso 'Revisando requisitos'
$python = $null
foreach ($cand in @('py -3.14', 'py -3.13', 'python')) {
    $partes = $cand.Split(' ')
    try {
        $ver = & $partes[0] @(Resto $partes) -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($LASTEXITCODE -eq 0 -and $ver -and [version]$ver -ge [version]'3.13') { $python = $partes; Ok "Python $ver"; break }
    } catch {}
}
if (-not $python) { Falla 'Falta Python 3.13 o más nuevo. Instálalo de https://www.python.org/downloads/ marcando «Add python.exe to PATH» (ver la guía, paso B2).' }

$pgBin = Get-ChildItem 'C:\Program Files\PostgreSQL\*\bin\psql.exe' -ErrorAction SilentlyContinue |
    Sort-Object { [int]($_.Directory.Parent.Name -replace '\D', '') } -Descending | Select-Object -First 1 | ForEach-Object { $_.DirectoryName }
if (-not $pgBin) { Falla 'Falta PostgreSQL. Instálalo de https://www.postgresql.org/download/windows/ (versión 17) y anota la clave del usuario postgres (guía, paso B3).' }
Ok "PostgreSQL en $pgBin"
$pgServicio = Get-Service -Name 'postgresql*' -ErrorAction SilentlyContinue | Select-Object -First 1
if ($pgServicio) {
    if (-not $SoloRevisar) {
        Set-Service $pgServicio.Name -StartupType Automatic
        if ($pgServicio.Status -ne 'Running') { Start-Service $pgServicio.Name }
    }
    if ($SoloRevisar) { Ok "Servicio $($pgServicio.Name): $($pgServicio.Status), arranque $($pgServicio.StartType) (se pondría automático)" } else { Ok "Servicio $($pgServicio.Name) (arranque automático)" }
} else { Aviso 'No encontré el servicio de PostgreSQL; asegúrate de que arranque solo con Windows.' }

$puertoOcupado = Get-NetTCPConnection -LocalPort $BackendPort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($puertoOcupado) {
    $quien = (Get-Process -Id $puertoOcupado.OwningProcess -ErrorAction SilentlyContinue).ProcessName
    $nuestro = (Get-Service MultitecBackend -ErrorAction SilentlyContinue)
    if (-not $nuestro) { Falla "El puerto $BackendPort ya lo usa otro programa ($quien). Multitec lo necesita para su backend." }
}
Ok "Puerto $BackendPort disponible para el backend"

function Asegurar-Herramienta([string]$nombre, [string]$wingetId, [scriptblock]$descargar) {
    if (Get-Command $nombre -ErrorAction SilentlyContinue) { Ok "$nombre ya está"; return }
    if ($SoloRevisar) { Aviso "$nombre no está: se instalaría"; return }
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install --id $wingetId -e --accept-source-agreements --accept-package-agreements --silent | Out-Null
        Refrescar-Path
    }
    if (-not (Get-Command $nombre -ErrorAction SilentlyContinue)) {
        New-Item -ItemType Directory -Force $Tools | Out-Null
        & $descargar
        $machinePath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
        if ($machinePath -notlike "*$Tools*") { [Environment]::SetEnvironmentVariable('Path', "$machinePath;$Tools", 'Machine') }
        Refrescar-Path
    }
    if (Get-Command $nombre -ErrorAction SilentlyContinue) { Ok "$nombre instalado" } else { Falla "No se pudo instalar $nombre. Descárgalo a mano (ver la guía) y vuelve a ejecutar." }
}
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Asegurar-Herramienta 'nssm' 'NSSM.NSSM' {
    $zip = Join-Path $env:TEMP 'nssm.zip'
    Invoke-WebRequest 'https://nssm.cc/release/nssm-2.24.zip' -OutFile $zip -UseBasicParsing
    Expand-Archive $zip -DestinationPath (Join-Path $env:TEMP 'nssm') -Force
    Copy-Item (Join-Path $env:TEMP 'nssm\nssm-2.24\win64\nssm.exe') (Join-Path $Tools 'nssm.exe') -Force
}
Asegurar-Herramienta 'caddy' 'CaddyServer.Caddy' {
    Invoke-WebRequest 'https://caddyserver.com/api/download?os=windows&arch=amd64' -OutFile (Join-Path $Tools 'caddy.exe') -UseBasicParsing
}
if (-not (Test-Path (Join-Path $Root 'frontend\dist\index.html'))) { Falla 'Al paquete le falta frontend\dist (la web compilada). Vuelve a generarlo con EMPAQUETAR.bat.' }
Ok 'Web compilada incluida en el paquete'

# ------------------------------------------------------------------------------------------------ preguntas
$cfg = Leer-Env $EnvFile
if (-not $Modo) {
    if ($actualizar -and $cfg['CORS_ORIGINS']) {
        $Modo = 'actual'
    } elseif ($SoloRevisar) {
        $Modo = 'dominio'; $Dominio = 'app.ejemplo.com.do'
    } else {
        Write-Host ''
        Write-Host '¿Cómo se va a abrir Multitec desde afuera?' -ForegroundColor White
        Write-Host '  1) Con un dominio propio apuntando a este servidor (HTTPS automático, abre los puertos 80 y 443)'
        Write-Host '  2) Con Cloudflare Tunnel (recomendado: no abre puertos y protege de ataques)'
        Write-Host '  3) Solo en la red local de la oficina'
        switch (Read-Host 'Escribe 1, 2 o 3') { '1' { $Modo = 'dominio' } '2' { $Modo = 'cloudflare' } '3' { $Modo = 'red-local' } default { Falla 'Opción no válida' } }
    }
}
if ($Modo -in @('dominio', 'cloudflare') -and -not $Dominio) { $Dominio = Read-Host 'Escribe el dominio (por ejemplo app.multitec.com.do)' }
if ($Modo -eq 'red-local' -and -not $Dominio) {
    $Dominio = Read-Host "Nombre o IP con que la red verá el servidor (Enter = $env:COMPUTERNAME)"
    if (-not $Dominio) { $Dominio = $env:COMPUTERNAME }
}
if ($Modo -ne 'actual') { Ok "Acceso: $Modo · $Dominio" } else { Ok 'Acceso: se mantiene el configurado' }

if ($Datos) {
    if (-not (Test-Path $Datos)) { Falla "No encontré el archivo de datos: $Datos" }
    Ok "Datos a restaurar: $Datos"
} elseif (-not $actualizar) {
    $zipDatos = Get-ChildItem $Root -Filter 'MultitecDatos_*.zip' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($zipDatos) {
        $resp = if ($SoloRevisar) { 's' } else { Read-Host "Encontré $($zipDatos.Name). ¿Restaurar esos datos? (s/n)" }
        if ($resp -match '^[sS]') { $Datos = $zipDatos.FullName; Ok "Datos a restaurar: $($zipDatos.Name)" }
    }
    if (-not $Datos) { Aviso 'Sin datos para restaurar: se creará una base nueva con un administrador.' }
}

if ($SoloRevisar) {
    Write-Host ''
    Write-Host 'Revisión terminada. Para instalar de verdad: clic derecho en INSTALAR.bat → «Ejecutar como administrador».' -ForegroundColor Green
    exit 0
}

# ------------------------------------------------------------------------------------------------ base de datos
$psql = Join-Path $pgBin 'psql.exe'
if (-not $actualizar) {
    Paso 'Creando la base de datos'
    $segura = Read-Host 'Clave del usuario «postgres» (la que pusiste al instalar PostgreSQL)' -AsSecureString
    $env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($segura))
    $claveDb = Clave 32
    $existeRol = & $psql -h 127.0.0.1 -U postgres -d postgres -tAc "select 1 from pg_roles where rolname='multitec'"
    if ($LASTEXITCODE -ne 0) { Falla 'No pude entrar a PostgreSQL con esa clave del usuario postgres.' }
    if ($existeRol -eq '1') {
        & $psql -h 127.0.0.1 -U postgres -d postgres -v ON_ERROR_STOP=1 -qc "ALTER ROLE multitec WITH LOGIN PASSWORD '$claveDb'" | Out-Null
    } else {
        & $psql -h 127.0.0.1 -U postgres -d postgres -v ON_ERROR_STOP=1 -qc "CREATE ROLE multitec WITH LOGIN PASSWORD '$claveDb'" | Out-Null
    }
    $existeDb = & $psql -h 127.0.0.1 -U postgres -d postgres -tAc "select 1 from pg_database where datname='multitec'"
    if ($existeDb -ne '1') { & $psql -h 127.0.0.1 -U postgres -d postgres -v ON_ERROR_STOP=1 -qc 'CREATE DATABASE multitec OWNER multitec ENCODING ''UTF8'' TEMPLATE template0' | Out-Null }
    Remove-Item Env:\PGPASSWORD
    if ($LASTEXITCODE -ne 0) { Falla 'No se pudo crear la base de datos multitec.' }
    Ok 'Usuario y base «multitec» listos (clave al azar, guardada solo en backend\.env)'
}

# ------------------------------------------------------------------------------------------------ backend
Paso 'Preparando el backend (puede tardar unos minutos)'
$venvPy = Join-Path $Backend 'venv\Scripts\python.exe'
if (-not (Test-Path $venvPy)) { & $python[0] @(Resto $python) -m venv (Join-Path $Backend 'venv') }
& $venvPy -m pip install --upgrade pip --quiet --disable-pip-version-check
& $venvPy -m pip install -r (Join-Path $Backend 'requirements.lock') --quiet --disable-pip-version-check
if ($LASTEXITCODE -ne 0) { Falla 'No se pudieron instalar las librerías de Python (¿hay internet?).' }
Ok 'Librerías instaladas'

$temporal = Join-Path $env:TEMP "multitec-datos-$(Get-Random)"
$configTraida = @{}
if ($Datos) {
    Expand-Archive $Datos -DestinationPath $temporal -Force
    $configTraida = Leer-Env (Join-Path $temporal 'configuracion.env')
}

$claveAdmin = $null
if (-not $actualizar) {
    Copy-Item (Join-Path $Backend '.env.example') $EnvFile -Force
    $cambios = @{
        'DATABASE_URL'    = "postgresql://multitec:$claveDb@127.0.0.1:5432/multitec"
        'ENVIRONMENT'     = 'production'
        'JWT_SECRET'      = (Hex 32)
        'UPLOAD_DIR'      = './uploads'
        'BACKUP_DIR'      = $CarpetaRespaldos
        'PG_BIN_PATH'     = $pgBin
    }
    if (-not $Datos) { $claveAdmin = Clave 14; $cambios['ADMIN_PASSWORD'] = $claveAdmin }
    # Lo que se trae de la PC anterior: datos de la empresa, correo, plataforma, IA (nunca su base ni su secreto).
    $permitidas = '^(COMPANY_|SMTP_|NOTIFICATION_EMAIL|PLATFORM_|PUBLIC_SIGNUP_ENABLED|GEO_|AI_|OLLAMA_HOST|ADMIN_EMAIL|ADMIN_NAME|WHISPER_)'
    foreach ($k in $configTraida.Keys) { if ($k -match $permitidas) { $cambios[$k] = $configTraida[$k] } }
    Escribir-Env $EnvFile $cambios
    Ok 'backend\.env creado para producción (clave secreta nueva)'
}
if ($Modo -in @('dominio', 'cloudflare')) { Escribir-Env $EnvFile @{ 'CORS_ORIGINS' = "https://$Dominio" } }
elseif ($Modo -eq 'red-local') { Escribir-Env $EnvFile @{ 'CORS_ORIGINS' = "https://$Dominio" } }

Push-Location $Backend
try {
    $hayTablas = $false
    $cfg = Leer-Env $EnvFile
    if ($cfg['DATABASE_URL'] -match '://([^:]+):([^@]+)@') { $env:PGPASSWORD = [uri]::UnescapeDataString($Matches[2]) }
    $n = & $psql -h 127.0.0.1 -U multitec -d multitec -tAc "select count(*) from information_schema.tables where table_schema='public'"
    $hayTablas = ([int]$n) -gt 0

    if ($Datos) {
        Paso 'Restaurando tus datos'
        if ($hayTablas -and -not $Sobrescribir) { Falla 'La base ya tiene información. Para reemplazarla con los datos del ZIP, vuelve a ejecutar con -Sobrescribir.' }
        $dump = Get-ChildItem $temporal -Filter '*.dump' | Select-Object -First 1
        if (-not $dump) { Falla 'El ZIP de datos no trae la copia de la base (.dump).' }
        $argsRestore = @('-h', '127.0.0.1', '-U', 'multitec', '-d', 'multitec', '--no-owner', '--role=multitec')
        if ($hayTablas) { $argsRestore += @('--clean', '--if-exists') }
        & (Join-Path $pgBin 'pg_restore.exe') @argsRestore $dump.FullName
        if ($LASTEXITCODE -ne 0) { Aviso 'pg_restore terminó con avisos; revisa el registro de la instalación.' }
        $fotos = Get-ChildItem $temporal -Filter '*uploads*.zip' | Select-Object -First 1
        if ($fotos) { Expand-Archive $fotos.FullName -DestinationPath (Join-Path $Backend 'uploads') -Force; Ok 'Fotos, audios y logos restaurados' }
        Ok "Base restaurada desde $($dump.Name)"
    }

    Paso 'Actualizando la estructura de la base de datos'
    & $venvPy -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { Falla 'Falló la actualización de la base (alembic). Revisa el registro.' }
    if (-not $Datos -and -not $hayTablas) {
        & $venvPy -m app.db.seed
        if ($LASTEXITCODE -ne 0) { Falla 'No se pudo crear el administrador inicial.' }
    }
    Ok 'Base de datos al día'
} finally {
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
    Pop-Location
    if (Test-Path $temporal) { Remove-Item $temporal -Recurse -Force }
}

# ------------------------------------------------------------------------------------------------ servicios
Paso 'Configurando la web (Caddy) y los servicios'
$caddyDestino = Join-Path $Deploy 'Caddyfile.servidor'
if ($Modo -eq 'cloudflare') {
    Copy-Item (Join-Path $Deploy 'Caddyfile.tunnel') $caddyDestino -Force
} elseif ($Modo -in @('dominio', 'red-local')) {
    $texto = [IO.File]::ReadAllText((Join-Path $Deploy 'Caddyfile'))
    if ($Modo -eq 'dominio') { $texto = $texto -replace 'multitec\.local \{\s*\r?\n\s*tls internal', "$Dominio {" }
    else { $texto = $texto -replace 'multitec\.local \{', "$Dominio {" }
    [IO.File]::WriteAllText($caddyDestino, $texto, (New-Object Text.UTF8Encoding $false))
}
if (-not (Test-Path $caddyDestino)) { Falla 'No hay configuración de Caddy (Caddyfile.servidor).' }
& caddy validate --config $caddyDestino --adapter caddyfile 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { Falla 'La configuración de Caddy no es válida. Revisa deploy\Caddyfile.servidor.' }
Ok 'Configuración de Caddy válida'

foreach ($svc in 'MultitecWeb', 'MultitecBackend') {
    if (Get-Service $svc -ErrorAction SilentlyContinue) { & nssm stop $svc | Out-Null; & nssm remove $svc confirm | Out-Null }
}
& (Join-Path $Deploy 'install-backend-service.ps1') -RepoRoot $Root | Out-Null
& (Join-Path $Deploy 'install-web-service.ps1') -RepoRoot $Root -CaddyConfig 'Caddyfile.servidor' | Out-Null
Ok 'Servicios MultitecBackend y MultitecWeb instalados (arrancan solos con Windows)'

if ($Modo -in @('dominio', 'red-local')) {
    foreach ($puerto in 80, 443) {
        if (-not (Get-NetFirewallRule -DisplayName "Multitec $puerto" -ErrorAction SilentlyContinue)) {
            New-NetFirewallRule -DisplayName "Multitec $puerto" -Direction Inbound -LocalPort $puerto -Protocol TCP -Action Allow | Out-Null
        }
    }
    Ok 'Firewall abierto en 80 y 443'
}

# ------------------------------------------------------------------------------------------------ respaldos e IA
Paso 'Programando la copia de seguridad diaria'
New-Item -ItemType Directory -Force $CarpetaRespaldos | Out-Null
$argsBackup = @{ EnvFile = $EnvFile; BackupDir = $CarpetaRespaldos }
if ($CopiaExterna) { $argsBackup['CopyTo'] = $CopiaExterna }
& (Join-Path $Deploy 'register-backup-task.ps1') @argsBackup | Out-Null
Ok "Copia diaria a las 2:00 a. m. en $CarpetaRespaldos$(if ($CopiaExterna) { " y $CopiaExterna" })"
if (-not $CopiaExterna) { Aviso 'Sin segunda copia fuera de este disco: agrégala con -CopiaExterna (un disco externo o unidad de red).' }

if ($ConIA) {
    Paso 'Instalando la IA local (Ollama) — descarga varios GB'
    if (-not (Get-Command ollama -ErrorAction SilentlyContinue) -and (Get-Command winget -ErrorAction SilentlyContinue)) {
        winget install --id Ollama.Ollama -e --accept-source-agreements --accept-package-agreements --silent | Out-Null
        Refrescar-Path
    }
    if (Get-Command ollama -ErrorAction SilentlyContinue) {
        foreach ($modelo in 'llama3.2', 'llava', 'nomic-embed-text') { & ollama pull $modelo }
        Ok 'IA local lista'
    } else { Aviso 'No se pudo instalar Ollama; instálalo de https://ollama.com y vuelve a ejecutar con -ConIA.' }
}

# ------------------------------------------------------------------------------------------------ prueba final
Paso 'Probando'
Start-Sleep -Seconds 5
try {
    $salud = Invoke-WebRequest "http://127.0.0.1:$BackendPort/api/health" -UseBasicParsing -TimeoutSec 20
    Ok "Backend responde ($($salud.StatusCode))"
} catch { Aviso "El backend todavía no responde; revisa $Backend\logs\backend.err.log" }

Write-Host ''
Write-Host '=================================================' -ForegroundColor Green
Write-Host '   Multitec quedó instalado' -ForegroundColor Green
Write-Host '=================================================' -ForegroundColor Green
switch ($Modo) {
    'dominio' { Write-Host "  Abre:  https://$Dominio   (el certificado HTTPS puede tardar 1 minuto la primera vez)" }
    'cloudflare' { Write-Host "  Falta conectar el túnel de Cloudflare a http://127.0.0.1:8080 (guía, parte C). Después: https://$Dominio" }
    'red-local' { Write-Host "  En la oficina abre:  https://$Dominio   (acepta el aviso del certificado la primera vez)" }
    default { Write-Host '  Se mantuvo la forma de acceso que ya estaba configurada.' }
}
Write-Host '  Página pública: /web   ·   Registro de empresas: /registro'
Write-Host ''
Write-Host "  Registro de esta instalación: $Deploy\logs" -ForegroundColor Gray
# El registro se cierra ANTES de mostrar la clave del administrador: así no queda escrita en ningún archivo.
try { Stop-Transcript | Out-Null } catch {}
if ($claveAdmin) {
    $adminEmail = (Leer-Env $EnvFile)['ADMIN_EMAIL']
    Write-Host ''
    Write-Host "  Administrador: $adminEmail" -ForegroundColor Yellow
    Write-Host "  Clave temporal: $claveAdmin   (anótala ahora; cámbiala al entrar)" -ForegroundColor Yellow
}
