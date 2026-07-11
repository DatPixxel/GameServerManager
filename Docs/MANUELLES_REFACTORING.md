# 🏗️ Game Server Manager Pro - MANUELLES Refactoring

**Schritt-für-Schritt Anleitung zum sicheren Code-Strukturieren**

---

## ⚠️ WICHTIG VORHER:

### **1. Backup erstellen**
```cmd
cd C:\Users\Dat Pixxel\GameServerManager_v2
copy game_server_manager.py game_server_manager.py.MANUAL_BACKUP
```

### **2. Git nutzen (EMPFOHLEN!)**
```cmd
git init
git add .
git commit -m "Vor manuellem Refactoring"
```

Dann kannst du jederzeit zurück mit: `git reset --hard`

---

## 🎯 ZIEL-STRUKTUR

```
GameServerManager_v2/
├── game_server_manager.py       ← Haupt-GUI (wird kleiner)
│
├── core/
│   ├── __init__.py
│   ├── constants.py             ← SUPPORTED_GAMES, VERSION, etc.
│   ├── config_manager.py        ← ConfigManager Klasse
│   └── server_instance.py       ← ServerInstance Klasse
│
├── web/
│   ├── __init__.py
│   └── web_security.py          ← (schon da vom security_patch)
│
└── utils/
    └── __init__.py
```

---

## 📋 PHASE 1: ORDNER ERSTELLEN

### **Schritt 1.1: Ordner-Struktur**

```cmd
cd C:\Users\Dat Pixxel\GameServerManager_v2

mkdir core
mkdir utils

# Falls web/ nicht existiert:
mkdir web
```

### **Schritt 1.2: __init__.py Dateien**

**Erstelle `core\__init__.py`:**
```cmd
echo # Core modules > core\__init__.py
```

**Erstelle `utils\__init__.py`:**
```cmd
echo # Utility modules > utils\__init__.py
```

**Erstelle `web\__init__.py`:**
```cmd
echo # Web modules > web\__init__.py
```

---

## 📋 PHASE 2: CONSTANTS.PY ERSTELLEN

### **Schritt 2.1: Datei erstellen**

Öffne **Notepad** oder **VS Code**:

```cmd
notepad core\constants.py
```

### **Schritt 2.2: Inhalt kopieren**

**Kopiere DIESEN CODE rein:**

