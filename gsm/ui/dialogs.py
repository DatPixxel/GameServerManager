"""Dialog zum Hinzufügen eines Servers.

Aus game_server_manager.py ausgelagert.
"""

import re
from datetime import datetime

import customtkinter as ctk
from tkinter import messagebox

from gsm.games import SUPPORTED_GAMES


class AddServerDialog(ctk.CTkToplevel):
    """Dialog zum Hinzufügen eines neuen Servers"""
    
    def __init__(self, parent, config_manager, on_add):
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.on_add = on_add
        
        t = self.config_manager.get_text
        
        self.title(t("add_server"))
        self.geometry("550x750")
        self.resizable(True, True)
        self.minsize(500, 650)
        
        self.transient(parent)
        self.grab_set()
        
        # Zentrieren
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 550) // 2
        y = (self.winfo_screenheight() - 750) // 2
        self.geometry(f"550x750+{x}+{y}")
        
        self.create_ui()
    
    def create_ui(self):
        t = self.config_manager.get_text
        
        # Scrollable Frame
        scroll = ctk.CTkScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Server-Name
        ctk.CTkLabel(scroll, text=t("server_name") + ":", font=("Arial", 14)).pack(anchor="w", pady=(10, 5))
        self.name_entry = ctk.CTkEntry(scroll, width=450, height=38, font=("Arial", 13))
        self.name_entry.pack(pady=5)
        self.name_entry.insert(0, "Mein Server")
        
        # Spiel auswählen
        ctk.CTkLabel(scroll, text=t("game") + ":", font=("Arial", 14)).pack(anchor="w", pady=(20, 5))
        self.game_var = ctk.StringVar(value="ARK: Survival Ascended")
        self.game_menu = ctk.CTkOptionMenu(
            scroll,
            variable=self.game_var,
            values=list(SUPPORTED_GAMES.keys()),
            width=450,
            height=38,
            font=("Arial", 13),
            command=self.on_game_changed
        )
        self.game_menu.pack(pady=5)
        
        # Map (für ARK)
        self.map_label = ctk.CTkLabel(scroll, text=t("map") + ":", font=("Arial", 14))
        self.map_label.pack(anchor="w", pady=(20, 5))
        
        self.map_var = ctk.StringVar(value="The Island")
        self.map_menu = ctk.CTkOptionMenu(
            scroll,
            variable=self.map_var,
            values=[m["name"] for m in SUPPORTED_GAMES["ARK: Survival Ascended"]["maps"]],
            width=450,
            height=38,
            font=("Arial", 13)
        )
        self.map_menu.pack(pady=5)
        
        # Ports
        port_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        port_frame.pack(fill="x", pady=(20, 5))
        
        ctk.CTkLabel(port_frame, text=t("port") + ":", font=("Arial", 14)).pack(side="left")
        self.port_entry = ctk.CTkEntry(port_frame, width=120, height=38, font=("Arial", 13))
        self.port_entry.pack(side="left", padx=10)
        
        ctk.CTkLabel(port_frame, text=t("query_port") + ":", font=("Arial", 14)).pack(side="left", padx=(20, 0))
        self.query_port_entry = ctk.CTkEntry(port_frame, width=120, height=38, font=("Arial", 13))
        self.query_port_entry.pack(side="left", padx=10)
        
        # Automatisch freie Ports setzen
        base_port = SUPPORTED_GAMES.get("ARK: Survival Ascended", {}).get("default_ports", {}).get("game", 7777)
        base_query = SUPPORTED_GAMES.get("ARK: Survival Ascended", {}).get("default_ports", {}).get("query", 27015)
        free_port, free_query = self.get_next_free_ports(base_port, base_query)
        self.port_entry.insert(0, str(free_port))
        self.query_port_entry.insert(0, str(free_query))
        
        # Max Players
        ctk.CTkLabel(scroll, text=t("max_players") + ":", font=("Arial", 14)).pack(anchor="w", pady=(20, 5))
        self.players_entry = ctk.CTkEntry(scroll, width=100, height=35)
        self.players_entry.pack(anchor="w", pady=5)
        self.players_entry.insert(0, "10")
        
        # Passwörter
        ctk.CTkLabel(scroll, text="🔐 " + t("password") + ":", font=("Arial", 14)).pack(anchor="w", pady=(20, 5))
        
        pw_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        pw_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(pw_frame, text="Server:", font=("Arial", 11)).pack(side="left")
        self.server_pw_entry = ctk.CTkEntry(pw_frame, width=150, height=30, placeholder_text="(optional)")
        self.server_pw_entry.pack(side="left", padx=(5, 20))
        
        ctk.CTkLabel(pw_frame, text="Admin:", font=("Arial", 11)).pack(side="left")
        self.admin_pw_entry = ctk.CTkEntry(pw_frame, width=150, height=30)
        self.admin_pw_entry.pack(side="left", padx=5)
        self.admin_pw_entry.insert(0, "admin")
        
        # Auto-Optionen
        ctk.CTkLabel(scroll, text=t("settings") + ":", font=("Arial", 14)).pack(anchor="w", pady=(20, 5))
        
        self.auto_restart_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            scroll,
            text=t("auto_restart"),
            variable=self.auto_restart_var
        ).pack(anchor="w", pady=5)
        
        self.auto_backup_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            scroll,
            text=t("auto_backup"),
            variable=self.auto_backup_var
        ).pack(anchor="w", pady=5)
        
        # Backup-Intervall Auswahl
        backup_interval_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        backup_interval_frame.pack(fill="x", pady=(5, 5), padx=(25, 0))
        
        ctk.CTkLabel(backup_interval_frame, text=t("backup_interval") + ":", font=("Arial", 12)).pack(side="left")
        
        self.backup_interval_var = ctk.StringVar(value=t("backup_interval_3h"))
        self.backup_interval_menu = ctk.CTkOptionMenu(
            backup_interval_frame,
            variable=self.backup_interval_var,
            values=[t("backup_interval_off"), t("backup_interval_1h"), t("backup_interval_3h"), t("backup_interval_6h")],
            width=150,
            height=30
        )
        self.backup_interval_menu.pack(side="left", padx=10)
        
        # Max Backups
        ctk.CTkLabel(backup_interval_frame, text=t("backup_max_count") + ":", font=("Arial", 12)).pack(side="left", padx=(20, 0))
        self.max_backups_entry = ctk.CTkEntry(backup_interval_frame, width=60, height=30)
        self.max_backups_entry.pack(side="left", padx=5)
        self.max_backups_entry.insert(0, "10")
        
        # Buttons
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=30)
        
        ctk.CTkButton(
            btn_frame,
            text=t("cancel"),
            command=self.destroy,
            width=150,
            fg_color="gray"
        ).pack(side="left")
        
        ctk.CTkButton(
            btn_frame,
            text=t("add_server"),
            command=self.add_server,
            width=150,
            fg_color="green"
        ).pack(side="right")
    
    def get_next_free_ports(self, base_port, base_query):
        """Findet die nächsten freien Ports"""
        used_ports = set()
        used_query_ports = set()
        
        for server_config in self.config_manager.servers.values():
            used_ports.add(server_config.get("port", 0))
            used_query_ports.add(server_config.get("query_port", 0))
        
        # Freien Game-Port finden
        port = base_port
        while port in used_ports:
            port += 10
        
        # Freien Query-Port finden
        query = base_query
        while query in used_query_ports:
            query += 10
        
        return port, query
    
    def on_game_changed(self, game):
        """Wird aufgerufen wenn das Spiel geändert wird"""
        game_info = SUPPORTED_GAMES.get(game, {})
        
        # Map-Auswahl nur für ARK
        if "maps" in game_info:
            self.map_label.pack(anchor="w", pady=(20, 5))
            self.map_menu.pack(pady=5)
            self.map_menu.configure(values=[m["name"] for m in game_info["maps"]])
            self.map_var.set(game_info["maps"][0]["name"])
        else:
            self.map_label.pack_forget()
            self.map_menu.pack_forget()
        
        # Default Ports - automatisch freie finden
        if "default_ports" in game_info:
            base_port = game_info["default_ports"]["game"]
            base_query = game_info["default_ports"]["query"]
            
            # Nächste freie Ports finden
            free_port, free_query = self.get_next_free_ports(base_port, base_query)
            
            self.port_entry.delete(0, "end")
            self.port_entry.insert(0, str(free_port))
            self.query_port_entry.delete(0, "end")
            self.query_port_entry.insert(0, str(free_query))
    
    def add_server(self):
        """Fügt den Server hinzu"""
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Fehler", "Bitte Server-Namen eingeben!")
            return
        
        # Server-ID generieren
        server_id = name.lower().replace(" ", "_")
        server_id = re.sub(r'[^a-z0-9_]', '', server_id)
        
        # Prüfen ob ID schon existiert
        if server_id in self.config_manager.servers:
            # ID einzigartig machen
            counter = 1
            while f"{server_id}_{counter}" in self.config_manager.servers:
                counter += 1
            server_id = f"{server_id}_{counter}"
        
        game = self.game_var.get()
        game_info = SUPPORTED_GAMES.get(game, {})
        
        # Map-Parameter für ARK
        map_param = ""
        if "maps" in game_info:
            map_name = self.map_var.get()
            for m in game_info["maps"]:
                if m["name"] == map_name:
                    map_param = m["param"]
                    break
        
        # Backup-Intervall aus Dropdown konvertieren
        t = self.config_manager.get_text
        interval_text = self.backup_interval_var.get()
        if interval_text == t("backup_interval_off"):
            backup_hours = 0
        elif interval_text == t("backup_interval_1h"):
            backup_hours = 1
        elif interval_text == t("backup_interval_3h"):
            backup_hours = 3
        elif interval_text == t("backup_interval_6h"):
            backup_hours = 6
        else:
            backup_hours = 3  # Default
        
        # Max Backups
        try:
            max_backups = int(self.max_backups_entry.get())
        except:
            max_backups = 10
        
        server_config = {
            "name": name,
            "game": game,
            "map": map_param,
            "map_name": self.map_var.get() if "maps" in game_info else "",
            "port": int(self.port_entry.get()),
            "query_port": int(self.query_port_entry.get()),
            "max_players": int(self.players_entry.get()),
            "server_password": self.server_pw_entry.get().strip(),
            "admin_password": self.admin_pw_entry.get().strip() or "admin",
            "mods": [],
            "mod_names": {},
            "conan_auto_mod_update": True if game == "Conan Exiles" else False,
            "conan_mod_sync": {},
            "conan_mod_upload": {},
            "auto_restart": self.auto_restart_var.get(),
            "auto_backup": self.auto_backup_var.get(),
            "backup_interval_hours": backup_hours,
            "max_backups": max_backups,
            "installed": False,
            "created_at": datetime.now().isoformat()
        }
        
        self.config_manager.add_server(server_id, server_config)
        
        self.destroy()
        self.on_add(server_id, server_config)

