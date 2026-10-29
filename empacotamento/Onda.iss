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
UninstallDisplayName=Onda 1.2.4
AppVersion=1.2.4
VersionInfoVersion=1.2.4.0
AppPublisher=Onda
DefaultDirName={localappdata}\Programs\Onda
DefaultGroupName=Onda
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#InstallerOutput}
OutputBaseFilename=Onda-1.2.4-Setup-Windows-x64
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
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
brazilianportuguese.DesktopShortcut=Criar atalho na Área de Trabalho
spanish.DesktopShortcut=Crear acceso directo en el escritorio
english.DesktopShortcut=Create a desktop shortcut
brazilianportuguese.Shortcuts=Atalhos:
spanish.Shortcuts=Accesos directos:
english.Shortcuts=Shortcuts:
brazilianportuguese.UninstallShortcut=Desinstalar Onda
spanish.UninstallShortcut=Desinstalar Onda
english.UninstallShortcut=Uninstall Onda
brazilianportuguese.OpenApp=Abrir Onda
spanish.OpenApp=Abrir Onda
english.OpenApp=Open Onda
brazilianportuguese.DeleteDataPrompt=Deseja apagar também os dados pessoais do ONDA?%n%nIsso remove configurações, fila, histórico, contas salvas e o registro da primeira abertura. Esses dados são compartilhados com a versão portátil neste PC.%n%nSim: apagar os dados.%nNão: manter os dados para uma próxima instalação.%nCancelar: cancelar a desinstalação.%n%nAs músicas, os vídeos, as imagens e os arquivos de cookies não serão apagados.
spanish.DeleteDataPrompt=¿Quieres borrar también los datos personales de ONDA?%n%nEsto elimina la configuración, la cola, el historial, las cuentas guardadas y el registro del primer inicio. Estos datos se comparten con la versión portátil en este PC.%n%nSí: borrar los datos.%nNo: conservar los datos para una próxima instalación.%nCancelar: cancelar la desinstalación.%n%nNo se borrarán la música, los vídeos, las imágenes ni los archivos de cookies.
english.DeleteDataPrompt=Do you also want to delete ONDA's personal data?%n%nThis removes settings, the queue, history, saved accounts and the first-run record. This data is shared with the portable version on this PC.%n%nYes: delete the data.%nNo: keep the data for a future installation.%nCancel: cancel uninstallation.%n%nMusic, videos, images and cookie files will not be deleted.
brazilianportuguese.DeleteToolsPrompt=Deseja remover também as ferramentas baixadas pelo ONDA, como o FFmpeg?%n%nEssa escolha é independente das configurações e remove o cache de ferramentas do ONDA, compartilhado com a versão portátil. Será necessário baixar as ferramentas novamente no próximo uso.%n%nSim: remover as ferramentas baixadas.%nNão: manter para uma próxima utilização.%nCancelar: cancelar a desinstalação.%n%nFerramentas instaladas por você em outras pastas e seus arquivos de mídia serão preservados. Os componentes incluídos na instalação são removidos junto com o programa.
spanish.DeleteToolsPrompt=¿Quieres eliminar también las herramientas descargadas por ONDA, como FFmpeg?%n%nEsta opción es independiente de la configuración y elimina la caché de herramientas de ONDA, compartida con la versión portátil. Tendrás que descargar las herramientas de nuevo en el próximo uso.%n%nSí: eliminar las herramientas descargadas.%nNo: conservarlas para un uso futuro.%nCancelar: cancelar la desinstalación.%n%nSe conservarán las herramientas que instalaste en otras carpetas y tus archivos multimedia. Los componentes incluidos en la instalación se eliminan junto con el programa.
english.DeleteToolsPrompt=Do you also want to remove tools downloaded by ONDA, such as FFmpeg?%n%nThis choice is independent of settings and removes ONDA's tools cache, which is shared with the portable version. Tools will need to be downloaded again on next use.%n%nYes: remove downloaded tools.%nNo: keep them for future use.%nCancel: cancel uninstallation.%n%nTools you installed in other folders and your media files will be preserved. Components included in the installation are removed with the application.
brazilianportuguese.ToolsFailure=Algumas ferramentas não puderam ser removidas. Feche o ONDA e tente novamente:
spanish.ToolsFailure=No se pudieron eliminar algunas herramientas. Cierra ONDA e inténtalo de nuevo:
english.ToolsFailure=Some tools could not be removed. Close ONDA and try again:
brazilianportuguese.DataFailure=O programa foi desinstalado, mas alguns dados não puderam ser removidos.%nFeche o ONDA e confira a pasta %%LOCALAPPDATA%%\Onda:
spanish.DataFailure=El programa se desinstaló, pero no se pudieron eliminar algunos datos.%nCierra ONDA y revisa la carpeta %%LOCALAPPDATA%%\Onda:
english.DataFailure=The application was uninstalled, but some data could not be removed.%nClose ONDA and check the %%LOCALAPPDATA%%\Onda folder:

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopShortcut}"; GroupDescription: "{cm:Shortcuts}"

[Files]
#ifdef UninstallerFrontend
Source: "{#UninstallerFrontend}"; DestDir: "{app}"; DestName: "Desinstalar ONDA.exe"; Flags: ignoreversion
#endif
Source: "{#PackageRoot}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "Onda-Portable*.zip,__pycache__\*,*.pyc,*.obj,*.pdb,*.lib,*.exp,_runtime\ffmpeg\*"


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
#ifdef UninstallerFrontend
Name: "{group}\{cm:UninstallShortcut}"; Filename: "{app}\Desinstalar ONDA.exe"
#else
Name: "{group}\{cm:UninstallShortcut}"; Filename: "{uninstallexe}"
#endif
Name: "{userdesktop}\Onda"; Filename: "{app}\Onda.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\Onda.exe"; Description: "{cm:OpenApp}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{app}\uninstall-engine.sha256"