```python
"""
Konstanten für Game Server Manager Pro
"""

VERSION = "3.14"
APP_NAME = "Game Server Manager Pro"

# GitHub für Auto-Updates
GITHUB_REPO = "DatPixxel/GameServerManager"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

# Supported Games
SUPPORTED_GAMES = {
    "ARK: Survival Ascended": {
        "name": "ARK: Survival Ascended",
        "app_id": "2430930",
        "default_port": 7777,
        "default_query_port": 27015,
        "default_rcon_port": 27020,
        "requires_steamcmd": True,
        "install_dir": "ARK Survival Ascended Dedicated Server",
        "executable": "ArkAscendedServer.exe",
        "icon": "🦖",
        "maps": [
            {"name": "The Island", "param": "TheIsland_WP"},
            {"name": "Scorched Earth", "param": "ScorchedEarth_WP"},
            {"name": "Aberration", "param": "Aberration_WP"},
            {"name": "Extinction", "param": "Extinction_WP"},
            {"name": "The Center", "param": "TheCenter_WP"},
            {"name": "Ragnarok", "param": "Ragnarok_WP"},
            {"name": "Valguero", "param": "Valguero_WP"},
            {"name": "Genesis Part 1", "param": "Genesis_WP"},
            {"name": "Genesis Part 2", "param": "Gen2_WP"},
            {"name": "Crystal Isles", "param": "CrystalIsles_WP"},
            {"name": "Lost Island", "param": "LostIsland_WP"},
            {"name": "Fjordur", "param": "Fjordur_WP"}
        ],
        "supports_mods": True,
        "supports_rcon": True,
        "config_files": [
            "ShooterGame/Saved/Config/WindowsServer/GameUserSettings.ini",
            "ShooterGame/Saved/Config/WindowsServer/Game.ini"
        ]
    },
    "Rust": {
        "name": "Rust",
        "app_id": "258550",
        "default_port": 28015,
        "default_query_port": 28016,
        "default_rcon_port": 28016,
        "requires_steamcmd": True,
        "install_dir": "RustDedicatedServer",
        "executable": "RustDedicated.exe",
        "icon": "🔧",
        "supports_mods": True,
        "supports_rcon": True,
        "config_files": [
            "server/my_server_identity/cfg/server.cfg"
        ]
    },
    "Minecraft Java (Forge)": {
        "name": "Minecraft Java (Forge)",
        "app_id": None,
        "default_port": 25565,
        "default_query_port": 25565,
        "default_rcon_port": 25575,
        "requires_steamcmd": False,
        "install_dir": "MinecraftServer",
        "executable": "forge-server.jar",
        "icon": "⛏️",
        "supports_mods": True,
        "supports_rcon": True,
        "forge_versions": [
            {"version": "1.21.1", "forge": "52.0.29"},
            {"version": "1.20.1", "forge": "47.3.0"},
            {"version": "1.19.4", "forge": "45.2.0"},
            {"version": "1.19.2", "forge": "43.4.0"},
            {"version": "1.18.2", "forge": "40.2.21"},
            {"version": "1.18.1", "forge": "39.1.2"},
            {"version": "1.17.1", "forge": "37.1.1"},
            {"version": "1.16.5", "forge": "36.2.42"},
            {"version": "1.15.2", "forge": "31.2.57"},
            {"version": "1.14.4", "forge": "28.2.26"},
            {"version": "1.13.2", "forge": "25.0.223"},
            {"version": "1.12.2", "forge": "14.23.5.2859"}
        ],
        "config_files": [
            "server.properties",
            "eula.txt"
        ]
    },
    "Minecraft Bedrock": {
        "name": "Minecraft Bedrock",
        "app_id": None,
        "default_port": 19132,
        "default_query_port": 19132,
        "requires_steamcmd": False,
        "install_dir": "BedrockServer",
        "executable": "bedrock_server.exe",
        "icon": "🧱",
        "supports_mods": False,
        "supports_rcon": False,
        "config_files": [
            "server.properties"
        ]
    },
    "Valheim": {
        "name": "Valheim",
        "app_id": "896660",
        "default_port": 2456,
        "default_query_port": 2457,
        "requires_steamcmd": True,
        "install_dir": "ValheimServer",
        "executable": "valheim_server.exe",
        "icon": "⚔️",
        "supports_mods": True,
        "config_files": []
    },
    "Palworld": {
        "name": "Palworld",
        "app_id": "2394010",
        "default_port": 8211,
        "default_query_port": 27015,
        "default_rcon_port": 25575,
        "requires_steamcmd": True,
        "install_dir": "PalworldServer",
        "executable": "PalServer.exe",
        "icon": "🐾",
        "supports_mods": True,
        "supports_rcon": True,
        "config_files": [
            "Pal/Saved/Config/WindowsServer/PalWorldSettings.ini"
        ]
    },
    "7 Days to Die": {
        "name": "7 Days to Die",
        "app_id": "294420",
        "default_port": 26900,
        "default_query_port": 26900,
        "requires_steamcmd": True,
        "install_dir": "7DaysToDieServer",
        "executable": "7DaysToDieServer.exe",
        "icon": "🧟",
        "supports_mods": True,
        "config_files": [
            "serverconfig.xml"
        ]
    },
    "Project Zomboid": {
        "name": "Project Zomboid",
        "app_id": "380870",
        "default_port": 16261,
        "default_query_port": 16262,
        "requires_steamcmd": True,
        "install_dir": "ProjectZomboidServer",
        "executable": "ProjectZomboid64.exe",
        "icon": "🧟‍♂️",
        "supports_mods": True,
        "config_files": []
    },
    "Terraria": {
        "name": "Terraria",
        "app_id": "105600",
        "default_port": 7777,
        "default_query_port": 7777,
        "requires_steamcmd": True,
        "install_dir": "TerrariaServer",
        "executable": "TerrariaServer.exe",
        "icon": "🌍",
        "supports_mods": True,
        "config_files": [
            "serverconfig.txt"
        ]
    },
    "Counter-Strike 2": {
        "name": "Counter-Strike 2",
        "app_id": "730",
        "default_port": 27015,
        "default_query_port": 27015,
        "default_rcon_port": 27015,
        "requires_steamcmd": True,
        "install_dir": "CS2Server",
        "executable": "cs2.exe",
        "icon": "🔫",
        "supports_mods": True,
        "supports_rcon": True,
        "config_files": [
            "game/csgo/cfg/server.cfg"
        ]
    },
    "Don't Starve Together": {
        "name": "Don't Starve Together",
        "app_id": "343050",
        "default_port": 10999,
        "default_query_port": 10999,
        "requires_steamcmd": True,
        "install_dir": "DSTServer",
        "executable": "dontstarve_dedicated_server_nullrenderer_x64.exe",
        "icon": "🔥",
        "supports_mods": True,
        "config_files": []
    },
    "V Rising": {
        "name": "V Rising",
        "app_id": "1829350",
        "default_port": 9876,
        "default_query_port": 9877,
        "requires_steamcmd": True,
        "install_dir": "VRisingServer",
        "executable": "VRisingServer.exe",
        "icon": "🧛",
        "supports_mods": True,
        "config_files": [
            "Settings/ServerHostSettings.json",
            "Settings/ServerGameSettings.json"
        ]
    },
    "Conan Exiles": {
        "name": "Conan Exiles",
        "app_id": "443030",
        "default_port": 7777,
        "default_query_port": 27015,
        "default_rcon_port": 25575,
        "requires_steamcmd": True,
        "install_dir": "ConanExilesServer",
        "executable": "ConanSandboxServer.exe",
        "icon": "⚔️",
        "supports_mods": True,
        "supports_rcon": True,
        "config_files": [
            "ConanSandbox/Saved/Config/WindowsServer/ServerSettings.ini"
        ]
    },
    "DayZ": {
        "name": "DayZ",
        "app_id": "223350",
        "default_port": 2302,
        "default_query_port": 27016,
        "requires_steamcmd": True,
        "install_dir": "DayZServer",
        "executable": "DayZServer_x64.exe",
        "icon": "🧟",
        "supports_mods": True,
        "config_files": [
            "serverDZ.cfg"
        ]
    },
    "The Forest": {
        "name": "The Forest",
        "app_id": "556450",
        "default_port": 27015,
        "default_query_port": 27016,
        "requires_steamcmd": True,
        "install_dir": "TheForestServer",
        "executable": "TheForestDedicatedServer.exe",
        "icon": "🌲",
        "supports_mods": True,
        "config_files": [
            "config.cfg"
        ]
    },
    "Sons of the Forest": {
        "name": "Sons of the Forest",
        "app_id": "2465200",
        "default_port": 8766,
        "default_query_port": 27016,
        "requires_steamcmd": True,
        "install_dir": "SonsOfTheForestServer",
        "executable": "SonsOfTheForestDS.exe",
        "icon": "🌲",
        "supports_mods": True,
        "config_files": [
            "dedicatedserver.cfg"
        ]
    },
    "Space Engineers": {
        "name": "Space Engineers",
        "app_id": "298740",
        "default_port": 27016,
        "default_query_port": 27016,
        "requires_steamcmd": True,
        "install_dir": "SpaceEngineersServer",
        "executable": "SpaceEngineersDedicated.exe",
        "icon": "🚀",
        "supports_mods": True,
        "config_files": [
            "SpaceEngineers-Dedicated.cfg"
        ]
    },
    "Unturned": {
        "name": "Unturned",
        "app_id": "1110390",
        "default_port": 27015,
        "default_query_port": 27016,
        "requires_steamcmd": True,
        "install_dir": "UnturnedServer",
        "executable": "Unturned.exe",
        "icon": "🧟",
        "supports_mods": True,
        "config_files": [
            "Server/Commands.dat"
        ]
    },
    "Left 4 Dead 2": {
        "name": "Left 4 Dead 2",
        "app_id": "222860",
        "default_port": 27015,
        "default_query_port": 27015,
        "default_rcon_port": 27015,
        "requires_steamcmd": True,
        "install_dir": "L4D2Server",
        "executable": "srcds.exe",
        "icon": "🧟",
        "supports_mods": True,
        "supports_rcon": True,
        "config_files": [
            "left4dead2/cfg/server.cfg"
        ]
    },
    "Team Fortress 2": {
        "name": "Team Fortress 2",
        "app_id": "232250",
        "default_port": 27015,
        "default_query_port": 27015,
        "default_rcon_port": 27015,
        "requires_steamcmd": True,
        "install_dir": "TF2Server",
        "executable": "srcds.exe",
        "icon": "🎮",
        "supports_mods": True,
        "supports_rcon": True,
        "config_files": [
            "tf/cfg/server.cfg"
        ]
    },
    "Factorio": {
        "name": "Factorio",
        "app_id": "427520",
        "default_port": 34197,
        "default_query_port": 34197,
        "requires_steamcmd": True,
        "install_dir": "FactorioServer",
        "executable": "factorio.exe",
        "icon": "🏭",
        "supports_mods": True,
        "config_files": [
            "config/server-settings.json"
        ]
    },
    "Garry's Mod": {
        "name": "Garry's Mod",
        "app_id": "4020",
        "default_port": 27015,
        "default_query_port": 27015,
        "default_rcon_port": 27015,
        "requires_steamcmd": True,
        "install_dir": "GModServer",
        "executable": "srcds.exe",
        "icon": "🎮",
        "supports_mods": True,
        "supports_rcon": True,
        "config_files": [
            "garrysmod/cfg/server.cfg"
        ]
    },
    "Icarus": {
        "name": "Icarus",
        "app_id": "2089300",
        "default_port": 17777,
        "default_query_port": 27015,
        "requires_steamcmd": True,
        "install_dir": "IcarusServer",
        "executable": "IcarusServer.exe",
        "icon": "🌍",
        "supports_mods": True,
        "config_files": []
    },
    "StarRupture": {
        "name": "StarRupture",
        "app_id": "2930490",
        "default_port": 7777,
        "default_query_port": 27015,
        "requires_steamcmd": True,
        "install_dir": "StarRuptureServer",
        "executable": "StarRuptureServer.exe",
        "icon": "🌟",
        "supports_mods": True,
        "config_files": []
    },
    "Enshrouded": {
        "name": "Enshrouded",
        "app_id": "2278520",
        "default_port": 15636,
        "default_query_port": 15637,
        "requires_steamcmd": True,
        "install_dir": "EnshroudedServer",
        "executable": "enshrouded_server.exe",
        "icon": "🌫️",
        "supports_mods": True,
        "config_files": [
            "enshrouded_server.json"
        ]
    },
    "Satisfactory": {
        "name": "Satisfactory",
        "app_id": "1690800",
        "default_port": 7777,
        "default_query_port": 15777,
        "requires_steamcmd": True,
        "install_dir": "SatisfactoryServer",
        "executable": "FactoryServer.exe",
        "icon": "🏭",
        "supports_mods": True,
        "config_files": []
    }
}
```

