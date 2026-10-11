@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0Onda-Setup.exe" (
  echo Onda-Setup.exe nao encontrado. Baixe o instalador completo do Onda.
  pause
  exit /b 1
)
start "" /wait "%~dp0Onda-Setup.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- /TASKS="desktopicon" /LOG="%TEMP%\Onda-instalacao.log" %*
set "ONDA_INSTALL_RESULT=%errorlevel%"
if not "%ONDA_INSTALL_RESULT%"=="0" echo A instalacao nao foi concluida. Consulte "%TEMP%\Onda-instalacao.log".
exit /b %ONDA_INSTALL_RESULT%
