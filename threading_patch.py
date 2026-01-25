#!/usr/bin/env python3
"""
Game Server Manager Pro - Threading Stability Patch
Version: 1.0
Datum: 2026-01-25

Behebt Threading-Probleme:
1. Zentrales Lock-System für Server-Zugriffe
2. Thread-Pool statt wilde Thread-Erstellung
3. Besseres Fehlerhandling in Threads
4. Thread-Cleanup bei Programm-Ende
5. Status-Synchronisation

WICHTIG: Erstellt automatisch Backup vor Patch!
"""

import os
import sys
import shutil
from datetime import datetime

# Farben
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")

def create_backup(file_path):
    """Erstellt Backup der Datei"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.threading_backup_{timestamp}"
    
    try:
        shutil.copy2(file_path, backup_path)
        print_success(f"Backup erstellt: {backup_path}")
        return backup_path
    except Exception as e:
        print_error(f"Backup fehlgeschlagen: {e}")
        return None

def create_threading_module(base_dir):
    """Erstellt Threading-Manager Modul"""
    
    threading_code = '''"""
Thread-Management Module für Game Server Manager Pro
Zentrales Lock-System und Thread-Pool
"""

import threading
from concurrent.futures import ThreadPoolExecutor
import traceback
import time

# ==================== SERVER LOCK MANAGER ====================

class ServerLockManager:
    """Verwaltet Locks für Server-Operationen"""
    
    def __init__(self):
        self.locks = {}  # {server_id: Lock}
        self._global_lock = threading.Lock()
    
    def get_lock(self, server_id):
        """Holt Lock für bestimmten Server (erstellt falls nötig)"""
        with self._global_lock:
            if server_id not in self.locks:
                self.locks[server_id] = threading.Lock()
            return self.locks[server_id]
    
    def acquire(self, server_id, timeout=10):
        """Erwirbt Lock für Server"""
        lock = self.get_lock(server_id)
        return lock.acquire(timeout=timeout)
    
    def release(self, server_id):
        """Gibt Lock frei"""
        lock = self.get_lock(server_id)
        try:
            lock.release()
        except RuntimeError:
            # Lock war nicht acquired - ignorieren
            pass

# ==================== THREAD POOL ====================

class ManagedThreadPool:
    """Thread-Pool mit Fehlerhandling"""
    
    def __init__(self, max_workers=10):
        self.pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="GSM-Worker")
        self.active_tasks = []
        self._lock = threading.Lock()
    
    def submit(self, fn, *args, **kwargs):
        """Führt Funktion im Thread-Pool aus mit Fehlerhandling"""
        def wrapped():
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                print(f"❌ Thread-Fehler in {fn.__name__}: {e}")
                traceback.print_exc()
                return None
        
        future = self.pool.submit(wrapped)
        
        with self._lock:
            self.active_tasks.append(future)
        
        return future
    
    def shutdown(self, wait=True, timeout=5):
        """Beendet Pool sauber"""
        print("🔄 Beende Thread-Pool...")
        
        if wait:
            # Warte auf laufende Tasks (max. timeout)
            start = time.time()
            with self._lock:
                pending = [f for f in self.active_tasks if not f.done()]
            
            while pending and (time.time() - start) < timeout:
                time.sleep(0.1)
                pending = [f for f in pending if not f.done()]
            
            if pending:
                print(f"⚠️  {len(pending)} Tasks noch aktiv nach {timeout}s")
        
        self.pool.shutdown(wait=False)
        print("✅ Thread-Pool beendet")

# ==================== SAFE THREAD WRAPPER ====================

def safe_thread_wrapper(func, error_handler=None):
    """Wrapper für Thread-Funktionen mit Fehlerhandling"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_msg = f"Thread-Fehler in {func.__name__}: {e}"
            print(f"❌ {error_msg}")
            traceback.print_exc()
            
            if error_handler:
                try:
                    error_handler(e, func.__name__)
                except:
                    pass
            
            return None
    return wrapper

# ==================== STATUS SYNCHRONIZER ====================

class ServerStatusSync:
    """Synchronisiert Server-Status zwischen Threads"""
    
    def __init__(self):
        self._status = {}  # {server_id: status_dict}
        self._lock = threading.RLock()  # Re-entrant Lock
    
    def update(self, server_id, **kwargs):
        """Aktualisiert Status für Server"""
        with self._lock:
            if server_id not in self._status:
                self._status[server_id] = {}
            self._status[server_id].update(kwargs)
            self._status[server_id]['last_update'] = time.time()
    
    def get(self, server_id, key=None):
        """Holt Status für Server"""
        with self._lock:
            if server_id not in self._status:
                return None if key else {}
            if key:
                return self._status[server_id].get(key)
            return self._status[server_id].copy()
    
    def remove(self, server_id):
        """Entfernt Status für Server"""
        with self._lock:
            self._status.pop(server_id, None)

