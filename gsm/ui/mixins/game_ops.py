"""Mixin: Spielspezifische Aktionen (Minecraft/Conan/Enshrouded) und Ordner-Zugriff.

Aus game_server_manager.py ausgelagert (Phase 3d, verhaltenserhaltend). Nur
Methoden, kein __init__; teilt sich self mit GameServerManagerApp.
"""

import os
import subprocess
import threading

import customtkinter as ctk
from tkinter import messagebox

from gsm.paths import PATHS
from gsm.games import SUPPORTED_GAMES
from gsm.rcon import RCONClient


class GameServerOpsMixin:
    """Minecraft/Conan/Enshrouded-Aktionen + Ordner-Oeffner (Mixin fuer GameServerManagerApp)."""

    def install_minecraft_forge(self, server_id):
        """Installiert Minecraft Forge Server"""
        t = self.config_manager.get_text
        server_config = self.config_manager.servers.get(server_id)
        if not server_config:
            return
        
        game_info = SUPPORTED_GAMES.get("Minecraft Java (Forge)", {})
        versions = game_info.get("versions", [])
        
        # Version-Auswahl Dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("⛏️ Minecraft Forge Version")
        dialog.geometry("550x600")
        dialog.transient(self)
        dialog.grab_set()
        
        # Zentrieren
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 550) // 2
        y = (dialog.winfo_screenheight() - 600) // 2
        dialog.geometry(f"550x600+{x}+{y}")
        
        # Header
        ctk.CTkLabel(
            dialog,
            text="⛏️ Minecraft Forge Server installieren",
            font=("Arial", 20, "bold")
        ).pack(pady=20)
        
        ctk.CTkLabel(
            dialog,
            text="Wähle die Minecraft & Forge Version:",
            font=("Arial", 12),
            text_color="gray"
        ).pack(pady=(0, 10))
        
        # Version Liste
        version_frame = ctk.CTkScrollableFrame(dialog, width=480, height=350)
        version_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        selected_version = ctk.StringVar()
        
        for mc_version, forge_version, recommended in versions:
            frame = ctk.CTkFrame(version_frame, fg_color="transparent")
            frame.pack(fill="x", pady=2)
            
            label_text = f"Minecraft {mc_version}  →  Forge {forge_version}"
            if recommended:
                label_text += "  ⭐ Empfohlen"
            
            rb = ctk.CTkRadioButton(
                frame,
                text=label_text,
                variable=selected_version,
                value=f"{mc_version}|{forge_version}",
                font=("Arial", 12)
            )
            rb.pack(side="left", padx=10, pady=5)
            
            # Standard: Erste empfohlene Version
            if recommended and not selected_version.get():
                selected_version.set(f"{mc_version}|{forge_version}")
        
        # RAM Auswahl
        ram_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        ram_frame.pack(fill="x", padx=30, pady=10)
        
        ctk.CTkLabel(ram_frame, text="Server RAM:", font=("Arial", 12)).pack(side="left")
        
        ram_var = ctk.StringVar(value="4G")
        ram_combo = ctk.CTkComboBox(
            ram_frame,
            values=["2G", "4G", "6G", "8G", "10G", "12G", "16G"],
            variable=ram_var,
            width=100
        )
        ram_combo.pack(side="left", padx=10)
        
        # Java Info
        ctk.CTkLabel(
            dialog,
            text="💡 Java 17+ wird benötigt für Minecraft 1.18+\n     Java 8 für ältere Versionen (1.16.5, 1.12.2)",
            font=("Arial", 12),
            text_color="gray"
        ).pack(pady=5)
        
        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=30, pady=15)
        
        def do_install():
            if not selected_version.get():
                messagebox.showerror(t("error"), "Bitte Version auswählen!")
                return
            
            mc_ver, forge_ver = selected_version.get().split("|")
            ram = ram_var.get()
            dialog.destroy()
            
            # Server-Config aktualisieren
            server_config["mc_version"] = mc_ver
            server_config["forge_version"] = forge_ver
            server_config["ram"] = ram
            self.config_manager.save_servers()
            
            # Installation starten
            self._do_minecraft_forge_install(server_id, mc_ver, forge_ver, ram)
        
        ctk.CTkButton(
            btn_frame,
            text="📥 Installieren",
            command=do_install,
            fg_color="#2B7A2B",
            hover_color="#236323",
            width=200
        ).pack(side="left", padx=10)
        
        ctk.CTkButton(
            btn_frame,
            text="Abbrechen",
            command=dialog.destroy,
            fg_color="gray",
            width=120
        ).pack(side="right", padx=10)
    
    def _do_minecraft_forge_install(self, server_id, mc_version, forge_version, ram):
        """Führt die Minecraft Forge Installation durch"""
        def do_install():
            try:
                instance = self.server_instances.get(server_id)
                server_dir = os.path.join(PATHS["servers"], server_id)
                os.makedirs(server_dir, exist_ok=True)
                
                if instance:
                    instance.log(f"⛏️ Installiere Minecraft {mc_version} mit Forge {forge_version}...")
                
                # 1. Java prüfen
                if instance:
                    instance.log("🔍 Prüfe Java Installation...")
                
                java_path = self._find_java()
                if not java_path:
                    if instance:
                        instance.log("❌ Java nicht gefunden!")
                        instance.log("💡 Bitte Java 17+ installieren: https://adoptium.net/")
                    return
                
                if instance:
                    instance.log(f"✓ Java gefunden: {java_path}")
                
                # 2. Forge Installer herunterladen
                # Format: https://maven.minecraftforge.net/net/minecraftforge/forge/1.20.1-47.3.22/forge-1.20.1-47.3.22-installer.jar
                forge_full_version = f"{mc_version}-{forge_version}"
                installer_url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{forge_full_version}/forge-{forge_full_version}-installer.jar"
                installer_path = os.path.join(server_dir, f"forge-{forge_full_version}-installer.jar")
                
                if instance:
                    instance.log(f"📥 Lade Forge Installer herunter...")
                    instance.log(f"   URL: {installer_url}")
                
                try:
                    import urllib.request
                    urllib.request.urlretrieve(installer_url, installer_path)
                except Exception as e:
                    if instance:
                        instance.log(f"❌ Download fehlgeschlagen: {e}")
                        instance.log("💡 Versuche alternativen Download...")
                    
                    # Alternativer URL für ältere Versionen
                    alt_url = f"https://files.minecraftforge.net/maven/net/minecraftforge/forge/{forge_full_version}/forge-{forge_full_version}-installer.jar"
                    try:
                        urllib.request.urlretrieve(alt_url, installer_path)
                    except:
                        if instance:
                            instance.log(f"❌ Auch alternativer Download fehlgeschlagen!")
                            instance.log("💡 Bitte manuell herunterladen von: https://files.minecraftforge.net/")
                        return
                
                if instance:
                    instance.log("✓ Forge Installer heruntergeladen")
                
                # 3. Forge Installer ausführen
                if instance:
                    instance.log("🔧 Führe Forge Installer aus (kann 1-3 Minuten dauern)...")
                
                install_cmd = [java_path, "-jar", installer_path, "--installServer"]
                
                process = subprocess.Popen(
                    install_cmd,
                    cwd=server_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    shell=False
                )
                
                for line in process.stdout:
                    line_stripped = line.strip()
                    if line_stripped and instance:
                        # Nur wichtige Zeilen loggen
                        if any(x in line_stripped.lower() for x in ["download", "install", "extract", "error", "success", "complete"]):
                            instance.log(f"   {line_stripped}")
                
                process.wait()
                
                if process.returncode != 0:
                    if instance:
                        instance.log(f"❌ Forge Installation fehlgeschlagen (Code: {process.returncode})")
                    return
                
                if instance:
                    instance.log("✓ Forge Installation abgeschlossen")
                
                # 4. run.bat erstellen falls nicht vorhanden
                run_bat = os.path.join(server_dir, "run.bat")
                if not os.path.exists(run_bat):
                    # Suche nach der Server JAR
                    server_jar = None
                    for f in os.listdir(server_dir):
                        if f.startswith("forge-") and f.endswith("-server.jar"):
                            server_jar = f
                            break
                        elif f.startswith("forge-") and f.endswith("-shim.jar"):
                            server_jar = f
                            break
                    
                    if not server_jar:
                        # Neuere Forge Versionen haben andere Namen
                        for f in os.listdir(server_dir):
                            if "forge" in f.lower() and f.endswith(".jar") and "installer" not in f.lower():
                                server_jar = f
                                break
                    
                    if server_jar:
                        # run.bat erstellen
                        bat_content = f'''@echo off
java -Xmx{ram} -Xms{ram} -jar {server_jar} nogui
pause
'''
                        with open(run_bat, 'w') as f:
                            f.write(bat_content)
                        
                        if instance:
                            instance.log(f"✓ run.bat erstellt mit {ram} RAM")
                
                # 5. eula.txt akzeptieren
                eula_path = os.path.join(server_dir, "eula.txt")
                with open(eula_path, 'w') as f:
                    f.write("# EULA akzeptiert durch Game Server Manager\neula=true\n")
                
                if instance:
                    instance.log("✓ EULA akzeptiert")
                
                # 6. server.properties erstellen
                server_props = os.path.join(server_dir, "server.properties")
                if not os.path.exists(server_props):
                    server_name = self.config_manager.servers.get(server_id, {}).get("name", "Minecraft Server")
                    props_content = f'''#Minecraft server properties
server-port=25565
motd={server_name}
max-players=20
online-mode=true
difficulty=normal
gamemode=survival
level-name=world
enable-command-block=true
spawn-protection=0
'''
                    with open(server_props, 'w') as f:
                        f.write(props_content)
                    
                    if instance:
                        instance.log("✓ server.properties erstellt")
                
                # 7. Mods Ordner erstellen
                mods_dir = os.path.join(server_dir, "mods")
                os.makedirs(mods_dir, exist_ok=True)
                
                if instance:
                    instance.log("✓ Mods Ordner erstellt")
                
                # 8. Installation als abgeschlossen markieren
                self.config_manager.servers[server_id]["installed"] = True
                self.config_manager.save_servers()
                
                if instance:
                    instance.log("")
                    instance.log("=" * 50)
                    instance.log("✅ MINECRAFT FORGE SERVER INSTALLIERT!")
                    instance.log("=" * 50)
                    instance.log("")
                    instance.log("📁 Mods-Ordner: " + mods_dir)
                    instance.log("💡 Kopiere deine .jar Mod-Dateien in den Mods-Ordner")
                    instance.log("")
                    instance.log("🎮 Server kann jetzt gestartet werden!")
                
                # UI aktualisieren
                self.after(0, lambda: self.select_server(server_id))
                
            except Exception as e:
                if instance:
                    instance.log(f"❌ Fehler: {str(e)}")
                import traceback
                traceback.print_exc()
        
        threading.Thread(target=do_install, daemon=True).start()
    
    def _find_java(self):
        """Sucht nach Java Installation"""
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
                # Suche nach java.exe in Unterordnern
                for root, dirs, files in os.walk(base_path):
                    if "java.exe" in files:
                        return os.path.join(root, "java.exe")
        
        return None
    
    def open_minecraft_mods_folder(self, server_id):
        """Öffnet den Minecraft Mods-Ordner im Explorer"""
        server_dir = os.path.join(PATHS["servers"], server_id)
        mods_dir = os.path.join(server_dir, "mods")
        
        # Erstellen falls nicht vorhanden
        os.makedirs(mods_dir, exist_ok=True)
        
        # Im Explorer öffnen
        if os.name == 'nt':
            os.startfile(mods_dir)
        else:
            subprocess.run(["xdg-open", mods_dir])
        
        instance = self.server_instances.get(server_id)
        if instance:
            instance.log(f"📁 Mods-Ordner geöffnet: {mods_dir}")
    
    # ============ CONAN EXILES FUNKTIONEN ============
    
    def save_conan_world(self, server_id):
        """Speichert die Conan Exiles Welt über RCON"""
        server_config = self.config_manager.servers.get(server_id, {})
        instance = self.server_instances.get(server_id)
        
        if not instance or not instance.is_running():
            messagebox.showwarning("Server nicht aktiv", "Der Server muss laufen um zu speichern!")
            return
        
        # RCON Einstellungen
        rcon_port = server_config.get("rcon_port", 25575)
        rcon_password = server_config.get("admin_password", server_config.get("rcon_password", ""))
        
        if not rcon_password:
            # Dialog für RCON Setup
            self.show_conan_rcon_setup(server_id)
            return
        
        try:
            # RCON Befehl senden
            rcon = RCONClient(host="127.0.0.1", port=rcon_port, password=rcon_password)
            response, error = rcon.send_command("SaveWorld")
            
            if error:
                instance.log(f"⚠️ RCON Fehler: {error}")
                # Alternative Meldung
                messagebox.showinfo(
                    "💾 Speichern",
                    "RCON nicht verfügbar.\n\n"
                    "Alternative: Im Spiel als Admin:\n"
                    "1. ESC → Admin Panel\n"
                    "2. Oder Konsole (~): SaveWorld\n\n"
                    "Der Server speichert auch automatisch alle 15 Min."
                )
            else:
                instance.log("💾 Welt gespeichert!")
                messagebox.showinfo("💾 Gespeichert", "Die Welt wurde erfolgreich gespeichert!")
                # Server-Details neu laden für aktualisierte Zeit
                self.show_server_details(server_id)
                
        except Exception as e:
            instance.log(f"❌ Speichern fehlgeschlagen: {e}")
            messagebox.showerror("Fehler", f"Speichern fehlgeschlagen:\n{e}")
    
    def show_conan_rcon_setup(self, server_id):
        """Zeigt RCON Setup Dialog für Conan Exiles"""
        server_config = self.config_manager.servers.get(server_id, {})
        server_dir = os.path.join(PATHS["servers"], server_id)
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("⚙️ RCON einrichten")
        dialog.geometry("500x400")
        dialog.transient(self)
        dialog.grab_set()
        
        # Anleitung
        ctk.CTkLabel(
            dialog,
            text="⚔️ RCON für Conan Exiles einrichten",
            font=("Arial", 16, "bold")
        ).pack(pady=20)
        
        info_text = """Um die Speichern-Funktion zu nutzen, muss RCON aktiviert werden.

1. Öffne: ServerSettings.ini
   (Button unten)

2. Füge diese Zeilen hinzu:
   RCONEnabled=True
   RCONPort=25575
   RCONPassword=dein_passwort

3. Server neustarten

4. Admin-Passwort hier eingeben:"""
        
        ctk.CTkLabel(
            dialog,
            text=info_text,
            font=("Arial", 11),
            justify="left"
        ).pack(padx=20, pady=10)
        
        # Passwort Eingabe
        pass_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        pass_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(pass_frame, text="Admin/RCON Passwort:").pack(side="left")
        pass_entry = ctk.CTkEntry(pass_frame, width=200, show="*")
        pass_entry.pack(side="left", padx=10)
        pass_entry.insert(0, server_config.get("admin_password", ""))
        
        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)
        
        def save_password():
            password = pass_entry.get().strip()
            if password:
                server_config["admin_password"] = password
                server_config["rcon_password"] = password
                server_config["rcon_port"] = 25575
                self.config_manager.servers[server_id] = server_config
                self.config_manager.save_servers()
                messagebox.showinfo("✅ Gespeichert", "RCON-Passwort wurde gespeichert!")
                dialog.destroy()
        
        def open_settings_ini():
            ini_path = os.path.join(server_dir, "ConanSandbox", "Saved", "Config", "WindowsServer", "ServerSettings.ini")
            if os.path.exists(ini_path):
                if os.name == 'nt':
                    os.startfile(ini_path)
                else:
                    subprocess.run(["xdg-open", ini_path])
            else:
                messagebox.showwarning("Nicht gefunden", f"Datei nicht gefunden:\n{ini_path}\n\nServer zuerst starten!")
        
        ctk.CTkButton(
            btn_frame,
            text="📄 ServerSettings.ini öffnen",
            command=open_settings_ini,
            fg_color="#FF9800",
            hover_color="#F57C00"
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text="💾 Passwort speichern",
            command=save_password,
            fg_color="#2B7A2B",
            hover_color="#236323"
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text="Abbrechen",
            command=dialog.destroy,
            fg_color="#666",
            hover_color="#555"
        ).pack(side="right", padx=5)
    
    def open_conan_mods_folder(self, server_id):
        """Öffnet den Conan Exiles Mods-Ordner im Explorer"""
        server_dir = os.path.join(PATHS["servers"], server_id)
        mods_dir = os.path.join(server_dir, "ConanSandbox", "Mods")
        
        # Erstellen falls nicht vorhanden
        os.makedirs(mods_dir, exist_ok=True)
        
        # Im Explorer öffnen
        if os.name == 'nt':
            os.startfile(mods_dir)
        else:
            subprocess.run(["xdg-open", mods_dir])
        
        instance = self.server_instances.get(server_id)
        if instance:
            instance.log(f"📁 Mods-Ordner geöffnet: {mods_dir}")
    
    def open_conan_save_folder(self, server_id):
        """Öffnet den Conan Exiles Save-Ordner im Explorer"""
        server_dir = os.path.join(PATHS["servers"], server_id)
        save_dir = os.path.join(server_dir, "ConanSandbox", "Saved")
        
        # Im Explorer öffnen
        if os.path.exists(save_dir):
            if os.name == 'nt':
                os.startfile(save_dir)
            else:
                subprocess.run(["xdg-open", save_dir])
            
            instance = self.server_instances.get(server_id)
            if instance:
                instance.log(f"📂 Savegame-Ordner geöffnet: {save_dir}")
        else:
            messagebox.showwarning("Nicht gefunden", "Savegame-Ordner existiert noch nicht.\nServer zuerst starten!")

    def set_conan_auto_mod_update(self, server_id, enabled):
        server_config = self.config_manager.servers.get(server_id)
        if not server_config or server_config.get("game") != "Conan Exiles":
            return
        server_config["conan_auto_mod_update"] = bool(enabled)
        self.config_manager.save_servers()
        instance = self.server_instances.get(server_id)
        if instance:
            instance.config = server_config
            instance.log(f"🧩 Conan Auto-Mod-Update {'aktiviert' if enabled else 'deaktiviert'}")

    def sync_conan_mods_now(self, server_id):
        server_config = self.config_manager.servers.get(server_id)
        instance = self.server_instances.get(server_id)
        if not server_config or server_config.get("game") != "Conan Exiles" or not instance:
            return

        def do_sync():
            ok = instance.sync_conan_mods()
            self.after(0, lambda: self.select_server(server_id))
            if ok:
                self.after(0, lambda: messagebox.showinfo("Conan Mods", "Conan Mod-Sync abgeschlossen."))
            else:
                self.after(0, lambda: messagebox.showwarning("Conan Mods", "Conan Mod-Sync fehlgeschlagen. Bitte Logs prüfen."))

        threading.Thread(target=do_sync, daemon=True).start()
    
    # ============ END CONAN EXILES FUNKTIONEN ============
    
    # ============ ENSHROUDED FUNKTIONEN ============
    
    def open_enshrouded_config(self, server_id):
        """Öffnet die Enshrouded Server-Config (JSON)"""
        server_dir = os.path.join(PATHS["servers"], server_id)
        config_file = os.path.join(server_dir, "enshrouded_server.json")
        
        if os.path.exists(config_file):
            if os.name == 'nt':
                os.startfile(config_file)
            else:
                subprocess.run(["xdg-open", config_file])
            
            instance = self.server_instances.get(server_id)
            if instance:
                instance.log(f"⚙️ Config geöffnet: enshrouded_server.json")
        else:
            # Config-Vorlage erstellen
            result = messagebox.askyesno(
                "Config nicht gefunden",
                "Die Config-Datei existiert noch nicht.\n\n"
                "Sie wird beim ersten Server-Start automatisch erstellt.\n\n"
                "Möchtest du eine Vorlage erstellen?"
            )
            if result:
                self.create_enshrouded_config_template(server_id)
    
    def create_enshrouded_config_template(self, server_id):
        """Erstellt eine Enshrouded Config-Vorlage"""
        server_dir = os.path.join(PATHS["servers"], server_id)
        config_file = os.path.join(server_dir, "enshrouded_server.json")
        
        template = {
            "name": "Enshrouded Server",
            "saveDirectory": "./savegame",
            "logDirectory": "./logs",
            "ip": "0.0.0.0",
            "queryPort": 15637,
            "slotCount": 16,
            "voiceChatMode": "Proximity",
            "enableVoiceChat": False,
            "enableTextChat": False,
            "gameSettingsPreset": "Default",
            "gameSettings": {
                "playerHealthFactor": 1,
                "playerManaFactor": 1,
                "playerStaminaFactor": 1,
                "enableDurability": True,
                "enableStarvingDebuff": False,
                "foodBuffDurationFactor": 1,
                "shroudTimeFactor": 1,
                "tombstoneMode": "AddBackpackMaterials",
                "miningDamageFactor": 1,
                "plantGrowthSpeedFactor": 1,
                "resourceDropStackAmountFactor": 1,
                "factoryProductionSpeedFactor": 1,
                "experienceCombatFactor": 1,
                "experienceMiningFactor": 1,
                "experienceExplorationQuestsFactor": 1
            }
        }
        
        import json
        os.makedirs(server_dir, exist_ok=True)
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=2)
        
        messagebox.showinfo("✅ Erstellt", f"Config-Vorlage erstellt:\n{config_file}")
        
        # Öffnen
        if os.name == 'nt':
            os.startfile(config_file)
        else:
            subprocess.run(["xdg-open", config_file])
    
    def open_enshrouded_save_folder(self, server_id):
        """Öffnet den Enshrouded Savegame-Ordner"""
        server_dir = os.path.join(PATHS["servers"], server_id)
        save_dir = os.path.join(server_dir, "savegame")
        
        # Erstellen falls nicht vorhanden
        os.makedirs(save_dir, exist_ok=True)
        
        if os.name == 'nt':
            os.startfile(save_dir)
        else:
            subprocess.run(["xdg-open", save_dir])
        
        instance = self.server_instances.get(server_id)
        if instance:
            instance.log(f"📂 Savegame-Ordner geöffnet: {save_dir}")
    
    def open_enshrouded_logs_folder(self, server_id):
        """Öffnet den Enshrouded Logs-Ordner"""
        server_dir = os.path.join(PATHS["servers"], server_id)
        logs_dir = os.path.join(server_dir, "logs")
        
        # Erstellen falls nicht vorhanden
        os.makedirs(logs_dir, exist_ok=True)
        
        if os.name == 'nt':
            os.startfile(logs_dir)
        else:
            subprocess.run(["xdg-open", logs_dir])
        
        instance = self.server_instances.get(server_id)
        if instance:
            instance.log(f"📋 Logs-Ordner geöffnet: {logs_dir}")
    
    # ============ END ENSHROUDED FUNKTIONEN ============
    
    # ============ UNIVERSAL SERVER FOLDER FUNKTIONEN ============
    
    def open_server_folder(self, server_id):
        """Öffnet den Haupt-Server-Ordner"""
        server_dir = os.path.join(PATHS["servers"], server_id)
        
        if os.path.exists(server_dir):
            if os.name == 'nt':
                os.startfile(server_dir)
            else:
                subprocess.run(["xdg-open", server_dir])
            
            instance = self.server_instances.get(server_id)
            if instance:
                instance.log(f"📂 Server-Ordner geöffnet")
        else:
            messagebox.showwarning("Nicht gefunden", "Server-Ordner existiert noch nicht.\nServer zuerst installieren!")
    
    def open_config_folder(self, server_id):
        """Öffnet den Config-Ordner basierend auf Spiel-Definition"""
        server_config = self.config_manager.servers.get(server_id, {})
        server_dir = os.path.join(PATHS["servers"], server_id)
        game_info = SUPPORTED_GAMES.get(server_config.get("game", ""), {})
        
        config_path = game_info.get("config_path", "")
        if config_path:
            # Prüfen ob es eine Datei oder ein Ordner ist
            full_path = os.path.join(server_dir, config_path)
            
            if os.path.isfile(full_path):
                # Es ist eine Datei - direkt öffnen
                if os.name == 'nt':
                    os.startfile(full_path)
                else:
                    subprocess.run(["xdg-open", full_path])
            elif os.path.isdir(full_path):
                # Es ist ein Ordner - im Explorer öffnen
                if os.name == 'nt':
                    os.startfile(full_path)
                else:
                    subprocess.run(["xdg-open", full_path])
            else:
                # Pfad existiert nicht - Ordner erstellen oder Hinweis geben
                parent_dir = os.path.dirname(full_path)
                if os.path.exists(parent_dir):
                    if os.name == 'nt':
                        os.startfile(parent_dir)
                    else:
                        subprocess.run(["xdg-open", parent_dir])
                else:
                    messagebox.showwarning(
                        "Nicht gefunden", 
                        f"Config-Pfad nicht gefunden:\n{full_path}\n\nServer zuerst starten!"
                    )
                    return
            
            instance = self.server_instances.get(server_id)
            if instance:
                instance.log(f"⚙️ Config-Ordner geöffnet: {config_path}")
        else:
            # Kein config_path definiert - Server-Ordner öffnen
            self.open_server_folder(server_id)
    
    def open_save_folder(self, server_id):
        """Öffnet den Savegame-Ordner basierend auf Spiel-Definition"""
        server_config = self.config_manager.servers.get(server_id, {})
        server_dir = os.path.join(PATHS["servers"], server_id)
        game_info = SUPPORTED_GAMES.get(server_config.get("game", ""), {})
        
        save_path = game_info.get("save_path", "")
        if save_path:
            full_path = os.path.join(server_dir, save_path)
            
            # Ordner erstellen falls nicht vorhanden
            os.makedirs(full_path, exist_ok=True)
            
            if os.name == 'nt':
                os.startfile(full_path)
            else:
                subprocess.run(["xdg-open", full_path])
            
            instance = self.server_instances.get(server_id)
            if instance:
                instance.log(f"💾 Savegame-Ordner geöffnet: {save_path}")
        else:
            # Kein save_path definiert - Server-Ordner öffnen
            self.open_server_folder(server_id)
    
    def open_logs_folder(self, server_id):
        """Öffnet den Logs-Ordner (versucht verschiedene Pfade)"""
        server_config = self.config_manager.servers.get(server_id, {})
        server_dir = os.path.join(PATHS["servers"], server_id)
        game = server_config.get("game", "")
        
        # Bekannte Log-Pfade für verschiedene Spiele
        log_paths = [
            "logs",
            "Logs",
            "log",
            "Log",
            "ShooterGame/Saved/Logs",  # ARK
            "ConanSandbox/Saved/Logs",  # Conan Exiles
            "Pal/Saved/Logs",  # Palworld
            "Saved/Logs",
            "serverfiles/logs",
        ]
        
        # Spezifische Pfade basierend auf Spiel
        game_log_paths = {
            "ARK: Survival Ascended": ["ShooterGame/Saved/Logs"],
            "Conan Exiles": ["ConanSandbox/Saved/Logs"],
            "Palworld": ["Pal/Saved/Logs"],
            "Enshrouded": ["logs"],
            "Valheim": ["logs"],
            "Satisfactory": ["FactoryGame/Saved/Logs"],
            "7 Days to Die": ["7DaysToDieServer_Data"],
            "Rust": ["RustDedicated_Data"],
        }
        
        # Spiel-spezifische Pfade zuerst versuchen
        if game in game_log_paths:
            log_paths = game_log_paths[game] + log_paths
        
        # Ersten existierenden Pfad finden
        for log_path in log_paths:
            full_path = os.path.join(server_dir, log_path)
            if os.path.exists(full_path):
                if os.name == 'nt':
                    os.startfile(full_path)
                else:
                    subprocess.run(["xdg-open", full_path])
                
                instance = self.server_instances.get(server_id)
                if instance:
                    instance.log(f"📋 Logs-Ordner geöffnet: {log_path}")
                return
        
        # Kein Log-Ordner gefunden - "logs" Ordner erstellen
        default_logs = os.path.join(server_dir, "logs")
        os.makedirs(default_logs, exist_ok=True)
        
        if os.name == 'nt':
            os.startfile(default_logs)
        else:
            subprocess.run(["xdg-open", default_logs])
        
        instance = self.server_instances.get(server_id)
        if instance:
            instance.log(f"📋 Logs-Ordner erstellt und geöffnet: logs")
    
    # ============ END UNIVERSAL SERVER FOLDER FUNKTIONEN ============
    
    def show_minecraft_properties_editor(self, server_id):
        """Zeigt Editor für server.properties"""
        t = self.config_manager.get_text
        server_config = self.config_manager.servers.get(server_id, {})
        server_dir = os.path.join(PATHS["servers"], server_id)
        props_path = os.path.join(server_dir, "server.properties")
        
        # Properties laden
        properties = {}
        if os.path.exists(props_path):
            with open(props_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        properties[key.strip()] = value.strip()
        
        # Dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("⚙️ Minecraft Server Einstellungen")
        dialog.geometry("500x550")
        dialog.transient(self)
        dialog.grab_set()
        
        # Zentrieren
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 500) // 2
        y = (dialog.winfo_screenheight() - 550) // 2
        dialog.geometry(f"500x550+{x}+{y}")
        
        # Header
        ctk.CTkLabel(
            dialog,
            text="⚙️ Server Einstellungen",
            font=("Arial", 20, "bold")
        ).pack(pady=20)
        
        # Scrollable Frame
        scroll = ctk.CTkScrollableFrame(dialog, width=450, height=380)
        scroll.pack(fill="both", expand=True, padx=20, pady=10)
        
        entries = {}
        
        # Wichtige Einstellungen
        settings = [
            ("server-port", "Server Port", "25565"),
            ("max-players", "Max Spieler", "20"),
            ("motd", "Server Beschreibung (MOTD)", "A Minecraft Server"),
            ("gamemode", "Spielmodus (survival/creative/adventure)", "survival"),
            ("difficulty", "Schwierigkeit (peaceful/easy/normal/hard)", "normal"),
            ("pvp", "PvP erlaubt (true/false)", "true"),
            ("online-mode", "Online Mode (true/false)", "true"),
            ("white-list", "Whitelist aktiv (true/false)", "false"),
            ("spawn-protection", "Spawn Schutz Radius", "16"),
            ("view-distance", "Sichtweite (Chunks)", "10"),
            ("simulation-distance", "Simulation Distanz", "10"),
            ("level-name", "Welt Name", "world"),
            ("level-seed", "Welt Seed (leer = zufällig)", ""),
            ("enable-command-block", "Command Blocks (true/false)", "true"),
        ]
        
        for key, label, default in settings:
            frame = ctk.CTkFrame(scroll, fg_color="transparent")
            frame.pack(fill="x", pady=3)
            
            ctk.CTkLabel(frame, text=label + ":", width=250, anchor="w").pack(side="left", padx=5)
            
            entry = ctk.CTkEntry(frame, width=180)
            entry.insert(0, properties.get(key, default))
            entry.pack(side="right", padx=5)
            entries[key] = entry
        
        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=15)
        
        def save_properties():
            # Alle Properties laden (um andere nicht zu verlieren)
            all_props = {}
            if os.path.exists(props_path):
                with open(props_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line_stripped = line.strip()
                        if line_stripped and not line_stripped.startswith('#') and '=' in line_stripped:
                            key, value = line_stripped.split('=', 1)
                            all_props[key.strip()] = value.strip()
            
            # Neue Werte setzen
            for key, entry in entries.items():
                all_props[key] = entry.get()
            
            # Speichern
            with open(props_path, 'w', encoding='utf-8') as f:
                f.write("#Minecraft server properties\n")
                f.write(f"#Modified by Game Server Manager\n")
                for key, value in sorted(all_props.items()):
                    f.write(f"{key}={value}\n")
            
            # Port in Server-Config aktualisieren
            try:
                new_port = int(entries["server-port"].get())
                self.config_manager.servers[server_id]["port"] = new_port
                self.config_manager.servers[server_id]["query_port"] = new_port
                self.config_manager.save_servers()
            except:
                pass
            
            instance = self.server_instances.get(server_id)
            if instance:
                instance.log("✅ Server Einstellungen gespeichert!")
                instance.log("⚠️ Server-Neustart erforderlich!")
            
            dialog.destroy()
            self.select_server(server_id)
        
        ctk.CTkButton(
            btn_frame,
            text="💾 Speichern",
            command=save_properties,
            fg_color="#2B7A2B",
            hover_color="#236323",
            width=150
        ).pack(side="left", padx=10)
        
        ctk.CTkButton(
            btn_frame,
            text="Abbrechen",
            command=dialog.destroy,
            fg_color="gray",
            width=100
        ).pack(side="right", padx=10)
    
    def show_minecraft_ram_dialog(self, server_id):
        """Dialog zum Ändern des RAM"""
        server_config = self.config_manager.servers.get(server_id, {})
        current_ram = server_config.get("ram", "4G")
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("💾 RAM ändern")
        dialog.geometry("350x200")
        dialog.transient(self)
        dialog.grab_set()
        
        # Zentrieren
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 350) // 2
        y = (dialog.winfo_screenheight() - 200) // 2
        dialog.geometry(f"350x200+{x}+{y}")
        
        ctk.CTkLabel(
            dialog,
            text="💾 Server RAM ändern",
            font=("Arial", 18, "bold")
        ).pack(pady=20)
        
        ctk.CTkLabel(
            dialog,
            text=f"Aktuell: {current_ram}",
            font=("Arial", 12),
            text_color="gray"
        ).pack()
        
        ram_var = ctk.StringVar(value=current_ram)
        ram_combo = ctk.CTkComboBox(
            dialog,
            values=["2G", "4G", "6G", "8G", "10G", "12G", "16G", "20G", "24G", "32G"],
            variable=ram_var,
            width=150
        )
        ram_combo.pack(pady=15)
        
        def save_ram():
            new_ram = ram_var.get()
            self.config_manager.servers[server_id]["ram"] = new_ram
            self.config_manager.save_servers()
            
            # run.bat aktualisieren
            server_dir = os.path.join(PATHS["servers"], server_id)
            run_bat = os.path.join(server_dir, "run.bat")
            
            if os.path.exists(run_bat):
                # Server JAR finden
                server_jar = None
                for f in os.listdir(server_dir):
                    if "forge" in f.lower() and f.endswith(".jar") and "installer" not in f.lower():
                        server_jar = f
                        break
                
                if server_jar:
                    bat_content = f'''@echo off
java -Xmx{new_ram} -Xms{new_ram} -jar {server_jar} nogui
pause
'''
                    with open(run_bat, 'w') as f:
                        f.write(bat_content)
            
            instance = self.server_instances.get(server_id)
            if instance:
                instance.log(f"✅ RAM geändert: {current_ram} → {new_ram}")
                instance.log("⚠️ Server-Neustart erforderlich!")
            
            dialog.destroy()
            self.select_server(server_id)
        
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkButton(
            btn_frame,
            text="💾 Speichern",
            command=save_ram,
            fg_color="#2B7A2B",
            width=100
        ).pack(side="left", padx=10)
        
        ctk.CTkButton(
            btn_frame,
            text="Abbrechen",
            command=dialog.destroy,
            fg_color="gray",
            width=100
        ).pack(side="right", padx=10)
    
    def show_minecraft_version_change(self, server_id):
        """Dialog zum Wechseln der Forge Version"""
        t = self.config_manager.get_text
        server_config = self.config_manager.servers.get(server_id, {})
        current_mc = server_config.get("mc_version", "?")
        current_forge = server_config.get("forge_version", "?")
        
        game_info = SUPPORTED_GAMES.get("Minecraft Java (Forge)", {})
        versions = game_info.get("versions", [])
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("🔄 Forge Version wechseln")
        dialog.geometry("550x550")
        dialog.transient(self)
        dialog.grab_set()
        
        # Zentrieren
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 550) // 2
        y = (dialog.winfo_screenheight() - 550) // 2
        dialog.geometry(f"550x550+{x}+{y}")
        
        # Header
        ctk.CTkLabel(
            dialog,
            text="🔄 Forge Version wechseln",
            font=("Arial", 20, "bold")
        ).pack(pady=20)
        
        ctk.CTkLabel(
            dialog,
            text=f"Aktuell: Minecraft {current_mc} | Forge {current_forge}",
            font=("Arial", 12),
            text_color="#00d4ff"
        ).pack(pady=(0, 10))
        
        # Warning
        ctk.CTkLabel(
            dialog,
            text="⚠️ ACHTUNG: Versionswechsel kann Mods inkompatibel machen!\nMache vorher ein Backup!",
            font=("Arial", 11),
            text_color="orange"
        ).pack(pady=5)
        
        # Version Liste
        version_frame = ctk.CTkScrollableFrame(dialog, width=480, height=300)
        version_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        selected_version = ctk.StringVar()
        
        for mc_version, forge_version, recommended in versions:
            frame = ctk.CTkFrame(version_frame, fg_color="transparent")
            frame.pack(fill="x", pady=2)
            
            label_text = f"Minecraft {mc_version}  →  Forge {forge_version}"
            if recommended:
                label_text += "  ⭐"
            if mc_version == current_mc and forge_version == current_forge:
                label_text += "  (Aktuell)"
            
            rb = ctk.CTkRadioButton(
                frame,
                text=label_text,
                variable=selected_version,
                value=f"{mc_version}|{forge_version}",
                font=("Arial", 12)
            )
            rb.pack(side="left", padx=10, pady=5)
        
        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=30, pady=15)
        
        def do_version_change():
            if not selected_version.get():
                messagebox.showerror(t("error"), "Bitte Version auswählen!")
                return
            
            mc_ver, forge_ver = selected_version.get().split("|")
            
            if mc_ver == current_mc and forge_ver == current_forge:
                messagebox.showinfo(t("info"), "Diese Version ist bereits installiert!")
                return
            
            if not messagebox.askyesno(
                "⚠️ Bestätigung",
                f"Wirklich auf Minecraft {mc_ver} / Forge {forge_ver} wechseln?\n\n"
                "Deine Mods könnten inkompatibel werden!\n"
                "Welt-Daten bleiben erhalten."
            ):
                return
            
            dialog.destroy()
            
            # Server Config aktualisieren
            ram = server_config.get("ram", "4G")
            self.config_manager.servers[server_id]["mc_version"] = mc_ver
            self.config_manager.servers[server_id]["forge_version"] = forge_ver
            self.config_manager.save_servers()
            
            # Neuinstallation starten
            self._do_minecraft_forge_install(server_id, mc_ver, forge_ver, ram)
        
        ctk.CTkButton(
            btn_frame,
            text="🔄 Version wechseln",
            command=do_version_change,
            fg_color="#9C27B0",
            hover_color="#7B1FA2",
            width=180
        ).pack(side="left", padx=10)
        
        ctk.CTkButton(
            btn_frame,
            text="Abbrechen",
            command=dialog.destroy,
            fg_color="gray",
            width=120
        ).pack(side="right", padx=10)
    
    def delete_minecraft_mod(self, server_id, mod_file):
        """Löscht eine Minecraft Mod"""
        t = self.config_manager.get_text
        
        if not messagebox.askyesno(
            t("warning"),
            f"Mod '{mod_file}' wirklich löschen?"
        ):
            return
        
        server_dir = os.path.join(PATHS["servers"], server_id)
        mod_path = os.path.join(server_dir, "mods", mod_file)
        
        try:
            os.remove(mod_path)
            
            instance = self.server_instances.get(server_id)
            if instance:
                instance.log(f"🗑️ Mod gelöscht: {mod_file}")
            
            self.select_server(server_id)
        except Exception as e:
            messagebox.showerror(t("error"), f"Fehler beim Löschen: {e}")
