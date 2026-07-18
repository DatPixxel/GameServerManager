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

# Konsolen-Ausgabe robust machen (Windows-cp1252 kann keine Emojis)
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def _log(msg):
    """Ausgabe, die niemals crasht (auch ohne/mit exotischer Konsole)."""
    try:
        print(msg)
    except Exception:
        pass


def _port_open(port, host="127.0.0.1"):
    with socket.socket() as s:
        s.settimeout(0.3)
        try:
            s.connect((host, port))
            return True
        except OSError:
            return False


def _serve_forever(url):
    """Nur den Webserver laufen lassen (für Server ohne Desktop)."""
    _log(f"🌐 Web-Oberfläche läuft:  {url}")
    _log("   Im selben Netz erreichbar unter  http://<server-ip>:<port>")
    _log("   Zum Beenden: Strg+C")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        return 0


def main(window=True):
    # Server-/Headless-Modus: nur ausliefern, kein Fenster
    if "--serve" in sys.argv or "--headless" in sys.argv or "--no-window" in sys.argv:
        window = False

    from gsm.paths import load_base_dir, set_base_dir, ensure_directories

    base = load_base_dir()
    if not base:
        _log("❌ Kein Installationsordner konfiguriert.")
        _log("   Bitte zuerst einrichten:  python run.py  (bzw. python run.py --classic)")
        return 1

    set_base_dir(base)
    ensure_directories()

    from gsm.core import GsmCore
    from gsm.web.server import start_web_server

    _log("🚀 Starte Backend …")
    core = GsmCore()
    port = core.config_manager.app_config.get("web", {}).get("port", 5001)
    start_web_server(core, core.config_manager)

    # Auf den Flask-Server warten (max. ~5 s)
    for _ in range(50):
        if _port_open(port):
            break
        time.sleep(0.1)

    url = f"http://localhost:{port}"

    # Server-Modus: nur laufen lassen
    if not window:
        return _serve_forever(url)

    # Desktop-Modus: natives Fenster (pywebview)
    try:
        import webview
    except ImportError:
        _log("⚠️  pywebview ist nicht installiert  ->  für das native Fenster:  pip install pywebview")
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            pass
        return _serve_forever(url)

    _log(f"🖥️  Öffne Fenster:  {url}")
    webview.create_window(
        "Game Server Manager",
        url,
        width=1280, height=820, min_size=(1000, 640),
    )
    webview.start()
    return 0


if __name__ == "__main__":
    sys.exit(main())
