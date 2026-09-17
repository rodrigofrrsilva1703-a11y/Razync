$ErrorActionPreference = "Stop"

if ($env:OS -ne "Windows_NT") {
    throw "Este instalador funciona somente no Windows."
}

$source = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Join-Path $env:LOCALAPPDATA "Razync\Connector"
$target = Join-Path $root "app"
$runtime = Join-Path $root "python"

# Encerra somente instancias antigas do proprio conector antes de atualizar.
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
$pythonwPath = Join-Path $runtime "pythonw.exe"
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
if (-not (Test-Path $pythonPath) -or -not (Test-Path $pythonwPath)) {
    throw "Nao foi possivel preparar o componente interno do conector."
}

$connector = Join-Path $target "connector.py"

# Atalho visivel, usado somente para diagnostico.
$launcherContent = '@echo off' + [Environment]::NewLine +
    'title Conector Razync - Diagnostico' + [Environment]::NewLine +
    '"' + $pythonPath + '" "' + $connector + '"' + [Environment]::NewLine +
    'echo.' + [Environment]::NewLine +
    'echo O Conector Razync foi encerrado ou encontrou um erro.' + [Environment]::NewLine +
    'pause'

$localLauncher = Join-Path $target "ABRIR_CONECTOR_RAZYNC.cmd"
Set-Content -Path $localLauncher -Value $launcherContent -Encoding ASCII

# Inicializador silencioso: usa pythonw.exe e nao deixa janela preta aberta.
$silentLauncher = Join-Path $target "INICIAR_CONECTOR_SILENCIOSO.vbs"
$silentCommand = '"' + $pythonwPath + '" "' + $connector + '"'
$vbsContent = 'Set shell = CreateObject("WScript.Shell")' + [Environment]::NewLine +
    'shell.Run "' + ($silentCommand -replace '"', '""') + '", 0, False'
Set-Content -Path $silentLauncher -Value $vbsContent -Encoding ASCII

$desktop = [Environment]::GetFolderPath("Desktop")
$desktopLauncher = Join-Path $desktop "Conector Razync - Diagnostico.cmd"
Copy-Item $localLauncher $desktopLauncher -Force

$stopLauncher = Join-Path $desktop "Parar Conector Razync.cmd"
$stopContent = '@echo off' + [Environment]::NewLine +
    'powershell.exe -NoLogo -NoProfile -Command "Get-CimInstance Win32_Process ^| Where-Object { $_.CommandLine -and $_.CommandLine -like ''*Razync*Connector*connector.py*'' } ^| ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"' + [Environment]::NewLine +
    'echo Conector Razync encerrado.' + [Environment]::NewLine +
    'timeout /t 2 /nobreak >nul'
Set-Content -Path $stopLauncher -Value $stopContent -Encoding ASCII

# Inicia silenciosamente em cada entrada no Windows.
$startup = [Environment]::GetFolderPath("Startup")
$oldStartupLauncher = Join-Path $startup "Razync Connector.cmd"
Remove-Item $oldStartupLauncher -Force -ErrorAction SilentlyContinue
$startupLauncher = Join-Path $startup "Razync Connector.vbs"
Copy-Item $silentLauncher $startupLauncher -Force

Write-Host ""
Write-Host "Conector Razync instalado com sucesso." -ForegroundColor Green
Write-Host "Ele ficara ativo em segundo plano, sem janela aberta."
Write-Host "Ele tambem iniciara automaticamente com o Windows."
Write-Host "Foi criado um atalho de diagnostico e outro para encerrar na Area de Trabalho."
Write-Host "Iniciando em segundo plano..."
Start-Process "wscript.exe" -ArgumentList ('"' + $silentLauncher + '"')
Start-Sleep -Seconds 2
