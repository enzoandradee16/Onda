#ifndef PackageRoot
  #define PackageRoot AddBackslash(SourcePath) + "..\Portatil"
#endif
#ifndef InstallerOutput
  #define InstallerOutput AddBackslash(SourcePath) + "..\Instalador"
#endif
[Setup]
AppId={{C522DFD9-6BF4-4FE0-9CE4-5D3C5C88E470}
AppName=Onda
AppMutex=Local\Onda.Desktop.C522DFD9-6BF4-4FE0-9CE4-5D3C5C88E470.Mutex
UninstallDisplayName=Onda 1.2.0-rc.1
AppVersion=1.2.0-rc.1
VersionInfoVersion=1.2.0.0
AppPublisher=Onda
DefaultDirName={localappdata}\Programs\Onda
DefaultGroupName=Onda
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#InstallerOutput}
OutputBaseFilename=Onda-1.2.0-rc.1-Setup-Windows-x64
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
Source: "{#PackageRoot}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "Onda-Portable*.zip,__pycache__\*,*.pyc,_runtime\ffmpeg\*"


#ifdef ToolsRoot
Source: "{#ToolsRoot}\ffmpeg.exe"; DestDir: "{app}\_runtime\ffmpeg"; Flags: ignoreversion
Source: "{#ToolsRoot}\ffprobe.exe"; DestDir: "{app}\_runtime\ffmpeg"; Flags: ignoreversion
Source: "{#ToolsRoot}\ffplay.exe"; DestDir: "{app}\_runtime\ffmpeg"; Flags: ignoreversion
Source: "{#ToolsRoot}\LICENSE.txt"; DestDir: "{app}\_runtime\ffmpeg"; Flags: ignoreversion
Source: "{#ToolsRoot}\README.txt"; DestDir: "{app}\_runtime\ffmpeg"; Flags: ignoreversion
#endif

[InstallDelete]
; Remove only the legacy bundled tools during upgrade; user downloads are untouched.
Type: files; Name: "{app}\_runtime\ffmpeg\ffmpeg.exe"
Type: files; Name: "{app}\_runtime\ffmpeg\ffprobe.exe"
Type: files; Name: "{app}\_runtime\ffmpeg\ffplay.exe"

[Icons]
Name: "{group}\Onda"; Filename: "{app}\Onda.exe"; WorkingDir: "{app}"
Name: "{group}\Desinstalar Onda"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Onda"; Filename: "{app}\Onda.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\Onda.exe"; Description: "Abrir Onda"; Flags: nowait postinstall skipifsilent

[Code]
var
  DeleteUserData: Boolean;
  DeleteDownloadedTools: Boolean;

function AskDeleteUserData: Integer;
begin
  { Silent removal keeps personal data; no command-line flag deletes it. }
  if UninstallSilent then
    Result := IDNO
  else
    Result := MsgBox(
      'Deseja apagar também os dados pessoais do ONDA?' + #13#10#13#10 +
      'Isso remove configurações, fila, histórico, contas salvas e o registro da primeira abertura.' + #13#10 +
      'Esses dados são compartilhados com a versão portátil neste PC.' + #13#10#13#10 +
      'Sim: apagar os dados.' + #13#10 +
      'Não: manter os dados para uma próxima instalação.' + #13#10 +
      'Cancelar: cancelar a desinstalação.' + #13#10#13#10 +
      'As músicas, os vídeos, as imagens e os arquivos de cookies não serão apagados.',
      mbConfirmation, MB_YESNOCANCEL or MB_DEFBUTTON2);
end;

function AskDeleteDownloadedTools: Integer;
begin
  if UninstallSilent then
    Result := IDNO
  else
    Result := MsgBox(
      'Deseja remover também as ferramentas baixadas pelo ONDA, como o FFmpeg?' + #13#10#13#10 +
      'Essa escolha é independente das configurações e remove o cache de ferramentas do ONDA.' + #13#10 +
      'O cache é compartilhado com a versão portátil. Será necessário baixar as ferramentas novamente no próximo uso.' + #13#10#13#10 +
      'Sim: remover as ferramentas baixadas.' + #13#10 +
      'Não: manter para uma próxima utilização.' + #13#10 +
      'Cancelar: cancelar a desinstalação.' + #13#10#13#10 +
      'Ferramentas instaladas por você em outras pastas e seus arquivos de mídia serão preservados.' + #13#10 +
      'Os componentes incluídos na instalação são removidos junto com o programa.',
      mbConfirmation, MB_YESNOCANCEL or MB_DEFBUTTON2);
end;

function InitializeUninstall: Boolean;
var
  Choice: Integer;
begin
  Choice := AskDeleteUserData;
  DeleteUserData := Choice = IDYES;
  Result := Choice <> IDCANCEL;
  if not Result then Exit;
  Choice := AskDeleteDownloadedTools;
  DeleteDownloadedTools := Choice = IDYES;
  Result := Choice <> IDCANCEL;
end;

function PlainDirectory(Path: String): Boolean;
var
  Rec: TFindRec;
begin
  Result := False;
  if FindFirst(Path, Rec) then
  begin
    Result := ((Rec.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0) and
      ((Rec.Attributes and FILE_ATTRIBUTE_REPARSE_POINT) = 0);
    FindClose(Rec);
  end;
end;

function VersionDirectory(Name: String): Boolean;
var
  I: Integer;
begin
  Result := False;
  if (Name = '') or (Name = '.') or (Name = '..') then Exit;
  for I := 1 to Length(Name) do
    if Pos(Name[I], '0123456789.') = 0 then Exit;
  Result := True;
end;

procedure RemoveDownloadedTools;
var
  DataDir, ToolsDir, CacheDir, VersionDir, FilePath, Failures: String;
  Rec: TFindRec;
  Names: TArrayOfString;
  I: Integer;
begin
  { Only registered cache files, never recursive deletion or custom tool paths. }
  DataDir := ExpandConstant('{localappdata}\Onda');
  ToolsDir := AddBackslash(DataDir) + 'tools';
  CacheDir := AddBackslash(ToolsDir) + 'ffmpeg';
  if not PlainDirectory(DataDir) then Exit;
  if not PlainDirectory(ToolsDir) then Exit;
  if not PlainDirectory(CacheDir) then Exit;
  Names := ['ffmpeg.exe', 'ffprobe.exe', 'ffplay.exe', 'LICENSE.txt', 'README.txt', 'verified.json'];
  Failures := '';
  if FindFirst(AddBackslash(CacheDir) + '*', Rec) then
  begin
    try
      repeat
        VersionDir := AddBackslash(CacheDir) + Rec.Name;
        if VersionDirectory(Rec.Name) and PlainDirectory(VersionDir) then
        begin
          for I := 0 to GetArrayLength(Names) - 1 do
          begin
            FilePath := AddBackslash(VersionDir) + Names[I];
            if FileExists(FilePath) then
              if not DeleteFile(FilePath) then
                Failures := Failures + #13#10 + FilePath;
          end;
          RemoveDir(VersionDir);
        end;
      until not FindNext(Rec);
    finally
      FindClose(Rec);
    end;
  end;
  RemoveDir(CacheDir);
  RemoveDir(ToolsDir);
  RemoveDir(DataDir);
  if Failures <> '' then
  begin
    Log('Não foi possível remover algumas ferramentas:' + Failures);
    if not UninstallSilent then
      MsgBox('Algumas ferramentas não puderam ser removidas. Feche o ONDA e tente novamente:' + #13#10 +
        Failures, mbError, MB_OK);
  end;
end;

procedure RemoveUserData;
var
  DataDir, FilePath, Failures: String;
  Names: TArrayOfString;
  I: Integer;
begin
  { An explicit allowlist protects downloads and unrelated files in this folder. }
  DataDir := ExpandConstant('{localappdata}\Onda');
  Names := ['settings.json', 'library.sqlite3', 'library.sqlite3-wal',
    'library.sqlite3-shm', 'library.sqlite3-journal', 'spotify.dpapi',
    'spotify-account.dpapi', 'welcome-seen.json', 'startup-error.log'];
  Failures := '';
  for I := 0 to GetArrayLength(Names) - 1 do
  begin
    FilePath := AddBackslash(DataDir) + Names[I];
    if FileExists(FilePath) then
      if not DeleteFile(FilePath) then
        Failures := Failures + #13#10 + Names[I];
  end;
  { Non-recursive: a folder containing user files is deliberately retained. }
  RemoveDir(DataDir);
  if Failures <> '' then
  begin
    Log('Não foi possível remover alguns dados pessoais:' + Failures);
    if not UninstallSilent then
      MsgBox('O programa foi desinstalado, mas alguns dados não puderam ser removidos.' + #13#10 +
        'Feche o ONDA e confira a pasta %LOCALAPPDATA%\Onda:' + Failures,
        mbError, MB_OK);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if DeleteUserData then RemoveUserData;
    if DeleteDownloadedTools then RemoveDownloadedTools;
  end;
end;
