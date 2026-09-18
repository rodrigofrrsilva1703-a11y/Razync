@echo off
setlocal
title Instalador do Conector Razync 1.7
color 0B
echo.
echo  ==========================================
echo       CONECTOR RAZYNC PARA WINDOWS 1.7
echo  ==========================================
echo.
echo  Etapa 1 de 3 - Baixando arquivos novos...
set "RAZYNC_TEMP=%TEMP%\RazyncConnectorSetup170"
set "RAZYNC_LOG=%TEMP%\RazyncConnectorSetup170.log"
if exist "%RAZYNC_TEMP%" rmdir /s /q "%RAZYNC_TEMP%"
mkdir "%RAZYNC_TEMP%"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "try { $ErrorActionPreference='Stop'; $base='https://raw.githubusercontent.com/rodrigofrrsilva1703-a11y/Razync/main/connector_windows/'; $dest=$env:RAZYNC_TEMP; foreach($file in @('connector.py','list_certificates.ps1','sign_challenge.ps1','install_1_7.ps1')) { $uri=$base+$file+'?build=170-unique'; Invoke-WebRequest -UseBasicParsing -Headers @{'Cache-Control'='no-cache';'Pragma'='no-cache'} -Uri $uri -OutFile (Join-Path $dest $file) }; & (Join-Path $dest 'install_1_7.ps1'); if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } } catch { Write-Error $_.Exception.Message; exit 1 }" > "%RAZYNC_LOG%" 2>&1
if errorlevel 1 goto erro

echo.
echo  Etapa 2 de 3 - Conferindo o inicializador...
set "RAZYNC_LAUNCHER=%LOCALAPPDATA%\Razync\Connector\app\INICIAR_CONECTOR_SILENCIOSO.lnk"
if not exist "%RAZYNC_LAUNCHER%" goto erro

echo  Etapa 3 de 3 - Testando o conector local...
powershell.exe -NoLogo -NoProfile -Command "try { $r=Invoke-RestMethod -UseBasicParsing -Uri 'http://127.0.0.1:17891/v1/health' -TimeoutSec 8; if(-not $r.ok){exit 1}; Write-Host ('Conector ativo - versao '+$r.version) } catch { exit 1 }" >> "%RAZYNC_LOG%" 2>&1
if errorlevel 1 goto erro

color 0A
echo.
type "%RAZYNC_LOG%"
echo.
echo  ==========================================
echo       INSTALACAO CONCLUIDA
echo  ==========================================
echo.
echo  O Conector Razync esta funcionando em segundo plano.
echo  Pode fechar esta janela.
echo.
pause
exit /b 0

:erro
color 0C
echo.
echo  A instalacao nao foi concluida.
echo  Diagnostico:
echo  %RAZYNC_LOG%
echo.
type "%RAZYNC_LOG%"
echo.
echo  Envie uma foto desta tela.
pause
exit /b 1
