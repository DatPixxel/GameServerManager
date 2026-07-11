; Game Server Manager Pro - Inno Setup Script
; Beendet laufende Instanzen automatisch vor der Installation

#define MyAppName "Game Server Manager Pro"
#define MyAppVersion "3.37"
#define MyAppPublisher "DatPixxel"
#define MyAppURL "https://github.com/DatPixxel/GameServerManager"
#define MyAppExeName "GameServerManager.exe"

[Setup]
AppId={{B8F3A9C2-1234-5678-9ABC-DEF012345678}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=installer_output
OutputBaseFilename=GameServerManager_Setup_{#MyAppVersion}
SetupIconFile=gsm_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
PrivilegesRequired=admin
WizardStyle=modern
ShowLanguageDialog=yes

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\GameServerManager.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\relauncher.exe"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "gsm_icon.ico"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist; DestName: "Readme.txt"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\gsm_icon.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\gsm_icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM {#MyAppExeName}"; Flags: runhidden skipifdoesntexist

[Code]
// Prüft ob ein Prozess läuft
function IsProcessRunning(ProcessName: String): Boolean;
var
  WMIService: Variant;
  ProcessList: Variant;
begin
  Result := False;
  try
    WMIService := CreateOleObject('WbemScripting.SWbemLocator');
    WMIService := WMIService.ConnectServer('.', 'root\cimv2');
    ProcessList := WMIService.ExecQuery('SELECT * FROM Win32_Process WHERE Name = "' + ProcessName + '"');
    Result := (ProcessList.Count > 0);
  except
    // Bei Fehler annehmen dass Prozess nicht läuft
    Result := False;
  end;
end;

// Beendet Prozess und wartet bis er wirklich beendet ist
function KillProcessAndWait(ProcessName: String; MaxWaitSeconds: Integer): Boolean;
var
  ResultCode: Integer;
  WaitCount: Integer;
begin
  Result := True;
  
  // Erst prüfen ob Prozess überhaupt läuft
  if not IsProcessRunning(ProcessName) then
  begin
    Log('Prozess ' + ProcessName + ' läuft nicht.');
    Exit;
  end;
  
  Log('Beende Prozess ' + ProcessName + '...');
  
  // Prozess beenden
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM ' + ProcessName, '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  
  // Warten bis Prozess wirklich beendet ist
  WaitCount := 0;
  while IsProcessRunning(ProcessName) and (WaitCount < MaxWaitSeconds) do
  begin
    Log('Warte auf Beendigung... (' + IntToStr(WaitCount + 1) + '/' + IntToStr(MaxWaitSeconds) + ')');
    Sleep(1000);
    WaitCount := WaitCount + 1;
  end;
  
  // Prüfen ob erfolgreich
  if IsProcessRunning(ProcessName) then
  begin
    Log('WARNUNG: Prozess konnte nicht beendet werden!');
    Result := False;
  end
  else
  begin
    Log('Prozess erfolgreich beendet.');
    // Extra warten damit Windows die Datei freigibt
    Sleep(1000);
  end;
end;

// Wird VOR der Installation aufgerufen
function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  NeedsRestart := False;
  
  // Versuche Prozess zu beenden (max 10 Sekunden warten)
  if not KillProcessAndWait('GameServerManager.exe', 10) then
  begin
    // Benutzer informieren
    if MsgBox('Game Server Manager Pro konnte nicht automatisch beendet werden.' + #13#10 + #13#10 +
              'Bitte schließen Sie das Programm manuell und klicken Sie dann OK.', 
              mbError, MB_OKCANCEL) = IDCANCEL then
    begin
      Result := 'Installation abgebrochen.';
      Exit;
    end;
    
    // Nochmal versuchen
    if not KillProcessAndWait('GameServerManager.exe', 5) then
    begin
      Result := 'Das Programm läuft noch. Bitte schließen Sie es und starten Sie die Installation erneut.';
    end;
  end;
end;

// Wird bei Deinstallation aufgerufen
function InitializeUninstall(): Boolean;
begin
  Result := True;
  KillProcessAndWait('GameServerManager.exe', 10);
end;