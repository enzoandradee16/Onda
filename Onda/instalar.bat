@echo off
setlocal
if not exist "%~dp0..\Instalar Onda.bat" (
  echo Baixe Onda-Setup.exe e execute o instalador na pasta principal.
  pause
  exit /b 1
)
call "%~dp0..\Instalar Onda.bat" %*
exit /b %errorlevel%
