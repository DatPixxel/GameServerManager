"""
===============================================================================
Game Server Manager Pro v3.15 - Cross-Platform Utilities
===============================================================================
Dieses Modul wird von game_server_manager.py importiert und gibt es die
Plattform-spezifische Logik für Windows UND Linux.

Wie es funktioniert:
- Bei Start wird das OS erkannt (Windows / Linux)
- Alle Funktionen geben automatisch das Richtige zurück
- Das Rest des Programms muss NICHTS ändern!
===============================================================================
"""

import sys
import os
import subprocess
import shutil
import json
import logging

# ─── PLATTFORM-ERKENNUNG ──────────────────────────────────────────────────────
IS_WINDOWS = sys.platform == "win32"
IS_LINUX = sys.platform.startswith("linux")
PLATFORM_NAME = "Windows" if IS_WINDOWS else "Linux"

logger = logging.getLogger("GSM_Platform")

# ─── SPIELE MIT NATIVER LINUX-SERVER-UNTERSTÜTZUNG ───────────────────────────
# Diese Spiele haben offiziell oder bekannt funktionierte Linux-Dedicated-Server
NATIVE_LINUX_SERVERS = {
    "Minecraft Java (Forge)": {
        "executable": "forge-server.jar",
        "launch_cmd": ["java", "-jar", "forge-server.jar"],
        "notes": "Java ist Cross-Platform - funktioniert native"
    },
    "Minecraft Bedrock": {
        "executable": "bedrock_server",  # Kein .exe auf Linux
        "launch_cmd": ["./bedrock_server"],
        "notes": "Offizieller Linux-Server verfügbar"
    },
    "Rust": {
        "executable": "RustDedicated",  # Kein .exe auf Linux
        "launch_cmd": ["./RustDedicated"],
        "notes": "Native Linux Dedicated Server"
    },
    "Counter-Strike 2": {
        "executable": "srcds",  # Kein .exe auf Linux
        "launch_cmd": ["./srcds"],
        "notes": "Valve Source Dedicated Server - native Linux"
    },
    "Left 4 Dead 2": {
        "executable": "srcds",
        "launch_cmd": ["./srcds"],
        "notes": "Valve Source Dedicated Server - native Linux"
    },
    "Team Fortress 2": {
        "executable": "srcds",
        "launch_cmd": ["./srcds"],
        "notes": "Valve Source Dedicated Server - native Linux"
    },
    "Garry's Mod": {
        "executable": "srcds",
        "launch_cmd": ["./srcds"],
        "notes": "Valve Source Dedicated Server - native Linux"
    },
    "Don't Starve Together": {
        "executable": "dontstarve_dedicated_server_nullrenderer_x64",
        "launch_cmd": ["./dontstarve_dedicated_server_nullrenderer_x64"],
        "notes": "Native Linux Server verfügbar"
    },
    "Factorio": {
        "executable": "factorio",
        "launch_cmd": ["./factorio", "--start-server"],
        "notes": "Native Linux Dedicated Server"
    },
    "Project Zomboid": {
        "executable": "start-server.sh",
        "launch_cmd": ["bash", "start-server.sh"],
        "notes": "Native Linux Server"
    },
    "Terraria": {
        "executable": "TerrariaServer.exe",  # Läuft auch unter Mono/Wine
        "launch_cmd": ["mono", "TerrariaServer.exe"],
        "notes": "Läuft unter Mono (TShock empfohlen für Linux)"
    },
}

# ─── SPIELE DIE UNTER LINUX WINE/PROTON BRAUCHEN ─────────────────────────────
WINE_REQUIRED_SERVERS = [
    "ARK: Survival Ascended",
    "Valheim",
    "Palworld",
    "7 Days to Die",
    "The Forest",
    "Sons of the Forest",
    "V Rising",
    "Conan Exiles",
    "DayZ",
    "Space Engineers",
    "Unturned",
    "Icarus",
    "StarRupture",
    "Enshrouded",
    "Satisfactory",
]


# ═══════════════════════════════════════════════════════════════════════════════
# PFAD-FUNKTIONEN
# ═══════════════════════════════════════════════════════════════════════════════

def get_config_dir():
    """Gibt das Konfigurations-Verzeichnis zurück (plattformspezifisch)."""
    if IS_WINDOWS:
        return os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "GameServerManager")
    else:
        return os.path.join(os.path.expanduser("~"), ".config", "GameServerManager")


def get_default_server_dir():
    """Standard-Verzeichnis für Spielserver."""
    if IS_WINDOWS:
        # Typisch: C:\Users\<User>\GameServers
        return os.path.join(os.path.expanduser("~"), "GameServers")
    else:
        # Typisch: ~/GameServers oder /home/<user>/GameServers
        return os.path.join(os.path.expanduser("~"), "GameServers")


