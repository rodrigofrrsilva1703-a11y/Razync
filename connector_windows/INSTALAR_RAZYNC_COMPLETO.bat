@echo off
setlocal
title Instalador Completo do Conector Razync
color 0B
echo.
echo  ==========================================
echo       CONECTOR RAZYNC PARA WINDOWS
echo  ==========================================
echo.
echo  Preparando o conector. Isso pode levar alguns minutos...
set "RAZYNC_TEMP=%TEMP%\RazyncConnectorInstallV3"
if not exist "%RAZYNC_TEMP%" mkdir "%RAZYNC_TEMP%"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $base='https://raw.githubusercontent.com/rodrigofrrsilva1703-a11y/Razync/main/connector_windows/'; $version='?v=7adac9a'; $dest=$env:RAZYNC_TEMP; foreach($file in @('connector.py','list_certificates.ps1','sign_challenge.ps1','install.ps1')) { Invoke-WebRequest -UseBasicParsing -Headers @{'Cache-Control'='no-cache'} -Uri ($base+$file+$version) -OutFile (Join-Path $dest $file) }; & (Join-Path $dest 'install.ps1')"
if errorlevel 1 (
  echo.
  echo  A instalacao nao foi concluida.
  echo  Envie uma foto desta tela para verificarmos.
  echo.
  pause
  exit /b 1
)
echo.
echo  Instalacao concluida.
echo  O conector abrira mostrando o codigo de pareamento.
echo.
pause
