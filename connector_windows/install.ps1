$ErrorActionPreference = "Stop"

if ($env:OS -ne "Windows_NT") {
    throw "Este instalador funciona somente no Windows."
}

$source = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Join-Path $env:LOCALAPPDATA "Razync\Connector"
$target = Join-Path $root "app"
$runtime = Join-Path $root "python"

# Encerra somente instâncias antigas do próprio conector antes de atualizar.
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.CommandLine -and
        $_.CommandLine -like "*Razync*Connector*connector.py*"
    } |
    ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
Start-Sleep -Milliseconds 800

New-Item -ItemType Directory -Path $target -Force | Out-Null
New-Item -ItemType Directory -Path $runtime -Force | Out-Null

Copy-Item (Join-Path $source "connector.py") $target -Force
Copy-Item (Join-Path $source "list_certificates.ps1") $target -Force
Copy-Item (Join-Path $source "sign_challenge.ps1") $target -Force

$pythonPath = Join-Path $runtime "python.exe"
if (-not (Test-Path $pythonPath)) {
    Write-Host "Preparando o componente interno do conector..."
    $zipPath = Join-Path $env:TEMP "razync-python-3.12.10.zip"
    $pythonUrl = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip"
    Invoke-WebRequest -UseBasicParsing -Headers @{"Cache-Control"="no-cache"} -Uri $pythonUrl -OutFile $zipPath
    $checksumEsperado = "FE8EF205F2E9C3BA44D0CF9954E1ABD3"
    $checksumObtido = (Get-FileHash -Path $zipPath -Algorithm MD5).Hash.ToUpperInvariant()
    if ($checksumObtido -ne $checksumEsperado) {
        Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
        throw "A verificacao de integridade do componente interno falhou."
    }
    Expand-Archive -Path $zipPath -DestinationPath $runtime -Force
    Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
}
if (-not (Test-Path $pythonPath)) {
    throw "Nao foi possivel preparar o componente interno do conector."
}

$connector = Join-Path $target "connector.py"
$launcherContent = '@echo off' + [Environment]::NewLine +
    'title Conector Razync' + [Environment]::NewLine +
    '"' + $pythonPath + '" "' + $connector + '"' + [Environment]::NewLine +
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
