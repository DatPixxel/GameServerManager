"""Auto-Updater (GitHub Releases).

Aus game_server_manager.py ausgelagert.
"""

import os
import sys
import json
import shutil
import subprocess
import tempfile
import ctypes

import requests

from gsm.constants import VERSION, GITHUB_API_URL, GITHUB_REPO


class AutoUpdater:
    """Prüft auf Updates und installiert sie"""
    
    def __init__(self, app_instance=None):
        self.app = app_instance
        self.current_version = VERSION
        self.latest_version = None
        self.download_url = None
        self.release_notes = ""
    
    def parse_version(self, version_str):
        """Wandelt Version-String in vergleichbare Tuple um"""
        # Entferne 'v' am Anfang falls vorhanden
        version_str = version_str.lstrip('v').strip()
        try:
            parts = version_str.split('.')
            return tuple(int(p) for p in parts[:3])
        except:
            return (0, 0, 0)
    
    def check_for_updates(self, silent=False):
        """Prüft GitHub auf neue Releases"""
        try:
            response = requests.get(
                GITHUB_API_URL,
                headers={'Accept': 'application/vnd.github.v3+json'},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.latest_version = data.get('tag_name', '').lstrip('v')
                self.release_notes = data.get('body', '')
                
                # Download-URL finden (.exe Asset)
                assets = data.get('assets', [])
                for asset in assets:
                    if asset['name'].endswith('.exe'):
                        self.download_url = asset['browser_download_url']
                        break
                
                # Versionen vergleichen
                current = self.parse_version(self.current_version)
                latest = self.parse_version(self.latest_version)
                
                if latest > current:
                    return {
                        'available': True,
                        'current': self.current_version,
                        'latest': self.latest_version,
                        'download_url': self.download_url,
                        'release_notes': self.release_notes
                    }
                else:
                    return {
                        'available': False,
                        'current': self.current_version,
                        'latest': self.latest_version
                    }
            
            elif response.status_code == 404:
                return {'error': 'Repository nicht gefunden. Prüfe GITHUB_REPO.'}
            else:
                return {'error': f'GitHub API Fehler: {response.status_code}'}
                
        except requests.exceptions.Timeout:
            return {'error': 'Timeout - Keine Internetverbindung?'}
        except requests.exceptions.RequestException as e:
            return {'error': f'Netzwerkfehler: {str(e)}'}
        except Exception as e:
            return {'error': f'Fehler: {str(e)}'}
    
    def download_update(self, progress_callback=None):
        """Lädt das Update herunter"""
        if not self.download_url:
            return {'error': 'Keine Download-URL verfügbar'}
        
        try:
            # Temporärer Pfad - Windows Temp-Ordner (dort hat User immer Schreibrechte)
            import tempfile
            temp_dir = os.path.join(tempfile.gettempdir(), 'GameServerManager_update')
            os.makedirs(temp_dir, exist_ok=True)
            temp_file = os.path.join(temp_dir, 'GameServerManager_new.exe')
            
            # Download mit Fortschritt
            response = requests.get(self.download_url, stream=True, timeout=60)
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_size:
                            progress = int((downloaded / total_size) * 100)
                            progress_callback(progress)
            
            return {'success': True, 'file': temp_file}
            
        except Exception as e:
            return {'error': f'Download fehlgeschlagen: {str(e)}'}
    
    def install_update(self, new_exe_path):
        """
        Update-Installation mit CMD und Batch-Script.
        Funktioniert ohne VBS - nur native Windows CMD.
        """
        try:
            import tempfile
            import ctypes
            
            current_exe = os.path.abspath(sys.argv[0])
            
            # Wenn wir als .py laufen, nicht als .exe
            if not current_exe.endswith('.exe'):
                # Entwicklungsmodus
                if getattr(sys, 'frozen', False):
                    program_dir = os.path.dirname(sys.executable)
                else:
                    program_dir = os.path.dirname(os.path.abspath(__file__))
                shutil.copy(new_exe_path, os.path.join(program_dir, 'GameServerManager.exe'))
                return {'success': True, 'message': 'Update installiert (Entwicklungsmodus)'}
            
            working_dir = os.path.dirname(current_exe)
            
            # Prüfe ob wir in einem geschützten Ordner sind (Program Files)
            program_files = os.environ.get('ProgramFiles', 'C:\\Program Files')
            program_files_x86 = os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')
            needs_admin = current_exe.lower().startswith(program_files.lower()) or \
                          current_exe.lower().startswith(program_files_x86.lower())
            
            # Temp-Verzeichnis für Update-Script
            temp_dir = os.path.join(tempfile.gettempdir(), 'GSM_Update')
            os.makedirs(temp_dir, exist_ok=True)
            
            # Batch-Script mit eingebetteten Pfaden erstellen (keine Parameter nötig!)
            batch_path = os.path.join(temp_dir, 'gsm_update.bat')
            
            # Escaping für Batch: Backslashes verdoppeln nicht nötig, aber Anführungszeichen schon
            new_exe_escaped = new_exe_path.replace('"', '""')
            current_exe_escaped = current_exe.replace('"', '""')
            
            batch_script = f'''@echo off
title Game Server Manager Pro - Update
color 0A
echo.
echo ========================================
echo   Game Server Manager Pro - Update
echo ========================================
echo.

set "NEW_EXE={new_exe_escaped}"
set "OLD_EXE={current_exe_escaped}"

echo Neue Version: %NEW_EXE%
echo Zu ersetzen:  %OLD_EXE%
echo.

echo [1/5] Warte auf Programmende...
:waitloop
timeout /t 1 /nobreak >nul
tasklist /FI "IMAGENAME eq GameServerManager.exe" 2>NUL | find /I /N "GameServerManager.exe">NUL
if "%ERRORLEVEL%"=="0" goto waitloop
echo       Programm beendet.
echo.

echo [2/5] Raeume PyInstaller-Cache auf...
timeout /t 2 /nobreak >nul
for /d %%i in ("%TEMP%\\_MEI*") do (
    rmdir /s /q "%%i" >nul 2>&1
)
echo       Cache bereinigt.
echo.

echo [3/5] Erstelle Backup...
if exist "%OLD_EXE%.backup" del /F /Q "%OLD_EXE%.backup" >nul 2>&1
copy /Y "%OLD_EXE%" "%OLD_EXE%.backup" >nul 2>&1
echo       Backup erstellt.
echo.

echo [4/5] Installiere Update...
copy /Y "%NEW_EXE%" "%OLD_EXE%"
if %errorlevel% neq 0 (
    echo.
    echo ========================================
    echo   FEHLER beim Kopieren!
    echo ========================================
    echo.
    echo Stelle Backup wieder her...
    copy /Y "%OLD_EXE%.backup" "%OLD_EXE%" >nul 2>&1
    echo.
    echo Druecke eine Taste zum Beenden...
    pause >nul
    exit /b 1
)
echo       Update installiert!
echo.

echo [5/5] Starte Programm neu...
start "" "%OLD_EXE%"

echo.
echo ========================================
echo   Update erfolgreich!
echo ========================================
timeout /t 3 /nobreak >nul

:: Aufraeumen
del /F /Q "%OLD_EXE%.backup" >nul 2>&1
del /F /Q "%NEW_EXE%" >nul 2>&1
exit
'''
            
            with open(batch_path, 'w', encoding='cp850') as f:
                f.write(batch_script)
            
            if needs_admin:
                # Mit Admin-Rechten: CMD.EXE mit runas starten
                # CMD.EXE ist IMMER vorhanden und hat IMMER eine Verknüpfung!
                cmd_exe = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'cmd.exe')
                
                # Parameter für CMD: /c führt Befehl aus und beendet
                params = f'/c "{batch_path}"'
                
                print(f"🔐 Starte Update mit Admin-Rechten...")
                print(f"   CMD: {cmd_exe}")
                print(f"   Batch: {batch_path}")
                
                ret = ctypes.windll.shell32.ShellExecuteW(
                    None,           # hwnd
                    "runas",        # Operation (Admin-Rechte anfordern)
                    cmd_exe,        # CMD.EXE - funktioniert IMMER!
                    params,         # /c "pfad\zum\batch.bat"
                    temp_dir,       # Arbeitsverzeichnis
                    1               # SW_SHOWNORMAL (Fenster anzeigen)
                )
                
                # ShellExecute gibt >32 bei Erfolg zurück
                if ret <= 32:
                    error_codes = {
                        0: "Nicht genug Speicher",
                        2: "Datei nicht gefunden", 
                        3: "Pfad nicht gefunden",
                        5: "Zugriff verweigert (UAC abgelehnt?)",
                        31: "Keine Verknüpfung",
                        32: "DLL nicht gefunden"
                    }
                    error_msg = error_codes.get(ret, f"Unbekannter Fehler")
                    return {'error': f'Update fehlgeschlagen: {error_msg} (Code: {ret})\n\nBitte manuell updaten.'}
            else:
                # Ohne Admin: Batch normal starten
                subprocess.Popen(
                    ['cmd.exe', '/c', batch_path],
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            
            return {'success': True, 'restart': True}
            
        except Exception as e:
            return {'error': f'Update fehlgeschlagen: {str(e)}'}