def get_log_dir():
    """Log-Verzeichnis."""
    if IS_WINDOWS:
        return os.path.join(get_config_dir(), "logs")
    else:
        return os.path.join(os.path.expanduser("~"), ".local", "share", "GameServerManager", "logs")


def get_steamcmd_path():
    """Gibt den Pfad zum SteamCMD-Executable zurück."""
    if IS_WINDOWS:
        # Windows: steamcmd.exe im Programmverzeichnis oder PATH
        local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "steamcmd", "steamcmd.exe")
        if os.path.exists(local_path):
            return local_path
        # Oder im PATH suchen
        found = shutil.which("steamcmd.exe")
        return found if found else "steamcmd.exe"
    else:
        # Linux: steamcmd im PATH (sudo apt install steamcmd)
        # oder lokale Installation
        local_path = os.path.join(os.path.expanduser("~"), ".steam", "steamcmd", "steamcmd.sh")
        if os.path.exists(local_path):
            return local_path
        found = shutil.which("steamcmd")
        return found if found else "steamcmd"


def get_steamcmd_download_platform():
    """Gibt die SteamCMD-Download-Plattform zurück."""
    if IS_WINDOWS:
        return "windows"
    else:
        return "linux"


# ═══════════════════════════════════════════════════════════════════════════════
# WINE/PROTON KONFIGURATION (Linux only)
# ═══════════════════════════════════════════════════════════════════════════════

def find_proton():
    """Sucht nach Proton-Installationen auf Linux. Gibt den Pfad zurück oder None."""
    if IS_WINDOWS:
        return None

    proton_search_paths = [
        os.path.expanduser("~/.steam/steam/steamapps/common/"),
        os.path.expanduser("~/.local/share/Steam/steamapps/common/"),
        "/usr/lib/steam/steamapps/common/",
        "/usr/share/steam/steamapps/common/",
    ]

    proton_candidates = []

    for search_dir in proton_search_paths:
        if not os.path.isdir(search_dir):
            continue
        try:
            for entry in os.listdir(search_dir):
                full_path = os.path.join(search_dir, entry)
                if os.path.isdir(full_path) and ("Proton" in entry or "proton" in entry):
                    proton_exe = os.path.join(full_path, "proton")
                    if os.path.isfile(proton_exe):
                        proton_candidates.append((entry, full_path))
        except PermissionError:
            continue

    if not proton_candidates:
        return None

    # Sortiere: Bevorzuge Proton-GE, dann höchste Version
    proton_candidates.sort(key=lambda x: (
        1 if "GE" in x[0] else 0,  # GE bevorzugen
        x[0]  # Alphabetisch (höhere Versionen kommen sspäter)
    ), reverse=True)

    return proton_candidates[0][1]  # Gib den Pfad der besten Option zurück


def find_wine():
    """Sucht nach Wine auf Linux."""
    if IS_WINDOWS:
        return None

    # wine64 bevorzugen, dann wine
    for wine_name in ["wine64", "wine"]:
        found = shutil.which(wine_name)
        if found:
            return found
    return None


def get_wine_or_proton():
    """Gibt die beste verfügbare Compatibility-Layer zurück.
    
    Returns:
        dict mit:
            - 'type': 'proton' | 'wine' | None
            - 'path': Pfad zum Executable
            - 'available': True/False
    """
    if IS_WINDOWS:
        return {"type": None, "path": None, "available": False}

    # Erst Proton versuchen (bessere Kompatibilität)
    proton_path = find_proton()
    if proton_path:
        return {
            "type": "proton",
            "path": os.path.join(proton_path, "proton"),
            "available": True
        }

    # Dann Wine
    wine_path = find_wine()
    if wine_path:
        return {
            "type": "wine",
            "path": wine_path,
            "available": True
        }

    return {"type": None, "path": None, "available": False}


# ═══════════════════════════════════════════════════════════════════════════════
# SERVER START/STOP FUNKTIONEN
# ═══════════════════════════════════════════════════════════════════════════════

def get_server_executable(game_name, game_config):
    """Gibt den richtigen Executable-Pfad zurück (plattformspezifisch).
    
    Args:
        game_name: Name des Spiels (z.B. "ARK: Survival Ascended")
        game_config: Die Konfiguration aus SUPPORTED_GAMES
    
    Returns:
        str: Der Executable-Name für diese Plattform
    """
    if IS_WINDOWS:
        # Windows: immer .exe wie definiert
        return game_config.get("executable", "")

    # Linux: Prüfe ob natives Linux-Executable existiert
    if game_name in NATIVE_LINUX_SERVERS:
        return NATIVE_LINUX_SERVERS[game_name]["executable"]

    # Ansonsten: Windows .exe (für Wine/Proton)
    return game_config.get("executable", "")


