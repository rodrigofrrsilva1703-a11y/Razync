$ErrorActionPreference = "Stop"

if ($env:OS -ne "Windows_NT") {
    throw "Este instalador funciona somente no Windows."
}

$source = Split-Path -Parent $MyInvocation.MyCommand.Path
$target = Join-Path $env:LOCALAPPDATA "Razync\Connector\app"
New-Item -ItemType Directory -Path $target -Force | Out-Null

Copy-Item (Join-Path $source "connector.py") $target -Force
Copy-Item (Join-Path $source "list_certificates.ps1") $target -Force
Copy-Item (Join-Path $source "sign_challenge.ps1") $target -Force

$python = Get-Command python.exe -ErrorAction SilentlyContinue
if ($null -eq $python) {
    throw "Python 3 não foi encontrado. Instale o Python 3 e execute novamente."
}

$startup = [Environment]::GetFolderPath("Startup")
$launcher = Join-Path $startup "Razync Connector.cmd"
$command = '@echo off' + [Environment]::NewLine +
    'start "" "' + $python.Source + '" "' + (Join-Path $target "connector.py") + '"'
Set-Content -Path $launcher -Value $command -Encoding ASCII

Write-Host ""
Write-Host "Conector Razync instalado com sucesso." -ForegroundColor Green
Write-Host "Ele será iniciado automaticamente com o Windows."
Write-Host "Iniciando agora..."
Start-Process $python.Source -ArgumentList ('"' + (Join-Path $target "connector.py") + '"')
