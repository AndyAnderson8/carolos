; Inno Setup script for the Carol AIO installer. Build with:
;   ISCC.exe /DAppVersion=v1.2.3 installer\carol_aio.iss
; (build.py does this after PyInstaller has produced dist\CarolAIO\.)

#ifndef AppVersion
  #define AppVersion "dev"
#endif

[Setup]
; Never change this GUID: it is how upgrades find the existing install.
AppId={{1E326CCF-AD36-4976-B6BC-4746BF507E81}
AppName=Carol AIO
AppVersion={#AppVersion}
AppPublisher=Carol AIO
; Installs for the current user: no admin prompt, and the folder stays writable for config.yaml.
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\CarolAIO
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=CarolAIO-Setup-{#AppVersion}
SetupIconFile=..\assets\carol_aio.ico
UninstallDisplayIcon={app}\CarolAIO.exe
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
; Windows' Restart Manager can't close a tray app (it has no visible window), so Setup
; stops the app itself (see StopApp below) instead of stopping to ask the person to.
CloseApplications=no

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Shortcuts:"
Name: "startmenuicon"; Description: "Create a &Start menu shortcut"; GroupDescription: "Shortcuts:"

[Files]
; config.yaml is not listed here, so upgrades never touch it.
Source: "..\dist\CarolAIO\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autodesktop}\Carol AIO"; Filename: "{app}\CarolAIO.exe"; Tasks: desktopicon
Name: "{autoprograms}\Carol AIO"; Filename: "{app}\CarolAIO.exe"; Tasks: startmenuicon

[Run]
; A normal install offers a "Launch" checkbox; a silent one (an in-app update) relaunches by itself.
Filename: "{app}\CarolAIO.exe"; Description: "Launch Carol AIO"; Flags: nowait postinstall skipifsilent
Filename: "{app}\CarolAIO.exe"; Flags: nowait; Check: WizardSilent

[Code]
procedure StopApp;
var
  ResultCode: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM CarolAIO.exe', '', SW_HIDE,
    ewWaitUntilTerminated, ResultCode);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  StopApp;  { an upgrade can't replace a running app }
  Result := '';
end;

function InitializeUninstall: Boolean;
begin
  StopApp;
  Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Existing, Target: String;
begin
  { Bring settings along if a config.yaml sits next to the downloaded installer. }
  if CurStep = ssPostInstall then
  begin
    Existing := ExpandConstant('{src}\config.yaml');
    Target := ExpandConstant('{app}\config.yaml');
    if FileExists(Existing) and not FileExists(Target) then
      FileCopy(Existing, Target, True);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Config: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    Config := ExpandConstant('{app}\config.yaml');
    if FileExists(Config) and not UninstallSilent then
      if MsgBox('Also delete your Carol AIO settings?', mbConfirmation, MB_YESNO) = IDYES then
        DeleteFile(Config);
    RemoveDir(ExpandConstant('{app}'));  { only succeeds if nothing else is left in it }
  end;
end;
