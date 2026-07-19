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
                
                # Download-URL finden (.zip Asset – Ordner-Version)
                assets = data.get('assets', [])
                for asset in assets:
                    if asset['name'].lower().endswith('.zip'):
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
            temp_file = os.path.join(temp_dir, 'GameServerManager_new.zip')
            
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
    
    def install_update(self, new_zip_path):
        """Installiert das Update der Ordner-Version aus einem ZIP.

        Entpackt das ZIP in einen Staging-Ordner und startet ein abgekoppeltes Batch,
        das nach Programmende den alten Ordner-Inhalt (exe + _internal) durch den neuen
        ersetzt und neu startet. Der Programmordner bleibt am gleichen Ort -> Verknuepfung
        bleibt gueltig. Kein Selbst-Entpacken zur Laufzeit -> kein python313.dll-Fehler.
        """
        try:
            import tempfile
            import zipfile

            if not getattr(sys, 'frozen', False):
                return {'error': 'Update ist nur in der installierten Version moeglich.'}

            current_exe = sys.executable
            app_dir = os.path.dirname(current_exe)
            exe_name = os.path.basename(current_exe)
            parent = os.path.dirname(app_dir)

            # 1) ZIP in Staging-Ordner entpacken
            staging = os.path.join(parent, 'GSM_update_staging')
            try:
                if os.path.isdir(staging):
                    shutil.rmtree(staging, ignore_errors=True)
                os.makedirs(staging, exist_ok=True)
                with zipfile.ZipFile(new_zip_path) as z:
                    z.extractall(staging)
            except Exception as _e:
                return {'error': f'Konnte Update nicht entpacken: {_e}'}

            # Wurzel im Staging finden (ZIP flach ODER mit einem Unterordner)
            src = staging
            if not os.path.exists(os.path.join(src, exe_name)):
                for d in os.listdir(staging):
                    cand = os.path.join(staging, d)
                    if os.path.isdir(cand) and os.path.exists(os.path.join(cand, exe_name)):
                        src = cand
                        break
            if not os.path.exists(os.path.join(src, exe_name)):
                return {'error': 'Update-Paket unvollstaendig (Programm-Datei fehlt).'}

            # 2) Abgekoppeltes Batch schreiben
            temp_dir = os.path.join(tempfile.gettempdir(), 'GSM_Update')
            os.makedirs(temp_dir, exist_ok=True)
            bat = os.path.join(temp_dir, 'gsm_update.bat')

            app_esc = app_dir.replace('"', '""')
            src_esc = src.replace('"', '""')
            exe_esc = current_exe.replace('"', '""')
            name_esc = exe_name.replace('"', '""')
            staging_esc = staging.replace('"', '""')
            _crlf = chr(13) + chr(10)
            _lines = [
                "@echo off",
                "title Game Server Manager - Update",
                "echo Aktualisiere Game Server Manager ...",
                "timeout /t 2 /nobreak >nul",
                'taskkill /F /IM "' + name_esc + '" >nul 2>&1',
                "timeout /t 2 /nobreak >nul",
                ":waitgone",
                'tasklist /FI "IMAGENAME eq ' + name_esc + '" 2>NUL | find /I /N "' + name_esc + '">NUL',
                'if "%ERRORLEVEL%"=="0" ( timeout /t 1 /nobreak >nul & goto waitgone )',
                'del /F /Q "' + app_esc + chr(92) + name_esc + '" >nul 2>&1',
                'if exist "' + app_esc + chr(92) + '_internal" rmdir /S /Q "' + app_esc + chr(92) + '_internal"',
                'robocopy "' + src_esc + '" "' + app_esc + '" /E /MOVE >nul',
                'if exist "' + staging_esc + '" rmdir /S /Q "' + staging_esc + '"',
                'start "" "' + exe_esc + '"',
                "exit",
            ]
            with open(bat, "w", encoding="cp850") as f:
                f.write(_crlf.join(_lines) + _crlf)

            # Abgekoppelt starten, damit das Batch das Beenden des Programms ueberlebt
            DETACHED_PROCESS = 0x00000008
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            CREATE_BREAKAWAY_FROM_JOB = 0x01000000
            flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_BREAKAWAY_FROM_JOB
            try:
                subprocess.Popen(['cmd.exe', '/c', bat], creationflags=flags, close_fds=True)
            except Exception:
                subprocess.Popen(['cmd.exe', '/c', bat],
                                 creationflags=subprocess.CREATE_NEW_CONSOLE)

            return {'success': True, 'restart': True}

        except Exception as e:
            return {'error': f'Update fehlgeschlagen: {str(e)}'}
