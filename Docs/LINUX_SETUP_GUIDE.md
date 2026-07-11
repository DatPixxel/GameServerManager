# 🐧 Game Server Manager Pro v3.15 — Linux Setup Guide

**Von Windows auf Linux migrieren oder parallel betreiben**

---

## 📋 VORAUSSETZUNGEN

### Was du brauchst:
- Ubuntu 22.04 LTS / 24.04 LTS (empfohlen) oder Fedora 39+
- Python 3.10+
- Steam (für Proton-Downloads)
- Mindestens 8GB RAM, 100GB freie Festplatte

---

## 🔧 SCHRITT 1: SYSTEM-PAKETE INSTALLIEREN

```bash
# Aktualisiere das System
sudo apt update && sudo apt upgrade -y

# Python + Tk + Basis-Tools
sudo apt install -y python3 python3-pip python3-tk

# SteamCMD (für Spiele downloaden)
sudo apt install -y steamcmd

# Wine64 (für Windows-Server-Executables)
sudo apt install -y wine64

# Optional: 32-Bit Wine-Bibliotheken
sudo apt install -y libc6-i386 wine32
```

**Fedora:**
```bash
sudo dnf install -y python3 python3-pip python3-tkinter steamcmd wine
```

---

## 🔧 SCHRITT 2: PYTHON-PAKETE INSTALLIEREN

```bash
pip3 install --break-system-packages \
    customtkinter \
    flask \
    psutil \
    requests \
    pillow
```

---

## 🔧 SCHRITT 3: PROTON INSTALLIEREN (EMPFOHLEN)

Proton gibt dir bessere Kompatibilität als Wine allein:

1. Öffne **Steam** auf Linux
2. Gehe zu: **Settings → Downloads → Steam Library Folders**
3. Stelle sicher, dass eine Library-Location gesetzt ist
4. Gehe zu: **Settings → Compatibility**
5. Aktiviere: **Enable Steam Play for all other games**
6. Wähle: **Proton-GE** (Community-Version, beste Kompatibilität)

**Oder manuell installieren:**
```bash
# Proton-GE herunterladen (neueste Version)
cd ~/
PROTON_VERSION="GE-Proton9-20"
wget https://github.com/GloriousEggroll/proton-ge-custom/releases/download/${PROTON_VERSION}/${PROTON_VERSION}.tar.gz
mkdir -p ~/.steam/steam/steamapps/common/
tar -xzf ${PROTON_VERSION}.tar.gz -C ~/.steam/steam/steamapps/common/
```

---

## 🔧 SCHRITT 4: GAME SERVER MANAGER INSTALLIEREN

```bash
# Verzeichnis erstellen
mkdir -p ~/GameServerManager
cd ~/GameServerManager

# Deine Dateien kopieren (von Windows oder aus dem Backup):
# - game_server_manager.py
# - platform_utils.py          ← NEU! Muss vorhanden sein!
# - apply_cross_platform_patch.py  ← Nur wenn noch nicht gepatcht

# Falls noch nicht gepatcht, jetzt patchen:
python3 apply_cross_platform_patch.py

# Teste ob es startet:
python3 game_server_manager.py
```

---

## 🎮 SCHRITT 5: SPIELE — WAS FUNKTIONIERT WIE

### ✅ Native Linux-Server (funktionieren direkt):

| Spiel | Wie es läuft |
|---|---|
| Minecraft Java (Forge) | `java -jar forge-server.jar` |
| Minecraft Bedrock | `./bedrock_server` |
| Rust | `./RustDedicated` |
| Counter-Strike 2 | `./srcds` (Valve SRCDS) |
| Left 4 Dead 2 | `./srcds` |
| Team Fortress 2 | `./srcds` |
| Garry's Mod | `./srcds` |
| Don't Starve Together | Natives Linux-Executable |
| Factorio | `./factorio --start-server` |
| Project Zomboid | `bash start-server.sh` |
| Terraria | Via Mono oder TShock |

### 🍷 Über Wine/Proton (wie die Hosting-Provider):

| Spiel | Status |
|---|---|
| ARK: Survival Ascended | ✅ Funktioniert gut unter Proton |
| Valheim | ✅ Funktioniert gut unter Proton |
| Palworld | ✅ Funktioniert unter Proton |
| 7 Days to Die | ✅ Funktioniert unter Proton |
| Enshrouded | ✅ Funktioniert unter Proton |
| Satisfactory | ✅ Funktioniert unter Wine/Proton |
| The Forest | ⚠️ Funktioniert, gelegentlich Abstürze |
| Sons of the Forest | ⚠️ Teilweise funktionierend |
| V Rising | ⚠️ Unter Proton-GE möglich |
| Conan Exiles | ⚠️ Unter Proton möglich |
| DayZ | ⚠️ Unter Proton möglich |
| Space Engineers | ⚠️ Unter Wine möglich |

