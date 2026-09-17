@echo off
setlocal
title Instalador do Conector Razync 1.4
color 0B
echo.
echo  ==========================================
echo       CONECTOR RAZYNC PARA WINDOWS 1.4
echo  ==========================================
echo.
echo  O conector sera instalado somente para este usuario.
echo  Nenhum certificado ou senha sera exportado.
echo.
echo  Etapa 1 de 3 - Baixando componentes...
set "RAZYNC_TEMP=%TEMP%\RazyncConnectorSetup140"
set "RAZYNC_LOG=%TEMP%\RazyncConnectorSetup.log"
if exist "%RAZYNC_TEMP%" rmdir /s /q "%RAZYNC_TEMP%"
mkdir "%RAZYNC_TEMP%"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $base='https://raw.githubusercontent.com/rodrigofrrsilva1703-a11y/Razync/main/connector_windows/'; $version='?release=1.4.0'; $dest=$env:RAZYNC_TEMP; foreach($file in @('connector.py','list_certificates.ps1','sign_challenge.ps1','install.ps1')) { Invoke-WebRequest -UseBasicParsing -Headers @{'Cache-Control'='no-cache'} -Uri ($base+$file+$version) -OutFile (Join-Path $dest $file) }; & (Join-Path $dest 'install.ps1')" > "%RAZYNC_LOG%" 2>&1
if errorlevel 1 (
  color 0C
  echo.
  echo  A instalacao encontrou um erro.
  echo  O diagnostico foi salvo em:
  echo  %RAZYNC_LOG%
  echo.
  type "%RAZYNC_LOG%"
  echo.
  pause
  exit /b 1
)
color 0A
echo.
type "%RAZYNC_LOG%"
echo.
echo  Etapa 3 de 3 - Abrindo o Conector Razync...
set "RAZYNC_LAUNCHER=%LOCALAPPDATA%\Razync\Connector\app\ABRIR_CONECTOR_RAZYNC.cmd"
if not exist "%RAZYNC_LAUNCHER%" (
  color 0C
  echo  O atalho interno do conector nao foi criado.
  echo  Envie uma foto desta tela.
  pause
  exit /b 1
)
start "Conector Razync" "%RAZYNC_LAUNCHER%"
timeout /t 2 /nobreak >nul
echo.
echo  ==========================================
echo       INSTALACAO CONCLUIDA
echo  ==========================================
echo.
echo  O Conector Razync abriu em outra janela.
echo  Tambem foi criado um atalho na Area de Trabalho.
echo.
pause
