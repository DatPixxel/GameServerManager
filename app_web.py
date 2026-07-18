"""Startet die moderne Oberfläche als natives Desktop-Fenster (pywebview).

Nutzt den headless Kern (gsm.core.GsmCore) + den vorhandenen Flask-Server und
zeigt die neue Web-Oberfläche in einem eigenen Programmfenster – ohne Browser
und ohne die alte CustomTkinter-GUI.

Voraussetzung: Der Installationsordner muss einmal eingerichtet sein (dafür
ggf. einmalig das klassische Tool `run.py` starten). pywebview installieren mit:
    pip install pywebview
"""

import sys
import time
import socket


def _port_open(port, host="127.0.0.1"):
    with socket.socket() as s:
        s.settimeout(0.3)
        try:
            s.connect((host, port))
            return True
        except OSError:
            return False


def main():
    from gsm.paths import load_base_dir, set_base_dir, ensure_directories

    base = load_base_dir()
    if not base:
        print("❌ Kein Installationsordner konfiguriert.")
        print("   Bitte zuerst das Desktop-Tool starten und einrichten:  python run.py")
        return 1

    set_base_dir(base)
    ensure_directories()

    from gsm.core import GsmCore
    from gsm.web.server import start_web_server

    print("🚀 Starte Backend …")
    core = GsmCore()
    port = core.config_manager.app_config.get("web", {}).get("port", 5001)
    start_web_server(core, core.config_manager)

    # Auf den Flask-Server warten (max. ~5 s)
    for _ in range(50):
        if _port_open(port):
            break
        time.sleep(0.1)

    url = f"http://localhost:{port}"

    try:
        import webview
    except ImportError:
        print("⚠️  pywebview ist nicht installiert  ->  für das native Fenster:  pip install pywebview")
        print(f"   Öffne die Oberfläche stattdessen im Browser:  {url}")
        import webbrowser
        webbrowser.open(url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            return 0

    print(f"🖥️  Öffne Fenster:  {url}")
    webview.create_window(
        "Game Server Manager",
        url,
        width=1280, height=820, min_size=(1000, 640),
    )
    webview.start()
    return 0


if __name__ == "__main__":
    sys.exit(main())
