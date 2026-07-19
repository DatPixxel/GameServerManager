"""App-weite Konstanten (Skalare).

Aus game_server_manager.py ausgelagert, damit gsm-Module sie ohne Zirkelimport nutzen.
"""

VERSION = "3.52"
APP_NAME = "Game Server Manager Pro"

# Netzwerk / SSL
SSL_VERIFY = True

# GitHub für Auto-Updates
GITHUB_REPO = "DatPixxel/GameServerManager"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

# Web-Interface
WEB_PORT = 5001

# Conan Exiles Workshop
CONAN_WORKSHOP_APP_ID = "440900"
CONAN_UPLOAD_MAX_BYTES = 8 * 1024 * 1024 * 1024

# Sensible Felder in Server-Configs (Klartext-Geheimnisse)
SENSITIVE_SERVER_KEYS = ("server_password", "admin_password", "rcon_password")
