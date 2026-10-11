@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0Onda.exe" (
  echo Onda.exe nao encontrado. Extraia o pacote completo antes de abrir.
  pause
  exit /b 1
)
start "" "%~dp0Onda.exe"
