; Inno Setup 6 script -> dist\LANShareHub-Windows-Setup.exe
; Build: ISCC /DAppVersion=1.2.3 build_tools\installer.iss
#ifndef AppVersion
  #define AppVersion "1.0.1"
#endif
#define AppName "LAN Share Hub"
#define AppExe "LANShareHub.exe"
#define AppURL "https://github.com/madara1150/lan-share-hub"

[Setup]
AppId={{3F6B2C1E-8D47-4A6B-9C0E-5B1A7D2E9F41}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Tanathip
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
DefaultDirName={autopf}\LAN Share Hub
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=LANShareHub-Windows-Setup
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
VersionInfoVersion={#AppVersion}
VersionInfoCompany=Tanathip
VersionInfoCopyright=Copyright (c) 2026 Tanathip

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "thai"; MessagesFile: "compiler:Languages\Thai.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\LANShareHub\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
