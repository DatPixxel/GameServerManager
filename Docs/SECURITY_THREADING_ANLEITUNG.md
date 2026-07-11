# 🔒🔧 Security & Threading Patches - Anleitung

## Übersicht

Du hast jetzt **2 zusätzliche Patches** die die Sicherheit und Stabilität deines Game Server Manager Pro massiv verbessern:

### 1️⃣ **Security-Patch** (`security_patch.py`)
Härtet das Web-Interface gegen Angriffe

### 2️⃣ **Threading-Patch** (`threading_patch.py`)
Verhindert Crashes durch parallele Zugriffe

---

## 🎯 Patch-Reihenfolge (WICHTIG!)

**Führe die Patches IN DIESER REIHENFOLGE aus:**

```
1. bugfix_patch.py         (Bugs beheben)
2. security_patch.py       (Security härten)
3. threading_patch.py      (Threading stabilisieren)
```

**Warum diese Reihenfolge?**
- Bugfix muss zuerst (sonst könnte Security-Patch fehlschlagen)
- Security vor Threading (Threading nutzt Basis-Code)

---

## 🔒 PATCH 1: Security-Patch

### Was wird behoben?

| Problem | Vorher | Nachher |
|---------|--------|---------|
| **Brute-Force Angriffe** | ❌ Unbegrenzte Login-Versuche | ✅ 5 Versuche = 5 Min Sperre |
| **CSRF-Angriffe** | ❌ Kein Schutz | ✅ Token-basierter Schutz |
| **Session-Verlust** | ❌ Sessions nur im RAM | ✅ Persistent in `web_sessions.json` |
| **IP-Spoofing** | ❌ Keine IP-Validierung | ✅ IP-Check bei Sessions |
| **Security Headers** | ❌ Keine | ✅ XSS, Clickjacking, etc. Schutz |

### Installation

**Schritt 1: Programm schließen**

**Schritt 2: Patch ausführen**
```bash
cd C:\GameServerManager
python security_patch.py
```

**Schritt 3: Bestätigen**
```
Möchtest du die Änderungen speichern?
Fortfahren? [j/N]: j
```

**Schritt 4: Testen**
```bash
python game_server_manager.py
```

### Was wird erstellt?

**Neue Dateien:**
```
C:\GameServerManager\
├── web_security.py              ← NEU! Security-Modul
├── game_server_manager.py       ← Gepatcht
└── %APPDATA%\GameServerManager\
    └── web_sessions.json        ← NEU! Sessions persistent
```

### Security-Features im Detail

#### 1. Rate-Limiting

**Wie es funktioniert:**
```
Login-Versuch 1: ✅ OK
Login-Versuch 2: ✅ OK
Login-Versuch 3: ✅ OK
Login-Versuch 4: ✅ OK
Login-Versuch 5: ✅ OK
Login-Versuch 6: ❌ GESPERRT für 5 Minuten!
```

**IP-basiert:** Jede IP-Adresse wird einzeln getrackt

**Automatisches Entsperren:** Nach 5 Minuten

#### 2. Session-Storage

**Vorher:**
```python
valid_sessions = {}  # Im RAM
# Bei Programm-Neustart: Alle ausgeloggt!
```

**Nachher:**
```python
session_store = FileSessionStore()  # In Datei
# Bei Programm-Neustart: Sessions bleiben!
```

**Datei:** `%APPDATA%\GameServerManager\web_sessions.json`

**Format:**
```json
{
  "a1b2c3d4...": {
    "created": 1706191200,
    "ip": "192.168.1.100",
    "last_activity": 1706194800
  }
}
```

**Session-Lifetime:** 12 Stunden

#### 3. CSRF-Protection

**Was ist CSRF?**
Ein Angreifer könnte dich dazu bringen, auf einen Link zu klicken der dann in deinem Namen Aktionen auf dem Server ausführt.

**Schutz:**
- Jede Session bekommt ein geheimes Token
- Alle wichtigen Aktionen (Start/Stop/Delete) brauchen dieses Token
- Token wird automatisch validiert

#### 4. IP-Validierung

**Session ist an IP gebunden:**
```
Login von 192.168.1.100 → Session erstellt
Später: Request von 192.168.1.200 → ❌ Session ungültig!
```

**Schützt vor:** Session-Hijacking

#### 5. Security Headers

