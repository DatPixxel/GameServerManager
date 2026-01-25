# 🔧 Bug-Fix Patch - Anleitung

## Was behebt dieser Patch?

Dieser Patch behebt **5 kritische Bugs** im Game Server Manager Pro:

### Bug 1 & 2: `AttributeError` in Backup-Funktionen
**Problem:** `restore_backup()` und `delete_backup()` verwenden `self.id` statt `self.server_id`
```python
# VORHER (fehlerhaft):
validate_backup_path(PATHS["backups"], self.id, backup_path)

# NACHHER (korrekt):
validate_backup_path(PATHS["backups"], self.server_id, backup_path)
```
**Auswirkung:** Backup-Restore und Backup-Löschen führten zu `AttributeError: 'ServerInstance' object has no attribute 'id'`

---

### Bug 3: Falsche Parameter bei Server-Import
**Problem:** `import_server_config()` erstellt `ServerInstance` mit falschen Parametern
```python
# VORHER (fehlerhaft):
ServerInstance(
    new_id,
    server_config,
    game_info,                        # ← FALSCH!
    self.config_manager.get_text,     # ← FALSCH!
    discord_notifier=self.discord_notifier
)

# NACHHER (korrekt):
ServerInstance(
    new_id,
    server_config,
    self.config_manager,              # ← RICHTIG!
    discord_notifier=self.discord_notifier
)
```
**Auswirkung:** Server-Import funktionierte nicht, führte zu TypeError

---

### Bug 4: Nicht existierendes Widget
**Problem:** `save_settings()` versucht auf `self.web_label` zuzugreifen, das nie als Attribut gespeichert wurde
```python
# VORHER (fehlerhaft):
self.web_label.configure(text=f"🌐 localhost:{new_port}")

# NACHHER (auskommentiert):
# TODO: web_label als Attribut speichern oder entfernen
# self.web_label.configure(text=f"🌐 localhost:{new_port}")
```
**Auswirkung:** Einstellungen speichern führte zu `AttributeError: 'GameServerManagerApp' object has no attribute 'web_label'`

---

### Bug 5: Dashboard Auto-Refresh funktioniert nicht
**Problem:** `_auto_refresh_dashboard()` prüft falsches Attribut
```python
# VORHER (fehlerhaft):
if children and hasattr(self, 'auto_refresh_label'):

# NACHHER (korrekt):
if children and hasattr(self, '_dashboard_refresh_id'):
```
**Auswirkung:** Dashboard aktualisierte sich nicht automatisch

---

## Installation & Nutzung

### Schritt 1: Patch-Script herunterladen

Stelle sicher, dass `bugfix_patch.py` im **gleichen Ordner** wie `game_server_manager.py` liegt:

```
C:\GameServerManager\
├── game_server_manager.py
├── bugfix_patch.py          ← Hier!
└── ...
```

### Schritt 2: Programm schließen

**WICHTIG:** Schließe das Game Server Manager Programm komplett!

### Schritt 3: Patch ausführen

**Windows:**
```cmd
cd C:\GameServerManager
python bugfix_patch.py
```

**Linux:**
```bash
cd /opt/gameservermanager
python3 bugfix_patch.py
```

### Schritt 4: Bestätigung

Das Script zeigt dir:
1. ✅ Welche Bugs gefunden wurden
2. 📦 Wo das Backup gespeichert wird
3. ❓ Bestätigung vor dem Ändern

**Beispiel-Output:**
```
============================================================
     Game Server Manager Pro - Bug Fix Patch              
============================================================

ℹ️  Ziel-Datei: C:\GameServerManager\game_server_manager.py

============================================================
              Schritt 1: Backup erstellen                  
============================================================

✅ Backup erstellt: game_server_manager.py.backup_20260125_153000

============================================================
           Schritt 2: Bug-Fixes anwenden                   
============================================================

ℹ️  Bug Fix 1: restore_backup (Zeile 2162)
✅   Zeile 2162: self.id → self.server_id

ℹ️  Bug Fix 2: delete_backup (Zeile 2193)
✅   Zeile 2193: self.id → self.server_id

ℹ️  Bug Fix 3: import_server_config (Zeilen 7259-7265)
✅   Zeilen 7259-7265: Parameter korrigiert
ℹ️     Entfernt: game_info, self.config_manager.get_text
ℹ️     Korrigiert: self.config_manager als 3. Parameter

ℹ️  Bug Fix 4: save_settings (Zeile 7578)
✅   Zeile 7578: self.web_label auskommentiert
ℹ️     Grund: web_label wird nie als self.web_label gespeichert

ℹ️  Bug Fix 5: _auto_refresh_dashboard (Zeile 4798)
✅   Zeile 4798: auto_refresh_label → _dashboard_refresh_id

============================================================
              Schritt 3: Bestätigung                       
============================================================

ℹ️  Gefundene Fixes: 5/5

⚠️  Möchtest du die Änderungen speichern?
⚠️  Backup: game_server_manager.py.backup_20260125_153000
Fortfahren? [j/N]: j

============================================================
           Schritt 4: Änderungen speichern                 
============================================================

✅ Datei gespeichert: game_server_manager.py
✅ 5 Bug-Fixes erfolgreich angewendet!

============================================================
                  ✅ Patch erfolgreich!                    
============================================================

✅ Folgende Bugs wurden behoben:
ℹ️    1. restore_backup: self.id → self.server_id
ℹ️    2. delete_backup: self.id → self.server_id
ℹ️    3. import_server_config: ServerInstance Parameter korrigiert
ℹ️    4. save_settings: self.web_label auskommentiert
ℹ️    5. _auto_refresh_dashboard: Attribut-Name korrigiert

✅ Backup gespeichert: game_server_manager.py.backup_20260125_153000
ℹ️  Falls Probleme auftreten, kannst du das Backup wiederherstellen!

🎉 Programm ist jetzt stabiler!
```