---

## 🔥 SCHRITT 6: FIREWALL-PORTS ÖFFNEN

```bash
# Wenn du ufw hast:
sudo ufw enable

# Häufige Server-Ports:
sudo ufw allow 7777/udp      # ARK, Satisfactory, Conan
sudo ufw allow 27015/udp     # Rust, CS2, TF2, GMod, Query-Ports
sudo ufw allow 28015/udp     # Rust
sudo ufw allow 25565/tcp     # Minecraft Java
sudo ufw allow 19132/udp     # Minecraft Bedrock
sudo ufw allow 2456/tcp      # Valheim
sudo ufw allow 2457/tcp      # Valheim Query
sudo ufw allow 8211/udp      # Palworld
sudo ufw allow 26900/udp     # 7 Days to Die
sudo ufw allow 15636/udp     # Enshrouded

# Oder alle auf einmal (weniger sicher, aber schneller):
# sudo ufw allow 2000:30000/udp
# sudo ufw allow 2000:30000/tcp
```

---

## 🔄 SCHRITT 7: AUTOSTART (Optional)

Damit GSM beim Login automatisch startet:

```bash
# Erstelle einen Systemd-Service
sudo nano /etc/systemd/system/gameservermanager.ini
```

**Inhalt:**
```ini
[Unit]
Description=Game Server Manager Pro
After=network.target

[Service]
Type=simple
User=DEIN_USERNAME
WorkingDirectory=/home/DEIN_USERNAME/GameServerManager
ExecStart=/usr/bin/python3 /home/DEIN_USERNAME/GameServerManager/game_server_manager.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# Aktivieren:
sudo systemctl daemon-reload
sudo systemctl enable gameservermanager
sudo systemctl start gameservermanager

# Status prüfen:
sudo systemctl status gameservermanager
```

---

## 🚨 FEHLER-BEHEBUNG

### "ModuleNotFoundError: No module named 'platform_utils'"
```bash
# platform_utils.py fehlt! Kopiere es ins GSM-Verzeichnis
cp /path/to/platform_utils.py ~/GameServerManager/
```

### "No display name and no $DISPLAY environment variable"
```bash
# Du runnst ohne graphische Oberfläche
# Lösung: Starte in einer Desktop-Session oder nutze nur die Web-Oberfläche
export DISPLAY=:0
python3 game_server_manager.py
```

### "Permission denied" bei Server-Start
```bash
# Executable-Permission setzen
chmod +x ~/GameServers/RustDedicatedServer/RustDedicated
chmod +x ~/GameServers/CS2Server/srcds
```

### Wine/Proton nicht gefunden
```bash
# Wine installieren:
sudo apt install -y wine64

# Oder Proton-Pfad manuell prüfen:
find ~/.steam -name "proton" -type f 2>/dev/null
find ~/.local -name "proton" -type f 2>/dev/null
```

### SteamCMD läuft nicht
```bash
# SteamCMD testen:
steamcmd +login anonymous +quit

# Falls Fehler mit 32-Bit:
sudo apt install -y libc6-i386 libgcc-s1:i386 libncurses5:i386 libsdl2-2.0-0:i386
```

---

## 📁 VERZEICHNIS-STRUKTUR (Linux)

```
~/
├── GameServerManager/
│   ├── game_server_manager.py      ← Hauptprogramm
│   ├── platform_utils.py           ← Cross-Platform Modul (NEU!)
│   └── apply_cross_platform_patch.py
│
├── GameServers/                    ← Alle Spielserver hier
│   ├── ARK Survival Ascended Dedicated Server/
│   ├── RustDedicatedServer/
│   ├── MinecraftServer/
│   └── ...
│
└── .config/
    └── GameServerManager/          ← Konfiguration & Logs
        └── logs/
```

---

## ✅ CHECKLISTE

- [ ] Ubuntu/Fedora installiert
- [ ] Python 3.10+ installiert
- [ ] Python-Pakete installiert (customtkinter, flask, psutil)
- [ ] SteamCMD installiert
- [ ] Wine64 installiert
- [ ] Proton via Steam installiert (empfohlen)
- [ ] platform_utils.py vorhanden
- [ ] Cross-Platform-Patch angewendet
- [ ] game_server_manager.py startet
- [ ] Firewall-Ports geöffnet
- [ ] Erste Server getestet

---

*Game Server Manager Pro v3.15 — Cross-Platform Edition*
*Funktioniert auf Windows 10/11 und Ubuntu/Fedora Linux*