**Speichern & schließen!**

---

## 📋 PHASE 3: GAME_SERVER_MANAGER.PY ANPASSEN

### **Schritt 3.1: Öffne game_server_manager.py**

```cmd
notepad game_server_manager.py
```

### **Schritt 3.2: Imports anpassen**

**FINDE** diese Zeilen (ganz oben, nach den Standard-Imports):

```python
import socket

# SSL Fix für PyInstaller
try:
    import urllib3
```

**FÜGE DAVOR ein:**

```python
# ==================== REFACTORED MODULES ====================
from core.constants import SUPPORTED_GAMES, VERSION, APP_NAME, GITHUB_REPO, GITHUB_API_URL

# Security (falls vorhanden)
try:
    from web.web_security import RateLimiter, FileSessionStore, generate_csrf_token, get_client_ip
    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False
# ==================== END REFACTORED MODULES ====================

```

### **Schritt 3.3: Konstanten entfernen**

**FINDE und LÖSCHE:**

```python
VERSION = "3.14"
APP_NAME = "Game Server Manager Pro"

# GitHub für Auto-Updates
GITHUB_REPO = "DatPixxel/GameServerManager"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
```

**ERSETZE mit:**

```python
# VERSION, APP_NAME, etc. imported from core.constants
```

### **Schritt 3.4: SUPPORTED_GAMES entfernen**

