#!/usr/bin/env python3
"""
Game Server Manager Pro - Entry Point

Standard:  startet die moderne Oberfläche (Web-UI im nativen Fenster).
Erststart: ist noch kein Installationsordner eingerichtet, öffnet sich einmalig
           die klassische Einrichtung.
--classic: erzwingt die alte CustomTkinter-Oberfläche.
"""

import sys
import os

# Konsolen-Ausgabe robust machen (Windows-cp1252 kann keine Emojis -> sonst Crash)
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Aktuelles Verzeichnis in den Importpfad
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _start_classic():
    """Klassische CustomTkinter-Oberfläche (inkl. Erst-Einrichtungs-Wizard)."""
    from game_server_manager import GameServerManagerApp
    app = GameServerManagerApp()
    app.mainloop()


def main():
    # Ausdrücklich die alte Oberfläche gewünscht?
    if "--classic" in sys.argv:
        return _start_classic()

    # Ist bereits ein Installationsordner eingerichtet?
    from gsm.paths import load_base_dir
    base = load_base_dir()

    if base and os.path.exists(base):
        # Eingerichtet -> moderne Oberfläche
        import app_web
        return app_web.main()

    # Noch nicht eingerichtet -> klassische Erst-Einrichtung (einmalig).
    print("ℹ️  Erst-Einrichtung: die klassische Oberfläche wird einmalig geöffnet.")
    print("    Danach startet 'python run.py' automatisch die moderne Oberfläche.")
    return _start_classic()


if __name__ == "__main__":
    sys.exit(main() or 0)
