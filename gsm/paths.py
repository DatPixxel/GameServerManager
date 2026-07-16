"""Zentrale Pfad-Verwaltung.

WICHTIG: `PATHS` ist geteilter, veränderlicher Laufzeit-Zustand. Es darf NIE über
`PATHS = ...` neu gebunden werden (sonst driften Importe auseinander – genau daran
scheiterte das frühere core/-Refactoring). Änderungen laufen über `set_base_dir()`,
das das bestehende Dict **in place** aktualisiert. Dadurch ist `from gsm.paths import PATHS`
in allen Modulen sicher.
"""

import os
import sys
import json

# ==================== PROGRAMM- / CONFIG-VERZEICHNISSE ====================
# Läuft als .exe (PyInstaller) oder als .py-Script
if getattr(sys, 'frozen', False):
    PROGRAM_DIR = os.path.dirname(sys.executable)
else:
    PROGRAM_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Config-Verzeichnis in AppData (Windows) oder Home (Linux/Mac)
if os.name == 'nt':
    CONFIG_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'GameServerManager')
else:
    CONFIG_DIR = os.path.join(os.path.expanduser('~'), '.gameservermanager')

os.makedirs(CONFIG_DIR, exist_ok=True)
LAUNCHER_CONFIG_FILE = os.path.join(CONFIG_DIR, "gsm_launcher.json")


def load_base_dir():
    """Lädt den Basis-Pfad aus der Launcher-Config"""
    print(f"🔍 Suche Config: {LAUNCHER_CONFIG_FILE}")
    if os.path.exists(LAUNCHER_CONFIG_FILE):
        try:
            with open(LAUNCHER_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                base_dir = config.get("base_dir", "")
                print(f"✅ Gefunden: {base_dir}")
                return base_dir
        except Exception as e:
            print(f"❌ Fehler beim Laden: {e}")
    else:
        print("ℹ️ Keine Config gefunden - erster Start")
    return ""


def save_base_dir(path):
    """Speichert den Basis-Pfad in der Launcher-Config"""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(LAUNCHER_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump({"base_dir": path}, f, indent=4)
        print(f"✅ Config gespeichert: {LAUNCHER_CONFIG_FILE}")
        return True
    except Exception as e:
        print(f"❌ Fehler beim Speichern: {e}")
        return False


# Geteilter Laufzeit-Zustand – Objekt-Identität bleibt stabil.
PATHS = {}


def get_paths(base_dir):
    """Gibt alle Pfade basierend auf dem Basis-Verzeichnis zurück"""
    return {
        "base": base_dir,
        "config": os.path.join(base_dir, "config"),
        "servers": os.path.join(base_dir, "servers"),
        "backups": os.path.join(base_dir, "backups"),
        "logs": os.path.join(base_dir, "logs"),
        "steamcmd": os.path.join(base_dir, "steamcmd"),
        "app_config": os.path.join(base_dir, "config", "app_config.json"),
        "servers_config": os.path.join(base_dir, "config", "servers.json"),
        "users_config": os.path.join(base_dir, "config", "users.json")
    }


def set_base_dir(base_dir):
    """Setzt das Basis-Verzeichnis und aktualisiert PATHS in place."""
    PATHS.clear()
    PATHS.update(get_paths(base_dir))
    return PATHS


def ensure_directories():
    """Erstellt alle benötigten Verzeichnisse"""
    if PATHS:
        for key in ["base", "config", "servers", "backups", "logs", "steamcmd"]:
            if key in PATHS:
                os.makedirs(PATHS[key], exist_ok=True)
