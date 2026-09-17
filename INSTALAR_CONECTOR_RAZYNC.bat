@echo off
setlocal
title Instalador do Conector Razync
color 0B

echo.
echo  ==========================================
echo       CONECTOR RAZYNC PARA WINDOWS
echo  ==========================================
echo.
echo  Preparando a instalacao. Aguarde...
echo.

set "RAZYNC_TEMP=%TEMP%\RazyncConnectorInstall"
if not exist "%RAZYNC_TEMP%" mkdir "%RAZYNC_TEMP%"

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$base='https://raw.githubusercontent.com/rodrigofrrsilva1703-a11y/Razync/main/connector_windows/';" ^
  "$dest=$env:RAZYNC_TEMP;" ^
  "foreach($file in @('connector.py','list_certificates.ps1','sign_challenge.ps1','install.ps1')){" ^
  "Invoke-WebRequest -UseBasicParsing -Uri ($base+$file) -OutFile (Join-Path $dest $file)" ^
  "}; & (Join-Path $dest 'install.ps1')"

if errorlevel 1 (
  echo.
  echo  Nao foi possivel concluir a instalacao.
  echo  Verifique se o Python 3 esta instalado e tente novamente.
  echo.
  pause
  exit /b 1
)

echo.
echo  Instalacao concluida.
echo  A janela do conector mostrara o codigo para usar no Razync.
echo.
pause