[Code]
var
  DeleteUserData: Boolean;
  DeleteDownloadedTools: Boolean;
  CleanupFailed: Boolean;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Backend, Stamp, Key: String;
begin
  if CurStep = ssPostInstall then
  begin
    if not FileExists(ExpandConstant('{app}\Desinstalar ONDA.exe')) then Exit;
    Backend := ExpandConstant('{uninstallexe}');
    Stamp := ExtractFileName(Backend) + #13#10 + GetSHA256OfFile(Backend) + #13#10 +
      GetSHA256OfFile(ChangeFileExt(Backend, '.dat'));
    SaveStringToFile(ExpandConstant('{app}\uninstall-engine.sha256'), Stamp, False);
    Key := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{C522DFD9-6BF4-4FE0-9CE4-5D3C5C88E470}_is1';
    RegWriteStringValue(HKCU, Key, 'UninstallString', '"' + ExpandConstant('{app}\Desinstalar ONDA.exe') + '"');
    RegWriteStringValue(HKCU, Key, 'QuietUninstallString', '"' + Backend + '" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART');
    RegWriteStringValue(HKCU, Key, 'OndaUninstallLanguage', ActiveLanguage);
  end;
end;

procedure CurInstallProgressChanged(CurProgress, MaxProgress: Integer);
var
  ProgressFile: String;
begin
  { Optional local progress channel for the ONDA installer frontend. }
  ProgressFile := ExpandConstant('{param:ONDAPROGRESS|}');
  if ProgressFile <> '' then
    SaveStringToFile(ProgressFile, IntToStr(CurProgress) + '/' + IntToStr(MaxProgress), False);
end;

function AskDeleteUserData: Integer;
begin
  { Only the custom frontend forwards the user's explicit cleanup choices. }
  if UninstallSilent then
  begin
    Result := IDNO;
    if (ExpandConstant('{param:ONDACUSTOM|0}') = '1') and
       (ExpandConstant('{param:ONDADATA|0}') = '1') then Result := IDYES;
  end
  else
    Result := MsgBox(
      CustomMessage('DeleteDataPrompt'),
      mbConfirmation, MB_YESNOCANCEL or MB_DEFBUTTON2);
end;

function AskDeleteDownloadedTools: Integer;
begin
  if UninstallSilent then
  begin
    Result := IDNO;
    if (ExpandConstant('{param:ONDACUSTOM|0}') = '1') and
       (ExpandConstant('{param:ONDATOOLS|0}') = '1') then Result := IDYES;
  end
  else
    Result := MsgBox(
      CustomMessage('DeleteToolsPrompt'),
      mbConfirmation, MB_YESNOCANCEL or MB_DEFBUTTON2);
end;

function InitializeUninstall: Boolean;
var
  Choice, Code: Integer;
begin
  if (not UninstallSilent) and FileExists(ExpandConstant('{app}\Desinstalar ONDA.exe')) then
  begin
    Exec(ExpandConstant('{app}\Desinstalar ONDA.exe'), '', ExpandConstant('{app}'), SW_SHOWNORMAL, ewNoWait, Code);
    Result := False;
    Exit;
  end;
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
  if not PlainDirectory(DataDir) then
  begin
    if DirExists(DataDir) then CleanupFailed := True;
    Exit;
  end;
  if not PlainDirectory(ToolsDir) then
  begin
    if DirExists(ToolsDir) then CleanupFailed := True;
    Exit;
  end;
  if not PlainDirectory(CacheDir) then
  begin
    if DirExists(CacheDir) then CleanupFailed := True;
    Exit;
  end;
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
    CleanupFailed := True;
    Log('Não foi possível remover algumas ferramentas:' + Failures);
    if not UninstallSilent then
      MsgBox(CustomMessage('ToolsFailure') + #13#10 +
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
  if not PlainDirectory(DataDir) then
  begin
    if DirExists(DataDir) then CleanupFailed := True;
    Exit;
  end;
  Names := ['settings.json', 'library.sqlite3', 'library.sqlite3-wal',
    'library.sqlite3-shm', 'library.sqlite3-journal', 'spotify.dpapi',
    'spotify-account.dpapi', 'welcome-seen.json', 'startup-error.log',
    'remember.json', 'language.json', 'display.json', 'window.json',
    'playback-session.json', 'playback-session.tmp'];
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
    CleanupFailed := True;
    Log('Não foi possível remover alguns dados pessoais:' + Failures);
    if not UninstallSilent then
      MsgBox(CustomMessage('DataFailure') + Failures,
        mbError, MB_OK);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ProgressFile: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if DeleteUserData then RemoveUserData;
    if DeleteDownloadedTools then RemoveDownloadedTools;
  end;
  if CurUninstallStep = usDone then
  begin
    ProgressFile := ExpandConstant('{param:ONDAPROGRESS|}');
    if ProgressFile <> '' then
      if CleanupFailed then SaveStringToFile(ProgressFile, 'cleanup_failed', False)
      else SaveStringToFile(ProgressFile, 'complete', False);
  end;
end;