def build_server_launch_command(game_name, game_config, install_path, extra_args=None):
    """Erstellt den vollständigen Start-Befehl für einen Server.
    
    Args:
        game_name: Name des Spiels
        game_config: Konfiguration aus SUPPORTED_GAMES
        install_path: Pfad zum Server-Installationsverzeichnis
        extra_args: Zusätzliche Argumente als Liste
    
    Returns:
        list: Der Start-Befehl als Liste [programm, arg1, arg2, ...]
    """
    if extra_args is None:
        extra_args = []

    executable = game_config.get("executable", "")

    if IS_WINDOWS:
        # Windows: Direkt das .exe starten
        exe_path = os.path.join(install_path, executable)
        return [exe_path] + extra_args

    # ─── LINUX ───
    # Fall 1: Natives Linux-Server verfügbar
    if game_name in NATIVE_LINUX_SERVERS:
        native_info = NATIVE_LINUX_SERVERS[game_name]
        native_exe = native_info["executable"]

        # Spezialfall: Java-basierte Server (Minecraft)
        if native_exe.endswith(".jar"):
            jar_path = os.path.join(install_path, native_exe)
            return ["java", "-jar", jar_path] + extra_args

        # Spezialfall: Shell-Skript
        if native_exe.endswith(".sh"):
            sh_path = os.path.join(install_path, native_exe)
            return ["bash", sh_path] + extra_args

        # Spezialfall: Mono (z.B. Terraria)
        if "mono" in str(native_info.get("launch_cmd", [])):
            exe_path = os.path.join(install_path, executable)  # Verwende Original .exe
            return ["mono", exe_path] + extra_args

        # Standard: Direkter Aufruf
        exe_path = os.path.join(install_path, native_exe)
        return [exe_path] + extra_args

    # Fall 2: Wine/Proton für Windows-.exe nötig
    compat = get_wine_or_proton()

    if not compat["available"]:
        logger.error(f"FEHLER: Kein Wine/Proton gefunden! Server '{game_name}' kann nicht gestartet werden auf Linux!")
        logger.error("Bitte installiere: sudo apt install wine64")
        logger.error("Oder installiere Proton über Steam")
        return []  # Leerer Befehl = Start nicht möglich

    exe_path = os.path.join(install_path, executable)

    if compat["type"] == "proton":
        # Proton: proton waitforexitandrun <exe>
        proton_exe = compat["path"]
        return [proton_exe, "waitforexitandrun", exe_path] + extra_args

    elif compat["type"] == "wine":
        # Wine: wine <exe>
        wine_exe = compat["path"]
        return [wine_exe, exe_path] + extra_args

    return []


def build_steamcmd_command(app_id, install_dir, validate=True):
    """Erstellt einen SteamCMD-Befehl zum Downloaden eines Spiels.
    
    Args:
        app_id: Steam App-ID
        install_dir: Installationsverzeichnis
        validate: Ob validiert werden soll
    
    Returns:
        list: Der SteamCMD-Befehl
    """
    steamcmd = get_steamcmd_path()
    
    cmd = [
        steamcmd,
        "+login", "anonymous",
        "+force_install_dir", install_dir,
        "+app_update", str(app_id),
    ]
    
    if validate:
        cmd.append("validate")
    
    cmd.append("+quit")
    return cmd