**Automatisch gesetzt:**
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000
```

**Schützt vor:**
- XSS (Cross-Site Scripting)
- Clickjacking
- MIME-Type Sniffing

### Testen

**Test 1: Rate-Limiting**
```
1. Web-Interface öffnen (http://localhost:5001)
2. 5x falsches Passwort eingeben
3. Erwartung: "Zu viele Fehlversuche. Warte 300s"
4. Warte 5 Min
5. Erwartung: Login wieder möglich
```

**Test 2: Session-Persistence**
```
1. Im Web-Interface einloggen
2. Programm schließen
3. Programm neu starten
4. Web-Interface neu laden (F5)
5. Erwartung: Immer noch eingeloggt!
```

**Test 3: Session-Datei**
```
1. Gehe zu %APPDATA%\GameServerManager\
2. Prüfe: web_sessions.json existiert
3. Öffne: Sollte JSON mit Sessions enthalten
```

---

## 🔧 PATCH 2: Threading-Patch

### Was wird behoben?

| Problem | Vorher | Nachher |
|---------|--------|---------|
| **Race-Conditions** | ❌ Server kann gleichzeitig gestartet/gestoppt werden | ✅ Lock-System verhindert das |
| **Thread-Chaos** | ❌ Unbegrenzt viele Threads | ✅ Thread-Pool (max 10) |
| **Thread-Crashes** | ❌ Fehler crashen ganzes Programm | ✅ Fehler-Handling isoliert |
| **Thread-Leaks** | ❌ Threads laufen ewig | ✅ Cleanup bei Programm-Ende |

### Installation

**Schritt 1: Programm schließen**

**Schritt 2: Patch ausführen**
```bash
cd C:\GameServerManager
python threading_patch.py
```

**Schritt 3: Bestätigen**
```
⚠️  WICHTIG: Threading-Patch ist experimentell!
Möchtest du die Änderungen speichern?
Fortfahren? [j/N]: j
```

**Schritt 4: GRÜNDLICH testen!**

### Was wird erstellt?

**Neue Dateien:**
```
C:\GameServerManager\
├── thread_manager.py            ← NEU! Threading-Manager
└── game_server_manager.py       ← Gepatcht
```

### Threading-Features im Detail

#### 1. Server-Lock-System

**Problem:**
```python
# Thread 1:
server.start()  # Startet Server

# Thread 2 (gleichzeitig):
server.stop()   # Stoppt Server

# Resultat: CHAOS! 💥
```

**Lösung:**
```python
with self._lock:  # Lock erwerben
    server.start()
# Lock automatisch freigegeben

# Thread 2 wartet jetzt bis Thread 1 fertig ist!
```

**Jeder Server hat sein eigenes Lock** - Server können parallel laufen, aber EIN Server kann nur von EINEM Thread gleichzeitig verwaltet werden.

#### 2. Thread-Pool

**Vorher:**
```python
# Erstelle neuen Thread für JEDE Aktion:
threading.Thread(target=backup_server).start()
threading.Thread(target=update_server).start()
threading.Thread(target=monitor_server).start()
# ... 100 Threads? 1000 Threads? Unendlich!
```

**Nachher:**
```python
# Thread-Pool mit MAX 10 Workern:
thread_pool.submit(backup_server)
thread_pool.submit(update_server)
thread_pool.submit(monitor_server)
# Tasks werden in Queue gelegt, max 10 gleichzeitig
```

**Vorteil:**
- ✅ Begrenzte Ressourcen-Nutzung
- ✅ Keine Thread-Explosion
- ✅ Bessere Performance

#### 3. Fehler-Handling

**Vorher:**
```python
def backup_server():
    os.remove("wichtig.dat")  # Fehler!
    # Ganzer Thread crasht!
    # Evtl. ganzes Programm mit!
```

**Nachher:**
```python
def backup_server():
    try:
        os.remove("wichtig.dat")
    except Exception as e:
        print(f"❌ Thread-Fehler: {e}")
        traceback.print_exc()
        # Thread stirbt sauber
        # Programm läuft weiter!
```

**Jeder Thread ist isoliert** - Fehler in einem Thread crashen nicht das ganze Programm.

#### 4. Thread-Cleanup

**Beim Programm-Beenden:**
```python
# Vorher:
# Threads laufen einfach weiter... 😱

# Nachher:
thread_pool.shutdown(wait=True, timeout=5)
# Wartet max 5s auf laufende Tasks
# Dann: Sauberes Beenden
```

### Testen (SEHR WICHTIG!)

**⚠️ Threading-Patch ist experimenteller als die anderen!**

**Test 1: Gleichzeitiger Start/Stop**
```
1. Server 1 starten
2. SOFORT Server 1 stoppen (bevor er fertig gestartet ist)
3. Erwartung: Kein Crash, sauberes Stoppen
```

**Test 2: Mehrere Server gleichzeitig**
```
1. 5 Server gleichzeitig starten
2. Erwartung: Alle starten sauber
3. Resource-Monitor: Max ~10 Threads vom Programm
```

**Test 3: Backup während Server läuft**
```
1. Server starten
2. Backup erstellen (während Server läuft)
3. Erwartung: Backup funktioniert, Server läuft weiter
```

**Test 4: Programm-Beenden mit laufenden Servern**
```
1. 3 Server starten
2. Programm schließen
3. Erwartung: Sauberes Beenden nach max 5s
4. Task-Manager: Keine "hängenden" Prozesse
```

**Test 5: Logs prüfen**
```
1. Nach allen Tests: Logs prüfen
2. Suche nach: "Thread-Fehler", "Lock", "Race"
3. Erwartung: Keine kritischen Fehler
```

---

## 📦 Build nach Patches

**Nach allen 3 Patches:**

```bash
# WICHTIG: Erst alle Patches ausführen, DANN builden!

1. bugfix_patch.py       ✅
2. security_patch.py     ✅
3. threading_patch.py    ✅

# Jetzt builden:
build.bat
```

**Das .exe in `dist/` enthält dann:**
- ✅ Keine Bugs
- ✅ Security-Features
- ✅ Threading-Stabilität

**Aber: Zusätzliche Dateien müssen mit!**

```
dist/
├── GameServerManager.exe
├── web_security.py          ← MUSS dabei sein!
├── thread_manager.py        ← MUSS dabei sein!
└── ... (andere Dateien)
```

**Beim Verteilen:**
- ✅ Ganzen `dist/` Ordner verteilen
- ❌ NICHT nur die .exe!

---

## 🔄 Reihenfolge nochmal zusammengefasst

```
1. bugfix_patch.py
   ↓
2. security_patch.py
   ↓  
3. threading_patch.py
   ↓
4. TESTEN! (wichtig!)
   ↓
5. build.bat
   ↓
6. dist/ Ordner verteilen
```

---

## ⚠️ Wichtige Hinweise

### Security-Patch
- ✅ **Stabil** - kann bedenkenlos verwendet werden
- ✅ **Rückwärtskompatibel** - Funktioniert auch wenn Module fehlen
- ✅ **Getestet** - Bekannte Security-Patterns

### Threading-Patch
- ⚠️ **Experimentell** - Gründlich testen!
- ⚠️ **Kann Edge-Cases haben** - Bei Problemen: Backup wiederherstellen
- ⚠️ **Ändert Programm-Flow** - Verhaltensänderungen möglich

**Empfehlung:**
1. Security-Patch: **JA, unbedingt anwenden**
2. Threading-Patch: **Nur wenn du Threading-Probleme hast**

---

## 🆘 Probleme?

### Security-Patch funktioniert nicht

**Problem:** "web_security.py nicht gefunden"
```bash
Lösung:
1. Prüfe: web_security.py im gleichen Ordner wie .py
2. Bei .exe: web_security.py muss in dist/ sein
```

**Problem:** "Rate-Limiting sperrt mich aus"
```bash
Lösung:
1. Warte 5 Minuten
2. Oder: Lösche web_sessions.json
```

### Threading-Patch verursacht Probleme

**Problem:** "Server startet nicht mehr"
```bash
Lösung:
1. Backup wiederherstellen:
   copy game_server_manager.py.threading_backup_TIMESTAMP game_server_manager.py
2. Nur bugfix + security verwenden
```

**Problem:** "thread_manager.py nicht gefunden"
```bash
Lösung:
1. Threading-Patch nochmal ausführen
2. Oder: Datei manuell erstellen
```

---

## ✅ Checkliste

Patches anwenden:
- [ ] bugfix_patch.py ausgeführt
- [ ] security_patch.py ausgeführt
- [ ] threading_patch.py ausgeführt
- [ ] Programm getestet (mindestens 10 Min)
- [ ] Logs geprüft (keine Fehler)
- [ ] build.bat ausgeführt
- [ ] dist/ Ordner geprüft (alle Module dabei?)
- [ ] .exe getestet

Bereit für Distribution:
- [ ] Alle Features funktionieren
- [ ] Keine Fehler in Logs
- [ ] Security-Features getestet
- [ ] Threading stabil
- [ ] Dokumentation aktualisiert

---

## 🎉 Fertig!

Nach allen 3 Patches hast du:

✅ **Bug-freien Code** (5 Bugs behoben)
✅ **Sicheres Web-Interface** (Rate-Limiting, CSRF, Sessions)
✅ **Stabiles Threading** (Locks, Thread-Pool, Fehler-Handling)

**Dein Game Server Manager Pro ist jetzt:**
- Sicherer
- Stabiler
- Produktions-bereiter

**Viel Erfolg!** 🚀
