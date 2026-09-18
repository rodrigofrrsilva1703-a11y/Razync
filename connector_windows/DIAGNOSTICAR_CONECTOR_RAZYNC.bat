@echo off
setlocal
title Diagnostico do Conector Razync
color 0B
echo.
echo  ==========================================
echo       DIAGNOSTICO DO CONECTOR RAZYNC
echo  ==========================================
echo.
set "RAZYNC_APP=%LOCALAPPDATA%\Razync\Connector\app"
set "RAZYNC_PYTHON=%LOCALAPPDATA%\Razync\Connector\python\python.exe"
set "RAZYNC_SCRIPT=%LOCALAPPDATA%\Razync\Connector\app\connector.py"

echo  Verificando os arquivos instalados...
if not exist "%RAZYNC_PYTHON%" (
  color 0C
  echo.
  echo  ERRO: o Python interno nao foi encontrado:
  echo  %RAZYNC_PYTHON%
  echo.
  echo  Envie uma foto desta tela.
  pause
  exit /b 1
)
if not exist "%RAZYNC_SCRIPT%" (
  color 0C
  echo.
  echo  ERRO: o arquivo do conector nao foi encontrado:
  echo  %RAZYNC_SCRIPT%
  echo.
  echo  Envie uma foto desta tela.
  pause
  exit /b 1
)

echo  Arquivos encontrados.
echo.
echo  Iniciando o conector no modo de diagnostico...
echo  Esta janela deve permanecer aberta durante o teste.
echo.
"%RAZYNC_PYTHON%" "%RAZYNC_SCRIPT%"
set "RAZYNC_EXIT=%ERRORLEVEL%"
echo.
color 0C
echo  ==========================================
echo  O conector foi encerrado. Codigo: %RAZYNC_EXIT%
echo  Envie uma foto completa desta tela.
echo  ==========================================
echo.
pause
