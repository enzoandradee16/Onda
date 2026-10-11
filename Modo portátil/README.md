# Gerar os executáveis do Onda

Onda.exe é um inicializador Windows compilado em C#. Ele abre o Python privado
do pacote, sem instalar ou usar o Python do computador. Downloads e exportações
continuam usando processos separados desse runtime. Isso também permite manter
o atualizador de yt-dlp pela interface.

Onda-Setup.exe é compilado pelo Inno Setup. Instala por usuário em
`%LOCALAPPDATA%\Programs\Onda`, cria atalhos e registra um desinstalador.
Dados pessoais e downloads permanecem separados da instalação.

Para gerar uma nova versão, tenha CPython 3.11 x64 com Tkinter, FFmpeg com
ffplay/ffprobe, Node e Inno Setup 6.7 ou superior disponíveis na máquina de build.
Execute no PowerShell a partir da raiz do projeto:

```powershell
.\empacotamento\Build-Windows.ps1 -PythonHome 'C:\Python311' -FFmpegHome 'C:\ferramentas\ffmpeg' -NodeExe 'C:\ferramentas\node.exe' -InnoCompiler 'C:\ferramentas\Inno Setup\ISCC.exe'
```

O resultado fica em `dist\Onda-portatil` e `dist\Onda-Setup.exe`. Não envie
`_runtime`, arquivos EXE nem pastas de build em commits de código; distribua
os binários como anexos de uma versão no GitHub Releases.

O runtime é uma cópia independente: o script não modifica o Python usado
para o build. O programa funciona em Windows 10/11 x64. O instalador não apaga
músicas, configurações, credenciais ou histórico ao desinstalar.

Referências: https://docs.python.org/3.11/using/windows.html e
https://jrsoftware.org/ishelp/.