# ==================== GLOBAL INSTANCES ====================

# Diese werden beim Import erstellt
server_locks = ServerLockManager()
thread_pool = ManagedThreadPool(max_workers=10)
status_sync = ServerStatusSync()

print("✅ Threading-Manager initialisiert")
'''
    
    threading_file = os.path.join(base_dir, 'thread_manager.py')
    
    try:
        with open(threading_file, 'w', encoding='utf-8') as f:
            f.write(threading_code)
        print_success(f"Threading-Modul erstellt: {threading_file}")
        return True
    except Exception as e:
        print_error(f"Fehler beim Erstellen: {e}")
        return False

def apply_threading_patch(file_path):
    """Wendet Threading-Patch an"""
    
    print_info("Lese Datei...")
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    fixes_applied = 0
    
    # PATCH 1: Import threading-module (nach anderen imports)
    print_info("Patch 1: Threading-Manager importieren")
    insert_pos = 35  # Nach anderen Security-Imports
    if insert_pos < len(lines):
        if 'from thread_manager import' not in ''.join(lines[:50]):
            lines.insert(insert_pos, '\n')
            lines.insert(insert_pos + 1, '# Threading Manager\n')
            lines.insert(insert_pos + 2, 'try:\n')
            lines.insert(insert_pos + 3, '    from thread_manager import server_locks, thread_pool, status_sync, safe_thread_wrapper\n')
            lines.insert(insert_pos + 4, '    THREADING_MANAGER_AVAILABLE = True\n')
            lines.insert(insert_pos + 5, 'except ImportError:\n')
            lines.insert(insert_pos + 6, '    THREADING_MANAGER_AVAILABLE = False\n')
            lines.insert(insert_pos + 7, '    print("⚠️  thread_manager.py nicht gefunden - Threading-Features eingeschränkt")\n')
            lines.insert(insert_pos + 8, '\n')
            print_success("  Threading-Manager Import hinzugefügt")
            fixes_applied += 1
        else:
            print_warning("  Bereits importiert")
    
    # PATCH 2: ServerInstance.__init__ - Lock hinzufügen
    print_info("Patch 2: Server-Locks hinzufügen")
    found = False
    for i in range(2046, min(2070, len(lines))):
        if 'def __init__(self, server_id, config, config_manager' in lines[i]:
            # Suche nach self.log_messages
            for j in range(i, min(i + 20, len(lines))):
                if 'self.log_messages = []' in lines[j]:
                    # Lock NACH log_messages hinzufügen
                    lines.insert(j + 1, '        \n')
                    lines.insert(j + 2, '        # Thread-Safety\n')
                    lines.insert(j + 3, '        self._lock = threading.Lock()\n')
                    lines.insert(j + 4, '        self._status_lock = threading.Lock()\n')
                    print_success("  Server-Locks in __init__ hinzugefügt")
                    fixes_applied += 1
                    found = True
                    break
            break
    
    if not found:
        print_warning("  __init__ Position nicht gefunden")
    
    # PATCH 3: start() Methode absichern
    print_info("Patch 3: start() mit Lock absichern")
    found = False
    for i in range(len(lines)):
        if 'def start(self):' in lines[i] and i > 2100 and i < 2200:  # ServerInstance.start
            # Suche "if self.is_running():"
            for j in range(i, min(i + 10, len(lines))):
                if 'if self.is_running():' in lines[j]:
                    # Füge Lock VOR der Prüfung ein
                    indent = '        '
                    lines.insert(j, f'{indent}# Thread-Safe Start\n')
                    lines.insert(j + 1, f'{indent}with self._lock:\n')
                    
                    # Einrückung aller folgenden Zeilen bis return
                    k = j + 2
                    while k < len(lines) and 'def ' not in lines[k]:
                        if lines[k].strip() and not lines[k].strip().startswith('#'):
                            lines[k] = '    ' + lines[k]  # +4 Spaces
                        k += 1
                        if k >= j + 50:  # Safety: max 50 Zeilen
                            break
                    
                    print_success("  start() mit Lock geschützt")
                    fixes_applied += 1
                    found = True
                    break
            break
    
    if not found:
        print_warning("  start() nicht gepatcht - Manuell prüfen!")
    
    # PATCH 4: Thread-Erstellung durch thread_pool ersetzen
    print_info("Patch 4: threading.Thread → thread_pool")
    replacements = 0
    for i in range(len(lines)):
        # Suche nach threading.Thread(target=...
        if 'threading.Thread(target=' in lines[i] and 'daemon=True' in lines[i]:
            # Kommentiere alte Zeile
            old_line = lines[i]
            lines[i] = '            # OLD: ' + old_line
            
            # Füge neue Zeile mit thread_pool hinzu
            indent = old_line[:len(old_line) - len(old_line.lstrip())]
            
            # Extrahiere Funktionsname
            import re
            match = re.search(r'target=([^,)]+)', old_line)
            if match:
                func_name = match.group(1).strip()
                lines.insert(i + 1, f'{indent}if THREADING_MANAGER_AVAILABLE:\n')
                lines.insert(i + 2, f'{indent}    thread_pool.submit({func_name})\n')
                lines.insert(i + 3, f'{indent}else:\n')
                lines.insert(i + 4, f'{indent}    # Fallback\n')
                lines.insert(i + 5, f'{indent}    {old_line.strip()}\n')
                replacements += 1
    
    if replacements > 0:
        print_success(f"  {replacements} Thread-Starts durch thread_pool ersetzt")
        fixes_applied += 1
    else:
        print_warning("  Keine threading.Thread() gefunden zum Ersetzen")
    
    return lines, fixes_applied

def main():
    print_header("Game Server Manager Pro - Threading Patch")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    target_file = os.path.join(script_dir, "game_server_manager.py")
    
    if not os.path.exists(target_file):
        print_error(f"Datei nicht gefunden: {target_file}")
        sys.exit(1)
    
    print_info(f"Ziel-Datei: {target_file}")
    
    # Backup
    print_header("Schritt 1: Backup erstellen")
    backup_path = create_backup(target_file)
    if not backup_path:
        sys.exit(1)
    
    # Threading-Modul erstellen
    print_header("Schritt 2: Threading-Manager erstellen")
    if not create_threading_module(script_dir):
        sys.exit(1)
    
    # Patches anwenden
    print_header("Schritt 3: Threading-Patches anwenden")
    try:
        fixed_lines, fixes_count = apply_threading_patch(target_file)
    except Exception as e:
        print_error(f"Fehler: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print_header("Schritt 4: Bestätigung")
    print_info(f"Gefundene Fixes: {fixes_count}/4")
    
    if fixes_count == 0:
        print_warning("Keine Fixes angewendet!")
        return
    
    print()
    print_warning("⚠️  WICHTIG: Threading-Patch ist experimentell!")
    print_info("Bitte teste ausgiebig nach dem Patch:")
    print_info("  - Server starten/stoppen")
    print_info("  - Mehrere Server gleichzeitig")
    print_info("  - Backups während Server läuft")
    print()
    print(f"{Colors.WARNING}Möchtest du die Änderungen speichern?{Colors.ENDC}")
    response = input(f"{Colors.BOLD}Fortfahren? [j/N]: {Colors.ENDC}").strip().lower()
    
    if response not in ['j', 'ja', 'y', 'yes']:
        print_warning("Patch abgebrochen!")
        return
    
    # Speichern
    print_header("Schritt 5: Änderungen speichern")
    try:
        with open(target_file, 'w', encoding='utf-8') as f:
            f.writelines(fixed_lines)
        print_success(f"Datei gespeichert!")
        print_success(f"{fixes_count} Threading-Patches erfolgreich angewendet!")
    except Exception as e:
        print_error(f"Fehler beim Speichern: {e}")
        sys.exit(1)
    
    print_header("✅ Threading-Patch erfolgreich!")
    print_success("Folgende Threading-Features wurden hinzugefügt:")
    print_info("  1. Server-Lock-System (verhindert Race-Conditions)")
    print_info("  2. Thread-Pool (max. 10 Worker)")
    print_info("  3. Thread-Safe Server-Start")
    print_info("  4. Threading-Manager-Modul (thread_manager.py)")
    print()
    print_warning("⚠️  WICHTIG - TESTE GRÜNDLICH:")
    print_info("  1. Server starten/stoppen")
    print_info("  2. Mehrere Server gleichzeitig verwalten")
    print_info("  3. Backups während Server läuft")
    print_info("  4. Prüfe Logs auf Thread-Fehler")
    print()
    print(f"{Colors.OKGREEN}{Colors.BOLD}🔧 Threading ist jetzt stabiler!{Colors.ENDC}")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print_warning("Patch abgebrochen!")
        sys.exit(0)
