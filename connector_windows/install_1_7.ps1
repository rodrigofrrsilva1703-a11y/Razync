$ErrorActionPreference = "Stop"

try {
    if ($env:OS -ne "Windows_NT") {
        throw "Este instalador funciona somente no Windows."
    }

    $source = Split-Path -Parent $MyInvocation.MyCommand.Path
    $root = Join-Path $env:LOCALAPPDATA "Razync\Connector"
    $target = Join-Path $root "app"
    $runtime = Join-Path $root "python"

    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.CommandLine -and
            $_.CommandLine -like "*Razync*Connector*connector.py*"
        } |
        ForEach-Object {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
    Start-Sleep -Milliseconds 600

    New-Item -ItemType Directory -Path $target -Force | Out-Null
    New-Item -ItemType Directory -Path $runtime -Force | Out-Null

    foreach ($file in @("connector.py", "list_certificates.ps1", "sign_challenge.ps1")) {
        $sourceFile = Join-Path $source $file
        if (-not (Test-Path $sourceFile)) {
            throw "Arquivo obrigatorio nao encontrado: $file"
        }
        Copy-Item $sourceFile $target -Force
    }

    $pythonPath = Join-Path $runtime "python.exe"
    $pythonwPath = Join-Path $runtime "pythonw.exe"
    if (-not (Test-Path $pythonPath) -or -not (Test-Path $pythonwPath)) {
        Write-Host "Preparando o componente interno do conector..."
        $zipPath = Join-Path $env:TEMP "razync-python-3.12.10-170.zip"
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
        throw "O Python interno do conector nao foi preparado."
    }

    $connector = Join-Path $target "connector.py"
    $shell = New-Object -ComObject WScript.Shell

    # Atalho silencioso em formato LNK; evita bloqueios de arquivos VBS.
    $silentLauncher = Join-Path $target "INICIAR_CONECTOR_SILENCIOSO.lnk"
    $shortcut = $shell.CreateShortcut($silentLauncher)
    $shortcut.TargetPath = $pythonwPath
    $shortcut.Arguments = '"' + $connector + '"'
    $shortcut.WorkingDirectory = $target
    $shortcut.WindowStyle = 7
    $shortcut.Description = "Conector Razync em segundo plano"
    $shortcut.Save()
    if (-not (Test-Path $silentLauncher)) {
        throw "O atalho silencioso nao foi criado."
    }

    $diagnosticContent = '@echo off' + [Environment]::NewLine +
        'title Conector Razync - Diagnostico' + [Environment]::NewLine +
        '"' + $pythonPath + '" "' + $connector + '"' + [Environment]::NewLine +
        'echo.' + [Environment]::NewLine +
        'echo O Conector Razync foi encerrado ou encontrou um erro.' + [Environment]::NewLine +
        'pause'
    $diagnosticLocal = Join-Path $target "ABRIR_CONECTOR_RAZYNC.cmd"
    Set-Content -Path $diagnosticLocal -Value $diagnosticContent -Encoding ASCII

    $desktop = [Environment]::GetFolderPath("Desktop")
    Copy-Item $diagnosticLocal (Join-Path $desktop "Conector Razync - Diagnostico.cmd") -Force

    $stopLauncher = Join-Path $desktop "Parar Conector Razync.cmd"
    $stopContent = '@echo off' + [Environment]::NewLine +
        'powershell.exe -NoLogo -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -like ''*Razync*Connector*connector.py*'' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"' + [Environment]::NewLine +
        'echo Conector Razync encerrado.' + [Environment]::NewLine +
        'timeout /t 2 /nobreak >nul'
    Set-Content -Path $stopLauncher -Value $stopContent -Encoding ASCII

    $startup = [Environment]::GetFolderPath("Startup")
    Remove-Item (Join-Path $startup "Razync Connector.cmd") -Force -ErrorAction SilentlyContinue
    Remove-Item (Join-Path $startup "Razync Connector.vbs") -Force -ErrorAction SilentlyContinue
    Copy-Item $silentLauncher (Join-Path $startup "Razync Connector.lnk") -Force

    Start-Process -FilePath $pythonwPath -ArgumentList ('"' + $connector + '"') -WorkingDirectory $target -WindowStyle Hidden
    Start-Sleep -Seconds 3

    $health = Invoke-RestMethod -UseBasicParsing -Uri "http://127.0.0.1:17891/v1/health" -TimeoutSec 8
    if (-not $health.ok) {
        throw "O conector foi instalado, mas nao respondeu ao teste local."
    }

    Write-Host ""
    Write-Host "Conector Razync instalado e testado com sucesso." -ForegroundColor Green
    Write-Host "Versao ativa: $($health.version)"
    Write-Host "Ele esta executando em segundo plano e iniciara com o Windows."
    exit 0
}
catch {
    Write-Error $_.Exception.Message
    exit 1
}