**FINDE die RIESEN SUPPORTED_GAMES = { ... } Definition**

**Das ist ALLES von Zeile ~64 bis ~642**

**LÖSCHE DAS KOMPLETT!**

**ERSETZE mit:**

```python
# SUPPORTED_GAMES imported from core.constants
```

**WICHTIG:** Lösche wirklich ALLES von `SUPPORTED_GAMES = {` bis zur schließenden `}`

### **Schritt 3.5: Speichern**

- Datei → Speichern
- Notepad schließen

---

## 📋 PHASE 4: TESTEN

### **Schritt 4.1: Teste ob es startet**

```cmd
python game_server_manager.py
```

**MUSS starten ohne Fehler!**

**Falls Fehler:**
- "ModuleNotFoundError: No module named 'core'" → Prüfe ob `core\` Ordner existiert
- "ImportError: cannot import name 'SUPPORTED_GAMES'" → Prüfe `core\constants.py`
- Andere Fehler → **STOP** und zeig mir den Fehler!

---

## 📋 PHASE 5: BUILD

### **Schritt 5.1: build.bat anpassen**

**Öffne:**
```cmd
notepad build_working.bat
```

**FINDE:**
```batch
pyinstaller --name=GameServerManager --onefile --windowed --collect-all customtkinter --collect-all flask --noconfirm game_server_manager.py
```

**ERSETZE mit:**
```batch
pyinstaller ^
    --name=GameServerManager ^
    --onefile ^
    --windowed ^
    --add-data "core;core" ^
    --add-data "web;web" ^
    --hidden-import=core.constants ^
    --collect-all customtkinter ^
    --collect-all flask ^
    --noconfirm ^
    game_server_manager.py
