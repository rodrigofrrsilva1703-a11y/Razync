@echo off
setlocal
title Instalador Corrigido do Conector Razync
color 0B
echo.
echo  ==========================================
echo       CONECTOR RAZYNC PARA WINDOWS
echo  ==========================================
echo.
echo  Atualizando os componentes...
set "RAZYNC_TEMP=%TEMP%\RazyncConnectorInstallV2"
if not exist "%RAZYNC_TEMP%" mkdir "%RAZYNC_TEMP%"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $base='https://raw.githubusercontent.com/rodrigofrrsilva1703-a11y/Razync/main/connector_windows/'; $version='?v=d5833f'; $dest=$env:RAZYNC_TEMP; foreach($file in @('connector.py','list_certificates.ps1','sign_challenge.ps1','install.ps1')) { Invoke-WebRequest -UseBasicParsing -Headers @{'Cache-Control'='no-cache'} -Uri ($base+$file+$version) -OutFile (Join-Path $dest $file) }; & (Join-Path $dest 'install.ps1')"
if errorlevel 1 (
  echo.
  echo  A instalacao nao foi concluida.
  echo  Envie uma foto desta tela para verificarmos.
  echo.
  pause
  exit /b 1
)
echo.
echo  Atualizacao concluida.
echo  Procure Abrir Conector Razync na Area de Trabalho.
echo.
pause
