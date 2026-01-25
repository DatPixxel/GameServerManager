"""
Relauncher für Game Server Manager Pro
Dieses kleine Programm wird vom Hauptprogramm gestartet um Updates zu installieren.

Ablauf:
1. Wartet bis Hauptprogramm beendet ist (oder beendet es selbst)
2. Ersetzt die alte .exe durch die neue
3. Startet das Programm neu
4. Räumt auf

Aufruf: relauncher.exe <neue_exe> <alte_exe> <arbeitsverzeichnis>
"""

import sys
import os
import time
import shutil
import subprocess

def log(message):
    """Schreibt Log-Nachricht in Datei (keine Konsole nötig)"""
    try:
        log_file = os.path.join(os.environ.get('TEMP', '.'), 'gsm_update.log')
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"{time.strftime('%H:%M:%S')} - {message}\n")
    except:
        pass

def is_process_running(exe_name):
    """Prüft ob ein Prozess läuft"""
    try:
        output = subprocess.check_output(
            f'tasklist /FI "IMAGENAME eq {exe_name}" /NH',
            shell=True,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW
        ).decode('utf-8', errors='ignore')
        return exe_name.lower() in output.lower()
    except:
        return False

def kill_process(exe_name):
    """Beendet einen Prozess mit taskkill"""
    try:
        subprocess.run(
            f'taskkill /F /IM {exe_name}',
            shell=True,
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return True
    except:
        return False

def wait_for_process_exit(exe_name, timeout=15):
    """Wartet bis der Prozess beendet ist, beendet ihn notfalls selbst"""
    log(f"Warte auf Beendigung von {exe_name}...")
    
    # Erst kurz warten ob es sich selbst beendet
    for i in range(timeout):
        if not is_process_running(exe_name):
            log("Prozess hat sich selbst beendet.")
            return True
        log(f"Warte... ({i+1}/{timeout})")
        time.sleep(1)
    
    # Prozess läuft noch - selbst beenden
    log(f"Prozess läuft noch nach {timeout}s - beende mit taskkill...")
    kill_process(exe_name)
    
    # Nochmal kurz warten
    for i in range(5):
        if not is_process_running(exe_name):
            log("Prozess erfolgreich beendet.")
            return True
        time.sleep(1)
    
    log("WARNUNG: Prozess konnte nicht beendet werden!")
    return False

def main():
    log("=" * 50)
    log("Game Server Manager Pro - Update Installer")
    log("=" * 50)
    
    if len(sys.argv) < 4:
        log("Fehler: Nicht genug Argumente!")
        log(f"Erhalten: {sys.argv}")
        sys.exit(1)
    
    new_exe = sys.argv[1]
    old_exe = sys.argv[2]
    working_dir = sys.argv[3]
    
    log(f"Neue Version: {new_exe}")
    log(f"Zu ersetzen:  {old_exe}")
    log(f"Verzeichnis:  {working_dir}")
    
    # 1. Warte auf Prozessende (oder beende selbst)
    exe_name = os.path.basename(old_exe)
    wait_for_process_exit(exe_name, timeout=10)
    
    # Extra warten damit Windows die Datei freigibt
    log("Warte auf Dateifreigabe...")
    time.sleep(3)
    
    # 2. Backup erstellen
    backup_exe = old_exe + ".backup"
    try:
        if os.path.exists(backup_exe):
            os.remove(backup_exe)
        if os.path.exists(old_exe):
            log("Erstelle Backup...")
            shutil.copy2(old_exe, backup_exe)
            log("Backup erstellt.")
    except Exception as e:
        log(f"Backup-Warnung: {e}")
    
    # 3. Neue Version installieren
    log("Installiere Update...")
    max_retries = 10
    success = False
    
    for attempt in range(max_retries):
        try:
            shutil.copy2(new_exe, old_exe)
            success = True
            log("Update erfolgreich installiert!")
            break
        except PermissionError:
            log(f"Versuch {attempt + 1}/{max_retries} - Datei noch gesperrt, warte...")
            # Versuche nochmal zu beenden
            if attempt == 2:
                log("Versuche erneut Prozess zu beenden...")
                kill_process(exe_name)
            time.sleep(2)
        except Exception as e:
            log(f"Fehler: {e}")
            time.sleep(1)
    
    if not success:
        log("FEHLER: Update konnte nicht installiert werden!")
        # Rollback
        if os.path.exists(backup_exe):
            log("Stelle Backup wieder her...")
            try:
                shutil.copy2(backup_exe, old_exe)
            except:
                pass
        sys.exit(1)
    
    # 4. Aufräumen
    log("Räume auf...")
    try:
        if os.path.exists(backup_exe):
            os.remove(backup_exe)
        if os.path.exists(new_exe):
            os.remove(new_exe)
        # Temp-Ordner aufräumen
        temp_dir = os.path.dirname(new_exe)
        if "GSM_Update" in temp_dir or "GameServerManager_update" in temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception as e:
        log(f"Aufräum-Warnung: {e}")
    
    # 5. Programm neu starten
    log("Starte Programm neu...")
    time.sleep(1)
    
    try:
        subprocess.Popen(
            [old_exe],
            cwd=working_dir,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        )
        log("Programm gestartet!")
    except Exception as e:
        log(f"Start-Fehler: {e}")
        sys.exit(1)
    
    log("Update abgeschlossen!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"Kritischer Fehler: {e}")
        sys.exit(1)

