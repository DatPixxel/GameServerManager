"""
Server Instance für Game Server Manager Pro
Repräsentiert einen einzelnen Game-Server
"""

import os
import subprocess
import threading
import time
import psutil
import zipfile
import shutil
from datetime import datetime, timedelta

class ServerInstance:
    """Repräsentiert einen einzelnen Game-Server"""
    
    def __init__(self, server_id, config, config_manager, discord_notifier=None):
        self.server_id = server_id
        self.config = config
        self.config_manager = config_manager
        self.discord_notifier = discord_notifier
        self.process = None
        self.monitoring_active = False
        self.start_time = None
        self.log_messages = []
        
        # Auto-Backup System
        self.auto_backup_active = False
        self.auto_backup_thread = None
        self.last_backup_time = None
        self.next_backup_time = None
    
    def start_auto_backup(self):
        """Startet das Auto-Backup System"""
        if not self.config.get("auto_backup", False):
            return
        
        interval_hours = self.config.get("backup_interval_hours", 0)
        if interval_hours <= 0:
            return
        
        self.auto_backup_active = True
        self.auto_backup_thread = threading.Thread(target=self._auto_backup_loop, daemon=True)
        self.auto_backup_thread.start()
        self.log(f"🔄 Auto-Backup aktiviert (alle {interval_hours}h)")
    
    def stop_auto_backup(self):
        """Stoppt das Auto-Backup System"""
        self.auto_backup_active = False
        self.next_backup_time = None
    
    def _auto_backup_loop(self):
        """Backup-Loop der im Hintergrund läuft"""
        interval_hours = self.config.get("backup_interval_hours", 6)
        interval_seconds = interval_hours * 3600
        
        while self.auto_backup_active:
            # Nächste Backup-Zeit berechnen
            self.next_backup_time = datetime.now() + timedelta(seconds=interval_seconds)
            
            # Warte das Intervall (prüfe alle 60 Sekunden ob noch aktiv)
            waited = 0
            while waited < interval_seconds and self.auto_backup_active:
                time.sleep(60)
                waited += 60
            
            # Backup erstellen wenn noch aktiv und Server läuft
            if self.auto_backup_active and self.is_running():
                self.log("🔄 Auto-Backup wird erstellt...")
                self.create_backup()
                self.cleanup_old_backups()
    
    def cleanup_old_backups(self):
        """Löscht alte Backups wenn Max-Anzahl überschritten"""
        max_backups = self.config.get("max_backups", 10)
        if max_backups <= 0:
            return
        
        backup_dir = os.path.join(PATHS["backups"], self.server_id)
        if not os.path.exists(backup_dir):
            return
        
        # Alle Backup-Dateien finden und nach Datum sortieren
        backups = []
        for f in os.listdir(backup_dir):
            if f.endswith(".zip"):
                path = os.path.join(backup_dir, f)
                backups.append((path, os.path.getmtime(path)))
        
        # Nach Datum sortieren (neueste zuerst)
        backups.sort(key=lambda x: x[1], reverse=True)
        
        # Überschüssige löschen
        for path, _ in backups[max_backups:]:
            try:
                os.remove(path)
                self.log(f"🗑️ Altes Backup gelöscht: {os.path.basename(path)}")
            except:
                pass
    
    def get_backups(self):
        """Gibt Liste aller Backups zurück"""
        backup_dir = os.path.join(PATHS["backups"], self.server_id)
        backups = []
        
        if not os.path.exists(backup_dir):
            return backups
        
        for f in os.listdir(backup_dir):
            if f.endswith(".zip"):
                path = os.path.join(backup_dir, f)
                stat = os.stat(path)
                backups.append({
                    "filename": f,
                    "path": path,
                    "size": stat.st_size,
                    "date": datetime.fromtimestamp(stat.st_mtime)
                })
        
        # Nach Datum sortieren (neueste zuerst)
        backups.sort(key=lambda x: x["date"], reverse=True)
        return backups
    
    def restore_backup(self, backup_path):
        """Stellt ein Backup sicher wieder her (mit Path Traversal Schutz)"""
        try:
            if self.is_running():
                self.log("⚠️ Server muss gestoppt sein für Wiederherstellung!")
                return False
            
            # Pfad-Validierung (nur wenn PATHS gesetzt ist)
            if PATHS and PATHS.get("backups"):
                is_valid, error_msg = validate_backup_path(PATHS["backups"], self.server_id, backup_path)
                if not is_valid:
                    self.log(f"❌ Sicherheitsfehler: {error_msg}")
                    return False
            
            if not os.path.exists(backup_path):
                self.log("❌ Backup-Datei existiert nicht!")
                return False
            
            self.log(f"🔄 Stelle Backup wieder her: {os.path.basename(backup_path)}")
            
            server_dir = self.get_server_dir()
            
            # Sicheres Entpacken (verhindert ZIP Path Traversal)
            success, error_msg = safe_extract_zip(backup_path, server_dir)
            if not success:
                self.log(f"❌ {error_msg}")
                return False
            
            self.log("✅ Backup erfolgreich wiederhergestellt!")
            return True
            
        except Exception as e:
            self.log(f"❌ Wiederherstellung fehlgeschlagen: {str(e)}")
            return False
    
    def delete_backup(self, backup_path):
        """Löscht ein Backup (mit Pfad-Validierung)"""
        try:
            # Pfad-Validierung (nur wenn PATHS gesetzt ist)
            if PATHS and PATHS.get("backups"):
                is_valid, error_msg = validate_backup_path(PATHS["backups"], self.server_id, backup_path)
                if not is_valid:
                    self.log(f"❌ Sicherheitsfehler: {error_msg}")
                    return False
            
            if not os.path.exists(backup_path):
                self.log("❌ Backup-Datei existiert nicht!")
                return False
            
            os.remove(backup_path)
            self.log(f"🗑️ Backup gelöscht: {os.path.basename(backup_path)}")
            return True
        except Exception as e:
            self.log(f"❌ Löschen fehlgeschlagen: {str(e)}")
            return False
    
    def log(self, message):
        """Loggt eine Nachricht"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{self.config['name']}] {message}"
        self.log_messages.append(log_entry)
        if len(self.log_messages) > 100:
            self.log_messages = self.log_messages[-100:]
        print(log_entry)
    
    def get_exe_path(self):
        """Gibt den vollständigen Pfad zur Server-Exe zurück"""
        server_dir = os.path.join(PATHS["servers"], self.server_id)
        game_info = SUPPORTED_GAMES.get(self.config["game"], {})
        exe_path = game_info.get("exe_path", "").replace("/", os.sep)
        return os.path.join(server_dir, exe_path)
    
    def get_server_dir(self):
        """Gibt das Server-Verzeichnis zurück"""
        return os.path.join(PATHS["servers"], self.server_id)
    
    def is_installed(self):
        """Prüft ob der Server installiert ist"""
        # Minecraft Forge: Prüfe run.bat oder forge JAR
        if self.config.get("game") == "Minecraft Java (Forge)":
            server_dir = self.get_server_dir()
            
            # Prüfe run.bat
            if os.path.exists(os.path.join(server_dir, "run.bat")):
                return True
            
            # Prüfe forge JAR
            for f in os.listdir(server_dir) if os.path.exists(server_dir) else []:
                if "forge" in f.lower() and f.endswith(".jar") and "installer" not in f.lower():
                    return True
            
            return False
        
        return os.path.exists(self.get_exe_path())
    
    def is_running(self):
        """Prüft ob der Server läuft"""
        return self.process is not None and self.process.poll() is None
    
    def get_resource_usage(self):
        """Gibt CPU und RAM Nutzung des Server-Prozesses zurück"""
        if not self.is_running():
            return {"cpu": 0, "ram_mb": 0, "ram_percent": 0}
        
        try:
            # Prozess-Objekt von psutil holen
            proc = psutil.Process(self.process.pid)
            
            # CPU Nutzung (Durchschnitt über kurze Zeit)
            cpu_percent = proc.cpu_percent(interval=0.1)
            
            # RAM Nutzung
            mem_info = proc.memory_info()
            ram_mb = mem_info.rss / (1024 * 1024)  # In MB
            
            # RAM als Prozent vom Gesamtsystem
            total_ram = psutil.virtual_memory().total / (1024 * 1024)
            ram_percent = (ram_mb / total_ram) * 100
            
            # Kindprozesse einbeziehen (für Server die Subprozesse spawnen)
            try:
                children = proc.children(recursive=True)
                for child in children:
                    try:
                        cpu_percent += child.cpu_percent(interval=0)
                        child_mem = child.memory_info()
                        ram_mb += child_mem.rss / (1024 * 1024)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            
            return {
                "cpu": min(cpu_percent, 100),  # Cap bei 100%
                "ram_mb": ram_mb,
                "ram_percent": min((ram_mb / total_ram) * 100, 100),
                "ram_gb": ram_mb / 1024
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception) as e:
            return {"cpu": 0, "ram_mb": 0, "ram_percent": 0, "ram_gb": 0}
    
    def build_start_command(self):
        """Erstellt den Start-Befehl"""
        game_info = SUPPORTED_GAMES.get(self.config["game"], {})
        exe_path = self.get_exe_path()
        
        # Basis-Parameter
        params = self.config.get("start_params", game_info.get("default_params", ""))
        
        # ===== MINECRAFT FORGE =====
        if self.config["game"] == "Minecraft Java (Forge)":
            server_dir = self.get_server_dir()
            ram = self.config.get("ram", "4G")
            
            # Suche nach run.bat (bevorzugt)
            run_bat = os.path.join(server_dir, "run.bat")
            if os.path.exists(run_bat):
                return [run_bat]
            
            # Alternative: Direkt Java aufrufen
            java_path = self._find_java_for_minecraft()
            if not java_path:
                self.log("❌ Java nicht gefunden!")
                return None
            
            # Suche Server JAR
            server_jar = None
            for f in os.listdir(server_dir):
                if f.startswith("forge-") and f.endswith("-server.jar"):
                    server_jar = f
                    break
                elif f.startswith("forge-") and f.endswith("-shim.jar"):
                    server_jar = f
                    break
            
            if not server_jar:
                for f in os.listdir(server_dir):
                    if "forge" in f.lower() and f.endswith(".jar") and "installer" not in f.lower():
                        server_jar = f
                        break
            
            if server_jar:
                return [java_path, f"-Xmx{ram}", f"-Xms{ram}", "-jar", server_jar, "nogui"]
            
            self.log("❌ Keine Server JAR gefunden!")
            return None
        
        # Für ARK: Map und Mods
        if self.config["game"] == "ARK: Survival Ascended":
            map_param = self.config.get("map", "TheIsland_WP")
            session_name = self.config.get("name", "MyServer")
            port = self.config.get("port", 7777)
            query_port = self.config.get("query_port", 27015)
            max_players = self.config.get("max_players", 70)
            
            # Server-Passwort
            server_password = self.config.get("server_password", "")
            admin_password = self.config.get("admin_password", "admin")
            
            # URL-Style Parameter für ARK (erster Parameter)
            url_params = f'{map_param}?listen?SessionName="{session_name}"'
            url_params += f"?MaxPlayers={max_players}"
            
            # Passwörter
            if server_password:
                url_params += f"?ServerPassword={server_password}"
            if admin_password:
                url_params += f"?ServerAdminPassword={admin_password}"
            
            # Kommandozeilen-Flags als Liste
            cmd_args = [url_params]
            cmd_args.append(f"-Port={port}")
            cmd_args.append(f"-QueryPort={query_port}")
            cmd_args.append("-MultiHome=0.0.0.0")
            cmd_args.append("-nosteamclient")
            cmd_args.append("-NoBattlEye")
            cmd_args.append("-log")
            
            # Mods
            mods = self.config.get("mods", [])
            if mods:
                cmd_args.append(f"-mods={','.join(mods)}")
            
            # ===== CLUSTER SUPPORT =====
            cluster_id = self.config.get("cluster", "")
            if cluster_id and self.config_manager:
                clusters = self.config_manager.app_config.get("clusters", {})
                cluster_info = clusters.get(cluster_id)
                if cluster_info:
                    cluster_dir = cluster_info.get("directory", "")
                    if cluster_dir:
                        cmd_args.append(f"-clusterid={cluster_id}")
                        cmd_args.append(f'-ClusterDirOverride="{cluster_dir}"')
                        cmd_args.append("-NoTransferFromFiltering")
                        self.log(f"🔗 Cluster: {cluster_id}")
            
            # Rückgabe als Liste für shell=False
            return [exe_path] + cmd_args
        
        # ===== CONAN EXILES =====
        if self.config["game"] == "Conan Exiles":
            port = self.config.get("port", 7777)
            query_port = self.config.get("query_port", 27015)
            max_players = self.config.get("max_players", 40)
            
            cmd_args = [
                "-log",
                f"-Port={port}",
                f"-QueryPort={query_port}",
                f"-MaxPlayers={max_players}"
            ]
            
            return [exe_path] + cmd_args
        
        # Für andere Spiele: Standard-Parameter als Liste
        params = self.config.get("start_params", game_info.get("default_params", ""))
        if params:
            # Parameter-String in Liste umwandeln (einfaches Split)
            param_list = params.split()
            return [exe_path] + param_list
        return [exe_path]
    
    def _find_java_for_minecraft(self):
        """Sucht nach Java Installation für Minecraft"""
        # 1. JAVA_HOME prüfen
        java_home = os.environ.get("JAVA_HOME")
        if java_home:
            java_exe = os.path.join(java_home, "bin", "java.exe")
            if os.path.exists(java_exe):
                return java_exe
        
        # 2. PATH prüfen
        try:
            result = subprocess.run(
                ["where", "java"],
                capture_output=True,
                text=True,
                shell=False
            )
            if result.returncode == 0:
                java_path = result.stdout.strip().split('\n')[0]
                if os.path.exists(java_path):
                    return java_path
        except:
            pass
        
        # 3. Bekannte Installationspfade prüfen
        common_paths = [
            r"C:\Program Files\Java",
            r"C:\Program Files\Eclipse Adoptium",
            r"C:\Program Files\AdoptOpenJDK",
            r"C:\Program Files\Zulu",
            r"C:\Program Files\Microsoft\jdk-17",
            r"C:\Program Files\Amazon Corretto",
        ]
        
        for base_path in common_paths:
            if os.path.exists(base_path):
                for root, dirs, files in os.walk(base_path):
                    if "java.exe" in files:
                        return os.path.join(root, "java.exe")
        
        return None
    
    def start(self):
        """Startet den Server"""
        if self.is_running():
            self.log("⚠️ Server läuft bereits!")
            return False
        
        if not self.is_installed():
            self.log("❌ Server nicht installiert!")
            return False
        
        # StarRupture: DSSettings.txt erstellen falls nicht vorhanden
        if self.config.get("game") == "StarRupture":
            self._ensure_starrupture_settings()
        
        try:
            cmd_list = self.build_start_command()
            
            # Prüfen ob Befehl erstellt werden konnte (wichtig für Minecraft)
            if cmd_list is None:
                self.log("❌ Konnte Start-Befehl nicht erstellen!")
                return False
            
            # Für Logging: Liste als lesbaren String formatieren
            cmd_display = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in cmd_list)
            self.log(f"🚀 Starte: {cmd_display}")
            
            self.process = subprocess.Popen(
                cmd_list,
                cwd=self.get_server_dir(),
                shell=False
            )
            
            self.start_time = time.time()
            self.monitoring_active = True
            self.log(f"✅ Server gestartet (PID: {self.process.pid})")
            
            # Discord Benachrichtigung
            if self.discord_notifier:
                self.discord_notifier.notify_server_start(self.config.get("name", "Server"))
            
            # Monitoring Thread starten
            threading.Thread(target=self._monitor, daemon=True).start()
            
            # Auto-Backup starten
            self.start_auto_backup()
            
            return True
            
        except Exception as e:
            self.log(f"❌ Start fehlgeschlagen: {str(e)}")
            return False
    
    def stop(self):
        """Stoppt den Server und schließt alle zugehörigen Prozesse/Fenster"""
        if not self.is_running():
            self.log("⚠️ Server läuft nicht!")
            return False
        
        try:
            self.monitoring_active = False
            
            # Auto-Backup stoppen
            self.stop_auto_backup()
            
            # Alle Kindprozesse finden und beenden (inkl. Console-Fenster)
            try:
                parent = psutil.Process(self.process.pid)
                children = parent.children(recursive=True)
                
                # Erst alle Kindprozesse beenden
                for child in children:
                    try:
                        child.terminate()
                    except:
                        pass
                
                # Dann den Hauptprozess
                self.process.terminate()
                
                # Auf Beendigung warten
                gone, alive = psutil.wait_procs([parent] + children, timeout=5)
                
                # Falls noch welche leben, forciert beenden
                for p in alive:
                    try:
                        p.kill()
                    except:
                        pass
                        
            except psutil.NoSuchProcess:
                # Prozess bereits beendet
                pass
            except Exception as e:
                # Fallback: nur terminate
                self.process.terminate()
                self.process.wait(timeout=10)
            
            self.log("⚫ Server gestoppt")
            
            # Discord Benachrichtigung
            if self.discord_notifier:
                self.discord_notifier.notify_server_stop(self.config.get("name", "Server"))
            
            self.process = None
            self.start_time = None
            return True
            
        except Exception as e:
            try:
                self.process.kill()
                self.log("⚫ Server forciert gestoppt")
                self.process = None
                return True
            except:
                self.log(f"❌ Stoppen fehlgeschlagen: {str(e)}")
                return False
    
    def _ensure_starrupture_settings(self):
        """Erstellt DSSettings.txt für StarRupture falls nicht vorhanden"""
        server_dir = self.get_server_dir()
        
        # DSSettings.txt kann im Root oder im StarRupture Unterordner sein
        possible_paths = [
            os.path.join(server_dir, "DSSettings.txt"),
            os.path.join(server_dir, "StarRupture", "DSSettings.txt"),
            os.path.join(server_dir, "StarRupture", "Binaries", "Win64", "DSSettings.txt"),
        ]
        
        # Prüfen ob schon vorhanden
        for path in possible_paths:
            if os.path.exists(path):
                self.log(f"✓ DSSettings.txt gefunden: {path}")
                return
        
        # Erstellen im StarRupture Unterordner (wo auch die exe liegt)
        settings_dir = os.path.join(server_dir, "StarRupture", "Binaries", "Win64")
        if not os.path.exists(settings_dir):
            settings_dir = os.path.join(server_dir, "StarRupture")
        if not os.path.exists(settings_dir):
            settings_dir = server_dir
        
        settings_path = os.path.join(settings_dir, "DSSettings.txt")
        
        # Server-Name aus Config
        server_name = self.config.get("name", "StarRuptureServer").replace(" ", "_")
        
        default_settings = {
            "SessionName": server_name,
            "SaveGameInterval": "300",
            "StartNewGame": "true",
            "LoadSavedGame": "false",
            "SaveGameName": "AutoSave0.sav"
        }
        
        try:
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(default_settings, f, indent=2)
            self.log(f"✅ DSSettings.txt erstellt: {settings_path}")
            self.log("ℹ️ Neues Spiel wird gestartet. Nach erstem Start:")
            self.log("   → StartNewGame auf 'false' setzen")
            self.log("   → LoadSavedGame auf 'true' setzen")
        except Exception as e:
            self.log(f"⚠️ DSSettings.txt konnte nicht erstellt werden: {e}")
    
    def restart(self):
        """Startet den Server neu"""
        self.log("🔄 Neustart...")
        self.stop()
        time.sleep(3)
        return self.start()
    
    def _monitor(self):
        """Überwacht den Server-Prozess"""
        while self.monitoring_active:
            if self.process and self.process.poll() is not None:
                self.log("⚠️ Server ist abgestürzt!")
                
                # Discord Crash-Benachrichtigung
                if self.discord_notifier:
                    self.discord_notifier.notify_server_crash(self.config.get("name", "Server"))
                
                self.process = None
                self.start_time = None
                
                # Auto-Restart
                if self.config.get("auto_restart", True):
                    self.log("🔄 Auto-Restart in 5 Sekunden...")
                    time.sleep(5)
                    self.start()
                
                break
            
            time.sleep(5)
    
    def get_uptime(self):
        """Gibt die Laufzeit zurück"""
        if self.start_time:
            seconds = int(time.time() - self.start_time)
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        return "-"
    
    def create_backup(self):
        """Erstellt ein Backup"""
        try:
            self.log("💾 Erstelle Backup...")
            
            game_info = SUPPORTED_GAMES.get(self.config["game"], {})
            save_path = game_info.get("save_path", "")
            config_path = game_info.get("config_path", "")
            
            server_dir = self.get_server_dir()
            backup_dir = os.path.join(PATHS["backups"], self.server_id)
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_dir, f"{self.server_id}_{timestamp}.zip")
            
            with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Saves sichern
                if save_path:
                    full_save_path = os.path.join(server_dir, save_path.replace("/", os.sep))
                    if os.path.exists(full_save_path):
                        for root, dirs, files in os.walk(full_save_path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, server_dir)
                                zipf.write(file_path, arcname)
                
                # Config sichern
                if config_path:
                    full_config_path = os.path.join(server_dir, config_path.replace("/", os.sep))
                    if os.path.exists(full_config_path):
                        for root, dirs, files in os.walk(full_config_path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, server_dir)
                                zipf.write(file_path, arcname)
            
            self.log(f"✅ Backup erstellt: {os.path.basename(backup_file)}")
            
            # Discord Benachrichtigung
            if self.discord_notifier:
                self.discord_notifier.notify_backup(
                    self.config.get("name", "Server"),
                    os.path.basename(backup_file)
                )
            
            return True
            
        except Exception as e:
            self.log(f"❌ Backup fehlgeschlagen: {str(e)}")
            return False
    
    def get_server_logs(self, max_lines=500, search_filter="", level_filter="all"):
        """
        Liest Server-Logs aus verschiedenen Quellen:
        1. Interne Log-Messages
        2. Server-Log-Dateien
        """
        all_logs = []
        
        # 1. Interne Logs (von uns geschrieben)
        all_logs.extend(self.log_messages)
        
        # 2. Server-Log-Dateien suchen
        server_dir = self.get_server_dir()
        log_patterns = [
            "*.log",
            "logs/*.log",
            "Logs/*.log",
            "output_log*.txt",
            "ShooterGame/Saved/Logs/*.log",  # ARK
            "server/*.log",
        ]
        
        for pattern in log_patterns:
            log_path = os.path.join(server_dir, pattern)
            import glob
            for log_file in glob.glob(log_path):
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        # Letzte Zeilen lesen (nicht alles)
                        lines = f.readlines()[-200:]
                        for line in lines:
                            line = line.strip()
                            if line:
                                all_logs.append(f"[FILE] {line}")
                except:
                    pass
        
        # Filter anwenden
        if search_filter:
            search_lower = search_filter.lower()
            all_logs = [log for log in all_logs if search_lower in log.lower()]
        
        if level_filter == "errors":
            all_logs = [log for log in all_logs if any(x in log.lower() for x in ["error", "fail", "exception", "❌", "critical"])]
        elif level_filter == "warnings":
            all_logs = [log for log in all_logs if any(x in log.lower() for x in ["warn", "⚠️", "warning"])]
        
        # Auf max_lines begrenzen
        return all_logs[-max_lines:]
    
    def check_for_update(self):
        """
        Prüft ob ein Server-Update über SteamCMD verfügbar ist.
        Gibt True zurück wenn Update verfügbar, False wenn aktuell, None bei Fehler.
        """
        game_info = SUPPORTED_GAMES.get(self.config["game"], {})
        app_id = game_info.get("app_id", "")
        
        if not app_id:
            self.log("⚠️ Kein Steam App ID - Update-Check nicht möglich")
            return None
        
        # Für echte Update-Prüfung müsste man Steam API verwenden
        # Hier verwenden wir eine einfache Methode: SteamCMD app_update mit validate
        # Das lädt nur herunter wenn Update verfügbar
        self.log(f"🔍 Prüfe auf Updates für App {app_id}...")
        return True  # Für jetzt immer True - SteamCMD prüft selbst
    
    def update_server(self, progress_callback=None, username="anonymous", password=""):
        """
        Aktualisiert den Server über SteamCMD.
        Stoppt den Server vorher falls er läuft.
        """
        game_info = SUPPORTED_GAMES.get(self.config["game"], {})
        app_id = game_info.get("app_id", "")
        
        if not app_id:
            self.log("❌ Update nicht möglich - kein Steam-Spiel")
            return False
        
        was_running = self.is_running()
        
        # Server stoppen wenn läuft
        if was_running:
            self.log("⚫ Stoppe Server für Update...")
            self.stop()
            time.sleep(3)
        
        try:
            self.log(f"🔄 Aktualisiere Server (App {app_id})...")
            
            steamcmd_path = os.path.join(PATHS["steamcmd"], "steamcmd.exe")
            if not os.path.exists(steamcmd_path):
                self.log("❌ SteamCMD nicht installiert!")
                return False
            
            server_dir = self.get_server_dir()
            
            # Login-Befehl bauen
            # SteamCMD Befehl als Liste (shell=False für Sicherheit)
            cmd_list = [steamcmd_path, "+force_install_dir", server_dir]
            
            # Login
            if username == "anonymous":
                cmd_list.extend(["+login", "anonymous"])
            else:
                cmd_list.extend(["+login", username, password])
            
            # Update und Quit
            cmd_list.extend(["+app_update", str(app_id), "validate", "+quit"])
            
            self.log("📥 SteamCMD läuft...")
            
            process = subprocess.Popen(
                cmd_list,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                shell=False,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # Fortschritt lesen und Erfolg erkennen
            update_lines = []
            update_success = False
            
            for line in process.stdout:
                line = line.strip()
                if line:
                    update_lines.append(line)
                    
                    # Erfolg erkennen
                    if "Success!" in line and "fully installed" in line:
                        update_success = True
                    elif f"App '{app_id}' already up to date" in line:
                        update_success = True
                    
                    # Fortschritt parsen
                    if "progress:" in line.lower() or "downloading" in line.lower():
                        self.log(f"  {line}")
                    if progress_callback and "%" in line:
                        try:
                            # Versuche Prozent zu extrahieren
                            import re
                            match = re.search(r'(\d+(?:\.\d+)?)\s*%', line)
                            if match:
                                progress_callback(float(match.group(1)))
                        except:
                            pass
            
            process.wait()
            
            # Erfolg: Entweder returncode 0 ODER Success-Meldung
            if process.returncode == 0 or update_success:
                self.log("✅ Server erfolgreich aktualisiert!")
                
                # Server wieder starten wenn er vorher lief
                if was_running:
                    self.log("▶️ Starte Server wieder...")
                    time.sleep(2)
                    self.start()
                
                return True
            else:
                self.log(f"❌ Update fehlgeschlagen (Exit Code: {process.returncode})")
                return False
                
        except Exception as e:
            self.log(f"❌ Update-Fehler: {str(e)}")
            return False


# ==================== SETUP WIZARD ====================