def kill_server_process(process):
    """Tötet einen Server-Prozess (plattformspezifisch).
    
    Args:
        process: subprocess.Popen Objekt
    """
    if process is None:
        return

    try:
        if IS_WINDOWS:
            # Windows: taskkill für den Prozess-Baum
            subprocess.call(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            # Linux: Prozess und Kinder töten
            import signal
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            except (ProcessLookupError, PermissionError, OSError):
                try:
                    process.terminate()
                except ProcessLookupError:
                    pass
            
            # Warte kurz, dann SIGKILL falls nötig
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except (ProcessLookupError, PermissionError, OSError):
                    process.kill()
    except Exception as e:
        logger.error(f"Fehler beim Töten des Prozesses: {e}")


def start_process(cmd, cwd=None, shell=False):
    """Startet einen Prozess plattformspezifisch.
    
    Args:
        cmd: Befehl als Liste oder String
        cwd: Arbeitsverzeichnis
        shell: Ob Shell verwendet werden soll
    
    Returns:
        subprocess.Popen Objekt
    """
    kwargs = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "cwd": cwd,
        "shell": shell,
    }

    if IS_WINDOWS:
        # Windows: CREATE_NEW_PROCESS_GROUP für saubertes Beenden
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        # Linux: Neue Prozessgruppe starten
        kwargs["preexec_fn"] = os.setsid

    return subprocess.Popen(cmd, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# FIREWALL-FUNKTIONEN
# ═══════════════════════════════════════════════════════════════════════════════

def open_firewall_port(port, protocol="both", description="GSM Server"):
    """Öffnet einen Port in der Firewall (plattformspezifisch).
    
    Args:
        port: Port-Nummer
        protocol: 'tcp', 'udp', oder 'both'
        description: Beschreibung der Regel
    
    Returns:
        bool: Erfolgreich oder nicht
    """
    protocols = []
    if protocol in ("tcp", "both"):
        protocols.append("TCP")
    if protocol in ("udp", "both"):
        protocols.append("UDP")

    if IS_WINDOWS:
        for proto in protocols:
            try:
                subprocess.run([
                    "netsh", "advfirewall", "firewall", "add", "rule",
                    "name", f"{description} Port {port} {proto}",
                    "dir", "in",
                    "action", "allow",
                    "protocol", proto,
                    "localport", str(port)
                ], check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                logger.error(f"Firewall-Fehler (Windows): {e}")
                return False
        return True

    else:  # Linux
        # Versuche ufw, dann iptables
        ufw_path = shutil.which("ufw")
        
        if ufw_path:
            for proto in protocols:
                try:
                    subprocess.run([
                        "sudo", "ufw", "allow", f"{port}/{proto.lower()}"
                    ], check=True, capture_output=True)
                except subprocess.CalledProcessError as e:
                    logger.error(f"UFW-Fehler: {e}")
                    return False
            return True
        else:
            # iptables als Fallback
            for proto in protocols:
                try:
                    subprocess.run([
                        "sudo", "iptables", "-A", "INPUT",
                        "-p", proto.lower(),
                        "--dport", str(port),
                        "-j", "ACCEPT"
                    ], check=True, capture_output=True)
                except subprocess.CalledProcessError as e:
                    logger.error(f"iptables-Fehler: {e}")
                    return False
            return True


# ═══════════════════════════════════════════════════════════════════════════════
# HILFSFUNKTIONEN
# ═══════════════════════════════════════════════════════════════════════════════

def is_game_supported_on_platform(game_name):
    """Prüft ob ein Spiel auf der aktuellen Plattform möglich ist.
    
    Returns:
        dict:
            - 'supported': True/False
            - 'method': 'native' | 'wine' | 'proton' | 'not_supported'
            - 'message': Infobotschaft
    """
    if IS_WINDOWS:
        return {
            "supported": True,
            "method": "native",
            "message": "✅ Native Windows-Unterstützung"
        }

    # Linux: Prüfe ob native oder Wine/Proton
    if game_name in NATIVE_LINUX_SERVERS:
        return {
            "supported": True,
            "method": "native",
            "message": f"✅ Native Linux-Unterstützung"
        }

    if game_name in WINE_REQUIRED_SERVERS:
        compat = get_wine_or_proton()
        if compat["available"]:
            return {
                "supported": True,
                "method": compat["type"],
                "message": f"✅ Läuft über {compat['type'].capitalize()}"
            }
        else:
            return {
                "supported": False,
                "method": "not_supported",
                "message": "❌ Wine/Proton nicht installiert! (sudo apt install wine64)"
            }

    # Unbekanntes Spiel auf Linux
    compat = get_wine_or_proton()
    if compat["available"]:
        return {
            "supported": True,
            "method": compat["type"],
            "message": f"⚠️ Versuche über {compat['type'].capitalize()} (ungetestet)"
        }

    return {
        "supported": False,
        "method": "not_supported",
        "message": "❌ Nicht unterstützt auf Linux ohne Wine/Proton"
    }


def get_platform_info():
    """Gibt eine Zusammenfassung der Plattform-Informationen zurück."""
    info = {
        "platform": PLATFORM_NAME,
        "is_windows": IS_WINDOWS,
        "is_linux": IS_LINUX,
        "python_version": sys.version,
        "steamcmd_path": get_steamcmd_path(),
        "config_dir": get_config_dir(),
        "default_server_dir": get_default_server_dir(),
    }

    if IS_LINUX:
        compat = get_wine_or_proton()
        info["wine_proton"] = compat
        info["native_linux_games"] = list(NATIVE_LINUX_SERVERS.keys())
        info["wine_required_games"] = WINE_REQUIRED_SERVERS

    return info


def ensure_directories():
    """Erstellt notwendige Verzeichnisse falls nicht vorhanden."""
    dirs = [
        get_config_dir(),
        get_log_dir(),
        get_default_server_dir(),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def get_platform_label():
    """Gibt ein Label für die GUI zurück."""
    if IS_WINDOWS:
        return "🪟 Windows"
    else:
        compat = get_wine_or_proton()
        if compat["available"]:
            return f"🐧 Linux ({compat['type'].capitalize()} verfügbar)"
        else:
            return "🐧 Linux (Wine/Proton nicht gefunden)"
