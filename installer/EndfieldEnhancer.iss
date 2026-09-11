#define AppVersion "0.3.1"
[Setup]
AppId={{2F62B8B6-FA09-4D41-9871-3F5A92171C32}
AppName=Arknights Endfield FPS Unlocker Enhanced
AppVersion={#AppVersion}
AppPublisher=VagueDustin Enterprises
AppPublisherURL=https://github.com/VagueDustin/arknights-endfield-fps-unlocker-enhanced
DefaultDirName={localappdata}\Programs\EndfieldEnhancer
DefaultGroupName=Endfield Enhancer
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\build\installer
OutputBaseFilename=Endfield-FPS-Unlocker-Enhanced-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\EndfieldEnhancer.exe
LicenseFile=..\LICENSE
CloseApplications=yes
RestartApplications=no
[Files]
Source: "..\build\package\EndfieldEnhancer.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\build\package\EndfieldManager.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\build\package\*.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\build\package\package.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\build\package\licenses\*"; DestDir: "{app}\licenses"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\assets\fonts\*-OFL.txt"; DestDir: "{app}\licenses"; Flags: ignoreversion
[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; Flags: unchecked
[Icons]
Name: "{group}\Endfield Enhancer"; Filename: "{app}\EndfieldEnhancer.exe"
Name: "{autodesktop}\Endfield Enhancer"; Filename: "{app}\EndfieldEnhancer.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\EndfieldEnhancer.exe"; Description: "Open Endfield Enhancer"; Flags: nowait postinstall skipifsilent
[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var ResultCode: Integer;
begin
  if CurUninstallStep <> usUninstall then Exit;
  if not Exec(ExpandConstant('{app}\EndfieldManager.exe'), 'restore-recorded', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    RaiseException('Could not start game restoration. Open Endfield Enhancer and restore the game files before uninstalling.')
  else if ResultCode <> 0 then
    RaiseException('Game restoration stopped. Close Endfield, then use Recovery & logs in Endfield Enhancer to restore the game files. The app has not been removed.');
end;
