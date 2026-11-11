<#
Exporta los datos de Multitec de ESTA PC para llevarlos al servidor nuevo: copia completa de la base de datos, las
fotos/audios/logos subidos y la configuración del negocio (datos de la empresa, correo, plataforma, IA).

NO incluye: la clave secreta (JWT_SECRET) ni la clave de la base de datos; el servidor genera las suyas.

El ZIP tiene datos de tus clientes y la clave de aplicación del correo: llévalo en una memoria USB o disco, NO lo
subas a GitHub, a correos ni al OneDrive del trabajo, y bórralo cuando el servidor esté funcionando.

Uso: doble clic en EXPORTAR-DATOS.bat (o: powershell -ExecutionPolicy Bypass -File deploy\exportar-datos.ps1)
#>
param(
    [string]$Destino = (Join-Path $HOME 'MultitecServidor')
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$EnvFile = Join-Path $Root 'backend\.env'
if (-not (Test-Path $EnvFile)) { throw "No encontré $EnvFile" }
if ($Destino -match 'OneDrive - Ministerio') { throw 'No guardes datos de clientes en el OneDrive del trabajo. Usa otra carpeta o una memoria USB.' }

$stamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$tmp = Join-Path $env:TEMP "multitec-exportar-$stamp"
New-Item -ItemType Directory -Force $tmp, $Destino | Out-Null

Write-Host 'Sacando la copia de la base de datos y de las fotos...' -ForegroundColor Cyan
& (Join-Path $PSScriptRoot 'backup-postgres.ps1') -EnvFile $EnvFile -BackupDir $tmp -RetentionDays 36500
if (-not (Get-ChildItem $tmp -Filter '*.dump')) { throw 'No se generó la copia de la base de datos.' }

# Solo la configuración del negocio; nunca la base de datos, la clave secreta ni rutas de esta PC.
$permitidas = '^(COMPANY_|SMTP_|NOTIFICATION_EMAIL|PLATFORM_|PUBLIC_SIGNUP_ENABLED|GEO_|AI_|OLLAMA_HOST|ADMIN_EMAIL|ADMIN_NAME|WHISPER_)'
$lineas = foreach ($linea in [IO.File]::ReadAllLines($EnvFile)) {
    # La clave se guarda antes de compararla: cada -match reemplaza $Matches.
    if ($linea -match '^\s*([A-Z0-9_]+)\s*=') { $clave = $Matches[1]; if ($clave -match $permitidas -and $clave -ne 'COMPANY_LOGO_PATH') { $linea } }
}
[IO.File]::WriteAllLines((Join-Path $tmp 'configuracion.env'), [string[]]$lineas, (New-Object Text.UTF8Encoding $false))
@"
Datos de Multitec exportados el $(Get-Date -Format 'dd/MM/yyyy HH:mm') desde $env:COMPUTERNAME.
Contiene datos de clientes: guárdalo en un lugar seguro y bórralo cuando el servidor funcione.
En el servidor: copia este ZIP dentro de la carpeta de Multitec y ejecuta INSTALAR.bat como administrador.
"@ | Set-Content -Encoding UTF8 (Join-Path $tmp 'LEEME.txt')

$zip = Join-Path $Destino "MultitecDatos_$stamp.zip"
Compress-Archive -Path (Join-Path $tmp '*') -DestinationPath $zip -Force
Remove-Item $tmp -Recurse -Force

$mb = [math]::Round((Get-Item $zip).Length / 1MB, 1)
Write-Host ''
Write-Host "Listo: $zip ($mb MB)" -ForegroundColor Green
Write-Host 'Tiene datos de tus clientes y la clave del correo: llévalo en USB y bórralo cuando el servidor funcione.' -ForegroundColor Yellow
