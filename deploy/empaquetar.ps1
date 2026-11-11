<#
Arma el paquete de instalación de Multitec para el servidor: el backend (sin el entorno de Python, la
configuración ni los datos de esta PC), la web YA COMPILADA (el servidor no necesita Node.js), los scripts de
instalación, INSTALAR.bat y la guía.

Normal: el paquete NO tiene datos de clientes ni claves (se puede copiar sin riesgo); los datos van aparte con
EXPORTAR-DATOS.bat. Con -ConDatos (EMPAQUETAR-COMPLETO.bat) se arma UN SOLO archivo con todo: programa, imágenes,
videos y los datos de esta PC adentro; el instalador los encuentra y los restaura solo. Ese archivo tiene datos de
clientes: llévalo en USB.

Uso: doble clic en EMPAQUETAR.bat (o: powershell -ExecutionPolicy Bypass -File deploy\empaquetar.ps1)
#>
param(
    [string]$Destino = (Join-Path $HOME 'MultitecServidor'),
    # Un solo archivo con todo, incluidos los datos de esta PC (base, fotos, configuración).
    [switch]$ConDatos
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$commit = (git -C $Root rev-parse --short HEAD 2>$null)
if (-not $commit) { $commit = 'sin-git' }
$pendientes = git -C $Root status --porcelain 2>$null | Where-Object { $_ -notmatch '^\?\? \.vscode/' }
$stamp = Get-Date -Format 'yyyy-MM-dd'
$nombre = if ($ConDatos) { "MultitecCompleto_${stamp}_$commit" } else { "MultitecServidor_${stamp}_$commit" }
$staging = Join-Path $env:TEMP "multitec-paquete\$nombre"

Write-Host 'Compilando la web...' -ForegroundColor Cyan
Push-Location (Join-Path $Root 'frontend')
try {
    Remove-Item Env:\PWA_RESET -ErrorAction SilentlyContinue
    npm run build | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Falló la compilación de la web (npm run build).' }
} finally { Pop-Location }

if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
New-Item -ItemType Directory -Force $staging | Out-Null

Write-Host 'Copiando archivos...' -ForegroundColor Cyan
# robocopy: códigos < 8 son éxito.
robocopy (Join-Path $Root 'backend') (Join-Path $staging 'backend') /E /NFL /NDL /NJH /NJS /NP `
    /XD venv __pycache__ uploads logs tests .pytest_cache .mypy_cache /XF .env *.db *.pyc *.log | Out-Null
if ($LASTEXITCODE -ge 8) { throw 'Falló la copia del backend.' }
robocopy (Join-Path $Root 'frontend\dist') (Join-Path $staging 'frontend\dist') /E /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw 'Falló la copia de la web.' }
robocopy (Join-Path $Root 'deploy') (Join-Path $staging 'deploy') /E /NFL /NDL /NJH /NJS /NP `
    /XD backups logs /XF Caddyfile.servidor *.log | Out-Null
if ($LASTEXITCODE -ge 8) { throw 'Falló la copia de los scripts.' }
Copy-Item (Join-Path $Root 'deploy\INSTALAR.bat') $staging
Copy-Item (Join-Path $Root 'deploy\GUIA-INSTALACION.html') $staging
"Multitec — paquete $nombre`r`nVersión del código: $commit`r`nArmado: $(Get-Date -Format 'dd/MM/yyyy HH:mm') en $env:COMPUTERNAME" |
    Set-Content -Encoding UTF8 (Join-Path $staging 'VERSION.txt')

# Ninguna configuración, base de datos ni archivo subido de esta PC puede viajar SUELTO en el paquete (los datos solo
# van, si se pidió, dentro del ZIP de datos que se restaura en el servidor).
$prohibidos = Get-ChildItem $staging -Recurse -File | Where-Object { $_.Name -eq '.env' -or $_.Extension -in '.db', '.dump' -or $_.FullName -match '\\uploads\\' }
if ($prohibidos) { throw "El paquete incluiría archivos privados: $($prohibidos.FullName -join ', ')" }

if ($ConDatos) {
    Write-Host 'Exportando los datos de esta PC dentro del paquete...' -ForegroundColor Cyan
    & (Join-Path $PSScriptRoot 'exportar-datos.ps1') -Destino $staging
    if (-not (Get-ChildItem $staging -Filter 'MultitecDatos_*.zip')) { throw 'No se pudieron exportar los datos.' }
}

New-Item -ItemType Directory -Force $Destino | Out-Null
$zip = Join-Path $Destino "$nombre.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path (Join-Path $staging '*') -DestinationPath $zip
Remove-Item (Split-Path $staging) -Recurse -Force

$mb = [math]::Round((Get-Item $zip).Length / 1MB, 1)
Write-Host ''
Write-Host "Listo: $zip ($mb MB)" -ForegroundColor Green
if ($pendientes) { Write-Host 'Aviso: hay cambios sin commit en el código; el paquete los incluye igual.' -ForegroundColor Yellow }
if ($ConDatos) {
    Write-Host 'Este archivo tiene TODO, incluidos los datos de tus clientes y la clave del correo:' -ForegroundColor Yellow
    Write-Host 'llévalo en USB, no lo mandes por WhatsApp/correo ni lo subas a la nube, y bórralo cuando el servidor funcione.' -ForegroundColor Yellow
}
