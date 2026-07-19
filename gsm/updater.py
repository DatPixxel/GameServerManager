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

            # Vollständigkeit prüfen (unvollständiger Download -> beschädigte exe)
            if total_size and downloaded < total_size:
                return {'error': f'Download unvollständig ({downloaded}/{total_size} Bytes). Bitte erneut versuchen.'}
            if os.path.getsize(temp_file) < 1_000_000:
                return {'error': 'Heruntergeladene Datei ist zu klein/beschädigt. Bitte erneut versuchen.'}

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
            exe_name = os.path.basename(current_exe)

            # Die neue exe JETZT (das Programm laeuft noch) in den Programmordner kopieren –
            # unter neuem Namen, damit nichts Gesperrtes beruehrt wird. Danach verifizieren.
            # Der eigentliche Austausch ist dann nur ein Umbenennen (atomar, keine Beschaedigung).
            staged = os.path.join(working_dir, exe_name + '.new')
            try:
                if os.path.exists(staged):
                    os.remove(staged)
                shutil.copy2(new_exe_path, staged)
            except Exception as _e:
                return {'error': f'Konnte Update nicht vorbereiten: {_e}'}
            try:
                if os.path.getsize(staged) != os.path.getsize(new_exe_path):
                    os.remove(staged)
                    return {'error': 'Update-Datei wurde beim Vorbereiten unvollstaendig – abgebrochen.'}
            except Exception:
                pass

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
            
            # Batch: warten -> alte exe loeschen -> die bereits kopierte .new UMBENENNEN
            # (atomar, kein Byte-Kopieren der laufenden Datei -> keine Beschaedigung).
            old_exe_esc = current_exe.replace('"', '""')
            staged_esc = staged.replace('"', '""')
            name_esc = exe_name.replace('"', '""')

            batch_script = f'''@echo off
title Game Server Manager Pro - Update
echo Aktualisiere Game Server Manager Pro ...
echo.
set "OLD_EXE={old_exe_esc}"
set "STAGED={staged_esc}"

echo [1/3] Warte auf Programmende...
:waitloop
timeout /t 1 /nobreak >nul
tasklist /FI "IMAGENAME eq {name_esc}" 2>NUL | find /I /N "{name_esc}">NUL
if "%ERRORLEVEL%"=="0" goto waitloop

rem Windows die Datei freigeben lassen
timeout /t 3 /nobreak >nul

echo [2/3] Tausche Version aus...
set /a tries=0
:delloop
del /F /Q "%OLD_EXE%" >nul 2>&1
if exist "%OLD_EXE%" (
    set /a tries+=1
    if %tries% LSS 12 ( timeout /t 1 /nobreak >nul & goto delloop )
)

ren "%STAGED%" "{name_esc}"
if not exist "%OLD_EXE%" copy /Y "%STAGED%" "%OLD_EXE%" >nul 2>&1

echo [3/3] Starte neu...
start "" "%OLD_EXE%"
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
                
                print("Starte Update mit Admin-Rechten...")
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