### Schritt 5: Programm testen

Starte das Programm und teste ob alles funktioniert:

```cmd
python game_server_manager.py
```

**Teste speziell:**
- ✅ Backup erstellen & wiederherstellen
- ✅ Backup löschen
- ✅ Server importieren (falls du Import-Funktion nutzt)
- ✅ Einstellungen speichern (Sprache, Theme, Port ändern)
- ✅ Dashboard Auto-Refresh (lass Dashboard 10 Sekunden offen)

---

## Falls etwas schief geht

### Backup wiederherstellen

**Windows:**
```cmd
copy game_server_manager.py.backup_TIMESTAMP game_server_manager.py
```

**Linux:**
```bash
cp game_server_manager.py.backup_TIMESTAMP game_server_manager.py
```

Ersetze `TIMESTAMP` mit dem tatsächlichen Timestamp (z.B. `20260125_153000`)

---

## Technische Details

### Geänderte Zeilen

| Zeile | Vorher | Nachher | Bug |
|-------|--------|---------|-----|
| 2162 | `self.id` | `self.server_id` | AttributeError |
| 2193 | `self.id` | `self.server_id` | AttributeError |
| 7259-7265 | 4 Parameter | 3 Parameter | TypeError |
| 7578 | Code aktiv | Auskommentiert | AttributeError |
| 4798 | `'auto_refresh_label'` | `'_dashboard_refresh_id'` | Logik-Fehler |

### Backup-Datei

Format: `game_server_manager.py.backup_YYYYMMDD_HHMMSS`

Beispiel: `game_server_manager.py.backup_20260125_153000`

Die Backup-Datei ist eine **exakte Kopie** vor dem Patch und kann jederzeit wiederhergestellt werden.

---

## FAQ

**Q: Muss ich das Programm neu installieren?**  
A: Nein! Der Patch ändert nur die Python-Datei, keine Installation nötig.

**Q: Verliere ich meine Server-Konfigurationen?**  
A: Nein! Der Patch ändert nur Code, keine Config-Dateien.

**Q: Kann ich den Patch mehrmals ausführen?**  
A: Ja! Das Script erkennt bereits gepatchte Stellen und überspringt sie.

**Q: Was wenn der Patch einen Fehler meldet?**  
A: Das Backup bleibt erhalten. Stelle es wieder her und melde das Problem.

**Q: Funktioniert der Patch auf Linux?**  
A: Ja! Verwende `python3` statt `python`.

**Q: Brauche ich Python-Kenntnisse?**  
A: Nein! Einfach Script ausführen und Anweisungen folgen.

**Q: Was wenn ich den Code selbst geändert habe?**  
A: Der Patch erkennt das und warnt dich. Prüfe die Zeilen manuell.

---

## Zusammenfassung

✅ **5 kritische Bugs behoben**  
✅ **Automatisches Backup**  
✅ **Einfache Anwendung**  
✅ **Sicher & reversibel**  
✅ **Windows & Linux kompatibel**  

**Nach dem Patch:**
- Backup-Funktionen funktionieren korrekt
- Server-Import funktioniert
- Einstellungen speichern funktioniert
- Dashboard aktualisiert sich automatisch
- Keine AttributeErrors mehr

---

## Support

Falls Probleme auftreten:
1. Prüfe ob Backup existiert
2. Schaue in die Logs
3. Erstelle ein GitHub Issue mit dem Error-Log

**Viel Erfolg!** 🚀
