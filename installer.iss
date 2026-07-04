; Script de Inno Setup para StemPlayer
[Setup]
AppName=StemPlayer
AppVersion=0.1.0
AppPublisher=Pablo Jiménez
AppPublisherURL=https://github.com/bay122/stemplayer
AppSupportURL=https://github.com/bay122/stemplayer/issues
AppUpdatesURL=https://github.com/bay122/stemplayer/releases
DefaultDirName={pf}\StemPlayer
DefaultGroupName=StemPlayer
UninstallDisplayIcon={app}\icon.ico
Compression=lzma2
SolidCompression=yes
OutputDir=dist
OutputBaseFilename=StemPlayer-v0.1.0-win64-installer
SetupIconFile=assets\icons\icon.ico
WizardImageFile=assets\icons\wizard_image_file_icon.png
WizardSmallImageFile=assets\icons\wizard_small_image_file_icon.png

[Files]
; Copia todo el contenido de la carpeta compilada (después de generar el ZIP, descomprimimos)
Source: "dist\StemPlayer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Acceso directo en el menú Inicio
Name: "{group}\StemPlayer"; Filename: "{app}\StemPlayer.exe"; IconFilename: "{app}\icon.ico"
; Acceso directo en el escritorio
Name: "{commondesktop}\StemPlayer"; Filename: "{app}\StemPlayer.exe"; IconFilename: "{app}\icon.ico"

[Run]
; Opcional: ejecutar la aplicación al finalizar la instalación
; Filename: "{app}\StemPlayer.exe"; Description: "Ejecutar StemPlayer"; Flags: postinstall nowait skipifsilent
