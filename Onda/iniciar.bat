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
".venv\Scripts\python.exe" -c "import sys, tkinter; sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
if errorlevel 1 (
  echo O ambiente Python esta invalido. Execute instalar.bat para repara-lo.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" app.py
if errorlevel 1 pause
