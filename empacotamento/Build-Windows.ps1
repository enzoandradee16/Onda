param(
    [Parameter(Mandatory=$true)][string]$PythonHome,
    [Parameter(Mandatory=$true)][string]$FFmpegHome,
    [Parameter(Mandatory=$true)][string]$NodeExe,
    [Parameter(Mandatory=$true)][string]$InnoCompiler,
    [string]$ProjectRoot = (Split-Path $PSScriptRoot -Parent)
)
$ErrorActionPreference = 'Stop'
$project = [System.IO.Path]::GetFullPath($ProjectRoot)
$distribution = Join-Path $project 'dist\Portatil'
$installer = Join-Path $project 'dist\Instalador'
New-Item -ItemType Directory -Force -Path $installer | Out-Null
& (Join-Path $PythonHome 'python.exe') (Join-Path $PSScriptRoot 'build_package.py') --python-home $PythonHome --ffmpeg-home $FFmpegHome --node $NodeExe --source (Join-Path $project 'Onda') --output $distribution
if ($LASTEXITCODE -ne 0) { throw 'Falha ao montar o pacote.' }
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Leia-me.txt') -Destination $distribution
$nodeVersion = & $NodeExe --version
Invoke-WebRequest -Uri ('https://raw.githubusercontent.com/nodejs/node/' + $nodeVersion.Trim() + '/LICENSE') -OutFile (Join-Path $distribution '_runtime\node\LICENSE.txt')
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319\csc.exe'
& $compiler /nologo /target:winexe /platform:anycpu /reference:System.Windows.Forms.dll ('/win32icon:'+(Join-Path $distribution 'onda.ico')) ('/out:'+(Join-Path $distribution 'Onda.exe')) (Join-Path $PSScriptRoot 'Launcher.cs')
if ($LASTEXITCODE -ne 0) { throw 'Falha ao compilar Onda.exe.' }
& $InnoCompiler ('/DPackageRoot='+$distribution) ('/DInstallerOutput='+$installer) (Join-Path $PSScriptRoot 'Onda.iss')
if ($LASTEXITCODE -ne 0) { throw 'Falha ao compilar o instalador.' }
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Instalação Silenciosa Onda.bat') -Destination $installer -Force
Write-Output ('Pronto: ' + (Join-Path $project 'dist'))

