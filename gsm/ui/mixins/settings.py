"""Mixin: App-Einstellungen, Discord/Cluster-Settings, Import/Export, Autostart.

Aus game_server_manager.py ausgelagert (Phase 3e, verhaltenserhaltend). Nur
Methoden, kein __init__; teilt sich self mit GameServerManagerApp.
"""

import os
import sys
import json
from datetime import datetime

import customtkinter as ctk
from tkinter import messagebox, filedialog

# Windows Registry für Autostart
try:
    import winreg
    WINREG_AVAILABLE = True
except ImportError:
    WINREG_AVAILABLE = False

from gsm.constants import VERSION
from gsm.games import SUPPORTED_GAMES
from gsm.server import ServerInstance


class SettingsMixin:
    """App-/Discord-/Cluster-Settings, Import/Export, Autostart (Mixin)."""

    def get_autostart_enabled(self):
        """Prüft ob Autostart aktiviert ist"""
        if not WINREG_AVAILABLE:
            return False
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_READ
            )
            try:
                winreg.QueryValueEx(key, "GameServerManagerPro")
                winreg.CloseKey(key)
                return True
            except WindowsError:
                winreg.CloseKey(key)
                return False
        except Exception:
            return False
    
    def set_autostart(self, enabled):
        """Aktiviert oder deaktiviert Windows Autostart"""
        if not WINREG_AVAILABLE:
            return False
        
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )
            
            if enabled:
                # Pfad zur EXE oder zum Python-Script
                if getattr(sys, 'frozen', False):
                    # Wenn als EXE kompiliert
                    app_path = sys.executable
                else:
                    # Wenn als Python-Script
                    app_path = f'"{sys.executable}" "{os.path.abspath(__file__)}"'
                
                winreg.SetValueEx(key, "GameServerManagerPro", 0, winreg.REG_SZ, app_path)
            else:
                try:
                    winreg.DeleteValue(key, "GameServerManagerPro")
                except WindowsError:
                    pass
            
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"Autostart Fehler: {e}")
            return False
    
    # ==================== IMPORT/EXPORT FUNKTIONEN ====================
    def export_server_config(self, server_ids=None):
        """Exportiert Server-Konfigurationen als JSON"""
        t = self.config_manager.get_text
        
        if server_ids is None:
            server_ids = list(self.config_manager.servers.keys())
        
        export_data = {
            "version": VERSION,
            "export_date": datetime.now().isoformat(),
            "servers": {}
        }
        
        for server_id in server_ids:
            if server_id in self.config_manager.servers:
                export_data["servers"][server_id] = self.config_manager.servers[server_id].copy()
        
        # Datei-Dialog
        file_path = filedialog.asksaveasfilename(
            title=t("export_config"),
            defaultextension=".json",
            filetypes=[("JSON Dateien", "*.json"), ("Alle Dateien", "*.*")],
            initialfilename=f"gsm_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                messagebox.showinfo(t("success"), t("export_success") + f"\n\n{file_path}")
                return True
            except Exception as e:
                messagebox.showerror(t("error"), f"{t('export_failed')}\n\n{str(e)}")
                return False
        return False
    
    def import_server_config(self):
        """Importiert Server-Konfigurationen aus JSON"""
        t = self.config_manager.get_text
        
        # Datei-Dialog
        file_path = filedialog.askopenfilename(
            title=t("import_config"),
            filetypes=[("JSON Dateien", "*.json"), ("Alle Dateien", "*.*")]
        )
        
        if not file_path:
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            if "servers" not in import_data:
                messagebox.showerror(t("error"), "Ungültiges Dateiformat!")
                return False
            
            imported_count = 0
            skipped_count = 0
            
            for server_id, server_config in import_data["servers"].items():
                # Prüfen ob Server-ID bereits existiert
                new_id = server_id
                counter = 1
                while new_id in self.config_manager.servers:
                    new_id = f"{server_id}_{counter}"
                    counter += 1
                
                if new_id != server_id:
                    server_config["name"] = f"{server_config.get('name', 'Server')} (Import)"
                
                # Server hinzufügen
                self.config_manager.servers[new_id] = server_config
                
                # ServerInstance erstellen
                game_info = SUPPORTED_GAMES.get(server_config.get("game", ""), {})
                self.server_instances[new_id] = ServerInstance(
                    new_id,
                    server_config,
                    game_info,
                    self.config_manager.get_text,
                    discord_notifier=self.discord_notifier
                )
                
                imported_count += 1
            
            # Speichern
            self.config_manager.save_servers()
            
            # UI aktualisieren
            self.refresh_server_list()
            
            messagebox.showinfo(
                t("success"), 
                f"{t('import_success')}\n\n{imported_count} Server importiert"
            )
            return True
            
        except Exception as e:
            messagebox.showerror(t("error"), f"{t('import_failed')}\n\n{str(e)}")
            return False
    
    def show_import_export_dialog(self):
        """Zeigt den Import/Export Dialog"""
        t = self.config_manager.get_text
        
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"📦 {t('import_export')}")
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
            text=f"📦 {t('import_export')}",
            font=("Segoe UI", 20, "bold")
        ).pack(pady=20)
        
        # Export Bereich
        export_frame = ctk.CTkFrame(dialog)
        export_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            export_frame,
            text=f"📤 {t('export_config')}",
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(
            export_frame,
            text=t("select_servers_export"),
            font=("Segoe UI", 11),
            text_color="gray"
        ).pack(anchor="w", padx=10)
        
        # Server-Checkboxen für Export
        server_vars = {}
        checkbox_frame = ctk.CTkFrame(export_frame, fg_color="transparent")
        checkbox_frame.pack(fill="x", padx=10, pady=5)
        
        for server_id, server_config in self.config_manager.servers.items():
            var = ctk.BooleanVar(value=True)
            server_vars[server_id] = var
            ctk.CTkCheckBox(
                checkbox_frame,
                text=f"{server_config.get('name', server_id)} ({server_config.get('game', '')})",
                variable=var
            ).pack(anchor="w", pady=2)
        
        if not server_vars:
            ctk.CTkLabel(
                checkbox_frame,
                text="Keine Server vorhanden",
                text_color="gray"
            ).pack(anchor="w")
        
        def do_export():
            selected = [sid for sid, var in server_vars.items() if var.get()]
            if selected:
                self.export_server_config(selected)
        
        ctk.CTkButton(
            export_frame,
            text=f"📤 {t('export_all')}",
            command=do_export,
            fg_color="green"
        ).pack(pady=10)
        
        # Trennlinie
        ctk.CTkFrame(dialog, height=2, fg_color="gray").pack(fill="x", padx=20, pady=15)
        
        # Import Bereich
        import_frame = ctk.CTkFrame(dialog)
        import_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            import_frame,
            text=f"📥 {t('import_config')}",
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(
            import_frame,
            text="JSON-Datei mit Server-Konfigurationen importieren",
            font=("Segoe UI", 11),
            text_color="gray"
        ).pack(anchor="w", padx=10)
        
        def do_import():
            if self.import_server_config():
                dialog.destroy()
        
        ctk.CTkButton(
            import_frame,
            text=f"📥 {t('import_file')}",
            command=do_import,
            fg_color="#2196F3"
        ).pack(pady=10)
        
        # Schließen Button
        ctk.CTkButton(
            dialog,
            text=t("cancel"),
            command=dialog.destroy,
            width=100,
            fg_color="gray"
        ).pack(pady=20)
    
    # ==================== APP EINSTELLUNGEN ====================
    def show_app_settings(self):
        """Zeigt die allgemeinen Einstellungen"""
        t = self.config_manager.get_text
        
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"⚙️ {t('app_settings')}")
        dialog.geometry("550x650")
        dialog.transient(self)
        dialog.grab_set()
        
        # Zentrieren
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 550) // 2
        y = (dialog.winfo_screenheight() - 650) // 2
        dialog.geometry(f"550x650+{x}+{y}")
        
        # Scrollbarer Bereich
        scroll_frame = ctk.CTkScrollableFrame(dialog)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Header
        ctk.CTkLabel(
            scroll_frame,
            text=f"⚙️ {t('app_settings')}",
            font=("Segoe UI", 20, "bold")
        ).pack(pady=(10, 20))
        
        # === ALLGEMEIN ===
        general_frame = ctk.CTkFrame(scroll_frame)
        general_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            general_frame,
            text="📋 Allgemein",
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        # Web-Port
        port_row = ctk.CTkFrame(general_frame, fg_color="transparent")
        port_row.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(port_row, text=f"🌐 {t('web_port')}:", width=150, anchor="w").pack(side="left")
        current_port = self.config_manager.app_config.get("web", {}).get("port", 5001)
        port_entry = ctk.CTkEntry(port_row, width=80)
        port_entry.pack(side="left", padx=5)
        port_entry.insert(0, str(current_port))
        ctk.CTkLabel(port_row, text=t("web_port_hint"), text_color="gray", font=("Segoe UI", 12)).pack(side="left", padx=10)
        
        # Sprache
        lang_row = ctk.CTkFrame(general_frame, fg_color="transparent")
        lang_row.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(lang_row, text=f"🌍 {t('language')}:", width=150, anchor="w").pack(side="left")
        current_lang = self.config_manager.app_config.get("language", "de")
        lang_var = ctk.StringVar(value="Deutsch" if current_lang == "de" else "English")
        ctk.CTkOptionMenu(lang_row, variable=lang_var, values=["Deutsch", "English"], width=150).pack(side="left")
        
        # Theme
        theme_row = ctk.CTkFrame(general_frame, fg_color="transparent")
        theme_row.pack(fill="x", padx=10, pady=(5, 10))
        
        ctk.CTkLabel(theme_row, text=f"🎨 {t('theme')}:", width=150, anchor="w").pack(side="left")
        current_theme = self.config_manager.app_config.get("theme", "dark")
        theme_var = ctk.StringVar(value=t("theme_dark") if current_theme == "dark" else t("theme_light"))
        ctk.CTkOptionMenu(theme_row, variable=theme_var, values=[t("theme_dark"), t("theme_light")], width=150).pack(side="left")
        
        # === AUTOSTART ===
        autostart_frame = ctk.CTkFrame(scroll_frame)
        autostart_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            autostart_frame,
            text=f"🚀 {t('autostart')}",
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        # Programm Autostart
        autostart_program_var = ctk.BooleanVar(value=self.get_autostart_enabled())
        ctk.CTkCheckBox(
            autostart_frame,
            text=t("autostart_program"),
            variable=autostart_program_var
        ).pack(anchor="w", padx=20, pady=5)
        
        # Server automatisch starten
        autostart_servers_var = ctk.BooleanVar(
            value=self.config_manager.app_config.get("autostart_servers", False)
        )
        ctk.CTkCheckBox(
            autostart_frame,
            text=t("autostart_servers"),
            variable=autostart_servers_var
        ).pack(anchor="w", padx=20, pady=(5, 10))
        
        # Hinweis
        ctk.CTkLabel(
            autostart_frame,
            text="💡 Bei aktiviertem Server-Autostart werden alle\n     zuvor laufenden Server automatisch gestartet.",
            font=("Segoe UI", 12),
            text_color="gray",
            justify="left"
        ).pack(anchor="w", padx=20, pady=(0, 10))
        
        # === IMPORT / EXPORT ===
        ie_frame = ctk.CTkFrame(scroll_frame)
        ie_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            ie_frame,
            text=f"📦 {t('import_export')}",
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(
            ie_frame,
            text="Server-Konfigurationen exportieren oder importieren",
            font=("Segoe UI", 12),
            text_color="gray"
        ).pack(anchor="w", padx=10)
        
        ie_btn_frame = ctk.CTkFrame(ie_frame, fg_color="transparent")
        ie_btn_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(
            ie_btn_frame,
            text=f"📤 {t('export_config')}",
            command=lambda: self.export_server_config(),
            width=150,
            fg_color="green"
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            ie_btn_frame,
            text=f"📥 {t('import_config')}",
            command=lambda: [self.import_server_config(), dialog.destroy()],
            width=150,
            fg_color="#2196F3"
        ).pack(side="left", padx=5)
        
        # === SPEICHERN ===
        ctk.CTkLabel(
            scroll_frame,
            text="⚠️ " + t("settings_restart_required"),
            font=("Segoe UI", 11),
            text_color="orange"
        ).pack(pady=10)
        
        btn_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        def save_settings():
            # Port validieren
            try:
                new_port = int(port_entry.get().strip())
                if new_port < 1 or new_port > 65535:
                    raise ValueError("Port out of range")
            except ValueError:
                messagebox.showerror(t("error"), "Ungültiger Port (1-65535)")
                return
            
            # Sprache
            new_lang = "de" if lang_var.get() == "Deutsch" else "en"
            
            # Theme
            new_theme = "dark" if theme_var.get() in [t("theme_dark"), "Dunkel", "Dark"] else "light"
            
            # Autostart
            self.set_autostart(autostart_program_var.get())
            
            # Speichern
            if "web" not in self.config_manager.app_config:
                self.config_manager.app_config["web"] = {"enabled": True, "port": 5001}
            self.config_manager.app_config["web"]["port"] = new_port
            self.config_manager.app_config["language"] = new_lang
            self.config_manager.app_config["theme"] = new_theme
            self.config_manager.app_config["autostart_servers"] = autostart_servers_var.get()
            self.config_manager.save_app_config()
            
            # Web-Label aktualisieren
            self.web_label.configure(text=f"🌐 localhost:{new_port}")
            
            # Theme sofort anwenden
            ctk.set_appearance_mode(new_theme)
            
            # Bestätigung
            status = t("autostart_enabled") if autostart_program_var.get() else t("autostart_disabled")
            
            dialog.destroy()
            
            messagebox.showinfo(t("success"), f"{t('settings_saved')}\n\n{status}")
        
        ctk.CTkButton(
            btn_frame,
            text=t("save"),
            command=save_settings,
            width=120,
            fg_color="green"
        ).pack(side="right", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text=t("cancel"),
            command=dialog.destroy,
            width=100,
            fg_color="gray"
        ).pack(side="left", padx=5)
    
    # ==================== DISCORD EINSTELLUNGEN ====================
    def show_discord_settings(self):
        """Zeigt die Discord-Einstellungen"""
        t = self.config_manager.get_text
        discord_config = self.config_manager.app_config.get("discord", {})
        
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"🔔 {t('discord_settings')}")
        dialog.geometry("600x650")
        dialog.minsize(550, 600)
        dialog.resizable(True, True)
        dialog.transient(self)
        dialog.grab_set()
        
        # Zentrieren
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 600) // 2
        y = (dialog.winfo_screenheight() - 650) // 2
        dialog.geometry(f"600x650+{x}+{y}")
        
        # Scrollable Content
        scroll = ctk.CTkScrollableFrame(dialog)
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header
        ctk.CTkLabel(
            scroll,
            text=f"🔔 {t('discord_settings')}",
            font=("Segoe UI", 22, "bold")
        ).pack(pady=(0, 20))
        
        # Aktiviert
        enabled_var = ctk.BooleanVar(value=discord_config.get("enabled", False))
        ctk.CTkCheckBox(
            scroll,
            text=t("discord_notifications"),
            variable=enabled_var,
            font=("Segoe UI", 14)
        ).pack(anchor="w", padx=20, pady=10)
        
        # Webhook URL
        form_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        form_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(form_frame, text=f"{t('discord_webhook_url')}:", font=("Segoe UI", 14), anchor="w").pack(fill="x", pady=(10, 5))
        webhook_entry = ctk.CTkEntry(form_frame, height=40, font=("Segoe UI", 13))
        webhook_entry.pack(fill="x")
        webhook_entry.insert(0, discord_config.get("webhook_url", ""))
        
        ctk.CTkLabel(
            form_frame,
            text=t("discord_webhook_hint"),
            font=("Segoe UI", 12),
            text_color="gray"
        ).pack(anchor="w", pady=5)
        
        # Test-Button
        def test_webhook():
            webhook_url = webhook_entry.get().strip()
            if not webhook_url:
                messagebox.showerror(t("error"), "Bitte Webhook URL eingeben!")
                return
            
            # Temporär setzen
            self.config_manager.app_config["discord"]["webhook_url"] = webhook_url
            self.config_manager.app_config["discord"]["enabled"] = True
            
            if self.discord_notifier.send_test():
                messagebox.showinfo(t("success"), t("discord_test_success"))
            else:
                messagebox.showerror(t("error"), t("discord_test_failed"))
        
        ctk.CTkButton(
            form_frame,
            text=f"🧪 {t('discord_test')}",
            command=test_webhook,
            width=160,
            height=38,
            font=("Segoe UI", 13)
        ).pack(anchor="w", pady=10)
        
        # Benachrichtigungs-Optionen
        ctk.CTkLabel(
            scroll,
            text="Benachrichtigen bei:",
            font=("Segoe UI", 15, "bold")
        ).pack(anchor="w", padx=20, pady=(20, 10))
        
        options_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        options_frame.pack(fill="x", padx=20)
        
        notify_start_var = ctk.BooleanVar(value=discord_config.get("notify_start", True))
        ctk.CTkCheckBox(options_frame, text=t("discord_notify_start"), variable=notify_start_var, font=("Segoe UI", 13)).pack(anchor="w", pady=5)
        
        notify_stop_var = ctk.BooleanVar(value=discord_config.get("notify_stop", True))
        ctk.CTkCheckBox(options_frame, text=t("discord_notify_stop"), variable=notify_stop_var, font=("Segoe UI", 13)).pack(anchor="w", pady=5)
        
        notify_crash_var = ctk.BooleanVar(value=discord_config.get("notify_crash", True))
        ctk.CTkCheckBox(options_frame, text=t("discord_notify_crash"), variable=notify_crash_var, font=("Segoe UI", 13)).pack(anchor="w", pady=5)
        
        notify_backup_var = ctk.BooleanVar(value=discord_config.get("notify_backup", True))
        ctk.CTkCheckBox(options_frame, text=t("discord_notify_backup"), variable=notify_backup_var, font=("Segoe UI", 13)).pack(anchor="w", pady=5)
        
        notify_update_var = ctk.BooleanVar(value=discord_config.get("notify_update", True))
        ctk.CTkCheckBox(options_frame, text=t("discord_notify_update"), variable=notify_update_var, font=("Segoe UI", 13)).pack(anchor="w", pady=5)
        
        # Buttons (außerhalb des scrollable frame für bessere Sichtbarkeit)
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=40, pady=20)
        
        def save_settings():
            self.config_manager.app_config["discord"] = {
                "enabled": enabled_var.get(),
                "webhook_url": webhook_entry.get().strip(),
                "notify_start": notify_start_var.get(),
                "notify_stop": notify_stop_var.get(),
                "notify_crash": notify_crash_var.get(),
                "notify_backup": notify_backup_var.get(),
                "notify_update": notify_update_var.get()
            }
            self.config_manager.save_app_config()
            dialog.destroy()
        
        ctk.CTkButton(
            btn_frame,
            text=t("save"),
            command=save_settings,
            width=140,
            height=40,
            font=("Segoe UI", 14),
            fg_color="green"
        ).pack(side="right")
        
        ctk.CTkButton(
            btn_frame,
            text=t("cancel"),
            command=dialog.destroy,
            width=120,
            height=40,
            font=("Segoe UI", 14),
            fg_color="gray"
        ).pack(side="left")

    # ==================== CLUSTER VERWALTUNG ====================
    def show_cluster_settings(self):
        """Zeigt die Cluster-Verwaltung für ARK Server"""
        t = self.config_manager.get_text
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("🔗 ARK Cluster Verwaltung")
        dialog.geometry("700x600")
        dialog.transient(self)
        dialog.grab_set()
        
        # Zentrieren
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 700) // 2
        y = (dialog.winfo_screenheight() - 600) // 2
        dialog.geometry(f"700x600+{x}+{y}")
        
        # Header
        ctk.CTkLabel(
            dialog,
            text="🔗 ARK Cluster Verwaltung",
            font=("Segoe UI", 20, "bold")
        ).pack(pady=20)
        
        # Info-Box
        info_frame = ctk.CTkFrame(dialog, fg_color="#1e3a5f")
        info_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            info_frame,
            text="💡 Ein Cluster verbindet mehrere ARK-Server.\n"
                 "Spieler können Charakter, Dinos und Items zwischen Maps transferieren.",
            font=("Segoe UI", 11),
            text_color="#aaaaaa",
            justify="left"
        ).pack(padx=15, pady=10, anchor="w")
        
        # Hauptbereich mit Tabs
        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Linke Seite: Cluster-Liste
        left_frame = ctk.CTkFrame(main_frame)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        ctk.CTkLabel(
            left_frame,
            text="📂 Cluster",
            font=("Segoe UI", 14, "bold")
        ).pack(pady=10)
        
        # Cluster-Liste
        cluster_list_frame = ctk.CTkScrollableFrame(left_frame, height=300)
        cluster_list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Rechte Seite: Server im Cluster
        right_frame = ctk.CTkFrame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        self.cluster_detail_label = ctk.CTkLabel(
            right_frame,
            text="🎮 Server im Cluster",
            font=("Segoe UI", 14, "bold")
        )
        self.cluster_detail_label.pack(pady=10)
        
        server_list_frame = ctk.CTkScrollableFrame(right_frame, height=300)
        server_list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.current_cluster_id = None
        
        def refresh_cluster_list():
            """Aktualisiert die Cluster-Liste"""
            for widget in cluster_list_frame.winfo_children():
                widget.destroy()
            
            clusters = self.config_manager.app_config.get("clusters", {})
            
            if not clusters:
                ctk.CTkLabel(
                    cluster_list_frame,
                    text="Keine Cluster erstellt",
                    text_color="gray"
                ).pack(pady=20)
            else:
                for cluster_id, cluster_info in clusters.items():
                    frame = ctk.CTkFrame(cluster_list_frame, fg_color="#1c222b")
                    frame.pack(fill="x", pady=3)
                    
                    # Cluster-Name
                    name_btn = ctk.CTkButton(
                        frame,
                        text=f"🔗 {cluster_info.get('name', cluster_id)}",
                        fg_color="transparent",
                        hover_color="#232b36",
                        anchor="w",
                        command=lambda cid=cluster_id: select_cluster(cid)
                    )
                    name_btn.pack(side="left", fill="x", expand=True, padx=5, pady=5)
                    
                    # Server-Anzahl
                    server_count = len(cluster_info.get("servers", []))
                    ctk.CTkLabel(
                        frame,
                        text=f"({server_count})",
                        text_color="gray",
                        width=40
                    ).pack(side="right", padx=5)
                    
                    # Löschen-Button
                    ctk.CTkButton(
                        frame,
                        text="🗑️",
                        width=30,
                        height=24,
                        fg_color="#c0392b",
                        hover_color="#e74c3c",
                        command=lambda cid=cluster_id: delete_cluster(cid)
                    ).pack(side="right", padx=2, pady=5)
        
        def select_cluster(cluster_id):
            """Zeigt die Server eines Clusters"""
            self.current_cluster_id = cluster_id
            clusters = self.config_manager.app_config.get("clusters", {})
            cluster_info = clusters.get(cluster_id, {})
            
            self.cluster_detail_label.configure(
                text=f"🎮 {cluster_info.get('name', cluster_id)}"
            )
            
            # Server-Liste aktualisieren
            for widget in server_list_frame.winfo_children():
                widget.destroy()
            
            # Alle ARK Server anzeigen
            ark_servers = {
                sid: sconfig for sid, sconfig in self.config_manager.servers.items()
                if "ARK" in sconfig.get("game", "")
            }
            
            if not ark_servers:
                ctk.CTkLabel(
                    server_list_frame,
                    text="Keine ARK Server vorhanden",
                    text_color="gray"
                ).pack(pady=20)
                return
            
            cluster_servers = cluster_info.get("servers", [])
            
            for server_id, server_config in ark_servers.items():
                frame = ctk.CTkFrame(server_list_frame, fg_color="#1c222b")
                frame.pack(fill="x", pady=3)
                
                is_in_cluster = server_id in cluster_servers
                current_cluster = server_config.get("cluster", "")
                in_other_cluster = current_cluster and current_cluster != cluster_id
                
                # Checkbox
                var = ctk.BooleanVar(value=is_in_cluster)
                
                def toggle_server(sid=server_id, v=var):
                    if v.get():
                        add_server_to_cluster(sid)
                    else:
                        remove_server_from_cluster(sid)
                
                cb = ctk.CTkCheckBox(
                    frame,
                    text="",
                    variable=var,
                    command=lambda sid=server_id, v=var: toggle_server(sid, v),
                    width=24
                )
                cb.pack(side="left", padx=10, pady=8)
                
                if in_other_cluster:
                    cb.configure(state="disabled")
                
                # Server-Name
                server_name = server_config.get("name", server_id)
                map_name = server_config.get("map", "")
                
                ctk.CTkLabel(
                    frame,
                    text=f"{server_name}",
                    font=("Segoe UI", 12, "bold"),
                    anchor="w"
                ).pack(side="left", padx=5)
                
                ctk.CTkLabel(
                    frame,
                    text=f"({map_name})",
                    text_color="gray",
                    anchor="w"
                ).pack(side="left", padx=5)
                
                if in_other_cluster:
                    ctk.CTkLabel(
                        frame,
                        text=f"⚠️ In: {current_cluster}",
                        text_color="orange",
                        font=("Segoe UI", 12)
                    ).pack(side="right", padx=10)
        
        def add_server_to_cluster(server_id):
            """Fügt Server zum Cluster hinzu"""
            if not self.current_cluster_id:
                return
            
            clusters = self.config_manager.app_config.get("clusters", {})
            if self.current_cluster_id not in clusters:
                return
            
            if "servers" not in clusters[self.current_cluster_id]:
                clusters[self.current_cluster_id]["servers"] = []
            
            if server_id not in clusters[self.current_cluster_id]["servers"]:
                clusters[self.current_cluster_id]["servers"].append(server_id)
            
            # Server-Config aktualisieren
            if server_id in self.config_manager.servers:
                self.config_manager.servers[server_id]["cluster"] = self.current_cluster_id
                self.config_manager.save_servers()
            
            self.config_manager.save_app_config()
            refresh_cluster_list()
        
        def remove_server_from_cluster(server_id):
            """Entfernt Server vom Cluster"""
            if not self.current_cluster_id:
                return
            
            clusters = self.config_manager.app_config.get("clusters", {})
            if self.current_cluster_id in clusters:
                servers = clusters[self.current_cluster_id].get("servers", [])
                if server_id in servers:
                    servers.remove(server_id)
            
            # Server-Config aktualisieren
            if server_id in self.config_manager.servers:
                self.config_manager.servers[server_id]["cluster"] = ""
                self.config_manager.save_servers()
            
            self.config_manager.save_app_config()
            refresh_cluster_list()
        
        def create_cluster():
            """Erstellt einen neuen Cluster"""
            create_dialog = ctk.CTkToplevel(dialog)
            create_dialog.title("➕ Neuer Cluster")
            create_dialog.geometry("450x280")
            create_dialog.transient(dialog)
            create_dialog.grab_set()
            
            # Zentrieren
            create_dialog.update_idletasks()
            x = (create_dialog.winfo_screenwidth() - 450) // 2
            y = (create_dialog.winfo_screenheight() - 280) // 2
            create_dialog.geometry(f"450x280+{x}+{y}")
            
            ctk.CTkLabel(
                create_dialog,
                text="➕ Neuen Cluster erstellen",
                font=("Segoe UI", 16, "bold")
            ).pack(pady=15)
            
            # Name
            ctk.CTkLabel(create_dialog, text="Cluster-Name:").pack(anchor="w", padx=30)
            name_entry = ctk.CTkEntry(create_dialog, width=350, placeholder_text="z.B. MeinCluster")
            name_entry.pack(padx=30, pady=5)
            
            # Verzeichnis
            ctk.CTkLabel(create_dialog, text="Cluster-Verzeichnis:").pack(anchor="w", padx=30, pady=(10, 0))
            
            dir_frame = ctk.CTkFrame(create_dialog, fg_color="transparent")
            dir_frame.pack(fill="x", padx=30, pady=5)
            
            # Standard-Verzeichnis
            base_dir = self.config_manager.app_config.get("server_base_path", "C:\\GameServers")
            default_dir = os.path.join(base_dir, "ARKCluster")
            
            dir_entry = ctk.CTkEntry(dir_frame, width=280)
            dir_entry.pack(side="left")
            dir_entry.insert(0, default_dir)
            
            def browse_dir():
                from tkinter import filedialog
                path = filedialog.askdirectory()
                if path:
                    dir_entry.delete(0, "end")
                    dir_entry.insert(0, path)
            
            ctk.CTkButton(
                dir_frame,
                text="📂",
                width=40,
                command=browse_dir
            ).pack(side="left", padx=5)
            
            def save_cluster():
                name = name_entry.get().strip()
                directory = dir_entry.get().strip()
                
                if not name:
                    return
                
                # Cluster-ID aus Name (ohne Sonderzeichen)
                cluster_id = "".join(c for c in name if c.isalnum())
                
                # Verzeichnis erstellen
                try:
                    os.makedirs(directory, exist_ok=True)
                except Exception as e:
                    messagebox.showerror("Fehler", f"Verzeichnis konnte nicht erstellt werden:\n{e}")
                    return
                
                # Cluster speichern
                if "clusters" not in self.config_manager.app_config:
                    self.config_manager.app_config["clusters"] = {}
                
                self.config_manager.app_config["clusters"][cluster_id] = {
                    "name": name,
                    "directory": directory,
                    "servers": []
                }
                self.config_manager.save_app_config()
                
                create_dialog.destroy()
                refresh_cluster_list()
                select_cluster(cluster_id)
            
            btn_frame = ctk.CTkFrame(create_dialog, fg_color="transparent")
            btn_frame.pack(fill="x", padx=30, pady=20)
            
            ctk.CTkButton(
                btn_frame,
                text="✅ Erstellen",
                command=save_cluster,
                fg_color="green"
            ).pack(side="right")
            
            ctk.CTkButton(
                btn_frame,
                text="Abbrechen",
                command=create_dialog.destroy,
                fg_color="gray"
            ).pack(side="left")
        
        def delete_cluster(cluster_id):
            """Löscht einen Cluster"""
            clusters = self.config_manager.app_config.get("clusters", {})
            cluster_info = clusters.get(cluster_id, {})
            
            if not messagebox.askyesno(
                "Cluster löschen",
                f"Cluster '{cluster_info.get('name', cluster_id)}' wirklich löschen?\n\n"
                "Die Server werden nicht gelöscht, nur die Cluster-Verbindung."
            ):
                return
            
            # Server aus Cluster entfernen
            for server_id in cluster_info.get("servers", []):
                if server_id in self.config_manager.servers:
                    self.config_manager.servers[server_id]["cluster"] = ""
            
            # Cluster löschen
            del clusters[cluster_id]
            self.config_manager.save_app_config()
            self.config_manager.save_servers()
            
            self.current_cluster_id = None
            refresh_cluster_list()
            
            # Rechte Seite leeren
            for widget in server_list_frame.winfo_children():
                widget.destroy()
            self.cluster_detail_label.configure(text="🎮 Server im Cluster")
        
        # Buttons unten
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkButton(
            btn_frame,
            text="➕ Neuer Cluster",
            command=create_cluster,
            fg_color="#27ae60",
            hover_color="#2ecc71"
        ).pack(side="left")
        
        ctk.CTkButton(
            btn_frame,
            text="Schließen",
            command=dialog.destroy,
            fg_color="gray"
        ).pack(side="right")
        
        # Initial laden
        refresh_cluster_list()