```

**Speichern!**

### **Schritt 5.2: Build ausführen**

```cmd
build_working.bat
```

### **Schritt 5.3: Teste .exe**

```cmd
dist\GameServerManager.exe
```

**MUSS starten!**

---

## ✅ FERTIG - PHASE 1 ABGESCHLOSSEN!

**Du hast jetzt:**
- ✅ `core/constants.py` mit SUPPORTED_GAMES
- ✅ Imports in game_server_manager.py angepasst
- ✅ Funktionierendes Programm
- ✅ Funktionierender Build

**game_server_manager.py ist jetzt ~600 Zeilen kleiner!**

---

## 🎯 NÄCHSTE SCHRITTE (Optional):

### **PHASE 2: ConfigManager auslagern** (später)
### **PHASE 3: ServerInstance auslagern** (später)

**Aber erst Phase 1 komplett durchziehen!**

---

## 🆘 FALLS PROBLEME:

**Backup wiederherstellen:**
```cmd
copy game_server_manager.py.MANUAL_BACKUP game_server_manager.py
```

**Oder Git:**
```cmd
git reset --hard
```

---

## 📋 CHECKLISTE PHASE 1:

- [ ] Backup erstellt
- [ ] Ordner erstellt (core/, web/, utils/)
- [ ] __init__.py Dateien erstellt
- [ ] core/constants.py erstellt & gefüllt
- [ ] game_server_manager.py: Imports angepasst
- [ ] game_server_manager.py: VERSION/APP_NAME gelöscht
- [ ] game_server_manager.py: SUPPORTED_GAMES gelöscht
- [ ] Programm startet (python game_server_manager.py)
- [ ] build_working.bat angepasst
- [ ] Build erfolgreich
- [ ] .exe startet

**Wenn ALLES ✅ → Phase 1 FERTIG!** 🎉

---

**VIEL ERFOLG!** 🚀

Bei Problemen: **STOP** und zeig mir den Fehler!
