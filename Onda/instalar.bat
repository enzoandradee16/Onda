@echo off
setlocal
cd /d "%~dp0"
echo Instalando Onda em um ambiente Python local...
py -3 -m venv .venv
if errorlevel 1 goto erro
".venv\Scripts\python.exe" -m pip install --upgrade -r requirements.txt
if errorlevel 1 goto erro
echo.
echo Pronto. Instale FFmpeg e Deno conforme o README, depois abra iniciar.bat.
pause
exit /b 0
:erro
echo Falha na instalacao. Confira a mensagem acima e o README.
pause
exit /b 1
