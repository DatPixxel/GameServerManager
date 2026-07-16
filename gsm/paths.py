"""Zentrale Pfad-Verwaltung.

WICHTIG: `PATHS` ist geteilter, veränderlicher Laufzeit-Zustand. Es darf NIE über
`PATHS = ...` neu gebunden werden (sonst driften Importe auseinander – genau daran
scheiterte das frühere core/-Refactoring). Änderungen laufen über `set_base_dir()`,
das das bestehende Dict **in place** aktualisiert. Dadurch ist `from gsm.paths import PATHS`
in allen Modulen sicher.
"""

import os

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
