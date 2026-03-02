#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppName=SF2Converter
AppVersion={#AppVersion}
AppPublisher=Spectralis 2 Tools
DefaultDirName={autopf}\SF2Converter
DefaultGroupName=SF2Converter
UninstallDisplayIcon={app}\SF2Converter.exe
OutputDir=dist
OutputBaseFilename=SF2Converter-Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "dist\SF2Converter.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\SF2Converter"; Filename: "{app}\SF2Converter.exe"
Name: "{group}\Uninstall SF2Converter"; Filename: "{uninstallexe}"
Name: "{autodesktop}\SF2Converter"; Filename: "{app}\SF2Converter.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"
