# Game Server Manager Pro - Security Edition

## 🔒 Sicherheitsverbesserungen

Diese überarbeitete Version behebt **alle kritischen Sicherheitslücken** der ursprünglichen game_server_manager.py und implementiert moderne Security Best Practices.

## 📦 Inhalt

```
game-server-manager-security/
├── security_utils.py          # Core Security-Funktionen
├── web_security.py            # CSRF, Rate-Limiting, Session-Management
├── security_patches.py        # Sichere Ersatz-Implementierungen
├── auth_manager.py            # Auth-Management mit Hash-Migration
├── INTEGRATION_GUIDE.md       # Schritt-für-Schritt Integrations-Anleitung
├── SECURITY_SUMMARY.md        # Zusammenfassung aller Änderungen
├── requirements.txt           # Python-Dependencies
└── README.md                  # Diese Datei
```

## 🚀 Quick Start

### 1. Dependencies installieren

```bash
pip install -r requirements.txt
```

**Wichtig:** Wähle einen Passwort-Hasher:
- **Empfohlen:** `argon2-cffi` (höchste Sicherheit)
- **Fallback:** `bcrypt` (wenn Argon2 Probleme macht)
- **Letzter Fallback:** `scrypt` (Python Standard Library, keine Installation nötig)

### 2. Module kopieren

Kopiere alle `.py` Dateien in das Verzeichnis deiner `game_server_manager.py`:

```bash
cp security_utils.py web_security.py security_patches.py auth_manager.py /pfad/zu/gameservermanager/
```

### 3. Integration durchführen

Folge der **INTEGRATION_GUIDE.md** Schritt für Schritt:

```bash
# Lies zuerst die Anleitung
cat INTEGRATION_GUIDE.md

# Erstelle Backup der Original-Datei
cp game_server_manager.py game_server_manager.py.backup

# Führe dann die Integration durch
```

### 4. Konfiguration anpassen

Ergänze in deiner `app_config.json`:

```json
{
  "web": {
    "enabled": true,
    "port": 5001,
    "bind_mode": "local",           // NEU: "local" oder "tailscale"
    "allowed_tailscale_ips": []     // NEU: Zusätzliche erlaubte IPs
  }
}
```

### 5. Testing

Nach der Integration teste:

```bash
# Starte die Anwendung
python game_server_manager.py

# Teste Login (Passwort-Migration)
# Teste API-Endpunkte
# Prüfe Logs in gsm.log
```

## 🛡️ Behobene Sicherheitslücken

### ❌ VORHER (Kritische Probleme):

1. **Pfad-Traversal**: Client konnte mit `../../../` beliebige Dateien lesen/schreiben/löschen
2. **Command Injection**: `shell=True` mit User-Input ermöglichte Code-Ausführung
3. **Zip-Slip**: Manipulierte ZIP-Archive konnten Dateien außerhalb des Server-Ordners schreiben
4. **Schwache Passwörter**: SHA256 ohne Salt - anfällig für Rainbow Tables
5. **Keine Rate-Limits**: Brute-Force-Angriffe auf Login möglich
6. **Kein CSRF-Schutz**: Cross-Site Request Forgery möglich
7. **Offener Web-Zugang**: Von jedem im LAN/WAN erreichbar

### ✅ NACHHER (Sicher):

1. **Pfad-Sicherheit**: `safe_join()` validiert alle Pfade, Whitelist für Config-Dateien
2. **Kein shell=True**: Alle Subprocesses nutzen Argumentlisten, Input-Validierung
3. **Zip-Slip Protection**: `safe_extract()` validiert jeden Pfad vor Extraktion
4. **Argon2id Hashing**: State-of-the-art Passwort-Hashing mit automatischer Migration
5. **Rate-Limiting**: 5 Fehlversuche = 5 Minuten Lockout, pro IP UND Username
6. **CSRF-Tokens**: Alle state-changing Requests benötigen gültigen Token
7. **Tailscale-Only**: Optional nur über Tailscale-VPN erreichbar

## 📋 Feature-Übersicht

### Implementiert ✅

- ✅ Pfad-Traversal Prevention
- ✅ Command Injection Prevention
- ✅ Zip-Slip Protection
- ✅ Argon2id/bcrypt/scrypt Passwort-Hashing
- ✅ Automatische Hash-Migration
- ✅ CSRF-Schutz
- ✅ Rate-Limiting & Bruteforce-Protection
- ✅ Session-Management (12h TTL, Rolling Refresh)
- ✅ Security Headers (X-Frame-Options, CSP, etc.)
- ✅ Tailscale-Only Access Mode
- ✅ IP-Allowlist Middleware
- ✅ Thread-Safe Server-Zugriffe
- ✅ SHA256 Update-Integrität
- ✅ Konsistentes Error-Handling mit Error-Codes
- ✅ Security-Logging

### Optional / Empfohlen 🟡

- 🟡 HTTPS Setup (Self-Signed Cert oder Reverse Proxy)
- 🟡 Audit-Logging für alle Admin-Aktionen
- 🟡 2-Faktor-Authentifizierung (TOTP)
- 🟡 Separate API-Tokens für programmatischen Zugriff
- 🟡 Unit-Tests & Integration-Tests
- 🟡 Vollständige Modularisierung
- 🟡 Pydantic/Dataclass Schema-Validierung

## 📖 Dokumentation

### Detaillierte Guides:

1. **INTEGRATION_GUIDE.md** - Schritt-für-Schritt Integration (14 Schritte)
2. **SECURITY_SUMMARY.md** - Vollständige Übersicht aller Änderungen
3. **README.md** - Diese Datei (Quick Start & Übersicht)

