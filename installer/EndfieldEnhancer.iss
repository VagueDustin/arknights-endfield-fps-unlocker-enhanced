#include "..\build\brand\product.iss"
#ifndef PackageDir
  #define PackageDir "..\build\package"
#endif
[Setup]
#ifdef ValidationBuild
AppId=FateEngine-NativeNR-IsolatedValidation
#else
AppId={{2F62B8B6-FA09-4D41-9871-3F5A92171C32}
#endif
AppName={#ProductName} - {#ProductSubtitle}
AppVersion={#ProductVersion}
AppPublisher=VagueDustin Enterprises
AppPublisherURL=https://github.com/VagueDustin/arknights-endfield-fps-unlocker-enhanced
DefaultDirName={autopf}\VagueDustin Enterprises\{#ProductName}
DefaultGroupName=VagueDustin Enterprises
UsePreviousAppDir=no
UsePreviousGroup=no
UsePreviousPrivileges=no
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\build\installer
#ifdef BundledReShade
#ifdef ValidationBuild
OutputBaseFilename=Fate-Engine-ReShade-Validation
#else
OutputBaseFilename=Fate-Engine-Arknights-Endfield-Setup-{#ProductVersion}
#endif
#else
#ifdef PrivateNativeNR
#ifdef ValidationBuild
OutputBaseFilename=Fate-Engine-Native-NR-Validation
#else
OutputBaseFilename=Fate-Engine-Native-NR-Private-Setup-{#ProductVersion}
#endif
#else
OutputBaseFilename=Fate-Engine-Arknights-Endfield-Setup-{#ProductVersion}
#endif
#endif
Compression=lzma2
SolidCompression=yes
WizardStyle=modern dark
DisableWelcomePage=no
WizardBackColor={#BrandSurface}
WizardImageFile=..\assets\identity\installer-panel.bmp
WizardSmallImageFile=..\assets\identity\installer-mark.bmp
WizardImageStretch=yes
SetupIconFile=..\assets\identity\fate-engine.ico
UninstallDisplayIcon={app}\{#ProductExe}
LicenseFile=..\LICENSE
CloseApplications=yes
RestartApplications=no
[Files]
#ifdef BundledReShade
Source: "{#PackageDir}\prerequisites\*"; DestDir: "{app}\prerequisites"; Flags: ignoreversion
Source: "{#PackageDir}\neural-components\*"; DestDir: "{app}\neural-components"; Flags: ignoreversion
Source: "{#PackageDir}\reshade-payload.json"; DestDir: "{app}"; Flags: ignoreversion
#endif
Source: "..\docs\DLSS-RESHade-SETUP.md"; DestDir: "{app}"; Flags: ignoreversion
#ifdef PrivateNativeNR
Source: "{#PackageDir}\native-nr\*"; DestDir: "{app}\native-nr"; Flags: ignoreversion recursesubdirs createallsubdirs
#endif
Source: "{#PackageDir}\{#ProductExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#PackageDir}\EndfieldManager.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#PackageDir}\*.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#PackageDir}\package.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#PackageDir}\licenses\*"; DestDir: "{app}\licenses"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\assets\fonts\*-OFL.txt"; DestDir: "{app}\licenses"; Flags: ignoreversion
Source: "..\assets\identity\fate-engine.ico"; DestDir: "{app}"; Flags: ignoreversion
[InstallDelete]
#ifndef ValidationBuild
Type: files; Name: "{autoprograms}\Endfield Enhancer\Endfield Enhancer.lnk"
Type: files; Name: "{autodesktop}\Endfield Enhancer.lnk"
#endif
[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; Flags: unchecked
[Icons]
#ifndef ValidationBuild
Name: "{group}\{#ProductName} - {#ProductSubtitle}"; Filename: "{app}\{#ProductExe}"; IconFilename: "{app}\fate-engine.ico"; AppUserModelID: "{#ProductAppId}"; Comment: "Arknights Endfield FPS unlocker and live graphics controls by VagueDustin Enterprises"
Name: "{autodesktop}\{#ProductName} - {#ProductSubtitle}"; Filename: "{app}\{#ProductExe}"; IconFilename: "{app}\fate-engine.ico"; AppUserModelID: "{#ProductAppId}"; Tasks: desktopicon
#endif
[Run]
Filename: "{app}\{#ProductExe}"; Description: "Open {#ProductName}"; Flags: nowait postinstall skipifsilent runasoriginaluser
[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var ResultCode: Integer;
begin
  if CurUninstallStep <> usUninstall then Exit;
  if not Exec(ExpandConstant('{app}\EndfieldManager.exe'), 'restore-recorded', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    RaiseException('Could not start game restoration. Open {#ProductName} and restore the game files before uninstalling.')
  else if ResultCode <> 0 then
    RaiseException('Game restoration stopped. Close Endfield, then use Recovery & logs in {#ProductName} to restore the game files. The app has not been removed.');
end;
