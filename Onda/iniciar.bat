@echo off
setlocal
if exist "%~dp0..\Onda.exe" (
  start "" "%~dp0..\Onda.exe"
  exit /b 0
)
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Para usar sem Python, abra Onda.exe no pacote portatil completo.
  echo Para desenvolver, prepare o ambiente Python conforme o README.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" app.py
if errorlevel 1 pause
