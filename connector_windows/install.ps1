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

$connector = Join-Path $target "connector.py"
$launcherContent = '@echo off' + [Environment]::NewLine +
    'title Conector Razync' + [Environment]::NewLine +
    '"' + $python.Source + '" "' + $connector + '"' + [Environment]::NewLine +
    'echo.' + [Environment]::NewLine +
    'echo O Conector Razync foi encerrado ou encontrou um erro.' + [Environment]::NewLine +
    'pause'

$localLauncher = Join-Path $target "ABRIR_CONECTOR_RAZYNC.cmd"
Set-Content -Path $localLauncher -Value $launcherContent -Encoding ASCII

$desktop = [Environment]::GetFolderPath("Desktop")
$desktopLauncher = Join-Path $desktop "Abrir Conector Razync.cmd"
Copy-Item $localLauncher $desktopLauncher -Force

$startup = [Environment]::GetFolderPath("Startup")
$startupLauncher = Join-Path $startup "Razync Connector.cmd"
$startupContent = '@echo off' + [Environment]::NewLine +
    'start "Conector Razync" "' + $localLauncher + '"'
Set-Content -Path $startupLauncher -Value $startupContent -Encoding ASCII

Write-Host ""
Write-Host "Conector Razync instalado com sucesso." -ForegroundColor Green
Write-Host "Foi criado o atalho Abrir Conector Razync na Area de Trabalho."
Write-Host "Iniciando agora..."
Start-Process "cmd.exe" -ArgumentList ('/k ""' + $localLauncher + '""')
