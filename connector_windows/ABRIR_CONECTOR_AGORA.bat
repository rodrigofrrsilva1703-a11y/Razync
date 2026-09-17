@echo off
setlocal
title Conector Razync - Inicializacao Direta
color 0B
echo.
echo  ==========================================
echo       ABRINDO CONECTOR RAZYNC
echo  ==========================================
echo.

set "RAZYNC_ROOT=%LOCALAPPDATA%\Razync\Connector"
set "RAZYNC_APP=%RAZYNC_ROOT%\app"
set "RAZYNC_PYTHON=%RAZYNC_ROOT%\python\python.exe"

if not exist "%RAZYNC_PYTHON%" (
  color 0C
  echo  O componente interno nao foi encontrado.
  echo  Execute primeiro o instalador oficial do Conector Razync.
  echo.
  pause
  exit /b 1
)

if not exist "%RAZYNC_APP%" mkdir "%RAZYNC_APP%"

echo  Atualizando os arquivos do conector...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $base='https://raw.githubusercontent.com/rodrigofrrsilva1703-a11y/Razync/main/connector_windows/'; $dest=$env:RAZYNC_APP; foreach($file in @('connector.py','list_certificates.ps1','sign_challenge.ps1')) { Invoke-WebRequest -UseBasicParsing -Headers @{'Cache-Control'='no-cache'} -Uri ($base+$file+'?direct=2.1') -OutFile (Join-Path $dest $file) }"
if errorlevel 1 (
  color 0C
  echo.
  echo  Nao foi possivel atualizar os arquivos.
  echo.
  pause
  exit /b 1
)

echo  Encerrando uma instancia antiga, se existir...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -and $_.CommandLine -like '*Razync*Connector*connector.py*' -and $_.ProcessId -ne $PID } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
timeout /t 1 /nobreak >nul

echo.
echo  Iniciando na mesma janela...
echo.
"%RAZYNC_PYTHON%" "%RAZYNC_APP%\connector.py"

echo.
color 0C
echo  O conector foi encerrado. A mensagem acima mostra o motivo.
pause
