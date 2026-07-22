; ============================================================================
; parrot_installer.iss
; Script de Inno Setup para empaquetar el launcher de Parrot (generado por
; PyInstaller, dist\Parrot.exe) junto al código fuente que necesita para
; funcionar (main.py, tray_icon.py, hosts_setup.py, requirements.txt,
; frontend/, services/, static/) en un instalador clásico de Windows.
;
; A diferencia de Cicada (PyInstaller autocontenido), Parrot usa un "Smart
; Launcher" hueco: el código fuente real viaja SUELTO junto al ejecutable, no
; empaquetado dentro de él (ver SMART_LAUNCHER.txt). Por eso este script copia
; bastante más que el .exe, pero el resto de la lógica es la misma que
; cicada_installer.iss.
;
; Compilar con:
;   iscc parrot_installer.iss
;
; Requiere que PyInstaller ya haya generado: dist\Parrot.exe
; ============================================================================

#define MyAppName "Parrot"
#define MyAppVersion "0.1.3"
#define MyAppPublisher "JJaroll"
#define MyAppURL "https://github.com/JJaroll/Parrot"
#define MyAppExeName "Parrot.exe"
#define MyAppIcon "static\logos\parrot_yellow.ico"

[Setup]
AppId={{A4D1F2B3-7C5E-4A9D-8B6F-1E2C3D4E5F6A}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; El instalador final que consume el workflow de GitHub Actions
OutputDir=dist_installer
OutputBaseFilename=Parrot_Setup_Windows
SetupIconFile={#MyAppIcon}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Ejecutable "onefile" producido por PyInstaller (launcher.py)
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; Código fuente que el launcher necesita a su lado para poder ejecutar main.py
; (ver get_source_dir() en launcher.py: en Windows asume que está junto al .exe)
Source: "main.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "tray_icon.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "hosts_setup.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "TERMS.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "frontend\*"; DestDir: "{app}\frontend"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "services\*"; DestDir: "{app}\services"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "static\*"; DestDir: "{app}\static"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Menú Inicio
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppIcon}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
; Escritorio (opcional: el usuario elige el Task "desktopicon" durante la instalación)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppIcon}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
