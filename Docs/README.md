# Game Server Manager Pro

Desktop-Anwendung (CustomTkinter) zum Verwalten dedizierter Game-Server unter Windows,
mit integriertem Flask-Web-Interface, RCON, Backups, Auto-Update und optionalem
WebRTC-Chat/Screenshare.

> **Hinweis zur Architektur (Stand: aktuell):** Die gesamte laufende Anwendung liegt in
> `game_server_manager.py`. Die früher hier dokumentierten separaten Module
> (`security_utils.py`, `web_security.py`, `auth_manager.py`, `thread_manager.py`,
> `platform_utils.py`, `security_patches.py`) sowie das `core/`-Paket wurden **entfernt** –
> sie waren ungenutzter Parallelcode, der von der App nie importiert wurde. Alle real
> aktiven Sicherheits- und Serverfunktionen sind direkt im Hauptmodul implementiert.

## Inhalt

```
game_server_manager.py      # Komplette Anwendung (GUI + Flask-Web + Logik + Templates)
run.py                      # Entry-Point (startet GameServerManagerApp)
selftest.py                 # Schnelltest der laufenden App
templates/                  # Web-Dashboard- und Chat-HTML
static/                     # Web-Dashboard- und Chat-JavaScript
build.bat / GameServerManager.spec / installer.iss   # Build & Installer
Docs/                       # Dokumentation (teils historisch – siehe unten)
```

## Quick Start

```bash
pip install -r requirements.txt
python run.py

# Schnelltest
python selftest.py
```

**Python:** Es wird Python **3.12+** benötigt (siehe `setup.py`).

## Tatsächlich implementierte Sicherheit

Die folgenden Maßnahmen sind im laufenden Code (`game_server_manager.py`) aktiv:

- **Pfad-Traversal-Schutz** – `is_safe_path` / `validate_config_path` / `validate_backup_path`
  (realpath-basiert, Whitelist für Config-Dateien).
- **Zip-Slip-Schutz** – `safe_extract_zip` prüft jeden Pfad vor der Extraktion.
- **Keine Command Injection** – alle Subprozesse laufen mit Argumentlisten (`shell=False`),
  kein `eval`/`exec`/`os.system`.
- **Web-Login** – PBKDF2-HMAC-SHA256 (300.000 Iterationen, 32-Byte-Salt, `compare_digest`),
  automatische Migration von Legacy-SHA-256-Hashes.
- **Geheimnisse at-rest verschlüsselt** – Server-Passwörter (`server_password`,
  `admin_password`, `rcon_password`) werden in `servers.json` via Windows-DPAPI verschlüsselt
  (`enc:v1:`-Format); bestehender Klartext wird beim nächsten Speichern automatisch migriert.
- **Keine Geheimnis-Leaks über die API** – `/api/server/<id>/details` filtert die o.g. Felder heraus.
- **Optionales Tailscale-Gating** – Chat-/Signaling-Routen können auf das Tailscale-Netz
  (`100.64.0.0/10`) beschränkt werden.

### Bekannte offene Punkte (ehrlich)

Diese Punkte sind **noch nicht** umgesetzt und sollten bei Betrieb über vertrauenswürdige
Netze hinaus beachtet werden:

- Kein CSRF-Schutz und kein Login-Rate-Limiting auf den Web-Routen.
- Session-Cookies ohne `Secure`/`HttpOnly`/`SameSite`; kein TLS (nur HTTP).
- Der Flask-Server bindet auf `0.0.0.0` – im gesamten LAN/Tailscale erreichbar.
- Argon2id ist **nicht** in Betrieb (nur PBKDF2); frühere Doku, die Argon2 bewarb, war
  irreführend und bezog sich auf die inzwischen entfernten Module.

## Konfiguration

Config und Daten liegen unter:

```
%APPDATA%\GameServerManager\   (Windows)
~/.gameservermanager/          (Linux/Mac)
```

## Historische Dokumentation

Die übrigen Dateien in `Docs/` (z. B. `INTEGRATION_GUIDE.md`, `SECURITY_SUMMARY.md`,
`SECURITY_THREADING_ANLEITUNG.md`, `MANUELLES_REFACTORING.md`, `MODERNISIERUNG_KOMPLETT.md`)
beschreiben ein **abgebrochenes Modularisierungs-/Integrationsvorhaben** und beziehen sich
großteils auf die inzwischen entfernten Module. Sie sind als **historisch/veraltet** zu
betrachten und spiegeln nicht den aktuellen Code wider.
