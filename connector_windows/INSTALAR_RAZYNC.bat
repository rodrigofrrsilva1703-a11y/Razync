@echo off
setlocal
title Instalador do Conector Razync
color 0B
echo.
echo  ==========================================
echo       CONECTOR RAZYNC PARA WINDOWS
echo  ==========================================
echo.
set "RAZYNC_SOURCE=%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%RAZYNC_SOURCE%install.ps1"
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
echo.
pause
