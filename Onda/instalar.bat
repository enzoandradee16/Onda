@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Instale Python 3.11 ou superior com Tcl/Tk e o Python Launcher.
  pause
  exit /b 1
)
py -3 -c "import sys, tkinter; sys.exit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 (
  echo O ONDA precisa de Python 3.11 ou superior com Tcl/Tk.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" goto :recriar
".venv\Scripts\python.exe" -c "import sys, tkinter; sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
if errorlevel 1 goto :recriar
goto :dependencias

:recriar
if not exist ".venv" goto :criar
echo O ambiente Python anterior esta invalido. Ele sera preservado como backup.
:nome_backup
set "VENV_BACKUP=.venv-backup-%RANDOM%-%RANDOM%"
if exist "%VENV_BACKUP%" goto :nome_backup
ren ".venv" "%VENV_BACKUP%"
if errorlevel 1 goto :falha
echo Backup salvo em %VENV_BACKUP%.
:criar
py -3 -m venv .venv
if errorlevel 1 goto :falha
:dependencias
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :falha
echo Pronto. Abra iniciar.bat. Configure FFmpeg no aplicativo se necessario.
pause
exit /b 0
:falha
echo Nao foi possivel preparar o ambiente. Confira a mensagem acima.
pause
exit /b 1
