#ifndef PackageRoot
  #define PackageRoot AddBackslash(SourcePath) + "..\Portatil"
#endif
#ifndef InstallerOutput
  #define InstallerOutput AddBackslash(SourcePath) + "..\Instalador"
#endif
[Setup]
AppId={{C522DFD9-6BF4-4FE0-9CE4-5D3C5C88E470}
AppName=Onda
UninstallDisplayName=Onda 1.0
AppVersion=1.0.0
AppPublisher=Onda
DefaultDirName={localappdata}\Programs\Onda
DefaultGroupName=Onda
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#InstallerOutput}
OutputBaseFilename=Onda-Setup
SetupIconFile={#PackageRoot}\onda.ico
UninstallDisplayIcon={app}\Onda.exe
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"; GroupDescription: "Atalhos:"

[Files]
Source: "{#PackageRoot}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__\*,*.pyc"

[Icons]
Name: "{group}\Onda"; Filename: "{app}\Onda.exe"; WorkingDir: "{app}"
Name: "{group}\Desinstalar Onda"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Onda"; Filename: "{app}\Onda.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\Onda.exe"; Description: "Abrir Onda"; Flags: nowait postinstall skipifsilent