### Code-Dokumentation:

Alle Module enthalten ausführliche Docstrings und Kommentare:

```python
def safe_join(base_dir: str, user_path: str) -> str:
    """
    Sicherer Pfad-Join der Pfad-Traversal verhindert.
    
    Args:
        base_dir: Das Basis-Verzeichnis (z.B. Server-Ordner)
        user_path: Der vom Benutzer bereitgestellte Pfad (relativ)
    
    Returns:
        str: Der sichere absolute Pfad
    
    Raises:
        PathTraversalError: Wenn Pfad-Traversal erkannt wurde
    """
```

## 🧪 Testing

### Manuelle Tests:

```python
# 1. Pfad-Traversal Test
# Versuche in API: ../../../etc/passwd

# 2. Command Injection Test
# Servername: `; rm -rf /`

# 3. Zip-Slip Test
# Erstelle ZIP mit ../../../evil.txt

# 4. Rate-Limit Test
# 10x falsches Passwort eingeben

# 5. CSRF Test
# API-Call ohne X-CSRF-Token Header
```

### Automatisierte Tests (optional):

```bash
# pytest installieren
pip install pytest pytest-flask

# Tests ausführen (wenn implementiert)
pytest tests/
```

## 🔧 Konfiguration

### Tailscale-Modus aktivieren:

```json
{
  "web": {
    "bind_mode": "tailscale",
    "allowed_tailscale_ips": ["100.64.1.23"]
  }
}
```

### HTTPS aktivieren (Reverse Proxy):

```nginx
# nginx config
server {
    listen 443 ssl;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header X-Forwarded-For $remote_addr;
    }
}
```

Dann in app_config.json:

```json
{
  "web": {
    "bind_mode": "local",  // localhost, nginx leitet weiter
    "behind_proxy": true
  }
}
```

## 📊 Logging

Alle Security-Events werden geloggt:

```bash
# Log-Datei location
~/.gameservermanager/gsm.log  # Linux/Mac
%APPDATA%\GameServerManager\gsm.log  # Windows

# Wichtige Log-Messages:
🚨 Pfad-Traversal Versuch
🔒 IP gesperrt (Rate-Limit)
🔄 Passwort-Hash migriert
⚠️ CSRF-Token ungültig
✅ Login erfolgreich
```

### Log-Level anpassen:

```python
# In game_server_manager.py
logging.basicConfig(level=logging.DEBUG)  # Für mehr Details
```

## 🐛 Troubleshooting

### Problem: "Module 'security_utils' not found"

**Lösung:** Alle `.py` Module müssen im gleichen Verzeichnis wie `game_server_manager.py` sein.

### Problem: "argon2-cffi installation failed"

**Lösung:** Nutze bcrypt als Fallback:
```bash
pip install bcrypt
```
Oder nutze scrypt (kein Install nötig, aber weniger sicher).

### Problem: "403 Forbidden" beim Zugriff

**Lösung:** Prüfe `bind_mode` in Config. Wenn `tailscale`, greife über Tailscale-IP zu, nicht über LAN-IP.

### Problem: "CSRF token missing"

**Lösung:** Frontend muss CSRF-Token bei POST/PUT/DELETE mitschicken (siehe INTEGRATION_GUIDE.md Schritt 10).

### Problem: "Session expired" nach kurzer Zeit

**Lösung:** Erhöhe SESSION_LIFETIME in Config oder aktiviere Rolling Refresh.

## 🔐 Best Practices

1. **Niemals** das Master-Passwort in Logs ausgeben
2. **Immer** HTTPS verwenden wenn über Internet erreichbar
3. **Regelmäßig** Logs auf SecurityErrors prüfen
4. **Aktiviere** Tailscale-Mode wenn remote Access benötigt
5. **Erstelle** regelmäßig Backups der Config-Dateien
6. **Teste** Updates zuerst in Entwicklungsumgebung
7. **Überwache** fehlgeschlagene Login-Versuche
8. **Verwende** starke Passwörter (min. 16 Zeichen)

## 📝 Changelog

### Version 2.0 Security Hardening (2024)

**Kritische Fixes:**
- Behebung aller Pfad-Traversal Lücken
- Entfernung von shell=True (Command Injection)
- Zip-Slip Protection implementiert
- Passwort-Hashing auf Argon2id upgraded

**Neue Features:**
- CSRF-Schutz
- Rate-Limiting
- Tailscale-Only Mode
- Session-Management
- Security-Logging
- Update-Integrität (SHA256)

**Verbesserungen:**
- Thread-Safety
- Konsistentes Error-Handling
- Input-Validierung
- Dokumentation

## 📄 Lizenz

Siehe Original-Lizenz von Game Server Manager Pro.

## 🤝 Contribution

Security-Verbesserungen und Bug-Reports sind willkommen!

Bei Sicherheitsproblemen bitte **NICHT** öffentlich melden, sondern:
1. Privat an Maintainer melden
2. Details und PoC bereitstellen
3. Auf Fix warten vor Public Disclosure

## ⚠️ Disclaimer

Diese Sicherheits-Überarbeitung verbessert die Sicherheit erheblich, garantiert aber keine 100% Sicherheit. Regelmäßige Updates und Security-Monitoring bleiben wichtig.

**Backup erstellen vor Produktiv-Einsatz!**

## 📞 Support

Bei Fragen zur Integration:
1. Konsultiere INTEGRATION_GUIDE.md
2. Prüfe SECURITY_SUMMARY.md
3. Schaue in gsm.log
4. Teste Module isoliert

---

**Viel Erfolg mit der sicheren Version! 🚀🔒**
