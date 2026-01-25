"""
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
