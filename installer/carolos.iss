; Inno Setup script for the CaroLoS installer. Build with:
;   ISCC.exe /DAppVersion=v1.2.3 installer\carolos.iss
; (build.py does this after PyInstaller has produced dist\CaroLoS\.)

#ifndef AppVersion
  #define AppVersion "dev"
#endif

[Setup]
; Never change this GUID: it is how upgrades find the existing install.
AppId={{1E326CCF-AD36-4976-B6BC-4746BF507E81}
AppName=CaroLoS
AppVersion={#AppVersion}
AppPublisher=CaroLoS
; Installs for the current user: no admin prompt, and the folder stays writable for config.yaml.
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\CaroLoS
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=CaroLoS-Setup-{#AppVersion}
SetupIconFile=..\assets\carolos.ico
UninstallDisplayIcon={app}\CaroLoS.exe
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
Source: "..\dist\CaroLoS\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[InstallDelete]
; Clean up after the old name (Carol AIO) when upgrading from it.
Type: files; Name: "{app}\CarolAIO.exe"
Type: files; Name: "{autodesktop}\Carol AIO.lnk"
Type: files; Name: "{autoprograms}\Carol AIO.lnk"

[Icons]
Name: "{autodesktop}\CaroLoS"; Filename: "{app}\CaroLoS.exe"; Tasks: desktopicon
Name: "{autoprograms}\CaroLoS"; Filename: "{app}\CaroLoS.exe"; Tasks: startmenuicon

[Run]
; A normal install offers a "Launch" checkbox; a silent one (an in-app update) relaunches by itself.
Filename: "{app}\CaroLoS.exe"; Description: "Launch CaroLoS"; Flags: nowait postinstall skipifsilent
Filename: "{app}\CaroLoS.exe"; Flags: nowait; Check: WizardSilent

[Code]
procedure StopApp;
var
  ResultCode: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM CaroLoS.exe', '', SW_HIDE,
    ewWaitUntilTerminated, ResultCode);
  Exec(ExpandConstant('{sys}	askkill.exe'), '/F /IM CarolAIO.exe', '', SW_HIDE,
    ewWaitUntilTerminated, ResultCode);  { the old name }
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
      if MsgBox('Also delete your CaroLoS settings?', mbConfirmation, MB_YESNO) = IDYES then
        DeleteFile(Config);
    RemoveDir(ExpandConstant('{app}'));  { only succeeds if nothing else is left in it }
  end;
end;
