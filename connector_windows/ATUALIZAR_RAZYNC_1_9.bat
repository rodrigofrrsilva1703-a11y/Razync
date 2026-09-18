@echo off
setlocal EnableExtensions
title Atualizacao do Conector Razync 1.9
color 0B

set "RAZYNC_APP=%LOCALAPPDATA%\Razync\Connector\app"
set "RAZYNC_SCRIPT=%LOCALAPPDATA%\Razync\Connector\app\connector.py"
set "RAZYNC_PYTHONW=%LOCALAPPDATA%\Razync\Connector\python\pythonw.exe"
set "RAZYNC_TEMP=%TEMP%\RazyncConnector190.py"
set "RAZYNC_LOG=%TEMP%\RazyncConnector190.log"

echo.
echo  ==========================================
echo       ATUALIZACAO CONECTOR RAZYNC 1.9
echo  ==========================================
echo.

if not exist "%RAZYNC_APP%" goto nao_instalado
if not exist "%RAZYNC_PYTHONW%" goto nao_instalado

echo  Baixando a correcao do e-CAC...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "try { $ErrorActionPreference='Stop'; Invoke-WebRequest -UseBasicParsing -Headers @{'Cache-Control'='no-cache';'Pragma'='no-cache'} -Uri 'https://raw.githubusercontent.com/rodrigofrrsilva1703-a11y/Razync/main/connector_windows/connector.py?build=190-ecac' -OutFile $env:RAZYNC_TEMP; exit 0 } catch { Write-Error $_.Exception.Message; exit 1 }" > "%RAZYNC_LOG%" 2>&1
if errorlevel 1 goto erro

echo  Reiniciando o conector...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -and $_.CommandLine -like '*Razync*Connector*connector.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >> "%RAZYNC_LOG%" 2>&1
copy /y "%RAZYNC_TEMP%" "%RAZYNC_SCRIPT%" >> "%RAZYNC_LOG%" 2>&1
if errorlevel 1 goto erro

start "" /b "%RAZYNC_PYTHONW%" "%RAZYNC_SCRIPT%"
timeout /t 3 /nobreak >nul

echo  Verificando a nova versao...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "try { $r=Invoke-RestMethod -UseBasicParsing -Uri 'http://127.0.0.1:17891/v1/health' -TimeoutSec 8; if(-not $r.ok -or $r.version -ne '0.4.1'){throw ('Versao inesperada: '+$r.version)}; Write-Output ('Conector ativo - versao '+$r.version); exit 0 } catch { Write-Error $_.Exception.Message; exit 1 }" >> "%RAZYNC_LOG%" 2>&1
if errorlevel 1 goto erro

del /q "%RAZYNC_TEMP%" 2>nul
color 0A
echo.
echo  ATUALIZACAO CONCLUIDA - CONECTOR 0.4.1
echo  Pode fechar esta janela.
echo.
pause
exit /b 0

:nao_instalado
color 0C
echo  A instalacao anterior do Conector Razync nao foi encontrada.
echo  Execute primeiro o instalador completo.
pause
exit /b 1

:erro
color 0C
echo.
echo  A atualizacao nao foi concluida.
echo.
type "%RAZYNC_LOG%"
echo.
pause
exit /b 1
