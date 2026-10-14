#define MyAppName "Vinogradov's Digitizer"
#define MyAppVersion "2.3.0"
#define MyAppPublisher "Vinogradov"
#define MyAppExeName "VinogradovsDigitizer.exe"
#define MyAppFolderName "VinogradovsDigitizer"


[Setup]
AppId={{8C796F59-2E77-4D30-BA8A-A0F22D742CB9}

AppName={#MyAppName}
AppVerName={#MyAppName} {#MyAppVersion}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

DefaultDirName={localappdata}\Programs\{#MyAppFolderName}
DefaultGroupName={#MyAppName}

DisableProgramGroupPage=yes

OutputDir=..\release
OutputBaseFilename=Vinogradovs_Digitizer_Setup_{#MyAppVersion}

SetupIconFile=..\assets\VinogradovsDigitizer.ico

UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}

Compression=lzma2
SolidCompression=yes

WizardStyle=modern

; Установка только для текущего пользователя.
; Права администратора не требуются.
PrivilegesRequired=lowest

; Сборка приложения предназначена для современных 64-битных Windows.
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

MinVersion=10.0

CloseApplications=yes
RestartApplications=no

SetupLogging=yes

VersionInfoVersion=2.3.0.0
VersionInfoCompany=Vinogradov
VersionInfoDescription=Vinogradov's Digitizer Installer
VersionInfoProductName=Vinogradov's Digitizer
VersionInfoProductVersion=2.3.0


[Languages]

Name: "russian"; \
    MessagesFile: "compiler:Languages\Russian.isl"

Name: "english"; \
    MessagesFile: "compiler:Default.isl"


[CustomMessages]

russian.CreateDesktopShortcut=Создать ярлык на рабочем столе
english.CreateDesktopShortcut=Create a desktop shortcut

russian.AdditionalIcons=Дополнительные значки:
english.AdditionalIcons=Additional icons:

russian.LaunchApplication=Запустить %1
english.LaunchApplication=Launch %1


[Tasks]

Name: "desktopicon"; \
    Description: "{cm:CreateDesktopShortcut}"; \
    GroupDescription: "{cm:AdditionalIcons}"; \
    Flags: checkedonce


[Files]

; PyInstaller создаёт:
;
; dist\
; └── VinogradovsDigitizer\
;     ├── VinogradovsDigitizer.exe
;     └── _internal\
;
; В установщик включается вся эта папка.

Source: "..\dist\VinogradovsDigitizer\*"; \
    DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs


[Icons]

; Ярлык в меню Пуск
Name: "{group}\{#MyAppName}"; \
    Filename: "{app}\{#MyAppExeName}"; \
    WorkingDir: "{app}"; \
    IconFilename: "{app}\{#MyAppExeName}"

; Ярлык на рабочем столе
Name: "{autodesktop}\{#MyAppName}"; \
    Filename: "{app}\{#MyAppExeName}"; \
    WorkingDir: "{app}"; \
    IconFilename: "{app}\{#MyAppExeName}"; \
    Tasks: desktopicon


[Run]

; После установки пользователь может сразу запустить приложение.
Filename: "{app}\{#MyAppExeName}"; \
    Description: "{cm:LaunchApplication,{#MyAppName}}"; \
    WorkingDir: "{app}"; \
    Flags: nowait postinstall skipifsilent