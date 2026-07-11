"""
INTEGRATION GUIDE - Game Server Manager Pro Security Überarbeitung
===================================================================

HINWEIS (v3.31):
`security_patches.py` wird nur noch fuer Legacy-Kompatibilitaet mitgefuehrt.
Die produktiv genutzten Security-Checks liegen direkt in
`game_server_manager.py`, `security_utils.py`, `web_security.py` und
`auth_manager.py`.

Dieses Dokument beschreibt, wie die Sicherheitsverbesserungen in die
Hauptdatei game_server_manager.py integriert werden.

ÜBERSICHT DER NEUEN MODULE:
===========================

1. security_utils.py        - Pfad-Sicherheit, Passwort-Hashing, Input-Validierung
2. web_security.py          - CSRF, Rate-Limiting, Session-Management
3. security_patches.py      - Legacy-Kompatibilitaet
4. auth_manager.py          - Auth-Management mit Hash-Migration

SCHRITT-FÜR-SCHRITT INTEGRATION:
================================

SCHRITT 1: Imports am Anfang der Hauptdatei hinzufügen
------------------------------------------------------

Nach den bestehenden Imports (Zeile ~26) einfügen:

```python
# Sicherheits-Module
from security_utils import (
    safe_join, safe_extract, validate_port, validate_mod_ids,
    validate_server_name, validate_map_param, is_config_file_allowed,
    PathTraversalError, InvalidInputError, ZipSlipError,
    PasswordHasher, generate_session_token, compute_file_sha256,
    verify_file_integrity, is_tailscale_ip, is_localhost
)
from web_security import (
    csrf_protection, csrf_required, rate_limiter, rate_limit,
    SessionManager, IPAllowlist, add_security_headers
)
from auth_manager import AuthManager
# optional: nur fuer Legacy-Integrationen
import security_patches
import logging

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(CONFIG_DIR, 'gsm.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
```

SCHRITT 2: Passwort-Hashing ersetzen
------------------------------------

Die Funktion hash_password() (Zeile 780-782) ENTFERNEN und durch Verwendung
von PasswordHasher ersetzen:

VORHER:
```python
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()
```

NACHHER:
```python
# Globale Hasher-Instanz
password_hasher = PasswordHasher()

def hash_password(password):
    """Legacy-Wrapper - nutzt jetzt PasswordHasher"""
    return password_hasher.hash_password(password)
```

SCHRITT 3: ConfigManager anpassen
----------------------------------

In der ConfigManager-Klasse die verify_password Methode ersetzen:

VORHER (ca. Zeile 750):
```python
def verify_password(self, password):
    stored_hash = self.app_config.get("password", "")
    if not stored_hash:
        return True
    return hash_password(password) == stored_hash
```

NACHHER:
```python
def verify_password(self, password):
    stored_hash = self.app_config.get("password", "")
    if not stored_hash:
        return True
    
    # Verwende PasswordHasher
    is_valid = password_hasher.verify_password(password, stored_hash)
    
    # Migration: Wenn altes SHA256-Hash und erfolgreich, aktualisiere
    if is_valid and password_hasher.needs_rehash(stored_hash):
        logger.info("🔄 Migriere Passwort-Hash")
        new_hash = password_hasher.hash_password(password)
        self.app_config["password"] = new_hash
        self.save_app_config()
    
    return is_valid
```

SCHRITT 4: ServerInstance - Methoden ersetzen
--------------------------------------------

In der ServerInstance-Klasse (ca. Zeile 1497-1560):

1. build_start_command() ERSETZEN durch:
```python
def build_start_command(self):
    return security_patches.build_start_command_secure(self)
```

2. start() ERSETZEN durch:
```python
def start(self):
    return security_patches.start_server_secure(self)
```

3. update_server() ERSETZEN durch:
```python
def update_server(self, progress_callback=None):
    return security_patches.update_server_secure(self, progress_callback)
```

4. restore_backup() ERSETZEN durch:
```python
def restore_backup(self, backup_path):
    return security_patches.restore_backup_secure(self, backup_path)
```

5. delete_backup() ERSETZEN durch:
```python
def delete_backup(self, backup_filename):
    return security_patches.delete_backup_secure(self, backup_filename)
```

SCHRITT 5: Flask Web-Server - Sicherheits-Setup
-----------------------------------------------

In start_web_server() (ca. Zeile 5478), NACH der Flask-App-Erstellung:

```python
def start_web_server(self):
    app_instance = self
    config_manager = self.config_manager
    
    flask_app = Flask(__name__)
    flask_app.secret_key = secrets.token_hex(32)
    
    # ===== NEU: Sicherheits-Konfiguration =====
    
    # Session-Konfiguration
    flask_app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=False,  # Nur True bei HTTPS
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12)
    )
    
    # Session-Manager
    session_manager = SessionManager(session_ttl=43200)
    
    # IP-Allowlist (Tailscale-Only)
    web_bind_mode = config_manager.app_config.get("web", {}).get("bind_mode", "local")
    tailscale_ips = config_manager.app_config.get("web", {}).get("allowed_tailscale_ips", [])
    ip_allowlist = IPAllowlist(mode=web_bind_mode, tailscale_ips=tailscale_ips)
    
    # Before-Request Handler für IP-Check
    @flask_app.before_request
    def check_ip_allowlist():
        # Skip für Login-Seite
        if request.endpoint in ['login', 'static']:
            return None
        
        result = ip_allowlist.check_request()
        if result:
            return result
    
    # After-Request Handler für Security-Headers
    @flask_app.after_request
    def apply_security_headers(response):
        return add_security_headers(response)
    
    # ===== ENDE Sicherheits-Konfiguration =====
    
    # ... Rest der Funktion bleibt gleich ...
```

SCHRITT 6: Flask-Routes - CSRF und Rate-Limiting hinzufügen
-----------------------------------------------------------

ALLE state-changing Routes (POST/PUT/DELETE) mit Decorators versehen:

VORHER:
```python
@flask_app.route('/api/server/<server_id>/start', methods=['POST'])
def api_server_start(server_id):
    if 'token' not in session or session['token'] not in valid_sessions:
        return jsonify({'error': 'Unauthorized'}), 401
    # ...
```

NACHHER:
```python
@flask_app.route('/api/server/<server_id>/start', methods=['POST'])
@csrf_required
@rate_limit(max_requests=30, time_window=60)
def api_server_start(server_id):
    if 'token' not in session or session['token'] not in valid_sessions:
        return jsonify({'error': 'Unauthorized'}), 401
    # ...
```

Für ALLE Routes anwenden:
- /api/server/<id>/start
- /api/server/<id>/stop
- /api/server/<id>/restart
- /api/server/<id>/backup
- /api/server/<id>/config/save
- /api/server/<id>/backups/delete
- /api/server/<id>/backups/restore
- /api/server/<id>/mods (POST)
- /api/server/<id>/mods/<mod_id> (DELETE)
- /api/server/<id>/update

SCHRITT 7: Login-Route mit Rate-Limiting
-----------------------------------------

Login-Route (ca. Zeile 5500-5510) ERSETZEN:

```python
@flask_app.route('/login', methods=['GET', 'POST'])
@rate_limit(max_requests=10, time_window=60)
def login():
    if request.method == 'POST':
        password = request.form.get('password', '')
        ip = request.remote_addr
        
        # Rate-Limit Check
        if not rate_limiter.is_login_allowed(ip):
            return render_template_string(
                get_login_template(config_manager, error=True, 
                error_msg="Zu viele Login-Versuche. Bitte warten.")
            )
        
        if config_manager.verify_password(password):
            token = generate_session_token()
            session_manager.create_session(token, 'admin')
            session['token'] = token
            
            # CSRF-Token für Session generieren
            csrf_token = csrf_protection.generate_token()
            session['csrf_token'] = csrf_token
            
            return redirect('/')
        else:
            # Fehlgeschlagenen Login aufzeichnen
            lockout_duration = rate_limiter.record_failed_login(ip, 'admin')
            
            error_msg = "Falsches Passwort"
            if lockout_duration:
                error_msg = f"Zu viele Fehlversuche. Gesperrt für {lockout_duration}s"
            
            return render_template_string(
                get_login_template(config_manager, error=True, error_msg=error_msg)
            )
    
    return render_template_string(get_login_template(config_manager))
```

SCHRITT 8: API-Routes für Config Read/Save ersetzen
---------------------------------------------------

Config Read (ca. Zeile 5769-5786) ERSETZEN:

```python
@flask_app.route('/api/server/<server_id>/config/read', methods=['POST'])
@csrf_required
@rate_limit(max_requests=60, time_window=60)
def api_read_config(server_id):
    if 'token' not in session or session_manager.validate_session(session.get('token')):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    result = security_patches.api_read_config_secure(server_id, data)
    
    status_code = 200 if result.get('success') else 400
    return jsonify(result), status_code
```

Config Save (ca. Zeile 5788-5806) ERSETZEN:

```python
@flask_app.route('/api/server/<server_id>/config/save', methods=['POST'])
@csrf_required
@rate_limit(max_requests=60, time_window=60)
def api_save_config(server_id):
    if 'token' not in session or not session_manager.validate_session(session.get('token')):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    result = security_patches.api_save_config_secure(server_id, data)
    
    status_code = 200 if result.get('success') else 400
    return jsonify(result), status_code
```

SCHRITT 9: Backup Restore/Delete Routes ersetzen
------------------------------------------------

Backup Restore (ca. Zeile 5693-5715) ERSETZEN:

```python
@flask_app.route('/api/server/<server_id>/backups/restore', methods=['POST'])
@csrf_required
@rate_limit(max_requests=10, time_window=60)
def api_restore_backup(server_id):
    if 'token' not in session or not session_manager.validate_session(session.get('token')):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    result = security_patches.api_restore_backup_secure(
        server_id, data, app_instance.server_instances
    )
    
    status_code = 200 if result.get('success') else 400
    return jsonify(result), status_code
```

Backup Delete (ca. Zeile 5717-5733) ERSETZEN:

```python
@flask_app.route('/api/server/<server_id>/backups/delete', methods=['POST'])
@csrf_required
@rate_limit(max_requests=30, time_window=60)
def api_delete_backup(server_id):
    if 'token' not in session or not session_manager.validate_session(session.get('token')):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    result = security_patches.api_delete_backup_secure(
        server_id, data, app_instance.server_instances
    )
    
    status_code = 200 if result.get('success') else 400
    return jsonify(result), status_code
```

SCHRITT 10: Web-Template - CSRF-Token hinzufügen
------------------------------------------------

Im Web-Template (ca. Zeile 5820+) JavaScript-Teil erweitern:

```javascript
// CSRF-Token Management
let csrfToken = "{{ session.get('csrf_token', '') }}";

// Fetch-Wrapper mit CSRF-Token
async function secureFetch(url, options = {}) {
    if (!options.headers) {
        options.headers = {};
    }
    
    // Füge CSRF-Token hinzu für state-changing Requests
    if (options.method && options.method !== 'GET') {
        options.headers['X-CSRF-Token'] = csrfToken;
    }
    
    return fetch(url, options);
}

// Ersetze alle fetch() Calls durch secureFetch()
// Beispiel:
async function serverAction(id, action) {
    const res = await secureFetch(`/api/server/${id}/${action}`, {method: 'POST'});
    const data = await res.json();
    showNotification(data.message);
    setTimeout(loadServers, 2000);
}
```

SCHRITT 11: Auto-Updater - SHA256-Integritätsprüfung
----------------------------------------------------

In AutoUpdater.download_update() (ca. Zeile 991-1020) NACH dem Download:

```python
def download_update(self, progress_callback=None):
    if not self.download_url:
        return {'error': 'Keine Download-URL verfügbar'}
    
    try:
        import tempfile
        temp_dir = os.path.join(tempfile.gettempdir(), 'GameServerManager_update')
        os.makedirs(temp_dir, exist_ok=True)
        temp_file = os.path.join(temp_dir, 'GameServerManager_new.exe')
        
        # Download
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
        
        # ===== NEU: SHA256-Integritätsprüfung =====
        
        # Hole SHA256-Hash vom Release (aus checksums.json oder Asset)
        checksums_url = self.download_url.replace('.exe', '.sha256')
        try:
            checksum_response = requests.get(checksums_url, timeout=10)
            if checksum_response.status_code == 200:
                expected_hash = checksum_response.text.strip()
                
                # Verifiziere
                if not verify_file_integrity(temp_file, expected_hash):
                    logger.error("🚨 SHA256-Mismatch! Update kompromittiert!")
                    os.remove(temp_file)
                    return {'error': 'Integritätsprüfung fehlgeschlagen - Update nicht vertrauenswürdig'}
                
                logger.info("✅ SHA256-Prüfung erfolgreich")
        except Exception as e:
            logger.warning(f"⚠️ Keine Checksumme verfügbar: {e}")
            # Optional: Bei fehlendem Checksum abbrechen für maximale Sicherheit
            # return {'error': 'Keine Checksumme verfügbar'}
        
        # ===== ENDE Integritätsprüfung =====
        
        return {'success': True, 'file': temp_file}
        
    except Exception as e:
        return {'error': f'Download fehlgeschlagen: {str(e)}'}
```

SCHRITT 12: Thread-Safety für Server-Liste
------------------------------------------

In GameServerManagerApp-Klasse ein Lock hinzufügen:

```python
class GameServerManagerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # ... bestehender Code ...
        
        # ===== NEU: Thread-Safety =====
        import threading
        self.server_instances_lock = threading.RLock()
        # ===== ENDE =====
        
        # ... Rest der __init__ ...
```

Dann ALLE Zugriffe auf self.server_instances mit Lock schützen:

```python
def start_server(self, server_id):
    with self.server_instances_lock:
        instance = self.server_instances.get(server_id)
        if instance:
            instance.start()
            self.select_server(server_id)

def stop_server(self, server_id):
    with self.server_instances_lock:
        instance = self.server_instances.get(server_id)
        if instance:
            instance.stop()
            self.select_server(server_id)

# Analog für alle anderen Methoden die server_instances verwenden
```

SCHRITT 13: App-Config - Tailscale-Modus hinzufügen
---------------------------------------------------

In ConfigManager - default app_config erweitern:

```python
self.app_config = {
    "password": "",
    "language": "de",
    "theme": "dark",
    "web": {
        "enabled": True,
        "port": 5001,
        "bind_mode": "local",  # NEU: "local" oder "tailscale"
        "allowed_tailscale_ips": []  # NEU: Zusätzliche IPs
    },
    # ... Rest ...
}
```

SCHRITT 14: Flask-Server Bind-Adresse anpassen
----------------------------------------------

In run_server() (ca. Zeile 5818-5820):

```python
def run_server():
    port = config_manager.app_config.get("web", {}).get("port", 5001)
    bind_mode = config_manager.app_config.get("web", {}).get("bind_mode", "local")
    
    if bind_mode == "local":
        # Nur localhost
        host = '127.0.0.1'
        logger.info(f"🌐 Web-Server: localhost-only (Port {port})")
    
    elif bind_mode == "tailscale":
        # Versuche Tailscale-IP zu ermitteln
        import socket
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        # Wenn Tailscale, nutze die 100.x.y.z IP
        # Alternativ: bind auf 0.0.0.0 und IP-Allowlist übernimmt die Filterung
        host = '0.0.0.0'
        logger.info(f"🌐 Web-Server: Tailscale-Modus (Port {port})")
    
    else:
        host = '127.0.0.1'
        logger.warning(f"⚠️ Unbekannter bind_mode: {bind_mode}, nutze localhost")
    
    flask_app.run(host=host, port=port, threaded=True, use_reloader=False)
```

SCHRITT 15: Dependencies installieren
-------------------------------------

Neue Abhängigkeiten in requirements.txt:

```
argon2-cffi>=23.1.0  # Für Argon2id Passwort-Hashing
```

Oder Fallback auf bcrypt:
```
bcrypt>=4.1.0
```

TESTING:
========

Nach der Integration sollten folgende Tests durchgeführt werden:

1. Pfad-Traversal Tests:
   - Versuche ../../../etc/passwd in Config-Read
   - Versuche absolute Pfade in Config-Save
   - Versuche Backup-Delete mit ../

2. Command Injection Tests:
   - Servername mit `; rm -rf /`
   - Mod-IDs mit Shell-Zeichen
   - Start-Parameter mit Injection-Versuchen

3. Zip-Slip Tests:
   - Erstelle ZIP mit ../../../evil.txt
   - Teste Restore mit präpariertem ZIP

4. Auth Tests:
   - Login mit falschem Passwort (Rate-Limit?)
   - Hash-Migration (altes SHA256 → Argon2id)
   - Session-Timeout

5. CSRF Tests:
   - API-Call ohne CSRF-Token
   - API-Call mit ungültigem Token

6. Tailscale Tests:
   - Zugriff von LAN-IP (sollte blockiert werden)
   - Zugriff von Tailscale-IP (sollte funktionieren)

BEKANNTE EINSCHRÄNKUNGEN:
========================

1. Frontend-JavaScript muss CSRF-Token bei allen POST/PUT/DELETE Requests senden
2. Alte Sessions werden ungültig (Benutzer müssen sich neu einloggen)
3. Alte Passwort-Hashes werden erst beim nächsten Login migriert
4. SHA256-Checksummen müssen in GitHub-Releases bereitgestellt werden

ROLLBACK-PLAN:
==============

Falls Probleme auftreten:
1. Sichere die neue Version als game_server_manager_secure.py
2. Restore die Original-Datei
3. Analysiere Fehler in gsm.log
4. Schrittweise einzelne Module aktivieren
"""
