@echo off
setlocal EnableExtensions
title Atualizacao Administrativa do Conector Razync 2.5
color 0B

set "RAZYNC_APP=%LOCALAPPDATA%\Razync\Connector\app"
set "RAZYNC_PYTHONW=%LOCALAPPDATA%\Razync\Connector\python\pythonw.exe"
set "RAZYNC_SCRIPT=%RAZYNC_APP%\connector.py"
set "RAZYNC_TEMP=%TEMP%\RazyncConnector250"
set "RAZYNC_LOG=%TEMP%\RazyncConnector250.log"

echo.
echo  =================================================
echo    CONECTOR RAZYNC 2.5 - CERTIFICADO AUTOMATICO
echo  =================================================
echo.
echo  Ao testar no Razync, o Windows pedira autorizacao.
echo  Clique em SIM para permitir a selecao do certificado A1.
echo.

if not exist "%RAZYNC_APP%" goto nao_instalado
if not exist "%RAZYNC_PYTHONW%" goto nao_instalado
if exist "%RAZYNC_TEMP%" rmdir /s /q "%RAZYNC_TEMP%"
mkdir "%RAZYNC_TEMP%"

echo  Baixando os componentes 2.5...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "try { $ErrorActionPreference='Stop'; $base='https://raw.githubusercontent.com/rodrigofrrsilva1703-a11y/Razync/main/connector_windows/'; $files=@('connector.py','configure_chrome.ps1','configure_chrome_admin.ps1','automate_ecac.ps1'); foreach($f in $files){Invoke-WebRequest -UseBasicParsing -Headers @{'Cache-Control'='no-cache';'Pragma'='no-cache'} -Uri ($base+$f+'?build=250') -OutFile (Join-Path $env:RAZYNC_TEMP $f)}; exit 0 } catch { Write-Error $_.Exception.Message; exit 1 }" > "%RAZYNC_LOG%" 2>&1
if errorlevel 1 goto erro

echo  Instalando e reiniciando o conector...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -and $_.CommandLine -like '*Razync*Connector*connector.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >> "%RAZYNC_LOG%" 2>&1
copy /y "%RAZYNC_TEMP%\connector.py" "%RAZYNC_SCRIPT%" >> "%RAZYNC_LOG%" 2>&1
copy /y "%RAZYNC_TEMP%\configure_chrome.ps1" "%RAZYNC_APP%\configure_chrome.ps1" >> "%RAZYNC_LOG%" 2>&1
copy /y "%RAZYNC_TEMP%\configure_chrome_admin.ps1" "%RAZYNC_APP%\configure_chrome_admin.ps1" >> "%RAZYNC_LOG%" 2>&1
copy /y "%RAZYNC_TEMP%\automate_ecac.ps1" "%RAZYNC_APP%\automate_ecac.ps1" >> "%RAZYNC_LOG%" 2>&1
if errorlevel 1 goto erro

start "" /b "%RAZYNC_PYTHONW%" "%RAZYNC_SCRIPT%"
timeout /t 3 /nobreak >nul

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "try { $r=Invoke-RestMethod -UseBasicParsing -Uri 'http://127.0.0.1:17891/v1/health' -TimeoutSec 8; if(-not $r.ok -or $r.version -ne '0.7.0'){throw ('Versao inesperada: '+$r.version)}; exit 0 } catch { Write-Error $_.Exception.Message; exit 1 }" >> "%RAZYNC_LOG%" 2>&1
if errorlevel 1 goto erro

rmdir /s /q "%RAZYNC_TEMP%" 2>nul
color 0A
echo.
echo  INSTALACAO CONCLUIDA - CONECTOR 2.5
echo  Agora feche todas as janelas do Chrome e teste no Razync.
echo  Quando o Windows pedir permissao, clique em SIM.
echo.
pause
exit /b 0

:nao_instalado
color 0C
echo  A instalacao anterior do Conector Razync nao foi encontrada.
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
