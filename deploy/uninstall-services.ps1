#Requires -RunAsAdministrator
<# Detiene y elimina los servicios de Windows de Multitec (backend + web/Caddy). #>

$nssm = (Get-Command nssm -ErrorAction SilentlyContinue).Source
if (-not $nssm) {
    throw "nssm no está en el PATH."
}

foreach ($service in @("MultitecWeb", "MultitecBackend")) {
    if (Get-Service -Name $service -ErrorAction SilentlyContinue) {
        Stop-Service $service -Force -ErrorAction SilentlyContinue
        & $nssm remove $service confirm
        Write-Output "$service eliminado."
    } else {
        Write-Output "$service no estaba instalado."
    }
}
