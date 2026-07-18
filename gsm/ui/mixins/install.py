"""Mixin: Server-Installation und -Update (SteamCMD, Login-Dialoge).

Aus game_server_manager.py ausgelagert (Phase 3c, verhaltenserhaltend). Nur
Methoden, kein __init__; teilt sich self mit GameServerManagerApp.
"""

import os
import time
import shutil
import zipfile
import subprocess
import threading

import requests
import customtkinter as ctk
from tkinter import messagebox

from gsm.paths import PATHS
from gsm.games import SUPPORTED_GAMES


class InstallUpdateMixin:
    """SteamCMD-Installation/-Update von Game-Servern (Mixin fuer GameServerManagerApp)."""

    def update_game_server(self, server_id):
        """Aktualisiert einen Game-Server über SteamCMD"""
        t = self.config_manager.get_text
        instance = self.server_instances.get(server_id)
        server_config = self.config_manager.servers.get(server_id, {})
        
        if not instance:
            return
        
        game_info = SUPPORTED_GAMES.get(server_config.get("game", ""), {})
        if not game_info.get("app_id"):
            messagebox.showerror(t("error"), "Kein Steam-Spiel - Update nicht möglich!")
            return
        
        # Warnung wenn Server läuft
        if instance.is_running():
            if not messagebox.askyesno(
                t("warning"),
                "Der Server läuft noch!\n\nEr wird für das Update gestoppt und danach automatisch wieder gestartet.\n\nFortfahren?"
            ):
                return
        
        # Prüfe ob Steam-Login erforderlich ist
        requires_login = game_info.get("requires_login", False)
        
        if requires_login:
            # Steam-Login Dialog für Update
            self._show_update_login_dialog(server_id, instance, server_config, game_info)
        else:
            # Normales Update mit anonymous
            self._do_server_update(server_id, instance, server_config, "anonymous", "")
    
    def _show_update_login_dialog(self, server_id, instance, server_config, game_info):
        """Zeigt Login-Dialog für Server-Update"""
        t = self.config_manager.get_text
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("🔐 Steam Login für Update")
        dialog.geometry("450x300")
        dialog.transient(self)
        dialog.grab_set()
        
        # Zentrieren
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 450) // 2
        y = (dialog.winfo_screenheight() - 300) // 2
        dialog.geometry(f"450x300+{x}+{y}")
        
        ctk.CTkLabel(
            dialog,
            text="🔐 Steam Login für Update",
            font=("Segoe UI", 18, "bold")
        ).pack(pady=15)
        
        ctk.CTkLabel(
            dialog,
            text=f"{server_config['game']} benötigt Steam-Login für Updates.",
            text_color="gray"
        ).pack(pady=(0, 15))
        
        # Formular
        form_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        form_frame.pack(fill="x", padx=40)
        
        ctk.CTkLabel(form_frame, text="Steam-Benutzername:", anchor="w").pack(fill="x", pady=(5, 3))
        username_entry = ctk.CTkEntry(form_frame, width=300)
        username_entry.pack(fill="x")
        
        ctk.CTkLabel(form_frame, text="Steam-Passwort:", anchor="w").pack(fill="x", pady=(10, 3))
        password_entry = ctk.CTkEntry(form_frame, width=300, show="*")
        password_entry.pack(fill="x")
        
        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=40, pady=20)
        
        def do_login():
            username = username_entry.get().strip()
            password = password_entry.get()
            
            if not username or not password:
                messagebox.showerror(t("error"), "Bitte Benutzername und Passwort eingeben!")
                return
            
            dialog.destroy()
            self._do_server_update(server_id, instance, server_config, username, password)
        
        ctk.CTkButton(btn_frame, text="⬆️ Update starten", command=do_login, width=150).pack(side="left")
        ctk.CTkButton(btn_frame, text=t("cancel"), command=dialog.destroy, width=100, fg_color="gray").pack(side="right")
    
    def _do_server_update(self, server_id, instance, server_config, username, password):
        """Führt das Server-Update durch mit Live-Ausgabe"""
        t = self.config_manager.get_text
        
        # Update-Dialog mit Live-Output
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"⬆️ {t('update_server')} - {server_config.get('name', 'Server')}")
        dialog.geometry("650x450")
        dialog.transient(self)
        dialog.grab_set()
        
        # Zentrieren
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 650) // 2
        y = (dialog.winfo_screenheight() - 450) // 2
        dialog.geometry(f"650x450+{x}+{y}")
        
        # Header
        ctk.CTkLabel(
            dialog,
            text=f"⬆️ {t('updating_server')}",
            font=("Segoe UI", 18, "bold")
        ).pack(pady=(15, 5))
        
        # Status Label
        status_label = ctk.CTkLabel(dialog, text="Starte Update...", font=("Segoe UI", 12))
        status_label.pack(pady=5)
        
        # Progress Bar
        progress = ctk.CTkProgressBar(dialog, width=550)
        progress.pack(pady=10)
        progress.set(0)
        
        # Prozent-Label
        percent_label = ctk.CTkLabel(dialog, text="0%", font=("Segoe UI", 14, "bold"))
        percent_label.pack()
        
        # Live-Output Textfeld
        ctk.CTkLabel(dialog, text="📜 SteamCMD Ausgabe:", anchor="w").pack(fill="x", padx=20, pady=(15, 5))
        
        output_frame = ctk.CTkFrame(dialog)
        output_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        output_text = ctk.CTkTextbox(
            output_frame,
            font=("Consolas", 10),
            fg_color="#1a1a1a",
            text_color="#00ff00"
        )
        output_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Button Frame
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)
        
        close_btn = ctk.CTkButton(
            btn_frame,
            text="Schließen",
            command=dialog.destroy,
            fg_color="gray",
            state="disabled"
        )
        close_btn.pack(side="right")
        
        def add_output(text):
            """Fügt Text zum Output hinzu"""
            try:
                output_text.insert("end", text + "\n")
                output_text.see("end")
            except:
                pass
        
        def update_progress(percent):
            """Aktualisiert die Fortschrittsanzeige"""
            try:
                progress.set(percent / 100)
                percent_label.configure(text=f"{percent:.1f}%")
            except:
                pass
        
        def update_status(text):
            """Aktualisiert den Status-Text"""
            try:
                status_label.configure(text=text)
            except:
                pass
        
        def do_update():
            game_info = SUPPORTED_GAMES.get(server_config.get("game", ""), {})
            app_id = game_info.get("app_id", "")
            
            was_running = instance.is_running()
            
            # Server stoppen wenn läuft
            if was_running:
                self.after(0, lambda: update_status("⚫ Stoppe Server für Update..."))
                self.after(0, lambda: add_output("Server wird gestoppt..."))
                instance.stop()
                time.sleep(3)
            
            steamcmd_path = os.path.join(PATHS["steamcmd"], "steamcmd.exe")
            server_dir = instance.get_server_dir()
            
            # ===== STEAMAPPS CACHE LÖSCHEN (verhindert State 0x6 Fehler) =====
            steamapps_cache = os.path.join(server_dir, "steamapps")
            if os.path.exists(steamapps_cache):
                self.after(0, lambda: update_status("🗑️ Lösche SteamCMD-Cache..."))
                self.after(0, lambda: add_output("Lösche steamapps-Cache (verhindert Update-Fehler)..."))
                try:
                    shutil.rmtree(steamapps_cache)
                    self.after(0, lambda: add_output("✅ Cache gelöscht"))
                except Exception as e:
                    err_msg = str(e)
                    self.after(0, lambda: add_output(f"⚠️ Cache-Löschung fehlgeschlagen: {err_msg}"))
            
            self.after(0, lambda: update_status("📥 Lade Update herunter..."))
            self.after(0, lambda: add_output(f"Starte SteamCMD für App {app_id}..."))
            
            # SteamCMD Befehl als Liste (shell=False für Sicherheit)
            cmd_list = [steamcmd_path, "+force_install_dir", server_dir]
            if username == "anonymous":
                cmd_list.extend(["+login", "anonymous"])
            else:
                cmd_list.extend(["+login", username, password])
            cmd_list.extend(["+app_update", str(app_id), "validate", "+quit"])
            
            # ===== DATEI-BASIERTES POLLING =====
            # Temporäre Log-Datei für SteamCMD Ausgabe
            import tempfile
            log_file = os.path.join(tempfile.gettempdir(), f"steamcmd_update_{server_id}.log")
            
            # Alte Log-Datei löschen falls vorhanden
            if os.path.exists(log_file):
                try:
                    os.remove(log_file)
                except:
                    pass
            
            self.after(0, lambda: add_output(f"Verzeichnis: {server_dir}"))
            self.after(0, lambda: add_output("-" * 50))
            
            # Prozess mit Ausgabe in Datei starten
            with open(log_file, 'w', encoding='utf-8', errors='replace') as log_f:
                process = subprocess.Popen(
                    cmd_list,
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    shell=False,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
            
            # Polling: Log-Datei alle 500ms lesen
            update_success = False
            last_percent = 0
            last_line_count = 0
            
            while process.poll() is None:
                time.sleep(0.5)  # 500ms warten
                
                # Log-Datei lesen
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                        lines = f.readlines()
                    
                    # Nur neue Zeilen verarbeiten
                    new_lines = lines[last_line_count:]
                    last_line_count = len(lines)
                    
                    for line in new_lines:
                        line = line.strip()
                        if line:
                            # Output anzeigen
                            self.after(0, lambda l=line: add_output(l))
                            
                            # Erfolg erkennen
                            if "Success!" in line and "fully installed" in line:
                                update_success = True
                            elif f"App '{app_id}' already up to date" in line:
                                update_success = True
                                self.after(0, lambda: update_status("✅ Server ist bereits aktuell!"))
                            
                            # Fortschritt parsen
                            try:
                                import re
                                percent = None
                                
                                # Format 1: "progress: 22.80 (bytes / total)"
                                match = re.search(r'progress:\s*(\d+(?:\.\d+)?)', line)
                                if match:
                                    percent = float(match.group(1))
                                
                                # Format 2: "22.80%" oder "22.80 %"
                                if percent is None:
                                    match = re.search(r'(\d+(?:\.\d+)?)\s*%', line)
                                    if match:
                                        percent = float(match.group(1))
                                
                                # Format 3: Bytes-basiert "(2752598223 / 12073582417)"
                                if percent is None:
                                    match = re.search(r'\((\d+)\s*/\s*(\d+)\)', line)
                                    if match:
                                        downloaded = int(match.group(1))
                                        total = int(match.group(2))
                                        if total > 0:
                                            percent = (downloaded / total) * 100
                                
                                if percent is not None and percent > last_percent:
                                    last_percent = percent
                                    self.after(0, lambda p=percent: update_progress(p))
                                    
                                    # Status mit Größe anzeigen
                                    if "downloading" in line.lower():
                                        match = re.search(r'\((\d+)\s*/\s*(\d+)\)', line)
                                        if match:
                                            downloaded_gb = int(match.group(1)) / (1024**3)
                                            total_gb = int(match.group(2)) / (1024**3)
                                            self.after(0, lambda d=downloaded_gb, t=total_gb, p=percent: 
                                                update_status(f"📥 Downloading... {p:.1f}% ({d:.2f} / {t:.2f} GB)"))
                            except:
                                pass
                            
                            # Status-Updates
                            if "Downloading" in line or "downloading" in line:
                                if last_percent == 0:
                                    self.after(0, lambda: update_status("📥 Downloading..."))
                            elif "Validating" in line or "validating" in line:
                                self.after(0, lambda: update_status("🔍 Validating..."))
                            elif "Updating" in line:
                                self.after(0, lambda: update_status("🔄 Updating..."))
                
                except Exception as e:
                    pass  # Datei noch nicht bereit oder anderer Fehler
            
            # Prozess beendet - letzte Zeilen noch lesen
            try:
                with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                
                new_lines = lines[last_line_count:]
                for line in new_lines:
                    line = line.strip()
                    if line:
                        self.after(0, lambda l=line: add_output(l))
                        if "Success!" in line and "fully installed" in line:
                            update_success = True
                        elif f"App '{app_id}' already up to date" in line:
                            update_success = True
            except:
                pass
            
            # ===== LOG-DATEI LÖSCHEN =====
            try:
                os.remove(log_file)
            except:
                pass
            
            def show_result():
                if process.returncode == 0 or update_success:
                    progress.set(1)
                    percent_label.configure(text="100%")
                    status_label.configure(text="✅ Update erfolgreich!")
                    add_output("-" * 50)
                    add_output("✅ UPDATE ABGESCHLOSSEN!")
                    
                    if was_running:
                        add_output("▶️ Starte Server wieder...")
                        status_label.configure(text="▶️ Starte Server...")
                        instance.start()
                        time.sleep(2)
                        add_output("✅ Server gestartet!")
                        status_label.configure(text="✅ Update abgeschlossen - Server läuft!")
                    
                    instance.log("✅ Server erfolgreich aktualisiert!")
                else:
                    status_label.configure(text="❌ Update fehlgeschlagen!")
                    add_output("-" * 50)
                    add_output(f"❌ FEHLER! Exit Code: {process.returncode}")
                    instance.log(f"❌ Update fehlgeschlagen (Exit Code: {process.returncode})")
                
                close_btn.configure(state="normal")
                self.show_server_details(server_id)
            
            self.after(0, show_result)
        
        threading.Thread(target=do_update, daemon=True).start()
    
    def install_server(self, server_id):
        """Installiert einen Server"""
        t = self.config_manager.get_text
        
        server_config = self.config_manager.servers.get(server_id)
        if not server_config:
            return
        
        game_info = SUPPORTED_GAMES.get(server_config["game"], {})
        
        # Spezielle Installation für Minecraft Forge
        if game_info.get("special_install") == "minecraft_forge":
            self.install_minecraft_forge(server_id)
            return
        
        # Prüfe SteamCMD
        steamcmd_exe = os.path.join(PATHS["steamcmd"], "steamcmd.exe")
        if not os.path.exists(steamcmd_exe):
            if messagebox.askyesno(
                t("info"),
                "SteamCMD ist nicht installiert.\n\nJetzt installieren?"
            ):
                self.install_steamcmd(lambda: self.install_server(server_id))
            return
        
        app_id = game_info.get("app_id")
        
        if not app_id:
            messagebox.showerror(t("error"), "Spiel wird nicht unterstützt!")
            return
        
        # Prüfe ob Steam-Login erforderlich ist
        requires_login = game_info.get("requires_login", False)
        
        if requires_login:
            # Steam-Login Dialog anzeigen
            self.show_steam_login_dialog(server_id, server_config, game_info, steamcmd_exe)
        else:
            # Normale Installation mit anonymous login
            self._do_server_install(server_id, server_config, steamcmd_exe, app_id, "anonymous", "")
    
    def show_steam_login_dialog(self, server_id, server_config, game_info, steamcmd_exe):
        """Zeigt Dialog für Steam-Login an"""
        t = self.config_manager.get_text
        app_id = game_info.get("app_id")
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("🔐 Steam Login erforderlich")
        dialog.geometry("500x450")
        dialog.transient(self)
        dialog.grab_set()
        
        # Zentrieren
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 500) // 2
        y = (dialog.winfo_screenheight() - 450) // 2
        dialog.geometry(f"500x450+{x}+{y}")
        
        # Header
        ctk.CTkLabel(
            dialog,
            text="🔐 Steam Login erforderlich",
            font=("Segoe UI", 20, "bold")
        ).pack(pady=20)
        
        ctk.CTkLabel(
            dialog,
            text=f"{server_config['game']} benötigt einen Steam-Account\nfür die Installation.",
            font=("Segoe UI", 12),
            text_color="gray"
        ).pack(pady=(0, 20))
        
        # Formular
        form_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        form_frame.pack(fill="x", padx=40)
        
        ctk.CTkLabel(form_frame, text="Steam-Benutzername:", anchor="w").pack(fill="x", pady=(10, 5))
        username_entry = ctk.CTkEntry(form_frame, width=300)
        username_entry.pack(fill="x")
        
        ctk.CTkLabel(form_frame, text="Steam-Passwort:", anchor="w").pack(fill="x", pady=(15, 5))
        password_entry = ctk.CTkEntry(form_frame, width=300, show="*")
        password_entry.pack(fill="x")
        
        # Hinweis
        ctk.CTkLabel(
            dialog,
            text="⚠️ Dein Passwort wird nur für diese Installation verwendet\nund NICHT gespeichert!",
            font=("Segoe UI", 12),
            text_color="orange"
        ).pack(pady=20)
        
        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=40, pady=10)
        
        def do_login():
            username = username_entry.get().strip()
            password = password_entry.get()
            
            if not username:
                messagebox.showerror(t("error"), "Bitte Benutzername eingeben!")
                return
            if not password:
                messagebox.showerror(t("error"), "Bitte Passwort eingeben!")
                return
            
            dialog.destroy()
            
            # Steam Guard Info
            messagebox.showinfo(
                "Steam Guard",
                "Falls Steam Guard aktiviert ist, wird sich ein Konsolen-Fenster öffnen.\n\n"
                "Gib dort den Code aus deiner Steam-App oder E-Mail ein."
            )
            
            self._do_server_install(server_id, server_config, steamcmd_exe, app_id, username, password)
        
        ctk.CTkButton(
            btn_frame,
            text="🔐 Einloggen & Installieren",
            command=do_login,
            width=200
        ).pack(side="left")
        
        ctk.CTkButton(
            btn_frame,
            text=t("cancel"),
            command=dialog.destroy,
            width=100,
            fg_color="gray"
        ).pack(side="right")
    
    def _do_server_install(self, server_id, server_config, steamcmd_exe, app_id, username, password):
        """Führt die eigentliche Server-Installation durch (mit Fortschritts-Dialog)"""
        from gsm.ui.progress import ProgressDialog
        progress = ProgressDialog(
            self,
            title=f"Installiere {server_config.get('game', 'Server')}",
            status="Starte SteamCMD…"
        )

        def do_install():
            instance = self.server_instances.get(server_id)
            try:
                if instance:
                    instance.log(f"📥 Installiere {server_config['game']}...")
                progress.append_log(f"📥 Installiere {server_config['game']}…")

                server_dir = os.path.join(PATHS["servers"], server_id)
                os.makedirs(server_dir, exist_ok=True)
                
                # SteamCMD Befehl als Liste (shell=False für Sicherheit)
                cmd_list = [steamcmd_exe, "+force_install_dir", server_dir]
                if username == "anonymous":
                    cmd_list.extend(["+login", "anonymous"])
                else:
                    cmd_list.extend(["+login", username, password])
                cmd_list.extend(["+app_update", str(app_id), "validate", "+quit"])
                
                progress.set_status("SteamCMD lädt die Server-Dateien… das kann einige Minuten dauern.")
                if instance:
                    instance.log(f"🔧 Befehl: steamcmd +force_install_dir ... +app_update {app_id}")

                # Für Steam Guard: Konsole anzeigen wenn Login erforderlich
                if os.name == 'nt':
                    if username != "anonymous":
                        # Mit Fenster für Steam Guard
                        process = subprocess.Popen(
                            cmd_list,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            shell=False
                        )
                    else:
                        # Ohne Fenster für anonymous
                        process = subprocess.Popen(
                            cmd_list,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            shell=False,
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                else:
                    process = subprocess.Popen(
                        cmd_list,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        shell=False
                    )
                
                # Output sammeln für Erfolgs-Erkennung
                output_lines = []
                install_success = False
                
                for line in process.stdout:
                    line_stripped = line.strip()
                    output_lines.append(line_stripped)
                    if line_stripped:
                        progress.append_log(line_stripped)
                    if instance:
                        instance.log(line_stripped)

                    # Erfolg erkennen anhand der SteamCMD Ausgabe
                    if "Success!" in line and "fully installed" in line:
                        install_success = True
                    elif f"App '{app_id}' already up to date" in line:
                        install_success = True
                
                process.wait()
                
                # Zusätzliche Erfolgs-Prüfung: Existiert die Server-EXE?
                game_info = SUPPORTED_GAMES.get(server_config["game"], {})
                exe_name = game_info.get("exe", "")
                if exe_name:
                    # Suche nach der EXE im Server-Verzeichnis
                    for root, dirs, files in os.walk(server_dir):
                        if exe_name in files:
                            install_success = True
                            break
                
                # Erfolg: Entweder returncode 0 ODER Success-Meldung ODER EXE gefunden
                if process.returncode == 0 or install_success:
                    self.config_manager.servers[server_id]["installed"] = True
                    self.config_manager.save_servers()
                    if instance:
                        instance.log("✅ Installation abgeschlossen!")
                    progress.finish(True, "✅ Installation abgeschlossen!")
                    self.after(0, lambda: self.select_server(server_id))
                else:
                    if instance:
                        instance.log(f"❌ Installation fehlgeschlagen! (Exit Code: {process.returncode})")
                    progress.finish(False, f"❌ Installation fehlgeschlagen (Exit-Code {process.returncode}). Details siehe Log oben.")

            except Exception as e:
                err = str(e)
                if instance:
                    instance.log(f"❌ Fehler: {err}")
                progress.finish(False, f"❌ Fehler: {err}")

        threading.Thread(target=do_install, daemon=True).start()
    
    def install_steamcmd(self, callback=None):
        """Installiert SteamCMD"""
        def do_install():
            try:
                os.makedirs(PATHS["steamcmd"], exist_ok=True)
                url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"
                zip_path = os.path.join(PATHS["steamcmd"], "steamcmd.zip")
                
                response = requests.get(url, stream=True)
                with open(zip_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(PATHS["steamcmd"])
                
                os.remove(zip_path)
                
                self.config_manager.app_config["steamcmd_installed"] = True
                self.config_manager.save_app_config()
                
                if callback:
                    self.after(0, callback)

            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda: messagebox.showerror("Fehler", err_msg))
        
        threading.Thread(target=do_install, daemon=True).start()
