@echo off
setlocal EnableExtensions
title Instalador do Conector Razync 1.8
color 0B
echo.
echo  ==========================================
echo       CONECTOR RAZYNC PARA WINDOWS 1.8
echo  ==========================================
echo.
set "RAZYNC_TEMP=%TEMP%\RazyncConnectorSetup180"
set "RAZYNC_LOG=%TEMP%\RazyncConnectorSetup180.log"
set "RAZYNC_ROOT=%LOCALAPPDATA%\Razync\Connector"
set "RAZYNC_APP=%LOCALAPPDATA%\Razync\Connector\app"
set "RAZYNC_PY=%LOCALAPPDATA%\Razync\Connector\python"
set "RAZYNC_PYTHON=%LOCALAPPDATA%\Razync\Connector\python\python.exe"
set "RAZYNC_PYTHONW=%LOCALAPPDATA%\Razync\Connector\python\pythonw.exe"
set "RAZYNC_SCRIPT=%LOCALAPPDATA%\Razync\Connector\app\connector.py"
set "RAZYNC_LAUNCHER=%LOCALAPPDATA%\Razync\Connector\app\INICIAR_CONECTOR_SILENCIOSO.cmd"

if exist "%RAZYNC_TEMP%" rmdir /s /q "%RAZYNC_TEMP%"
mkdir "%RAZYNC_TEMP%"
mkdir "%RAZYNC_APP%" 2>nul
mkdir "%RAZYNC_PY%" 2>nul
break > "%RAZYNC_LOG%"

echo  Etapa 1 de 4 - Baixando componentes...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "try { $ErrorActionPreference='Stop'; $base='https://raw.githubusercontent.com/rodrigofrrsilva1703-a11y/Razync/main/connector_windows/'; foreach($f in @('connector.py','list_certificates.ps1','sign_challenge.ps1')) { Invoke-WebRequest -UseBasicParsing -Headers @{'Cache-Control'='no-cache';'Pragma'='no-cache'} -Uri ($base+$f+'?build=180-direct') -OutFile (Join-Path $env:RAZYNC_TEMP $f) }; exit 0 } catch { Write-Error $_.Exception.Message; exit 1 }" >> "%RAZYNC_LOG%" 2>&1
if errorlevel 1 goto erro

copy /y "%RAZYNC_TEMP%\connector.py" "%RAZYNC_APP%\connector.py" >> "%RAZYNC_LOG%" 2>&1
copy /y "%RAZYNC_TEMP%\list_certificates.ps1" "%RAZYNC_APP%\list_certificates.ps1" >> "%RAZYNC_LOG%" 2>&1
copy /y "%RAZYNC_TEMP%\sign_challenge.ps1" "%RAZYNC_APP%\sign_challenge.ps1" >> "%RAZYNC_LOG%" 2>&1
if not exist "%RAZYNC_SCRIPT%" goto erro

echo  Etapa 2 de 4 - Conferindo o componente interno...
if exist "%RAZYNC_PYTHONW%" goto runtime_ok
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "try { $ErrorActionPreference='Stop'; $z=Join-Path $env:TEMP 'razync-python-3.12.10-180.zip'; Invoke-WebRequest -UseBasicParsing -Uri 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip' -OutFile $z; if((Get-FileHash $z -Algorithm MD5).Hash.ToUpperInvariant() -ne 'FE8EF205F2E9C3BA44D0CF9954E1ABD3'){throw 'Falha na verificacao do Python'}; Expand-Archive $z -DestinationPath $env:RAZYNC_PY -Force; Remove-Item $z -Force; exit 0 } catch { Write-Error $_.Exception.Message; exit 1 }" >> "%RAZYNC_LOG%" 2>&1
if errorlevel 1 goto erro

:runtime_ok
if not exist "%RAZYNC_PYTHONW%" goto erro

echo  Etapa 3 de 4 - Criando inicializacao em segundo plano...
(
echo @echo off
echo start "" /b "%RAZYNC_PYTHONW%" "%RAZYNC_SCRIPT%"
echo exit /b 0
) > "%RAZYNC_LAUNCHER%"
if not exist "%RAZYNC_LAUNCHER%" goto erro

set "RAZYNC_STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
copy /y "%RAZYNC_LAUNCHER%" "%RAZYNC_STARTUP%\Razync Connector.cmd" >> "%RAZYNC_LOG%" 2>&1
del /q "%RAZYNC_STARTUP%\Razync Connector.vbs" 2>nul
del /q "%RAZYNC_STARTUP%\Razync Connector.lnk" 2>nul

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -and $_.CommandLine -like '*Razync*Connector*connector.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >> "%RAZYNC_LOG%" 2>&1
call "%RAZYNC_LAUNCHER%"
timeout /t 3 /nobreak >nul

echo  Etapa 4 de 4 - Testando o conector...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "try { $r=Invoke-RestMethod -UseBasicParsing -Uri 'http://127.0.0.1:17891/v1/health' -TimeoutSec 8; if(-not $r.ok){exit 1}; Write-Output ('Conector ativo - versao '+$r.version); exit 0 } catch { Write-Error $_.Exception.Message; exit 1 }" >> "%RAZYNC_LOG%" 2>&1
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
echo.
type "%RAZYNC_LOG%"
echo.
echo  Envie uma foto desta tela.
pause
exit /b 1
