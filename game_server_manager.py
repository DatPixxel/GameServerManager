"""
Game Server Manager Pro v2.0
Multi-Server Edition

Entwickelt für die Veröffentlichung - Multi-Server, Multi-Game, Multi-User
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import subprocess
import threading
import os
import sys
import json
import psutil
import time
from datetime import datetime, timedelta
import zipfile
import shutil
import requests
import re
import hashlib
import secrets
import struct
import ipaddress
import uuid
from flask import Flask, render_template_string, jsonify, request, session, redirect
from werkzeug.exceptions import RequestEntityTooLarge
import socket

# ==================== MODULARISIERTE BAUSTEINE (gsm-Paket) ====================
from gsm.constants import (
    VERSION, APP_NAME, SSL_VERIFY, GITHUB_REPO, GITHUB_API_URL, WEB_PORT,
    CONAN_WORKSHOP_APP_ID, CONAN_UPLOAD_MAX_BYTES, SENSITIVE_SERVER_KEYS,
)
from gsm.paths import (
    PATHS, get_paths, set_base_dir, ensure_directories,
    PROGRAM_DIR, CONFIG_DIR, LAUNCHER_CONFIG_FILE, load_base_dir, save_base_dir,
)
from gsm.games import SUPPORTED_GAMES
from gsm.i18n import TRANSLATIONS
from gsm.security import (
    PBKDF2_ITERATIONS, SECRET_ENC_PREFIX, _DPAPI_ENTROPY, ALLOWED_CONFIG_EXTENSIONS,
    hash_password, verify_password, is_legacy_hash,
    _dpapi_available, _dpapi_protect, _dpapi_unprotect,
    encrypt_secret, decrypt_secret, _encrypt_server_secrets, _decrypt_server_secrets_inplace,
    is_safe_path, validate_config_path, validate_backup_path, safe_extract_zip,
    generate_session_token,
)
from gsm.mods import _normalize_mod_id, _sanitize_pak_filename, fetch_workshop_mod_names
from gsm.rcon import RCONClient
from gsm.ark import ARK_MAP_DATA, ArkMapManager, ArkSaveParser
from gsm.discord import DiscordNotifier
from gsm.updater import AutoUpdater
from gsm.config import ConfigManager
from gsm.server import ServerInstance
from gsm.web.templates import (
    get_login_template, get_web_template, _load_external_template,
    get_chat_disabled_template, get_chat_forbidden_template, get_chat_template,
)
from gsm.web.server import create_web_app, start_web_server as _create_and_start_web_server
from gsm.ui.wizard import SetupWizard
from gsm.ui.dialogs import AddServerDialog
from gsm.ui.mixins.services import TeamSpeakServicesMixin
from gsm.ui.mixins.backups import BackupsMixin

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# SSL Fix für PyInstaller
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except:
    pass

# System Tray (optional)
try:
    import pystray
    from PIL import Image, ImageDraw, ImageTk
    TRAY_AVAILABLE = True
    PIL_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False
    PIL_AVAILABLE = False

# Falls nur PIL fehlt
if not PIL_AVAILABLE:
    try:
        from PIL import Image, ImageDraw, ImageTk
        PIL_AVAILABLE = True
    except ImportError:
        PIL_AVAILABLE = False

# Windows Registry für Autostart
try:
    import winreg
    WINREG_AVAILABLE = True
except ImportError:
    WINREG_AVAILABLE = False

# ==================== KONSTANTEN ====================
# VERSION, APP_NAME, GITHUB_*, SSL_VERIFY, WEB_PORT, CONAN_*, SENSITIVE_SERVER_KEYS
# liegen jetzt in gsm/constants.py


# get_paths / PATHS / set_base_dir / ensure_directories liegen jetzt in gsm/paths.py
# CONAN_* liegen jetzt in gsm/constants.py
















# ==================== MAIN APPLICATION ====================
class GameServerManagerApp(TeamSpeakServicesMixin, BackupsMixin, ctk.CTk):
    """Hauptanwendung"""
    
    def __init__(self):
        super().__init__()
        
        global PATHS
        
        print(f"🚀 {APP_NAME} v{VERSION} startet...")
        print(f"📁 Config-Verzeichnis: {CONFIG_DIR}")
        
        # Server-Instanzen
        self.server_instances = {}
        
        # Discord Notifier (wird später initialisiert)
        self.discord_notifier = None
        
        # Global Log
        self.log_messages = []

        # Chat/Stream + TeamSpeak Runtime
        self.chat_runtime = {}
        self.ts3_process = None
        self.ts3_log_path = ""
        self.ts3_log_handle = None
        
        # Prüfe ob bereits eingerichtet
        saved_base_dir = load_base_dir()
        
        if saved_base_dir and os.path.exists(saved_base_dir):
            print(f"✅ Installationsordner gefunden: {saved_base_dir}")
            # Bereits eingerichtet - Pfade laden (in place)
            set_base_dir(saved_base_dir)
            self.config_manager = ConfigManager()
            
            # Discord Notifier initialisieren
            self.discord_notifier = DiscordNotifier(self.config_manager)
            
            # Prüfe ob first_run ODER Passwort fehlt
            first_run = self.config_manager.app_config.get("first_run", True)
            password_missing = not self.config_manager.users.get("admin", {}).get("password_hash", "")
            print(f"ℹ️ first_run = {first_run}, password_missing = {password_missing}")
            
            if first_run or password_missing:
                # Setup nicht abgeschlossen - neu starten
                print("⚠️ Setup war nicht abgeschlossen - starte Wizard")
                self.setup_window_minimal()
                self.withdraw()
                self.after(100, self.show_setup_wizard)
            else:
                # Normal starten
                print("✅ Starte normal...")
                self.setup_window()
                self.create_main_ui()
                self.start_services()
        else:
            # Erstes Mal - Setup Wizard zeigen
            print("ℹ️ Erster Start - zeige Setup Wizard")
            self.config_manager = None
            self.setup_window_minimal()
            self.withdraw()
            self.after(100, self.show_setup_wizard)
    
    def setup_window_minimal(self):
        """Minimale Fenster-Einstellungen für Setup"""
        self.title(f"{APP_NAME} v{VERSION}")
        self.geometry("1400x900")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
    
    def setup_window(self):
        """Grundlegende Fenster-Einstellungen"""
        t = self.config_manager.get_text
        
        self.title(f"{APP_NAME} v{VERSION}")
        self.geometry("1400x900")
        
        # Fenster zentrieren
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 1400) // 2
        y = (self.winfo_screenheight() - 900) // 2
        self.geometry(f"1400x900+{x}+{y}")
        
        ctk.set_appearance_mode(self.config_manager.app_config.get("theme", "dark"))
        ctk.set_default_color_theme("blue")
        
        # Close Event
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def show_setup_wizard(self):
        """Zeigt den Setup-Wizard"""
        wizard = SetupWizard(self, self.on_setup_complete)
        wizard.wait_window()
    
    def on_setup_complete(self, config_manager):
        """Wird aufgerufen wenn Setup abgeschlossen"""
        self.config_manager = config_manager
        self.deiconify()  # Hauptfenster anzeigen
        self.setup_window()
        self.create_main_ui()
        self.start_services()
    
    def create_main_ui(self):
        """Erstellt die Haupt-UI"""
        t = self.config_manager.get_text
        
        # Schriftgröße-Einstellung (Standard: 12)
        self.font_size = self.config_manager.app_config.get("font_size", 12)
        
        # Auto-Updater initialisieren
        self.updater = AutoUpdater(self)
        
        # ============ HEADER ============
        header = ctk.CTkFrame(self, height=55, corner_radius=0, fg_color="#0d0d15")
        header.pack(fill="x")
        header.pack_propagate(False)
        
        # Links: App Name + Version
        ctk.CTkLabel(
            header,
            text=f"🎮 {APP_NAME}",
            font=("Arial", 18, "bold"),
            text_color="#00d4ff"
        ).pack(side="left", padx=20, pady=12)
        
        ctk.CTkLabel(
            header,
            text=f"v{VERSION}",
            font=("Arial", 12),
            text_color="#555555"
        ).pack(side="left", padx=5)
        
        # Mitte-Links: Web Interface + Update
        mid_frame = ctk.CTkFrame(header, fg_color="transparent")
        mid_frame.pack(side="left", padx=30, pady=10)
        
        web_port = self.config_manager.app_config.get("web", {}).get("port", 5001)
        ctk.CTkButton(
            mid_frame,
            text=f"🌐 localhost:{web_port}",
            font=("Arial", 13),
            width=140,
            height=35,
            fg_color="#1a1a2e",
            hover_color="#2a2a3e",
            command=self.open_web_interface
        ).pack(side="left", padx=3)
        
        self.update_btn = ctk.CTkButton(
            mid_frame,
            text="🔄 Update",
            width=110,
            height=35,
            font=("Arial", 13),
            fg_color="#2d5a3d",
            hover_color="#3d7a4d",
            command=self.check_for_updates
        )
        self.update_btn.pack(side="left", padx=3)
        
        # Rechts: Settings, Discord, Cluster
        right_frame = ctk.CTkFrame(header, fg_color="transparent")
        right_frame.pack(side="right", padx=15, pady=10)
        
        ctk.CTkButton(
            right_frame,
            text="🔗 Cluster",
            width=110,
            height=35,
            font=("Arial", 13),
            fg_color="#6a3a8a",
            hover_color="#7a4a9a",
            command=self.show_cluster_settings
        ).pack(side="right", padx=3)
        
        ctk.CTkButton(
            right_frame,
            text="🔔 Discord",
            width=110,
            height=35,
            font=("Arial", 13),
            fg_color="#5865F2",
            hover_color="#4752C4",
            command=self.show_discord_settings
        ).pack(side="right", padx=3)
        
        ctk.CTkButton(
            right_frame,
            text="⚙️ Settings",
            width=110,
            height=35,
            font=("Arial", 13),
            fg_color="#3a3a4a",
            hover_color="#4a4a5a",
            command=self.show_app_settings
        ).pack(side="right", padx=3)
        
        # ============ MAIN CONTAINER ============
        main = ctk.CTkFrame(self, fg_color="#0d0d15")
        main.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Sidebar Container (für Resize)
        self.sidebar_container = ctk.CTkFrame(main, fg_color="transparent")
        self.sidebar_container.pack(side="left", fill="y", padx=(0, 0))
        
        # Sidebar - Modernes Design
        self.sidebar_width = 280
        self.sidebar = ctk.CTkFrame(
            self.sidebar_container, 
            width=self.sidebar_width,
            fg_color="#12121a",
            corner_radius=0
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        
        # Resize Handle (vertikaler Balken zum Ziehen)
        self.resize_handle = ctk.CTkFrame(
            self.sidebar_container, 
            width=4, 
            fg_color="#2a2a3a",
            cursor="sb_h_double_arrow"
        )
        self.resize_handle.pack(side="left", fill="y", padx=(0, 0))
        
        # Resize Events
        self.resize_handle.bind("<Button-1>", self._start_resize)
        self.resize_handle.bind("<B1-Motion>", self._do_resize)
        self.resize_handle.bind("<Enter>", lambda e: self.resize_handle.configure(fg_color="#00d4ff"))
        self.resize_handle.bind("<Leave>", lambda e: self.resize_handle.configure(fg_color="#2a2a3a"))
        
        # ============ SIDEBAR NAVIGATION ============
        
        # Navigation Variable für aktiven Zustand
        self.active_nav = "dashboard"
        
        # --- Logo/Brand Section ---
        brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_frame.pack(fill="x", padx=15, pady=(15, 10))
        
        ctk.CTkLabel(
            brand_frame,
            text="🎮",
            font=("Arial", 28)
        ).pack(side="left")
        
        ctk.CTkLabel(
            brand_frame,
            text="GSM Pro",
            font=("Arial", 18, "bold"),
            text_color="#00d4ff"
        ).pack(side="left", padx=8)
        
        # Trennlinie
        ctk.CTkFrame(self.sidebar, height=1, fg_color="#2a2a3a").pack(fill="x", padx=10, pady=5)
        
        # --- MENU Section ---
        ctk.CTkLabel(
            self.sidebar,
            text="MENU",
            font=("Arial", 12, "bold"),
            text_color="#666666",
            anchor="w"
        ).pack(fill="x", padx=20, pady=(10, 8))
        
        # Navigation Buttons Frame
        self.nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.nav_frame.pack(fill="x", padx=10)
        
        # Navigation Buttons erstellen
        self.nav_buttons = {}
        self.create_sidebar_nav()
        
        # Trennlinie
        ctk.CTkFrame(self.sidebar, height=1, fg_color="#2a2a3a").pack(fill="x", padx=10, pady=10)
        
        # --- SERVERS Section ---
        ctk.CTkLabel(
            self.sidebar,
            text="SERVERS",
            font=("Arial", 12, "bold"),
            text_color="#666666",
            anchor="w"
        ).pack(fill="x", padx=20, pady=(5, 8))
        
        # Add Server Button
        add_server_btn = ctk.CTkButton(
            self.sidebar,
            text="+ Add Server",
            font=("Arial", 13),
            height=40,
            fg_color="#2d5a2d",
            hover_color="#3d7a3d",
            corner_radius=8,
            command=self.show_add_server_dialog
        )
        add_server_btn.pack(fill="x", padx=15, pady=5)
        
        # Server-Liste (scrollable)
        self.server_list_frame = ctk.CTkScrollableFrame(
            self.sidebar,
            fg_color="transparent",
            scrollbar_button_color="#3a3a4a",
            scrollbar_button_hover_color="#4a4a5a"
        )
        self.server_list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Version Info am Ende
        ctk.CTkLabel(
            self.sidebar,
            text=f"v{VERSION}",
            font=("Arial", 12),
            text_color="#555555"
        ).pack(pady=10)
        
        # ============ END SIDEBAR NAVIGATION ============
        
        # Content Area
        self.content_area = ctk.CTkFrame(main, fg_color="#1a1a2e")
        self.content_area.pack(side="right", fill="both", expand=True)
        
        # Server-Liste laden
        self.refresh_server_list()
        
        # Dashboard anzeigen (Standard-Ansicht)
        self.show_dashboard()
    
    def create_sidebar_nav(self):
        """Erstellt die Sidebar Navigation Buttons"""
        # Alte Buttons löschen
        for widget in self.nav_frame.winfo_children():
            widget.destroy()
        
        # Navigation Items
        nav_items = [
            ("📊", "Dashboard", "dashboard", self.nav_show_dashboard),
            ("🖥️", "Servers", "servers", self.nav_show_servers),
            ("🔧", "Tools", "tools", self.nav_show_tools),
        ]
        
        server_count = len(self.config_manager.servers)
        
        for icon, text, nav_id, command in nav_items:
            is_active = self.active_nav == nav_id
            
            # Button Frame
            btn = ctk.CTkButton(
                self.nav_frame,
                text=f"{icon}  {text}" + (f"  ({server_count})" if nav_id == "servers" else ""),
                font=("Arial", 13, "bold") if is_active else ("Arial", 13),
                height=42,
                anchor="w",
                fg_color="#1e3a5f" if is_active else "transparent",
                hover_color="#2a2a3e",
                text_color="#ffffff" if is_active else "#aaaaaa",
                border_width=2 if is_active else 0,
                border_color="#00d4ff",
                command=command
            )
            btn.pack(fill="x", pady=2)
    
    def nav_show_dashboard(self):
        """Navigation: Dashboard anzeigen"""
        self.active_nav = "dashboard"
        self.create_sidebar_nav()
        self.show_dashboard()
    
    def nav_show_servers(self):
        """Navigation: Server-Liste fokussieren"""
        self.active_nav = "servers"
        self.create_sidebar_nav()
        self.show_servers_view()  # Eigene Server-Ansicht
    
    def show_servers_view(self):
        """Zeigt die Server-Übersicht (Liste aller Server)"""
        t = self.config_manager.get_text
        
        # Content leeren
        for widget in self.content_area.winfo_children():
            widget.destroy()
        
        # Header
        header = ctk.CTkFrame(self.content_area, fg_color="#12121a", height=50)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        ctk.CTkLabel(
            header,
            text="🖥️ Server Übersicht",
            font=("Arial", 18, "bold"),
            text_color="#00d4ff"
        ).pack(side="left", padx=20, pady=12)
        
        # Server Count
        total = len(self.config_manager.servers)
        running = sum(1 for sid in self.config_manager.servers 
                     if self.server_instances.get(sid) and self.server_instances[sid].is_running())
        
        ctk.CTkLabel(
            header,
            text=f"🟢 {running} Online  |  📦 {total} Total",
            font=("Arial", 13),
            text_color="#888888"
        ).pack(side="right", padx=20)
        
        # Scrollable Liste
        scroll = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=15, pady=10)
        
        if not self.config_manager.servers:
            ctk.CTkLabel(
                scroll,
                text="Keine Server vorhanden",
                font=("Arial", 16),
                text_color="#666666"
            ).pack(pady=50)
            return
        
        # Server als Listeneinträge
        for server_id, server_config in self.config_manager.servers.items():
            instance = self.server_instances.get(server_id)
            if not instance:
                instance = ServerInstance(server_id, server_config, self.config_manager, self.discord_notifier)
                self.server_instances[server_id] = instance
            
            is_running = instance.is_running()
            game_info = SUPPORTED_GAMES.get(server_config.get("game", ""), {})
            icon = game_info.get("icon", "🎮")
            
            # Server Row
            row = ctk.CTkFrame(scroll, fg_color="#1e1e2e", corner_radius=10)
            row.pack(fill="x", pady=5)
            
            row_inner = ctk.CTkFrame(row, fg_color="transparent")
            row_inner.pack(fill="x", padx=15, pady=12)
            
            # Status Indicator
            status_color = "#00ff88" if is_running else "#ff4444"
            ctk.CTkLabel(
                row_inner,
                text="●",
                font=("Arial", 20),
                text_color=status_color,
                width=30
            ).pack(side="left")
            
            # Icon + Name
            ctk.CTkLabel(
                row_inner,
                text=f"{icon} {server_config.get('name', 'Server')}",
                font=("Arial", 14, "bold"),
                anchor="w"
            ).pack(side="left", padx=10)
            
            # Game
            ctk.CTkLabel(
                row_inner,
                text=server_config.get("game", ""),
                font=("Arial", 12),
                text_color="#888888"
            ).pack(side="left", padx=20)
            
            # Port
            ctk.CTkLabel(
                row_inner,
                text=f":{server_config.get('port', '?')}",
                font=("Arial", 12),
                text_color="#666666"
            ).pack(side="left")
            
            # Buttons rechts
            btn_frame = ctk.CTkFrame(row_inner, fg_color="transparent")
            btn_frame.pack(side="right")
            
            # Details Button
            ctk.CTkButton(
                btn_frame,
                text="⚙️ Details",
                width=90,
                height=32,
                font=("Arial", 12),
                fg_color="#3a3a4a",
                hover_color="#4a4a5a",
                command=lambda sid=server_id: self.select_server(sid)
            ).pack(side="left", padx=3)
            
            # Start/Stop
            if is_running:
                ctk.CTkButton(
                    btn_frame,
                    text="⏹ Stop",
                    width=80,
                    height=32,
                    font=("Arial", 12),
                    fg_color="#aa3333",
                    hover_color="#cc4444",
                    command=lambda sid=server_id: self.quick_stop_server(sid)
                ).pack(side="left", padx=3)
            else:
                ctk.CTkButton(
                    btn_frame,
                    text="▶ Start",
                    width=80,
                    height=32,
                    font=("Arial", 12),
                    fg_color="#2d5a2d",
                    hover_color="#3d7a3d",
                    command=lambda sid=server_id: self.quick_start_server(sid)
                ).pack(side="left", padx=3)
    
    def nav_show_tools(self):
        """Navigation: Tools anzeigen"""
        self.active_nav = "tools"
        self.create_sidebar_nav()
        self.show_tools_menu()
    
    # Window Control Functions für Custom Title Bar
    def on_closing(self):
        """Wird beim Schließen des Fensters aufgerufen"""
        # Alle Server stoppen die laufen
        for server_id, instance in self.server_instances.items():
            if instance.is_running():
                try:
                    instance.stop()
                except:
                    pass

        # TeamSpeak 3 stoppen, falls gestartet
        try:
            self.stop_teamspeak3_server()
        except:
            pass
        
        # Fenster schließen
        self.destroy()
    
    def create_footer_button(self, parent, icon, text, command):
        """Erstellt einen Footer Button"""
        btn = ctk.CTkButton(
            parent,
            text=f"{icon} {text}",
            font=("Arial", 11),
            height=32,
            fg_color="transparent",
            hover_color="#2a2a3a",
            text_color="#888888",
            anchor="w",
            command=command
        )
        btn.pack(fill="x", pady=2)
    
    def set_active_nav(self, nav_id):
        """Setzt den aktiven Navigation-Zustand"""
        self.active_nav = nav_id
        # Navigation neu aufbauen wäre zu aufwändig, daher nur visuelles Update
    
    def toggle_server_list(self):
        """Toggle für Server-Liste (expandieren/kollabieren)"""
        # Server-Liste ist immer sichtbar, dieser Button scrollt einfach hoch
        self.server_list_frame._parent_canvas.yview_moveto(0)
    
    def show_tools_menu(self):
        """Zeigt das Tools-Menü"""
        # Auto-Refresh stoppen
        if hasattr(self, '_dashboard_refresh_id'):
            try:
                self.after_cancel(self._dashboard_refresh_id)
            except:
                pass
        
        # Content leeren
        for widget in self.content_area.winfo_children():
            widget.destroy()
        
        # Header
        header_frame = ctk.CTkFrame(self.content_area, fg_color="#1a1a2e", height=60)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        ctk.CTkLabel(
            header_frame,
            text="🔧 Tools & Utilities",
            font=("Arial", 22, "bold"),
            text_color="#00d4ff"
        ).pack(side="left", padx=20, pady=15)
        
        # Scrollable Content
        scroll = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Tools Grid (2 Spalten)
        scroll.grid_columnconfigure((0, 1), weight=1, uniform="tool")
        
        # Tool Cards
        tools = [
            ("🔄", "Auto-Updates", "SteamCMD Updates für alle Server", self.check_for_updates),
            ("💾", "Backup Manager", "Backups erstellen und verwalten", self.show_backup_manager),
            ("📊", "System Monitor", "CPU/RAM Übersicht", self.show_system_monitor),
            ("🌐", "Web Interface", "Browser-Zugriff öffnen", self.open_web_interface),
            ("💬", "Chat & Stream", "Textchat + Screen/Game Stream verwalten", self.show_chat_stream_manager),
            ("🎙️", "TeamSpeak Server", "TS3/TS6 Server starten/stoppen + Status", self.show_teamspeak3_manager),
            ("📁", "Ordner öffnen", "Server-Verzeichnis öffnen", self.open_base_folder),
            ("🔗", "Cluster Manager", "ARK Cluster verwalten", self.show_cluster_settings),
        ]
        
        for i, (icon, title, desc, cmd) in enumerate(tools):
            row = i // 2
            col = i % 2
            self.create_tool_card(scroll, icon, title, desc, cmd, row, col)
    
    def create_tool_card(self, parent, icon, title, desc, command, row, col):
        """Erstellt eine Tool-Karte"""
        card = ctk.CTkFrame(
            parent,
            corner_radius=12,
            fg_color="#1e1e2e",
            border_width=1,
            border_color="#2a2a3a"
        )
        card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        
        # Icon
        ctk.CTkLabel(
            card,
            text=icon,
            font=("Arial", 36)
        ).pack(pady=(20, 10))
        
        # Title
        ctk.CTkLabel(
            card,
            text=title,
            font=("Arial", 14, "bold")
        ).pack()
        
        # Description
        ctk.CTkLabel(
            card,
            text=desc,
            font=("Arial", 12),
            text_color="#666666"
        ).pack(pady=5)
        
        # Button
        ctk.CTkButton(
            card,
            text="Öffnen",
            width=100,
            height=32,
            fg_color="#00d4ff",
            hover_color="#00b4d8",
            text_color="#000000",
            command=command
        ).pack(pady=(10, 20))
    
    def show_system_monitor(self):
        """Zeigt System-Monitor mit CPU/RAM"""
        # Auto-Refresh stoppen
        if hasattr(self, '_dashboard_refresh_id'):
            try:
                self.after_cancel(self._dashboard_refresh_id)
            except:
                pass
        
        # Content leeren
        for widget in self.content_area.winfo_children():
            widget.destroy()
        
        # Header
        header_frame = ctk.CTkFrame(self.content_area, fg_color="#1a1a2e", height=60)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        ctk.CTkLabel(
            header_frame,
            text="📊 System Monitor",
            font=("Arial", 22, "bold"),
            text_color="#00d4ff"
        ).pack(side="left", padx=20, pady=15)
        
        # Content Frame
        content = ctk.CTkFrame(self.content_area, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=20)
        
        # System Stats
        try:
            cpu_percent = psutil.cpu_percent(interval=0.5)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
        except:
            cpu_percent = 0
            ram = None
            disk = None
        
        # Stats Grid
        content.grid_columnconfigure((0, 1, 2), weight=1, uniform="stat")
        
        # CPU Card
        self.create_stat_card(content, "CPU", f"{cpu_percent:.0f}%", 
                             cpu_percent/100, "#00ff88" if cpu_percent < 70 else "#ff4444", 0)
        
        # RAM Card
        if ram:
            ram_percent = ram.percent
            ram_used = ram.used / (1024**3)
            ram_total = ram.total / (1024**3)
            self.create_stat_card(content, "RAM", f"{ram_used:.1f} / {ram_total:.1f} GB",
                                 ram_percent/100, "#00d4ff" if ram_percent < 80 else "#ff4444", 1)
        
        # Disk Card
        if disk:
            disk_percent = disk.percent
            disk_used = disk.used / (1024**3)
            disk_total = disk.total / (1024**3)
            self.create_stat_card(content, "Disk", f"{disk_used:.0f} / {disk_total:.0f} GB",
                                 disk_percent/100, "#ffaa00" if disk_percent < 90 else "#ff4444", 2)
        
        # Server Stats Section
        server_frame = ctk.CTkFrame(content, fg_color="#1e1e2e", corner_radius=12)
        server_frame.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=20)
        
        ctk.CTkLabel(
            server_frame,
            text="🖥️ Server Ressourcen",
            font=("Arial", 16, "bold")
        ).pack(anchor="w", padx=20, pady=15)
        
        # Server Liste mit Ressourcen
        for server_id, server_config in self.config_manager.servers.items():
            instance = self.server_instances.get(server_id)
            is_running = instance and instance.is_running() if instance else False
            
            if is_running:
                resources = instance.get_resource_usage()
                self.create_server_resource_row(server_frame, server_config["name"], resources)
    
    def create_stat_card(self, parent, title, value, progress, color, col):
        """Erstellt eine Statistik-Karte"""
        card = ctk.CTkFrame(parent, fg_color="#1e1e2e", corner_radius=12)
        card.grid(row=0, column=col, padx=10, pady=10, sticky="nsew")
        
        ctk.CTkLabel(
            card,
            text=title,
            font=("Arial", 12),
            text_color="#666666"
        ).pack(pady=(20, 5))
        
        ctk.CTkLabel(
            card,
            text=value,
            font=("Arial", 24, "bold"),
            text_color=color
        ).pack()
        
        progress_bar = ctk.CTkProgressBar(card, width=150, height=8, progress_color=color)
        progress_bar.pack(pady=(10, 20))
        progress_bar.set(progress)
    
    def create_server_resource_row(self, parent, name, resources):
        """Erstellt eine Zeile für Server-Ressourcen"""
        row = ctk.CTkFrame(parent, fg_color="#2a2a3a", corner_radius=8)
        row.pack(fill="x", padx=15, pady=3)
        
        content = ctk.CTkFrame(row, fg_color="transparent")
        content.pack(fill="x", padx=10, pady=8)
        
        # Name
        ctk.CTkLabel(
            content,
            text=name,
            font=("Arial", 11),
            width=150,
            anchor="w"
        ).pack(side="left")
        
        # CPU
        cpu = resources.get("cpu", 0)
        ctk.CTkLabel(
            content,
            text=f"CPU: {cpu:.0f}%",
            font=("Arial", 12),
            text_color="#00ff88" if cpu < 50 else "#ffaa00" if cpu < 80 else "#ff4444",
            width=80
        ).pack(side="left", padx=10)
        
        # RAM
        ram = resources.get("ram_gb", 0)
        ctk.CTkLabel(
            content,
            text=f"RAM: {ram:.1f} GB",
            font=("Arial", 12),
            text_color="#00d4ff",
            width=100
        ).pack(side="left", padx=10)
    

    def open_base_folder(self):
        """Öffnet den Basis-Ordner"""
        import subprocess
        if os.name == 'nt':
            os.startfile(PATHS["base"])
        else:
            subprocess.run(["xdg-open", PATHS["base"]])
    
    def _start_resize(self, event):
        """Startet das Resize der Sidebar"""
        self._resize_start_x = event.x_root
        self._resize_start_width = self.sidebar_width
    
    def _do_resize(self, event):
        """Führt das Resize der Sidebar durch"""
        delta = event.x_root - self._resize_start_x
        new_width = self._resize_start_width + delta
        
        # Limits: min 200px, max 450px
        new_width = max(200, min(450, new_width))
        
        if new_width != self.sidebar_width:
            self.sidebar_width = new_width
            self.sidebar.configure(width=new_width)
    
    def refresh_server_list(self):
        """Aktualisiert die Server-Liste - gruppiert nach Spielen"""
        # Alte Einträge löschen
        for widget in self.server_list_frame.winfo_children():
            widget.destroy()
        
        # Server nach Spielen gruppieren
        games_servers = {}
        for server_id, server_config in self.config_manager.servers.items():
            game = server_config.get("game", "Unbekannt")
            if game not in games_servers:
                games_servers[game] = []
            games_servers[game].append((server_id, server_config))
        
        # Speicher für Gruppen-States (aufgeklappt/zugeklappt)
        if not hasattr(self, 'group_states'):
            self.group_states = {}
        
        # Für jedes Spiel eine Gruppe erstellen
        for game, servers in sorted(games_servers.items()):
            game_info = SUPPORTED_GAMES.get(game, {})
            icon = game_info.get("icon", "🎮")
            
            # Default: aufgeklappt
            if game not in self.group_states:
                self.group_states[game] = True
            
            # Kategorie-Header
            self.create_game_category(game, icon, servers)
    
    def create_game_category(self, game, icon, servers):
        """Erstellt eine moderne Spielkategorie mit Servern"""
        is_expanded = self.group_states.get(game, True)
        
        # Zähle laufende Server
        running_count = 0
        for server_id, _ in servers:
            instance = self.server_instances.get(server_id)
            if instance and instance.is_running():
                running_count += 1
        
        # Kategorie-Header Frame - moderneres Design
        header_frame = ctk.CTkFrame(
            self.server_list_frame, 
            cursor="hand2",
            corner_radius=8,
            fg_color=("#3a3a4a", "#252535")
        )
        header_frame.pack(fill="x", pady=(8, 2), padx=2)
        
        # Header Content
        header_content = ctk.CTkFrame(header_frame, fg_color="transparent")
        header_content.pack(fill="x", padx=12, pady=10)
        
        # Expand/Collapse Icon
        expand_icon = "▼" if is_expanded else "▶"
        expand_label = ctk.CTkLabel(
            header_content,
            text=expand_icon,
            font=("Arial", 12),
            text_color="#888888",
            width=15
        )
        expand_label.pack(side="left")
        
        # Game Icon + Name
        ctk.CTkLabel(
            header_content,
            text=f"{icon} {game}",
            font=("Arial", 13, "bold"),
            anchor="w"
        ).pack(side="left", padx=(5, 0))
        
        # Server-Anzahl Badge
        badge_color = "#2d5a2d" if running_count > 0 else "#4a4a5a"
        badge_text_color = "#00ff88" if running_count > 0 else "#888888"
        
        badge = ctk.CTkFrame(header_content, fg_color=badge_color, corner_radius=10)
        badge.pack(side="right")
        
        ctk.CTkLabel(
            badge,
            text=f"{running_count}/{len(servers)}",
            font=("Arial", 10, "bold"),
            text_color=badge_text_color,
            padx=8,
            pady=2
        ).pack()
        
        # Click Event für Expand/Collapse
        def toggle_category(event=None, g=game):
            self.group_states[g] = not self.group_states.get(g, True)
            self.refresh_server_list()
        
        header_frame.bind("<Button-1>", toggle_category)
        for child in header_frame.winfo_children():
            child.bind("<Button-1>", toggle_category)
            for subchild in child.winfo_children():
                subchild.bind("<Button-1>", toggle_category)
        
        # Server-Liste (nur wenn aufgeklappt)
        if is_expanded:
            for server_id, server_config in servers:
                self.create_server_list_item(server_id, server_config, indent=True)
    
    def create_server_list_item(self, server_id, server_config, indent=False):
        """Erstellt einen modernen Server-Eintrag in der Sidebar"""
        game_info = SUPPORTED_GAMES.get(server_config["game"], {})
        icon = game_info.get("icon", "🎮")
        
        # Status ermitteln
        instance = self.server_instances.get(server_id)
        is_running = instance and instance.is_running() if instance else False
        
        # Frame für den Server mit Status-abhängiger Farbe
        border_color = "#00ff88" if is_running else "#3a3a4a"
        frame = ctk.CTkFrame(
            self.server_list_frame, 
            cursor="hand2",
            corner_radius=8,
            border_width=1,
            border_color=border_color,
            fg_color=("#2a2a3a", "#1e1e2e")
        )
        if indent:
            frame.pack(fill="x", pady=3, padx=(15, 2))
        else:
            frame.pack(fill="x", pady=4, padx=2)
        
        # Haupt-Content Frame
        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.pack(fill="x", padx=10, pady=8)
        
        # Obere Zeile: Name + Status-Badge
        top_row = ctk.CTkFrame(content, fg_color="transparent")
        top_row.pack(fill="x")
        
        # Server Name
        ctk.CTkLabel(
            top_row,
            text=server_config['name'],
            font=("Arial", 12, "bold"),
            anchor="w"
        ).pack(side="left")
        
        # Status Badge
        status_color = "#00ff88" if is_running else "#ff4444"
        status_text = "●" if is_running else "○"
        
        status_badge = ctk.CTkLabel(
            top_row,
            text=status_text,
            text_color=status_color,
            font=("Arial", 12)
        )
        status_badge.pack(side="right")
        
        # Untere Zeile: Map und Port Info
        info_text_parts = []
        
        # Map (wenn vorhanden)
        map_name = server_config.get("map_name", "")
        if map_name:
            short_map = map_name[:15] + "..." if len(map_name) > 15 else map_name
            info_text_parts.append(f"🗺️ {short_map}")
        
        # Port
        port = server_config.get("port", game_info.get("default_ports", {}).get("game", ""))
        if port:
            info_text_parts.append(f":{port}")
        
        if info_text_parts:
            ctk.CTkLabel(
                content,
                text="  ".join(info_text_parts),
                font=("Arial", 12),
                text_color="#666666",
                anchor="w"
            ).pack(fill="x", pady=(3, 0))
        
        # Cluster-Info (wenn vorhanden)
        cluster_id = server_config.get("cluster", "")
        if cluster_id:
            clusters = self.config_manager.app_config.get("clusters", {})
            cluster_name = clusters.get(cluster_id, {}).get("name", cluster_id)
            ctk.CTkLabel(
                content,
                text=f"🔗 {cluster_name}",
                font=("Arial", 12),
                text_color="#9c27b0",
                anchor="w"
            ).pack(fill="x", pady=(2, 0))
        
        # Click Event
        frame.bind("<Button-1>", lambda e, sid=server_id: self.select_server(sid))
        for child in frame.winfo_children():
            child.bind("<Button-1>", lambda e, sid=server_id: self.select_server(sid))
            for subchild in child.winfo_children():
                subchild.bind("<Button-1>", lambda e, sid=server_id: self.select_server(sid))
                for subsubchild in subchild.winfo_children():
                    subsubchild.bind("<Button-1>", lambda e, sid=server_id: self.select_server(sid))
    
    def show_no_servers_message(self):
        """Zeigt Nachricht wenn keine Server vorhanden"""
        t = self.config_manager.get_text
        
        for widget in self.content_area.winfo_children():
            widget.destroy()
        
        msg_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
        msg_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        ctk.CTkLabel(
            msg_frame,
            text="🎮",
            font=("Arial", 72)
        ).pack(pady=20)
        
        ctk.CTkLabel(
            msg_frame,
            text=t("no_servers"),
            font=("Arial", 24, "bold")
        ).pack(pady=10)
        
        ctk.CTkLabel(
            msg_frame,
            text=t("add_first_server"),
            font=("Arial", 16),
            text_color="gray"
        ).pack(pady=10)
        
        ctk.CTkButton(
            msg_frame,
            text="+ " + t("add_server"),
            command=self.show_add_server_dialog,
            font=("Arial", 16),
            height=50,
            width=200
        ).pack(pady=30)
    
    def show_dashboard(self):
        """Zeigt das Dashboard mit Server-Karten im Grid-Layout"""
        t = self.config_manager.get_text
        
        # Auto-Refresh stoppen falls aktiv
        if hasattr(self, '_dashboard_refresh_id'):
            self.after_cancel(self._dashboard_refresh_id)
        
        # Content leeren
        for widget in self.content_area.winfo_children():
            widget.destroy()
        
        # Wenn keine Server, zeige "No Servers" Message
        if not self.config_manager.servers:
            self.show_no_servers_message()
            return
        
        # Dashboard Header - kompakt
        header_frame = ctk.CTkFrame(self.content_area, fg_color="#12121a", height=45)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        # Left: Title
        ctk.CTkLabel(
            header_frame,
            text="📊 Dashboard",
            font=("Arial", 16, "bold"),
            text_color="#00d4ff"
        ).pack(side="left", padx=15, pady=10)
        
        # Refresh Button (klein)
        ctk.CTkButton(
            header_frame,
            text="🔄",
            width=28,
            height=28,
            font=("Arial", 11),
            fg_color="#2a2a3a",
            hover_color="#3a3a4a",
            command=self.show_dashboard
        ).pack(side="left", padx=3, pady=8)
        
        # Live Badge
        live_badge = ctk.CTkFrame(header_frame, fg_color="#1a3a1a", corner_radius=10)
        live_badge.pack(side="left", padx=5, pady=10)
        ctk.CTkLabel(
            live_badge,
            text="● LIVE",
            font=("Arial", 12),
            text_color="#00ff88",
            padx=8,
            pady=2
        ).pack()
        
        # Server Stats (rechts)
        total_servers = len(self.config_manager.servers)
        running_servers = sum(1 for sid in self.config_manager.servers 
                            if self.server_instances.get(sid) and self.server_instances[sid].is_running())
        
        stats_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        stats_frame.pack(side="right", padx=15)
        
        # Online Badge
        online_badge = ctk.CTkFrame(stats_frame, fg_color="#1a3a1a", corner_radius=8)
        online_badge.pack(side="left", padx=3)
        ctk.CTkLabel(
            online_badge,
            text=f"🟢 {running_servers}",
            font=("Arial", 12),
            text_color="#00ff88",
            padx=8,
            pady=3
        ).pack()
        
        # Total Badge
        total_badge = ctk.CTkFrame(stats_frame, fg_color="#2a2a3a", corner_radius=8)
        total_badge.pack(side="left", padx=3)
        ctk.CTkLabel(
            total_badge,
            text=f"📦 {total_servers}",
            font=("Arial", 12),
            text_color="#888888",
            padx=8,
            pady=3
        ).pack()
        
        # Scrollable Grid Container
        scroll = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Grid-Layout für Karten (3 Spalten)
        scroll.grid_columnconfigure((0, 1, 2), weight=1, uniform="card")
        
        # Server-Karten erstellen
        row = 0
        col = 0
        for server_id, server_config in self.config_manager.servers.items():
            self.create_server_card(scroll, server_id, server_config, row, col)
            col += 1
            if col >= 3:
                col = 0
                row += 1
        
        # Auto-Refresh alle 5 Sekunden (nur wenn Dashboard sichtbar)
        self._dashboard_refresh_id = self.after(5000, self._auto_refresh_dashboard)
    
    def _auto_refresh_dashboard(self):
        """Auto-Refresh für Dashboard wenn es sichtbar ist"""
        # Prüfen ob Dashboard noch angezeigt wird
        try:
            children = self.content_area.winfo_children()
            if children and hasattr(self, 'auto_refresh_label'):
                # Dashboard ist noch sichtbar - aktualisieren
                self.show_dashboard()
        except:
            pass
    
    def create_server_card(self, parent, server_id, server_config, row, col):
        """Erstellt eine moderne Server-Karte mit Live-Stats"""
        game = server_config.get("game", "Unknown")
        game_info = SUPPORTED_GAMES.get(game, {})
        icon = game_info.get("icon", "🎮")
        
        instance = self.server_instances.get(server_id)
        is_running = instance and instance.is_running() if instance else False
        
        # Ressourcen-Nutzung holen (echte Werte!)
        resources = {"cpu": 0, "ram_mb": 0, "ram_gb": 0, "ram_percent": 0}
        if is_running and instance:
            resources = instance.get_resource_usage()
        
        # Haupt-Karte
        card = ctk.CTkFrame(
            parent,
            corner_radius=10,
            fg_color="#1e1e2e",
            border_width=1,
            border_color="#00ff88" if is_running else "#2a2a3a"
        )
        card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
        
        # === Header (kompakt) ===
        header_bg = "#1a3a1a" if is_running else "#3a1a1a"
        
        card_header = ctk.CTkFrame(card, fg_color=header_bg, corner_radius=8)
        card_header.pack(fill="x", padx=4, pady=4)
        
        header_content = ctk.CTkFrame(card_header, fg_color="transparent")
        header_content.pack(fill="x", padx=10, pady=6)
        
        # Game + Status
        ctk.CTkLabel(
            header_content,
            text=f"{icon} {game[:15]}",
            font=("Arial", 12),
            text_color="#888888"
        ).pack(side="left")
        
        # Status Text
        status_text = "●" if is_running else "○"
        status_color = "#00ff88" if is_running else "#ff4444"
        ctk.CTkLabel(
            header_content,
            text=status_text,
            font=("Arial", 12),
            text_color=status_color
        ).pack(side="right")
        
        # === Server Name ===
        name = server_config.get("name", "Server")
        if len(name) > 20:
            name = name[:18] + "..."
        ctk.CTkLabel(
            card,
            text=name,
            font=("Arial", 13, "bold"),
            anchor="w"
        ).pack(fill="x", padx=12, pady=(6, 3))
        
        # === Quick Info ===
        port = server_config.get("port", "?")
        map_name = server_config.get("map_name", server_config.get("map", ""))
        if map_name and len(map_name) > 12:
            map_name = map_name[:10] + ".."
        
        info_text = f":{port}"
        if map_name:
            info_text += f"  🗺️ {map_name}"
        
        ctk.CTkLabel(
            card,
            text=info_text,
            font=("Arial", 12),
            text_color="#666666",
            anchor="w"
        ).pack(fill="x", padx=12, pady=(0, 5))
        
        # === Stats (wenn online) ===
        if is_running:
            stats_frame = ctk.CTkFrame(card, fg_color="#151520", corner_radius=6)
            stats_frame.pack(fill="x", padx=8, pady=(0, 5))
            
            stats_inner = ctk.CTkFrame(stats_frame, fg_color="transparent")
            stats_inner.pack(fill="x", padx=8, pady=5)
            
            cpu_value = resources.get("cpu", 0)
            ram_gb = resources.get("ram_gb", 0)
            
            cpu_color = "#00ff88" if cpu_value < 50 else "#ffaa00" if cpu_value < 80 else "#ff4444"
            
            ctk.CTkLabel(
                stats_inner,
                text=f"CPU {cpu_value:.0f}%",
                font=("Arial", 12),
                text_color=cpu_color
            ).pack(side="left")
            
            ctk.CTkLabel(
                stats_inner,
                text=f"RAM {ram_gb:.1f}G",
                font=("Arial", 12),
                text_color="#00d4ff"
            ).pack(side="right")
        
        # === Action Buttons (kompakt) ===
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(fill="x", padx=8, pady=(3, 8))
        
        # Settings Button
        ctk.CTkButton(
            btn_frame,
            text="⚙️",
            width=32,
            height=26,
            font=("Arial", 12),
            fg_color="#3a3a4a",
            hover_color="#4a4a5a",
            command=lambda sid=server_id: self.select_server(sid)
        ).pack(side="left", padx=2)
        
        # Start/Stop Button
        if is_running:
            ctk.CTkButton(
                btn_frame,
                text="⏹ Stop",
                width=55,
                height=26,
                font=("Arial", 12),
                fg_color="#6a2a2a",
                hover_color="#8a3a3a",
                command=lambda sid=server_id: self.quick_stop_server(sid)
            ).pack(side="right", padx=2)
        else:
            ctk.CTkButton(
                btn_frame,
                text="▶ Start",
                width=55,
                height=26,
                font=("Arial", 12),
                fg_color="#2a5a2a",
                hover_color="#3a7a3a",
                command=lambda sid=server_id: self.quick_start_server(sid)
            ).pack(side="right", padx=2)
    
    def _create_info_row(self, parent, label, value):
        """Erstellt eine Info-Zeile in der Server-Karte"""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=2)
        
        ctk.CTkLabel(
            row,
            text=label,
            font=("Arial", 12),
            text_color="#666666",
            width=60,
            anchor="w"
        ).pack(side="left")
        
        ctk.CTkLabel(
            row,
            text=value[:25] + "..." if len(value) > 25 else value,
            font=("Arial", 12),
            text_color="#aaaaaa",
            anchor="w"
        ).pack(side="left")
    
    def quick_start_server(self, server_id):
        """Schnellstart eines Servers vom Dashboard"""
        instance = self.server_instances.get(server_id)
        if instance:
            instance.start()
            self.after(1000, self.show_dashboard)  # Dashboard nach 1s aktualisieren
    
    def quick_stop_server(self, server_id):
        """Schnellstop eines Servers vom Dashboard"""
        instance = self.server_instances.get(server_id)
        if instance:
            instance.stop()
            self.after(1000, self.show_dashboard)  # Dashboard nach 1s aktualisieren
    
    def show_add_server_dialog(self):
        """Zeigt den Dialog zum Hinzufügen eines Servers"""
        AddServerDialog(self, self.config_manager, self.on_server_added)
    
    def on_server_added(self, server_id, server_config):
        """Wird aufgerufen wenn ein Server hinzugefügt wurde"""
        # Server-Instanz erstellen
        self.server_instances[server_id] = ServerInstance(server_id, server_config, self.config_manager, self.discord_notifier)
        
        # UI aktualisieren
        self.refresh_server_list()
        self.select_server(server_id)
    
    def select_server(self, server_id):
        """Wählt einen Server aus und zeigt Details"""
        # Auto-Refresh stoppen
        if hasattr(self, '_dashboard_refresh_id'):
            try:
                self.after_cancel(self._dashboard_refresh_id)
            except:
                pass
        
        self.current_server_id = server_id
        self.show_server_details(server_id)
    
    def show_server_details(self, server_id):
        """Zeigt die Server-Details - Modernes Design"""
        t = self.config_manager.get_text
        
        server_config = self.config_manager.servers.get(server_id, {})
        instance = self.server_instances.get(server_id)
        
        if not instance:
            instance = ServerInstance(server_id, server_config, self.config_manager, self.discord_notifier)
            self.server_instances[server_id] = instance
        
        game_info = SUPPORTED_GAMES.get(server_config.get("game", ""), {})
        is_running = instance.is_running()
        
        # Content leeren
        for widget in self.content_area.winfo_children():
            widget.destroy()
        
        # Scrollable Content
        scroll = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=15, pady=10)
        
        # ============ HEADER CARD ============
        header_card = ctk.CTkFrame(scroll, fg_color="#1e1e2e", corner_radius=12)
        header_card.pack(fill="x", pady=(0, 15))
        
        header_inner = ctk.CTkFrame(header_card, fg_color="transparent")
        header_inner.pack(fill="x", padx=20, pady=15)
        
        # Left: Icon + Name + Game
        left_frame = ctk.CTkFrame(header_inner, fg_color="transparent")
        left_frame.pack(side="left", fill="y")
        
        icon = game_info.get("icon", "🎮")
        
        # Server Name
        name_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        name_frame.pack(anchor="w")
        
        ctk.CTkLabel(
            name_frame,
            text=icon,
            font=("Arial", 32)
        ).pack(side="left")
        
        ctk.CTkLabel(
            name_frame,
            text=server_config.get('name', 'Server'),
            font=("Arial", 22, "bold"),
            text_color="#ffffff"
        ).pack(side="left", padx=10)
        
        # Game Name
        ctk.CTkLabel(
            left_frame,
            text=server_config.get("game", "Unknown"),
            font=("Arial", 11),
            text_color="#666666"
        ).pack(anchor="w", padx=45)
        
        # Right: Status Badge + Actions
        right_frame = ctk.CTkFrame(header_inner, fg_color="transparent")
        right_frame.pack(side="right")
        
        # Status Badge
        status_bg = "#1a4a1a" if is_running else "#4a1a1a"
        status_color = "#00ff88" if is_running else "#ff4444"
        status_text = "● ONLINE" if is_running else "○ OFFLINE"
        
        status_badge = ctk.CTkFrame(right_frame, fg_color=status_bg, corner_radius=15)
        status_badge.pack(pady=5)
        
        ctk.CTkLabel(
            status_badge,
            text=status_text,
            font=("Arial", 11, "bold"),
            text_color=status_color,
            padx=15,
            pady=5
        ).pack()
        
        # Quick Stats unter Status
        if is_running:
            resources = instance.get_resource_usage()
            stats_text = f"CPU: {resources.get('cpu', 0):.0f}%  |  RAM: {resources.get('ram_gb', 0):.1f} GB"
            ctk.CTkLabel(
                right_frame,
                text=stats_text,
                font=("Arial", 12),
                text_color="#666666"
            ).pack()
        
        # ============ ACTION BUTTONS ============
        action_card = ctk.CTkFrame(scroll, fg_color="#1e1e2e", corner_radius=12)
        action_card.pack(fill="x", pady=(0, 15))
        
        action_inner = ctk.CTkFrame(action_card, fg_color="transparent")
        action_inner.pack(fill="x", padx=15, pady=12)
        
        # Primary Actions (links)
        primary_frame = ctk.CTkFrame(action_inner, fg_color="transparent")
        primary_frame.pack(side="left")
        
        # Start/Stop Button
        if is_running:
            self._create_action_btn(primary_frame, "⏹", "Stop", "#dc3545", "#c82333", 
                                   lambda: self.stop_server(server_id))
        else:
            self._create_action_btn(primary_frame, "▶", "Start", "#28a745", "#218838",
                                   lambda: self.start_server(server_id))
        
        self._create_action_btn(primary_frame, "🔄", "Restart", "#fd7e14", "#e86c0a",
                               lambda: self.restart_server(server_id))
        
        self._create_action_btn(primary_frame, "💾", "Backup", "#17a2b8", "#138496",
                               lambda: self.backup_server(server_id))
        
        # Install Button wenn nötig
        if not instance.is_installed():
            self._create_action_btn(primary_frame, "📥", "Install", "#6f42c1", "#5a32a3",
                                   lambda: self.install_server(server_id), width=100)
        elif game_info.get("app_id"):
            self._create_action_btn(primary_frame, "⬆", "Update", "#20c997", "#1aa179",
                                   lambda: self.update_game_server(server_id))
        
        # Secondary Actions (rechts)
        secondary_frame = ctk.CTkFrame(action_inner, fg_color="transparent")
        secondary_frame.pack(side="right")
        
        self._create_action_btn(secondary_frame, "✏", "Edit", "#6c757d", "#5a6268",
                               lambda: self.show_edit_server_dialog(server_id), small=True)
        
        self._create_action_btn(secondary_frame, "📝", "Config", "#6c757d", "#5a6268",
                               lambda: self.show_config_editor(server_id), small=True)
        
        self._create_action_btn(secondary_frame, "📋", "Clone", "#6c757d", "#5a6268",
                               lambda: self.show_clone_dialog(server_id), small=True)
        
        self._create_action_btn(secondary_frame, "🗑", "", "#6c757d", "#dc3545",
                               lambda: self.delete_server(server_id), small=True, width=36)
        
        # ============ STATS CARDS ============
        stats_card = ctk.CTkFrame(scroll, fg_color="#1e1e2e", corner_radius=12)
        stats_card.pack(fill="x", pady=(0, 15))
        
        stats_inner = ctk.CTkFrame(stats_card, fg_color="transparent")
        stats_inner.pack(fill="x", padx=15, pady=15)
        stats_inner.columnconfigure((0, 1, 2, 3), weight=1, uniform="stat")
        
        # Uptime Card
        self._create_stat_card(stats_inner, 0, "⏱️", "Uptime", instance.get_uptime())
        
        # Port Card
        self._create_stat_card(stats_inner, 1, "🔌", "Port", str(server_config.get("port", "-")))
        
        # Players Card
        self._create_stat_card(stats_inner, 2, "👥", "Players", f"0/{server_config.get('max_players', '-')}")
        
        # Map Card
        map_name = server_config.get("map_name", server_config.get("map", "-"))
        if len(str(map_name)) > 15:
            map_name = str(map_name)[:12] + "..."
        self._create_stat_card(stats_inner, 3, "🗺️", "Map", str(map_name))
        
        # ============ CONNECTION INFO ============
        connect_card = ctk.CTkFrame(scroll, fg_color="#1e1e2e", corner_radius=12)
        connect_card.pack(fill="x", pady=(0, 15))
        
        # Header
        connect_header = ctk.CTkFrame(connect_card, fg_color="transparent")
        connect_header.pack(fill="x", padx=15, pady=(12, 5))
        
        ctk.CTkLabel(
            connect_header,
            text="🔗 Connection",
            font=("Arial", 14, "bold")
        ).pack(side="left")
        
        # Content
        connect_content = ctk.CTkFrame(connect_card, fg_color="#252535", corner_radius=8)
        connect_content.pack(fill="x", padx=15, pady=(5, 15))
        
        # IP-Adressen ermitteln
        local_ip = self.get_local_ip()
        tailscale_ip = self.get_tailscale_ip()
        port = server_config.get("port", 7777)
        query_port = server_config.get("query_port", 27015)
        game_name = server_config.get("game", "")
        
        # Verbindungs-String je nach Spiel
        connect_string = f"{local_ip}:{port}"
        steam_connect = f"steam://connect/{local_ip}:{port}"
        
        # Tailscale Verbindungs-Strings
        if tailscale_ip:
            tailscale_connect = f"{tailscale_ip}:{port}"
            tailscale_steam = f"steam://connect/{tailscale_ip}:{port}"
        
        # Spiel-spezifische Anweisungen
        game_instructions = self.get_connection_instructions(game_name, local_ip, port, query_port)
        
        # Connection Rows
        info_grid = ctk.CTkFrame(connect_content, fg_color="transparent")
        info_grid.pack(fill="x", padx=12, pady=12)
        
        # Lokale IP Zeile
        self._create_connection_row(info_grid, "🏠 Local", connect_string)
        
        # Tailscale IP Zeile
        if tailscale_ip:
            self._create_connection_row(info_grid, "🔷 Tailscale", tailscale_connect, highlight=True)
        
        # Steam Connect Zeile (für unterstützte Spiele)
        if game_name in ["Rust", "ARK: Survival Ascended", "Valheim", "7 Days to Die", "Counter-Strike 2", "Garry's Mod", "Team Fortress 2", "Left 4 Dead 2"]:
            steam_ip_to_use = tailscale_steam if tailscale_ip else steam_connect
            self._create_connection_row(info_grid, "🎮 Steam", steam_ip_to_use)
        
        # Instructions (kompakt)
        if game_instructions:
            instr_text = game_instructions.split('\n')[0] if '\n' in game_instructions else game_instructions[:80]
            ctk.CTkLabel(
                connect_content,
                text=f"💡 {instr_text}",
                font=("Arial", 12),
                text_color="#666666"
            ).pack(anchor="w", padx=12, pady=(0, 10))
        
        # Tailscale Hinweis
        if tailscale_ip:
            hint_frame = ctk.CTkFrame(connect_card, fg_color="#1a3a1a", corner_radius=8)
            hint_frame.pack(fill="x", padx=15, pady=(0, 15))
            ctk.CTkLabel(
                hint_frame,
                text="✅ Tailscale aktiv - Kein Port-Forwarding nötig!",
                font=("Arial", 12),
                text_color="#00ff88",
                pady=8
            ).pack()
        
        # ============ END CONNECTION INFO BOX ============
        
        # Mods Section (für ARK)
        if server_config.get("game") == "ARK: Survival Ascended":
            mods_card = ctk.CTkFrame(scroll, fg_color="#1e1e2e", corner_radius=12)
            mods_card.pack(fill="x", pady=(0, 15))
            
            # Header
            mods_header = ctk.CTkFrame(mods_card, fg_color="transparent")
            mods_header.pack(fill="x", padx=15, pady=(12, 5))
            
            ctk.CTkLabel(
                mods_header,
                text="🧩 Mods",
                font=("Arial", 14, "bold")
            ).pack(side="left")
            
            mods = server_config.get("mods", [])
            ctk.CTkLabel(
                mods_header,
                text=f"{len(mods)} installed",
                font=("Arial", 12),
                text_color="#666666"
            ).pack(side="right")
            
            # Mods Content
            mods_content = ctk.CTkFrame(mods_card, fg_color="#252535", corner_radius=8)
            mods_content.pack(fill="x", padx=15, pady=(5, 10))
            
            if mods:
                for mod_id in mods:
                    mod_row = ctk.CTkFrame(mods_content, fg_color="transparent")
                    mod_row.pack(fill="x", padx=10, pady=3)
                    
                    ctk.CTkLabel(
                        mod_row,
                        text=f"📦 {mod_id}",
                        font=("Arial", 12)
                    ).pack(side="left")
                    
                    ctk.CTkButton(
                        mod_row,
                        text="✕",
                        width=24,
                        height=24,
                        font=("Arial", 12),
                        fg_color="#4a2a2a",
                        hover_color="#6a3a3a",
                        command=lambda mid=mod_id: self.remove_mod(server_id, mid)
                    ).pack(side="right")
            else:
                ctk.CTkLabel(
                    mods_content,
                    text="No mods installed",
                    text_color="#666666",
                    font=("Arial", 12),
                    pady=10
                ).pack()
            
            # Add Mod
            add_frame = ctk.CTkFrame(mods_card, fg_color="transparent")
            add_frame.pack(fill="x", padx=15, pady=(0, 12))
            
            self.mod_entry = ctk.CTkEntry(
                add_frame,
                placeholder_text="Mod ID...",
                width=150,
                height=30,
                font=("Arial", 12)
            )
            self.mod_entry.pack(side="left")
            
            ctk.CTkButton(
                add_frame,
                text="+ Add",
                width=60,
                height=30,
                font=("Arial", 12),
                fg_color="#2d5a2d",
                hover_color="#3d7a3d",
                command=lambda: self.add_mod(server_id)
            ).pack(side="left", padx=5)
        
        # ============ FOLDERS SECTION ============
        folders_card = ctk.CTkFrame(scroll, fg_color="#1e1e2e", corner_radius=12)
        folders_card.pack(fill="x", pady=(0, 15))
        
        # Header
        folders_header = ctk.CTkFrame(folders_card, fg_color="transparent")
        folders_header.pack(fill="x", padx=15, pady=(12, 10))
        
        ctk.CTkLabel(
            folders_header,
            text="📁 Folders & Files",
            font=("Arial", 14, "bold")
        ).pack(side="left")
        
        # Buttons
        folders_btns = ctk.CTkFrame(folders_card, fg_color="transparent")
        folders_btns.pack(fill="x", padx=15, pady=(0, 12))
        
        # Server-Ordner öffnen (immer verfügbar)
        ctk.CTkButton(
            folders_btns,
            text="📂 Server",
            command=lambda: self.open_server_folder(server_id),
            fg_color="#3a3a4a",
            hover_color="#4a4a5a",
            width=80,
            height=30,
            font=("Arial", 12)
        ).pack(side="left", padx=2)
        
        # Config-Ordner öffnen (wenn config_path definiert)
        config_path = game_info.get("config_path", "")
        if config_path:
            ctk.CTkButton(
                folders_btns,
                text="⚙️ Config",
                command=lambda: self.open_config_folder(server_id),
                fg_color="#3a3a4a",
                hover_color="#4a4a5a",
                width=80,
                height=30,
                font=("Arial", 12)
            ).pack(side="left", padx=2)
        
        # Save-Ordner öffnen (wenn save_path definiert)
        save_path = game_info.get("save_path", "")
        if save_path:
            ctk.CTkButton(
                folders_btns,
                text="💾 Saves",
                command=lambda: self.open_save_folder(server_id),
                fg_color="#3a3a4a",
                hover_color="#4a4a5a",
                width=80,
                height=30,
                font=("Arial", 12)
            ).pack(side="left", padx=2)
        
        # Logs-Ordner öffnen
        ctk.CTkButton(
            folders_btns,
            text="📋 Logs",
            command=lambda: self.open_logs_folder(server_id),
            fg_color="#3a3a4a",
            hover_color="#4a4a5a",
            width=70,
            height=30,
            font=("Arial", 12)
        ).pack(side="left", padx=2)
        
        # ============ END UNIVERSAL SERVER FOLDERS SECTION ============
        
        # ============ MINECRAFT FORGE SECTION ============
        if server_config.get("game") == "Minecraft Java (Forge)":
            mc_frame = ctk.CTkFrame(scroll)
            mc_frame.pack(fill="x", pady=10)
            
            # Header
            header_mc = ctk.CTkFrame(mc_frame, fg_color="transparent")
            header_mc.pack(fill="x", padx=20, pady=15)
            
            ctk.CTkLabel(
                header_mc,
                text="⛏️ Minecraft Forge Server",
                font=("Arial", 18, "bold")
            ).pack(side="left")
            
            # Version Info
            mc_version = server_config.get("mc_version", "?")
            forge_version = server_config.get("forge_version", "?")
            ram = server_config.get("ram", "4G")
            
            ctk.CTkLabel(
                header_mc,
                text=f"MC {mc_version} | Forge {forge_version} | RAM: {ram}",
                font=("Arial", 12),
                text_color="#00d4ff"
            ).pack(side="right", padx=10)
            
            # Buttons Frame
            mc_btn_frame = ctk.CTkFrame(mc_frame, fg_color="transparent")
            mc_btn_frame.pack(fill="x", padx=20, pady=5)
            
            # Mods-Ordner öffnen Button
            ctk.CTkButton(
                mc_btn_frame,
                text="📁 Mods-Ordner öffnen",
                command=lambda: self.open_minecraft_mods_folder(server_id),
                fg_color="#4CAF50",
                hover_color="#388E3C",
                width=160,
                height=35
            ).pack(side="left", padx=5)
            
            # Server Properties Editor Button
            ctk.CTkButton(
                mc_btn_frame,
                text="⚙️ Server Einstellungen",
                command=lambda: self.show_minecraft_properties_editor(server_id),
                fg_color="#2196F3",
                hover_color="#1976D2",
                width=160,
                height=35
            ).pack(side="left", padx=5)
            
            # RAM ändern Button
            ctk.CTkButton(
                mc_btn_frame,
                text="💾 RAM ändern",
                command=lambda: self.show_minecraft_ram_dialog(server_id),
                fg_color="#FF9800",
                hover_color="#F57C00",
                width=120,
                height=35
            ).pack(side="left", padx=5)
            
            # Forge Version wechseln Button
            ctk.CTkButton(
                mc_btn_frame,
                text="🔄 Version wechseln",
                command=lambda: self.show_minecraft_version_change(server_id),
                fg_color="#9C27B0",
                hover_color="#7B1FA2",
                width=140,
                height=35
            ).pack(side="left", padx=5)
            
            # Mods Liste
            mods_list_frame = ctk.CTkFrame(mc_frame)
            mods_list_frame.pack(fill="x", padx=20, pady=10)
            
            ctk.CTkLabel(
                mods_list_frame,
                text="📋 Installierte Mods:",
                font=("Arial", 14, "bold")
            ).pack(anchor="w", padx=15, pady=(10, 5))
            
            # Mods aus dem Ordner lesen
            server_dir = os.path.join(PATHS["servers"], server_id)
            mods_dir = os.path.join(server_dir, "mods")
            
            if os.path.exists(mods_dir):
                mod_files = [f for f in os.listdir(mods_dir) if f.endswith(".jar")]
                
                if mod_files:
                    # Scrollable Frame für Mods
                    mods_scroll = ctk.CTkScrollableFrame(mods_list_frame, height=150)
                    mods_scroll.pack(fill="x", padx=15, pady=5)
                    
                    for mod_file in sorted(mod_files):
                        mod_row = ctk.CTkFrame(mods_scroll, fg_color="#2a2a3e")
                        mod_row.pack(fill="x", pady=2)
                        
                        # Mod Name (ohne .jar)
                        mod_name = mod_file[:-4] if mod_file.endswith(".jar") else mod_file
                        ctk.CTkLabel(
                            mod_row,
                            text=f"🧩 {mod_name}",
                            font=("Arial", 11),
                            anchor="w"
                        ).pack(side="left", padx=10, pady=5, fill="x", expand=True)
                        
                        # Löschen Button
                        ctk.CTkButton(
                            mod_row,
                            text="🗑️",
                            width=30,
                            height=25,
                            fg_color="red",
                            hover_color="darkred",
                            command=lambda mf=mod_file: self.delete_minecraft_mod(server_id, mf)
                        ).pack(side="right", padx=5, pady=3)
                    
                    ctk.CTkLabel(
                        mods_list_frame,
                        text=f"📊 {len(mod_files)} Mod(s) installiert",
                        font=("Arial", 12),
                        text_color="gray"
                    ).pack(anchor="w", padx=15, pady=(5, 10))
                else:
                    ctk.CTkLabel(
                        mods_list_frame,
                        text="Keine Mods installiert.\nKopiere .jar Dateien in den Mods-Ordner!",
                        font=("Arial", 11),
                        text_color="gray"
                    ).pack(padx=15, pady=15)
            else:
                ctk.CTkLabel(
                    mods_list_frame,
                    text="⚠️ Mods-Ordner nicht gefunden.\nServer zuerst installieren!",
                    font=("Arial", 11),
                    text_color="orange"
                ).pack(padx=15, pady=15)
        
        # ============ END MINECRAFT FORGE SECTION ============
        
        # ============ CONAN EXILES SECTION ============
        if server_config.get("game") == "Conan Exiles":
            conan_frame = ctk.CTkFrame(scroll)
            conan_frame.pack(fill="x", pady=10)
            
            # Header
            header_conan = ctk.CTkFrame(conan_frame, fg_color="transparent")
            header_conan.pack(fill="x", padx=20, pady=15)
            
            ctk.CTkLabel(
                header_conan,
                text="⚔️ Conan Exiles Server",
                font=("Arial", 18, "bold")
            ).pack(side="left")
            
            # Buttons Frame
            conan_btn_frame = ctk.CTkFrame(conan_frame, fg_color="transparent")
            conan_btn_frame.pack(fill="x", padx=20, pady=5)
            
            # Speichern Button
            ctk.CTkButton(
                conan_btn_frame,
                text="💾 Welt speichern",
                command=lambda: self.save_conan_world(server_id),
                fg_color="#2B7A2B",
                hover_color="#236323",
                width=140,
                height=35
            ).pack(side="left", padx=5)
            
            # Mods-Ordner öffnen Button
            ctk.CTkButton(
                conan_btn_frame,
                text="📁 Mods-Ordner öffnen",
                command=lambda: self.open_conan_mods_folder(server_id),
                fg_color="#4CAF50",
                hover_color="#388E3C",
                width=160,
                height=35
            ).pack(side="left", padx=5)
            
            # Save-Ordner öffnen Button
            ctk.CTkButton(
                conan_btn_frame,
                text="📂 Savegame-Ordner",
                command=lambda: self.open_conan_save_folder(server_id),
                fg_color="#FF9800",
                hover_color="#F57C00",
                width=160,
                height=35
            ).pack(side="left", padx=5)

            ctk.CTkButton(
                conan_btn_frame,
                text="🧩 Mods jetzt syncen",
                command=lambda: self.sync_conan_mods_now(server_id),
                fg_color="#7E57C2",
                hover_color="#673AB7",
                width=170,
                height=35
            ).pack(side="left", padx=5)

            auto_mod_var = ctk.BooleanVar(value=server_config.get("conan_auto_mod_update", True))
            ctk.CTkCheckBox(
                conan_frame,
                text="Beim Start automatisch Conan Mods updaten",
                variable=auto_mod_var,
                command=lambda: self.set_conan_auto_mod_update(server_id, auto_mod_var.get())
            ).pack(anchor="w", padx=20, pady=(4, 8))

            instance_for_status = self.server_instances.get(server_id)
            if instance_for_status:
                status = instance_for_status.get_conan_mod_status()
                cfg_count = len(status.get("configured", []))
                inst_count = len(status.get("installed", []))
                miss_count = len(status.get("missing", []))
                extra_count = len(status.get("extra", []))
                ctk.CTkLabel(
                    conan_frame,
                    text=f"🧩 Konfiguriert: {cfg_count} | Installiert: {inst_count} | Fehlend: {miss_count} | Extra: {extra_count}",
                    font=("Arial", 11),
                    text_color="#7dcfff"
                ).pack(anchor="w", padx=20, pady=(2, 8))

                if status.get("configured"):
                    ctk.CTkLabel(
                        conan_frame,
                        text="Mod-Auswahl",
                        font=("Arial", 10, "bold"),
                        text_color="#c9d1ff"
                    ).pack(anchor="w", padx=20, pady=(0, 4))

                    options = [f"{m['name']}" for m in status["configured"]]
                    selected_mod_var = ctk.StringVar(value=options[0])
                    ctk.CTkOptionMenu(
                        conan_frame,
                        values=options,
                        variable=selected_mod_var,
                        width=500,
                        fg_color="#2a3554",
                        button_color="#3d4f7a",
                        button_hover_color="#51679a"
                    ).pack(anchor="w", padx=20, pady=(0, 8))

            sync_info = server_config.get("conan_mod_sync", {}) or {}
            if sync_info.get("last_run"):
                try:
                    dt = datetime.fromisoformat(sync_info["last_run"]).strftime("%d.%m.%Y %H:%M:%S")
                except Exception:
                    dt = str(sync_info.get("last_run"))
                txt = "✅" if sync_info.get("success") else "⚠️"
                ctk.CTkLabel(
                    conan_frame,
                    text=f"{txt} Letzter Mod-Sync: {dt} - {sync_info.get('message', '')}",
                    font=("Arial", 10),
                    text_color="#9fd3ff" if sync_info.get("success") else "#ffb86c",
                    wraplength=1100,
                    justify="left"
                ).pack(anchor="w", padx=20, pady=(0, 10))
            
            # Letzte Speicherung anzeigen
            server_dir = os.path.join(PATHS["servers"], server_id)
            save_file = os.path.join(server_dir, "ConanSandbox", "Saved", "game.db")
            
            if os.path.exists(save_file):
                mod_time = os.path.getmtime(save_file)
                from datetime import datetime
                last_save = datetime.fromtimestamp(mod_time).strftime("%d.%m.%Y %H:%M:%S")
                
                ctk.CTkLabel(
                    conan_frame,
                    text=f"💾 Letzte Speicherung: {last_save}",
                    font=("Arial", 11),
                    text_color="#00ff88"
                ).pack(anchor="w", padx=20, pady=(5, 15))
            else:
                ctk.CTkLabel(
                    conan_frame,
                    text="⚠️ Noch kein Savegame vorhanden",
                    font=("Arial", 11),
                    text_color="orange"
                ).pack(anchor="w", padx=20, pady=(5, 15))
        
        # ============ END CONAN EXILES SECTION ============
        
        # ============ ENSHROUDED SECTION ============
        if server_config.get("game") == "Enshrouded":
            enshrouded_frame = ctk.CTkFrame(scroll)
            enshrouded_frame.pack(fill="x", pady=10)
            
            # Header
            header_enshrouded = ctk.CTkFrame(enshrouded_frame, fg_color="transparent")
            header_enshrouded.pack(fill="x", padx=20, pady=15)
            
            ctk.CTkLabel(
                header_enshrouded,
                text="🌑 Enshrouded Server",
                font=("Arial", 18, "bold")
            ).pack(side="left")
            
            # Buttons Frame
            enshrouded_btn_frame = ctk.CTkFrame(enshrouded_frame, fg_color="transparent")
            enshrouded_btn_frame.pack(fill="x", padx=20, pady=5)
            
            # Config öffnen Button
            ctk.CTkButton(
                enshrouded_btn_frame,
                text="⚙️ Server-Config öffnen",
                command=lambda: self.open_enshrouded_config(server_id),
                fg_color="#9C27B0",
                hover_color="#7B1FA2",
                width=170,
                height=35
            ).pack(side="left", padx=5)
            
            # Savegame-Ordner öffnen Button
            ctk.CTkButton(
                enshrouded_btn_frame,
                text="📂 Savegame-Ordner",
                command=lambda: self.open_enshrouded_save_folder(server_id),
                fg_color="#FF9800",
                hover_color="#F57C00",
                width=160,
                height=35
            ).pack(side="left", padx=5)
            
            # Logs-Ordner öffnen Button
            ctk.CTkButton(
                enshrouded_btn_frame,
                text="📋 Logs-Ordner",
                command=lambda: self.open_enshrouded_logs_folder(server_id),
                fg_color="#607D8B",
                hover_color="#455A64",
                width=130,
                height=35
            ).pack(side="left", padx=5)
            
            # Server-Info anzeigen
            server_dir = os.path.join(PATHS["servers"], server_id)
            config_file = os.path.join(server_dir, "enshrouded_server.json")
            
            if os.path.exists(config_file):
                try:
                    import json
                    with open(config_file, 'r', encoding='utf-8') as f:
                        ens_config = json.load(f)
                    
                    info_frame = ctk.CTkFrame(enshrouded_frame, fg_color="transparent")
                    info_frame.pack(fill="x", padx=20, pady=(5, 15))
                    
                    server_name = ens_config.get("name", "Enshrouded Server")
                    slot_count = ens_config.get("slotCount", 16)
                    preset = ens_config.get("gameSettingsPreset", "Default")
                    
                    ctk.CTkLabel(
                        info_frame,
                        text=f"📛 Name: {server_name}  |  👥 Slots: {slot_count}  |  🎮 Preset: {preset}",
                        font=("Arial", 11),
                        text_color="#00ff88"
                    ).pack(anchor="w")
                except:
                    pass
            else:
                ctk.CTkLabel(
                    enshrouded_frame,
                    text="⚠️ Config-Datei nicht gefunden. Server zuerst starten!",
                    font=("Arial", 11),
                    text_color="orange"
                ).pack(anchor="w", padx=20, pady=(5, 15))
        
        # ============ END ENSHROUDED SECTION ============
        
        # Log Section - Farbige Console
        log_frame = ctk.CTkFrame(scroll, fg_color="#1a1a2e")
        log_frame.pack(fill="x", pady=10)
        
        # Log Header
        log_header = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            log_header,
            text="📋 Console",
            font=("Arial", 18, "bold"),
            text_color="#00d4ff"
        ).pack(side="left")
        
        # Live Indicator
        if instance.is_running():
            live_badge = ctk.CTkFrame(log_header, fg_color="#2d5a2d", corner_radius=8)
            live_badge.pack(side="left", padx=10)
            ctk.CTkLabel(
                live_badge,
                text="● LIVE",
                font=("Arial", 9, "bold"),
                text_color="#00ff88",
                padx=8,
                pady=2
            ).pack()
        
        # Clear Button
        ctk.CTkButton(
            log_header,
            text="🗑️ Clear",
            width=70,
            height=28,
            font=("Arial", 12),
            fg_color="#4a4a5a",
            hover_color="#5a5a6a",
            command=lambda: self.clear_server_logs(server_id)
        ).pack(side="right")
        
        # Log Textbox mit dunklem Hintergrund
        self.server_log_text = ctk.CTkTextbox(
            log_frame,
            height=250,
            font=("Consolas", 11),
            fg_color="#0d0d15",
            text_color="#cccccc",
            corner_radius=8
        )
        self.server_log_text.pack(fill="x", padx=20, pady=(0, 20))
        
        # Farbige Logs anzeigen
        for log in instance.log_messages[-30:]:
            self.insert_colored_log(log)
        self.server_log_text.see("end")
    
    def insert_colored_log(self, log_text):
        """Fügt eine Log-Zeile mit Farbcodierung ein"""
        if not hasattr(self, 'server_log_text'):
            return
        
        # Zeitstempel in Grau
        timestamp_color = "#666666"
        
        # Farbe basierend auf Log-Inhalt bestimmen
        text_color = "#cccccc"  # Standard Grau
        
        log_lower = log_text.lower()
        
        # Fehler - Rot
        if any(x in log_lower for x in ["error", "fehler", "❌", "failed", "exception", "critical"]):
            text_color = "#ff4444"
        # Warnung - Orange
        elif any(x in log_lower for x in ["warning", "warnung", "⚠️", "warn"]):
            text_color = "#ffaa00"
        # Erfolg - Grün
        elif any(x in log_lower for x in ["success", "erfolg", "✅", "started", "gestartet", "online", "running", "🟢"]):
            text_color = "#00ff88"
        # Info - Cyan
        elif any(x in log_lower for x in ["info", "ℹ️", "📋", "installing", "downloading", "updating"]):
            text_color = "#00d4ff"
        # Stoppen - Orange
        elif any(x in log_lower for x in ["stop", "shutdown", "beendet", "offline", "🔴"]):
            text_color = "#ff8844"
        
        # Text einfügen
        self.server_log_text.insert("end", log_text + "\n")
        
        # Leider unterstützt CTkTextbox keine Tag-Konfiguration direkt
        # Aber wir haben den dunklen Hintergrund und hellen Text als Basis
    
    def clear_server_logs(self, server_id):
        """Löscht die Server-Logs"""
        instance = self.server_instances.get(server_id)
        if instance:
            instance.log_messages.clear()
            if hasattr(self, 'server_log_text'):
                self.server_log_text.delete("1.0", "end")
                self.server_log_text.insert("end", "📋 Logs gelöscht\n")
    
    def _create_action_btn(self, parent, icon, text, bg_color, hover_color, command, small=False, width=None):
        """Erstellt einen modernen Action Button"""
        btn_width = width if width else (70 if small else 85)
        btn_height = 30 if small else 34
        font_size = 10 if small else 11
        
        btn_text = f"{icon} {text}" if text else icon
        
        btn = ctk.CTkButton(
            parent,
            text=btn_text,
            font=("Arial", font_size),
            width=btn_width,
            height=btn_height,
            fg_color=bg_color,
            hover_color=hover_color,
            corner_radius=6,
            command=command
        )
        btn.pack(side="left", padx=2)
        return btn
    
    def _create_stat_card(self, parent, col, icon, title, value):
        """Erstellt eine kompakte Stat Card"""
        card = ctk.CTkFrame(parent, fg_color="#252535", corner_radius=8)
        card.grid(row=0, column=col, padx=4, pady=4, sticky="nsew")
        
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(padx=15, pady=12)
        
        # Icon
        ctk.CTkLabel(
            content,
            text=icon,
            font=("Arial", 22)
        ).pack()
        
        # Value
        ctk.CTkLabel(
            content,
            text=str(value),
            font=("Arial", 16, "bold"),
            text_color="#00d4ff"
        ).pack()
        
        # Title
        ctk.CTkLabel(
            content,
            text=title,
            font=("Arial", 12),
            text_color="#888888"
        ).pack()
    
    def _create_connection_row(self, parent, label, value, highlight=False):
        """Erstellt eine Connection Info Zeile"""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=4)
        
        # Label
        ctk.CTkLabel(
            row,
            text=label,
            font=("Arial", 13),
            text_color="#aaaaaa",
            width=100,
            anchor="w"
        ).pack(side="left")
        
        # Value Entry
        entry = ctk.CTkEntry(
            row,
            width=200,
            height=34,
            font=("Arial", 13),
            fg_color="#1a1a2a",
            border_color="#3a3a4a" if not highlight else "#00d4ff"
        )
        entry.insert(0, value)
        entry.configure(state="readonly")
        entry.pack(side="left", padx=5)
        
        # Copy Button
        ctk.CTkButton(
            row,
            text="📋",
            width=38,
            height=34,
            font=("Arial", 12),
            fg_color="#3a3a4a",
            hover_color="#4a4a5a",
            command=lambda v=value: self.copy_to_clipboard(v)
        ).pack(side="left", padx=2)
        
        # Highlight Badge
        if highlight:
            ctk.CTkLabel(
                row,
                text="✓",
                font=("Arial", 12),
                text_color="#00ff88"
            ).pack(side="left", padx=5)
    
    def create_info_card(self, parent, col, title, value, icon):
        """Erstellt eine Info-Card"""
        card = ctk.CTkFrame(parent)
        card.grid(row=0, column=col, padx=5, pady=5, sticky="nsew")
        
        ctk.CTkLabel(
            card,
            text=icon,
            font=("Arial", 32)
        ).pack(pady=(15, 5))
        
        ctk.CTkLabel(
            card,
            text=value,
            font=("Arial", 20, "bold"),
            text_color="#00d4ff"
        ).pack()
        
        ctk.CTkLabel(
            card,
            text=title,
            font=("Arial", 12),
            text_color="gray"
        ).pack(pady=(5, 15))
    
    def get_local_ip(self):
        """Ermittelt die lokale IP-Adresse"""
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def get_tailscale_ip(self):
        """Ermittelt die Tailscale IP-Adresse (falls vorhanden)"""
        try:
            import socket
            # Alle Netzwerk-Interfaces durchsuchen
            hostname = socket.gethostname()
            all_ips = socket.getaddrinfo(hostname, None, socket.AF_INET)
            
            for item in all_ips:
                ip = item[4][0]
                # Tailscale IPs sind im 100.x.x.x Bereich (CGNAT)
                if ip.startswith("100."):
                    return ip
            
            # Alternative: Direkt über Interface-Namen
            if os.name == 'nt':
                import subprocess
                result = subprocess.run(
                    ["tailscale", "ip", "-4"],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                if result.returncode == 0:
                    return result.stdout.strip()
        except:
            pass
        
        return None
    
    def copy_to_clipboard(self, text):
        """Kopiert Text in die Zwischenablage"""
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()
    
    def get_connection_instructions(self, game_name, ip, port, query_port):
        """Gibt spiel-spezifische Verbindungs-Anleitung zurück"""
        instructions = {
            "ARK: Survival Ascended": f"""1. Starte ARK: Survival Ascended
2. Klicke auf "Server beitreten"
3. Wähle "Inoffiziell" und suche nach deinem Server
   ODER: Drücke F3 → Konsole → Tippe: open {ip}:{port}""",
            
            "Rust": f"""1. Starte Rust
2. Drücke F1 für die Konsole
3. Tippe: client.connect {ip}:{port}
   ODER: Im Serverbrowser nach dem Namen suchen""",
            
            "Valheim": f"""1. Starte Valheim
2. Klicke auf "Spiel beitreten"
3. Klicke auf "Mit IP verbinden"
4. Gib ein: {ip}:{port}""",
            
            "Palworld": f"""1. Starte Palworld
2. Wähle "Multiplayer beitreten"
3. Gib die Server-IP ein: {ip}:{port}""",
            
            "Enshrouded": f"""1. Steam öffnen → Ansicht → Spielserver
2. Tab "Favoriten" → Server hinzufügen
3. IP eingeben: {ip}:{query_port}
4. Server erscheint in Enshrouded unter "Spiel beitreten\"""",
            
            "Satisfactory": f"""1. Starte Satisfactory
2. Wähle "Server-Manager"
3. Füge Server hinzu: {ip}:{port}""",
            
            "7 Days to Die": f"""1. Starte 7 Days to Die
2. Wähle "Mit Server verbinden"
3. Gib IP ein: {ip} und Port: {port}""",
            
            "Project Zomboid": f"""1. Starte Project Zomboid
2. Wähle "Online spielen"
3. Gib Server-IP ein: {ip}:{port}""",
            
            "Terraria": f"""1. Starte Terraria
2. Wähle "Multiplayer" → "Mit IP verbinden"
3. Gib ein: {ip} und Port: {port}""",
            
            "Counter-Strike 2": f"""1. Starte Counter-Strike 2
2. Öffne Konsole (~)
3. Tippe: connect {ip}:{port}""",
            
            "Don't Starve Together": f"""1. Starte Don't Starve Together
2. Wähle "Durchsuchen" bei Spielen
3. Suche nach deinem Server oder verbinde via Konsole""",
            
            "V Rising": f"""1. Starte V Rising
2. Wähle "Online spielen"
3. Gib Server-IP ein: {ip}:{port}""",
            
            "Conan Exiles": f"""1. Starte Conan Exiles
2. Wähle "Online spielen" → "Direkte Verbindung"
3. Gib ein: {ip}:{port}
4. WICHTIG: Server braucht 3 Ports offen: {port}, {port+1}, {query_port}""",
            
            "DayZ": f"""1. Starte DayZ
2. Gehe zu "Server" → "Remote"
3. Gib ein: {ip} und Port: {port}""",
            
            "The Forest": f"""1. Starte The Forest
2. Wähle "Multiplayer" → "Server beitreten"
3. Suche nach dem Server oder gib IP ein""",
            
            "Space Engineers": f"""1. Starte Space Engineers
2. Wähle "Server beitreten"
3. Gib Server-IP ein: {ip}:{port}""",
            
            "Unturned": f"""1. Starte Unturned
2. Wähle "Play" → "Connect"
3. Gib ein: {ip}:{port}""",
            
            "Left 4 Dead 2": f"""1. Starte Left 4 Dead 2
2. Öffne Konsole (~)
3. Tippe: connect {ip}:{port}""",
            
            "Team Fortress 2": f"""1. Starte Team Fortress 2
2. Öffne Konsole (~)
3. Tippe: connect {ip}:{port}""",
            
            "Factorio": f"""1. Starte Factorio
2. Wähle "Multiplayer" → "Mit Adresse verbinden"
3. Gib ein: {ip}:{port}""",
            
            "Garry's Mod": f"""1. Starte Garry's Mod
2. Öffne Konsole (~)
3. Tippe: connect {ip}:{port}""",
            
            "Minecraft Bedrock": f"""1. Starte Minecraft Bedrock
2. Wähle "Spielen" → "Server"
3. Füge Server hinzu: {ip} Port: {port}""",
            
            "Icarus": f"""1. Starte Icarus
2. Wähle "Multiplayer" → "Server beitreten"
3. Klicke auf "Server hinzufügen"
4. Gib IP ein: {ip} und Port: {port}""",
            "StarRupture": f"""1. Starte StarRupture
2. Wähle "Multiplayer" → "Join Game"
3. Wähle "Dedicated Server"
4. Gib ein: {ip}:{port}
5. Optional: Server-Passwort eingeben""",
            "Minecraft Java (Forge)": f"""1. Starte Minecraft mit Forge Profil (gleiche Version!)
2. Wähle "Multiplayer" → "Server hinzufügen"
3. Server-Adresse eingeben:
   • Lokal (selber PC): localhost
   • LAN (gleiches Netzwerk): {ip}
4. Port ist standardmäßig 25565 (nur angeben wenn anders)
5. WICHTIG: Client braucht exakt gleiche Mods wie Server!"""
        }
        
        return instructions.get(game_name, f"Verbinde mit: {ip}:{port}")
    
    def check_port_conflict(self, server_id):
        """Prüft ob Ports bereits von anderen Servern verwendet werden"""
        server_config = self.config_manager.servers.get(server_id, {})
        my_port = server_config.get("port", 0)
        my_query_port = server_config.get("query_port", 0)
        
        conflicts = []
        
        for other_id, other_instance in self.server_instances.items():
            if other_id == server_id:
                continue
            
            if not other_instance.is_running():
                continue
            
            other_config = self.config_manager.servers.get(other_id, {})
            other_port = other_config.get("port", 0)
            other_query = other_config.get("query_port", 0)
            other_name = other_config.get("name", other_id)
            
            if my_port and my_port == other_port:
                conflicts.append(f"Port {my_port} wird bereits von '{other_name}' verwendet!")
            if my_query_port and my_query_port == other_query:
                conflicts.append(f"Query-Port {my_query_port} wird bereits von '{other_name}' verwendet!")
        
        return conflicts
    
    def start_server(self, server_id):
        """Startet einen Server"""
        instance = self.server_instances.get(server_id)
        if instance:
            # Port-Konflikt prüfen
            conflicts = self.check_port_conflict(server_id)
            if conflicts:
                server_config = self.config_manager.servers.get(server_id, {})
                result = messagebox.askyesno(
                    "⚠️ Port-Konflikt!",
                    f"Server '{server_config.get('name', server_id)}' hat Port-Konflikte:\n\n" +
                    "\n".join(conflicts) + 
                    "\n\n⚠️ Der Server wird wahrscheinlich nicht richtig funktionieren!\n\n"
                    "Trotzdem starten?"
                )
                if not result:
                    return
            
            threading.Thread(target=instance.start, daemon=True).start()
            # Nach 2 Sekunden UI aktualisieren (Sidebar + Details)
            self.after(2000, lambda: self._update_after_status_change(server_id))
    
    def stop_server(self, server_id):
        """Stoppt einen Server"""
        instance = self.server_instances.get(server_id)
        if instance:
            threading.Thread(target=instance.stop, daemon=True).start()
            # Nach 2 Sekunden UI aktualisieren (Sidebar + Details)
            self.after(2000, lambda: self._update_after_status_change(server_id))
    
    def restart_server(self, server_id):
        """Startet einen Server neu"""
        instance = self.server_instances.get(server_id)
        if instance:
            threading.Thread(target=instance.restart, daemon=True).start()
            # Nach 5 Sekunden UI aktualisieren (Sidebar + Details)
            self.after(5000, lambda: self._update_after_status_change(server_id))
    
    def _update_after_status_change(self, server_id):
        """Aktualisiert UI nach Server-Status-Änderung"""
        self.refresh_server_list()  # Sidebar aktualisieren (Zahlen + Farben)
        self.select_server(server_id)  # Server-Details aktualisieren
    
    # ==================== SERVER BEARBEITEN ====================
    def show_edit_server_dialog(self, server_id):
        """Zeigt den Dialog zum Server bearbeiten"""
        t = self.config_manager.get_text
        server_config = self.config_manager.servers.get(server_id, {})
        
        if not server_config:
            return
        
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"✏️ Server bearbeiten - {server_config.get('name', 'Server')}")
        dialog.geometry("550x700")
        dialog.transient(self)
        dialog.grab_set()
        
        # Zentrieren
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 550) // 2
        y = (dialog.winfo_screenheight() - 700) // 2
        dialog.geometry(f"550x700+{x}+{y}")
        
        # Scrollable Content
        scroll = ctk.CTkScrollableFrame(dialog)
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header
        ctk.CTkLabel(
            scroll,
            text=f"✏️ Server bearbeiten",
            font=("Arial", 20, "bold")
        ).pack(pady=(0, 20))
        
        # === ALLGEMEIN ===
        ctk.CTkLabel(scroll, text="📋 Allgemein", font=("Arial", 14, "bold")).pack(anchor="w", pady=(10, 5))
        
        general_frame = ctk.CTkFrame(scroll)
        general_frame.pack(fill="x", pady=5)
        
        # Server-Name
        ctk.CTkLabel(general_frame, text="Server-Name:").pack(anchor="w", padx=15, pady=(10, 0))
        name_entry = ctk.CTkEntry(general_frame, width=400)
        name_entry.pack(padx=15, pady=5)
        name_entry.insert(0, server_config.get("name", ""))
        
        # Max Players
        ctk.CTkLabel(general_frame, text="Max. Spieler:").pack(anchor="w", padx=15, pady=(10, 0))
        players_entry = ctk.CTkEntry(general_frame, width=100)
        players_entry.pack(anchor="w", padx=15, pady=5)
        players_entry.insert(0, str(server_config.get("max_players", 70)))
        
        # === PORTS ===
        ctk.CTkLabel(scroll, text="🔌 Ports", font=("Arial", 14, "bold")).pack(anchor="w", pady=(20, 5))
        
        ports_frame = ctk.CTkFrame(scroll)
        ports_frame.pack(fill="x", pady=5)
        
        ports_inner = ctk.CTkFrame(ports_frame, fg_color="transparent")
        ports_inner.pack(fill="x", padx=15, pady=10)
        
        # Game Port
        ctk.CTkLabel(ports_inner, text="Game Port:").pack(side="left")
        port_entry = ctk.CTkEntry(ports_inner, width=80)
        port_entry.pack(side="left", padx=(5, 20))
        port_entry.insert(0, str(server_config.get("port", 7777)))
        
        # Query Port
        ctk.CTkLabel(ports_inner, text="Query Port:").pack(side="left")
        query_entry = ctk.CTkEntry(ports_inner, width=80)
        query_entry.pack(side="left", padx=5)
        query_entry.insert(0, str(server_config.get("query_port", 27015)))
        
        # === PASSWÖRTER ===
        ctk.CTkLabel(scroll, text="🔐 Passwörter", font=("Arial", 14, "bold")).pack(anchor="w", pady=(20, 5))
        
        pass_frame = ctk.CTkFrame(scroll)
        pass_frame.pack(fill="x", pady=5)
        
        # Server Passwort
        ctk.CTkLabel(pass_frame, text="Server Passwort (leer = kein Passwort):").pack(anchor="w", padx=15, pady=(10, 0))
        server_pass_entry = ctk.CTkEntry(pass_frame, width=300)
        server_pass_entry.pack(anchor="w", padx=15, pady=5)
        server_pass_entry.insert(0, server_config.get("server_password", ""))
        
        # Admin Passwort
        ctk.CTkLabel(pass_frame, text="Admin Passwort:").pack(anchor="w", padx=15, pady=(10, 0))
        admin_pass_entry = ctk.CTkEntry(pass_frame, width=300)
        admin_pass_entry.pack(anchor="w", padx=15, pady=(5, 10))
        admin_pass_entry.insert(0, server_config.get("admin_password", "admin"))
        
        # === BACKUP ===
        ctk.CTkLabel(scroll, text="💾 Backup-Einstellungen", font=("Arial", 14, "bold")).pack(anchor="w", pady=(20, 5))
        
        backup_frame = ctk.CTkFrame(scroll)
        backup_frame.pack(fill="x", pady=5)
        
        # Auto-Backup Checkbox
        auto_backup_var = ctk.BooleanVar(value=server_config.get("auto_backup", False))
        ctk.CTkCheckBox(
            backup_frame,
            text="Auto-Backup aktivieren",
            variable=auto_backup_var
        ).pack(anchor="w", padx=15, pady=10)
        
        # Backup-Intervall
        interval_frame = ctk.CTkFrame(backup_frame, fg_color="transparent")
        interval_frame.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(interval_frame, text="Intervall:").pack(side="left")
        
        interval_values = {
            "Jede Stunde": 1,
            "Alle 3 Stunden": 3,
            "Alle 6 Stunden": 6,
            "Alle 12 Stunden": 12,
            "Täglich": 24
        }
        
        # Aktuellen Wert finden
        current_hours = server_config.get("backup_interval_hours", 3)
        current_text = "Alle 3 Stunden"
        for text, hours in interval_values.items():
            if hours == current_hours:
                current_text = text
                break
        
        interval_var = ctk.StringVar(value=current_text)
        interval_menu = ctk.CTkOptionMenu(
            interval_frame,
            variable=interval_var,
            values=list(interval_values.keys()),
            width=150
        )
        interval_menu.pack(side="left", padx=10)
        
        # Max Backups
        ctk.CTkLabel(interval_frame, text="Max Backups:").pack(side="left", padx=(20, 0))
        max_backups_entry = ctk.CTkEntry(interval_frame, width=60)
        max_backups_entry.pack(side="left", padx=5)
        max_backups_entry.insert(0, str(server_config.get("max_backups", 5)))
        
        # === CLUSTER (nur für ARK) ===
        if "ARK" in server_config.get("game", ""):
            ctk.CTkLabel(scroll, text="🔗 Cluster", font=("Arial", 14, "bold")).pack(anchor="w", pady=(20, 5))
            
            cluster_frame = ctk.CTkFrame(scroll)
            cluster_frame.pack(fill="x", pady=5)
            
            clusters = self.config_manager.app_config.get("clusters", {})
            cluster_options = ["Kein Cluster"] + [c.get("name", cid) for cid, c in clusters.items()]
            
            current_cluster = server_config.get("cluster", "")
            current_cluster_name = "Kein Cluster"
            if current_cluster and current_cluster in clusters:
                current_cluster_name = clusters[current_cluster].get("name", current_cluster)
            
            cluster_var = ctk.StringVar(value=current_cluster_name)
            
            ctk.CTkLabel(cluster_frame, text="Cluster:").pack(anchor="w", padx=15, pady=(10, 0))
            cluster_menu = ctk.CTkOptionMenu(
                cluster_frame,
                variable=cluster_var,
                values=cluster_options,
                width=250
            )
            cluster_menu.pack(anchor="w", padx=15, pady=(5, 10))
        else:
            cluster_var = None
            clusters = {}
        
        # === BUTTONS ===
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=15)
        
        def save_changes():
            # Werte validieren
            try:
                new_port = int(port_entry.get().strip())
                new_query = int(query_entry.get().strip())
                new_players = int(players_entry.get().strip())
                new_max_backups = int(max_backups_entry.get().strip())
            except ValueError:
                messagebox.showerror("Fehler", "Ports, Spieler und Max Backups müssen Zahlen sein!")
                return
            
            # Prüfen ob Server läuft
            instance = self.server_instances.get(server_id)
            if instance and instance.is_running():
                if not messagebox.askyesno(
                    "Server läuft",
                    "Der Server läuft noch. Änderungen werden erst nach Neustart wirksam.\n\nTrotzdem speichern?"
                ):
                    return
            
            # Werte speichern
            self.config_manager.servers[server_id]["name"] = name_entry.get().strip()
            self.config_manager.servers[server_id]["port"] = new_port
            self.config_manager.servers[server_id]["query_port"] = new_query
            self.config_manager.servers[server_id]["max_players"] = new_players
            self.config_manager.servers[server_id]["server_password"] = server_pass_entry.get().strip()
            self.config_manager.servers[server_id]["admin_password"] = admin_pass_entry.get().strip()
            self.config_manager.servers[server_id]["auto_backup"] = auto_backup_var.get()
            self.config_manager.servers[server_id]["backup_interval_hours"] = interval_values.get(interval_var.get(), 3)
            self.config_manager.servers[server_id]["max_backups"] = new_max_backups
            
            # Cluster (für ARK)
            if cluster_var:
                selected_cluster_name = cluster_var.get()
                if selected_cluster_name == "Kein Cluster":
                    # Aus altem Cluster entfernen
                    old_cluster = self.config_manager.servers[server_id].get("cluster", "")
                    if old_cluster and old_cluster in clusters:
                        servers_in_cluster = self.config_manager.app_config["clusters"][old_cluster].get("servers", [])
                        if server_id in servers_in_cluster:
                            servers_in_cluster.remove(server_id)
                    self.config_manager.servers[server_id]["cluster"] = ""
                else:
                    # Cluster-ID finden
                    new_cluster_id = ""
                    for cid, cinfo in clusters.items():
                        if cinfo.get("name", cid) == selected_cluster_name:
                            new_cluster_id = cid
                            break
                    
                    if new_cluster_id:
                        # Aus altem Cluster entfernen
                        old_cluster = self.config_manager.servers[server_id].get("cluster", "")
                        if old_cluster and old_cluster in clusters and old_cluster != new_cluster_id:
                            servers_in_cluster = self.config_manager.app_config["clusters"][old_cluster].get("servers", [])
                            if server_id in servers_in_cluster:
                                servers_in_cluster.remove(server_id)
                        
                        # Zu neuem Cluster hinzufügen
                        self.config_manager.servers[server_id]["cluster"] = new_cluster_id
                        if "servers" not in self.config_manager.app_config["clusters"][new_cluster_id]:
                            self.config_manager.app_config["clusters"][new_cluster_id]["servers"] = []
                        if server_id not in self.config_manager.app_config["clusters"][new_cluster_id]["servers"]:
                            self.config_manager.app_config["clusters"][new_cluster_id]["servers"].append(server_id)
                        
                        self.config_manager.save_app_config()
            
            self.config_manager.save_servers()
            
            # Server-Instance Config aktualisieren
            if instance:
                instance.config = self.config_manager.servers[server_id]
            
            dialog.destroy()
            
            # UI aktualisieren
            self.refresh_server_list()
            self.show_server_details(server_id)
            
            messagebox.showinfo("Gespeichert", "Änderungen wurden gespeichert!")
        
        ctk.CTkButton(
            btn_frame,
            text="💾 Speichern",
            command=save_changes,
            fg_color="green",
            hover_color="darkgreen",
            width=120
        ).pack(side="right")
        
        ctk.CTkButton(
            btn_frame,
            text="Abbrechen",
            command=dialog.destroy,
            fg_color="gray",
            width=100
        ).pack(side="left")

    # ==================== SERVER KLONEN ====================
    def show_clone_dialog(self, server_id):
        """Zeigt den Dialog zum Server klonen"""
        t = self.config_manager.get_text
        server_config = self.config_manager.servers.get(server_id, {})
        
        if not server_config:
            return
        
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"📋 {t('clone_server_title')}")
        dialog.geometry("500x400")
        dialog.transient(self)
        dialog.grab_set()
        
        # Zentrieren
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 500) // 2
        y = (dialog.winfo_screenheight() - 400) // 2
        dialog.geometry(f"500x400+{x}+{y}")
        
        # Header
        ctk.CTkLabel(
            dialog,
            text=f"📋 {t('clone_server_title')}",
            font=("Arial", 20, "bold")
        ).pack(pady=20)
        
        ctk.CTkLabel(
            dialog,
            text=f"Original: {server_config.get('name', 'Server')}",
            font=("Arial", 12),
            text_color="gray"
        ).pack(pady=(0, 20))
        
        # Formular
        form_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        form_frame.pack(fill="x", padx=40)
        
        # Neuer Name
        ctk.CTkLabel(form_frame, text=f"{t('clone_new_name')}:", anchor="w").pack(fill="x", pady=(10, 5))
        name_entry = ctk.CTkEntry(form_frame, width=350)
        name_entry.pack(fill="x")
        name_entry.insert(0, f"{server_config.get('name', 'Server')} (Kopie)")
        
        # Optionen
        options_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        options_frame.pack(fill="x", padx=40, pady=20)
        
        include_files_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            options_frame,
            text=t("clone_include_files"),
            variable=include_files_var
        ).pack(anchor="w", pady=5)
        
        include_saves_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            options_frame,
            text=t("clone_include_saves"),
            variable=include_saves_var
        ).pack(anchor="w", pady=5)
        
        # Hinweis
        ctk.CTkLabel(
            dialog,
            text="⚠️ Server-Dateien kopieren kann lange dauern (mehrere GB)",
            font=("Arial", 12),
            text_color="orange"
        ).pack(pady=10)
        
        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=40, pady=20)
        
        def do_clone():
            new_name = name_entry.get().strip()
            if not new_name:
                messagebox.showerror(t("error"), "Bitte Namen eingeben!")
                return
            
            dialog.destroy()
            self._clone_server(server_id, new_name, include_files_var.get(), include_saves_var.get())
        
        ctk.CTkButton(
            btn_frame,
            text=f"📋 {t('clone_server')}",
            command=do_clone,
            width=150,
            fg_color="green"
        ).pack(side="right")
        
        ctk.CTkButton(
            btn_frame,
            text=t("cancel"),
            command=dialog.destroy,
            width=100,
            fg_color="gray"
        ).pack(side="left")
    
    def _clone_server(self, source_id, new_name, include_files, include_saves):
        """Klont einen Server"""
        t = self.config_manager.get_text
        
        def do_clone():
            try:
                source_config = self.config_manager.servers.get(source_id, {}).copy()
                
                # Neue ID generieren
                new_id = new_name.lower().replace(" ", "_")
                new_id = re.sub(r'[^a-z0-9_]', '', new_id)
                
                # ID einzigartig machen
                if new_id in self.config_manager.servers:
                    counter = 1
                    while f"{new_id}_{counter}" in self.config_manager.servers:
                        counter += 1
                    new_id = f"{new_id}_{counter}"
                
                # Neue Config erstellen
                new_config = source_config.copy()
                new_config["name"] = new_name
                new_config["installed"] = False
                new_config["created_at"] = datetime.now().isoformat()
                
                # Ports anpassen (um Konflikte zu vermeiden)
                new_config["port"] = source_config.get("port", 7777) + 10
                new_config["query_port"] = source_config.get("query_port", 27015) + 10
                
                # Server hinzufügen
                self.config_manager.add_server(new_id, new_config)
                
                # Dateien kopieren wenn gewünscht
                if include_files or include_saves:
                    source_dir = os.path.join(PATHS["servers"], source_id)
                    target_dir = os.path.join(PATHS["servers"], new_id)
                    
                    if os.path.exists(source_dir):
                        if include_files:
                            # Komplettes Verzeichnis kopieren
                            shutil.copytree(source_dir, target_dir)
                            new_config["installed"] = True
                            self.config_manager.servers[new_id] = new_config
                            self.config_manager.save_servers()
                        elif include_saves:
                            # Nur Saves kopieren
                            game_info = SUPPORTED_GAMES.get(source_config.get("game", ""), {})
                            save_path = game_info.get("save_path", "")
                            if save_path:
                                source_save = os.path.join(source_dir, save_path.replace("/", os.sep))
                                target_save = os.path.join(target_dir, save_path.replace("/", os.sep))
                                if os.path.exists(source_save):
                                    os.makedirs(os.path.dirname(target_save), exist_ok=True)
                                    shutil.copytree(source_save, target_save)
                
                # UI aktualisieren
                self.after(0, lambda: self._finish_clone(new_id, new_config))
                
            except Exception as e:
                self.after(0, lambda: messagebox.showerror(t("error"), f"{t('clone_failed')}: {str(e)}"))
        
        # In Thread ausführen
        threading.Thread(target=do_clone, daemon=True).start()
        messagebox.showinfo(t("info"), t("clone_in_progress"))
    
    def _finish_clone(self, new_id, new_config):
        """Beendet den Klon-Vorgang"""
        t = self.config_manager.get_text
        
        # Server-Instanz erstellen
        self.server_instances[new_id] = ServerInstance(new_id, new_config, self.config_manager, self.discord_notifier)
        
        # UI aktualisieren
        self.refresh_server_list()
        self.select_server(new_id)
        
        messagebox.showinfo(t("success"), t("clone_success"))
    
    # ==================== CONFIG EDITOR ====================
    def show_config_editor(self, server_id):
        """Zeigt den Config-Editor für einen Server"""
        t = self.config_manager.get_text
        server_config = self.config_manager.servers.get(server_id, {})
        
        if not server_config:
            return
        
        # Config-Dateien finden
        server_dir = os.path.join(PATHS["servers"], server_id)
        game_info = SUPPORTED_GAMES.get(server_config.get("game", ""), {})
        config_path = game_info.get("config_path", "")
        
        config_files = []
        
        # Im Config-Pfad suchen
        if config_path:
            full_config_path = os.path.join(server_dir, config_path.replace("/", os.sep))
            if os.path.exists(full_config_path):
                for root, dirs, files in os.walk(full_config_path):
                    for file in files:
                        if file.endswith(('.ini', '.cfg', '.txt', '.json', '.yaml', '.yml', '.conf', '.properties')):
                            config_files.append(os.path.join(root, file))
        
        # Auch im Hauptverzeichnis suchen
        if os.path.exists(server_dir):
            for file in os.listdir(server_dir):
                full_path = os.path.join(server_dir, file)
                if os.path.isfile(full_path) and file.endswith(('.ini', '.cfg', '.txt', '.json', '.yaml', '.yml', '.conf', '.properties')):
                    if full_path not in config_files:
                        config_files.append(full_path)
        
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"📝 {t('config_editor_title')} - {server_config.get('name', 'Server')}")
        dialog.geometry("900x700")
        dialog.transient(self)
        
        # Zentrieren
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 900) // 2
        y = (dialog.winfo_screenheight() - 700) // 2
        dialog.geometry(f"900x700+{x}+{y}")
        
        # Header
        header = ctk.CTkFrame(dialog)
        header.pack(fill="x", padx=15, pady=15)
        
        ctk.CTkLabel(
            header,
            text=f"📝 {t('config_editor_title')}",
            font=("Arial", 18, "bold")
        ).pack(side="left")
        
        if not config_files:
            ctk.CTkLabel(
                dialog,
                text=f"📭 {t('config_no_files')}",
                font=("Arial", 14),
                text_color="gray"
            ).pack(pady=50)
            
            ctk.CTkButton(
                dialog,
                text=t("cancel"),
                command=dialog.destroy,
                width=100,
                fg_color="gray"
            ).pack(pady=20)
            return
        
        # Datei-Auswahl
        file_frame = ctk.CTkFrame(header, fg_color="transparent")
        file_frame.pack(side="right")
        
        # Dateinamen kürzen für Dropdown
        file_names = []
        for f in config_files:
            rel_path = os.path.relpath(f, server_dir)
            file_names.append(rel_path)
        
        current_file_var = ctk.StringVar(value=file_names[0] if file_names else "")
        
        ctk.CTkLabel(file_frame, text=f"{t('config_select_file')}:").pack(side="left", padx=5)
        file_menu = ctk.CTkOptionMenu(
            file_frame,
            variable=current_file_var,
            values=file_names,
            width=300,
            command=lambda x: load_file()
        )
        file_menu.pack(side="left")
        
        # Editor
        editor_frame = ctk.CTkFrame(dialog)
        editor_frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        
        editor = ctk.CTkTextbox(editor_frame, font=("Consolas", 12), wrap="none")
        editor.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Status
        status_label = ctk.CTkLabel(dialog, text="", font=("Arial", 12))
        status_label.pack(pady=5)
        
        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=10)
        
        current_file_path = [None]  # Mutable container
        
        def load_file():
            """Lädt die ausgewählte Datei"""
            rel_path = current_file_var.get()
            file_path = os.path.join(server_dir, rel_path)
            current_file_path[0] = file_path
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                
                editor.delete("1.0", "end")
                editor.insert("1.0", content)
                status_label.configure(text=f"📂 {rel_path}", text_color="gray")
                
            except Exception as e:
                status_label.configure(text=f"❌ Fehler: {str(e)}", text_color="red")
        
        def save_file():
            """Speichert die aktuelle Datei"""
            if not current_file_path[0]:
                return
            
            try:
                content = editor.get("1.0", "end-1c")
                with open(current_file_path[0], 'w', encoding='utf-8') as f:
                    f.write(content)
                
                status_label.configure(text=f"✅ {t('config_saved')}", text_color="green")
                
            except Exception as e:
                status_label.configure(text=f"❌ {t('config_save_failed')}: {str(e)}", text_color="red")
        
        def reload_file():
            """Lädt die Datei neu"""
            load_file()
        
        ctk.CTkButton(
            btn_frame,
            text=f"💾 {t('config_save')}",
            command=save_file,
            width=120,
            fg_color="green"
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text=f"🔄 {t('config_reload')}",
            command=reload_file,
            width=120
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text=t("cancel"),
            command=dialog.destroy,
            width=100,
            fg_color="gray"
        ).pack(side="right", padx=5)
        
        # Initial laden
        load_file()
    
    # ==================== AUTOSTART FUNKTIONEN ====================
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
            font=("Arial", 20, "bold")
        ).pack(pady=20)
        
        # Export Bereich
        export_frame = ctk.CTkFrame(dialog)
        export_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            export_frame,
            text=f"📤 {t('export_config')}",
            font=("Arial", 14, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(
            export_frame,
            text=t("select_servers_export"),
            font=("Arial", 11),
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
            font=("Arial", 14, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(
            import_frame,
            text="JSON-Datei mit Server-Konfigurationen importieren",
            font=("Arial", 11),
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
            font=("Arial", 20, "bold")
        ).pack(pady=(10, 20))
        
        # === ALLGEMEIN ===
        general_frame = ctk.CTkFrame(scroll_frame)
        general_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            general_frame,
            text="📋 Allgemein",
            font=("Arial", 14, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        # Web-Port
        port_row = ctk.CTkFrame(general_frame, fg_color="transparent")
        port_row.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(port_row, text=f"🌐 {t('web_port')}:", width=150, anchor="w").pack(side="left")
        current_port = self.config_manager.app_config.get("web", {}).get("port", 5001)
        port_entry = ctk.CTkEntry(port_row, width=80)
        port_entry.pack(side="left", padx=5)
        port_entry.insert(0, str(current_port))
        ctk.CTkLabel(port_row, text=t("web_port_hint"), text_color="gray", font=("Arial", 12)).pack(side="left", padx=10)
        
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
            font=("Arial", 14, "bold")
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
            font=("Arial", 12),
            text_color="gray",
            justify="left"
        ).pack(anchor="w", padx=20, pady=(0, 10))
        
        # === IMPORT / EXPORT ===
        ie_frame = ctk.CTkFrame(scroll_frame)
        ie_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            ie_frame,
            text=f"📦 {t('import_export')}",
            font=("Arial", 14, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(
            ie_frame,
            text="Server-Konfigurationen exportieren oder importieren",
            font=("Arial", 12),
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
            font=("Arial", 11),
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
            font=("Arial", 22, "bold")
        ).pack(pady=(0, 20))
        
        # Aktiviert
        enabled_var = ctk.BooleanVar(value=discord_config.get("enabled", False))
        ctk.CTkCheckBox(
            scroll,
            text=t("discord_notifications"),
            variable=enabled_var,
            font=("Arial", 14)
        ).pack(anchor="w", padx=20, pady=10)
        
        # Webhook URL
        form_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        form_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(form_frame, text=f"{t('discord_webhook_url')}:", font=("Arial", 14), anchor="w").pack(fill="x", pady=(10, 5))
        webhook_entry = ctk.CTkEntry(form_frame, height=40, font=("Arial", 13))
        webhook_entry.pack(fill="x")
        webhook_entry.insert(0, discord_config.get("webhook_url", ""))
        
        ctk.CTkLabel(
            form_frame,
            text=t("discord_webhook_hint"),
            font=("Arial", 12),
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
            font=("Arial", 13)
        ).pack(anchor="w", pady=10)
        
        # Benachrichtigungs-Optionen
        ctk.CTkLabel(
            scroll,
            text="Benachrichtigen bei:",
            font=("Arial", 15, "bold")
        ).pack(anchor="w", padx=20, pady=(20, 10))
        
        options_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        options_frame.pack(fill="x", padx=20)
        
        notify_start_var = ctk.BooleanVar(value=discord_config.get("notify_start", True))
        ctk.CTkCheckBox(options_frame, text=t("discord_notify_start"), variable=notify_start_var, font=("Arial", 13)).pack(anchor="w", pady=5)
        
        notify_stop_var = ctk.BooleanVar(value=discord_config.get("notify_stop", True))
        ctk.CTkCheckBox(options_frame, text=t("discord_notify_stop"), variable=notify_stop_var, font=("Arial", 13)).pack(anchor="w", pady=5)
        
        notify_crash_var = ctk.BooleanVar(value=discord_config.get("notify_crash", True))
        ctk.CTkCheckBox(options_frame, text=t("discord_notify_crash"), variable=notify_crash_var, font=("Arial", 13)).pack(anchor="w", pady=5)
        
        notify_backup_var = ctk.BooleanVar(value=discord_config.get("notify_backup", True))
        ctk.CTkCheckBox(options_frame, text=t("discord_notify_backup"), variable=notify_backup_var, font=("Arial", 13)).pack(anchor="w", pady=5)
        
        notify_update_var = ctk.BooleanVar(value=discord_config.get("notify_update", True))
        ctk.CTkCheckBox(options_frame, text=t("discord_notify_update"), variable=notify_update_var, font=("Arial", 13)).pack(anchor="w", pady=5)
        
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
            font=("Arial", 14),
            fg_color="green"
        ).pack(side="right")
        
        ctk.CTkButton(
            btn_frame,
            text=t("cancel"),
            command=dialog.destroy,
            width=120,
            height=40,
            font=("Arial", 14),
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
            font=("Arial", 20, "bold")
        ).pack(pady=20)
        
        # Info-Box
        info_frame = ctk.CTkFrame(dialog, fg_color="#1e3a5f")
        info_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            info_frame,
            text="💡 Ein Cluster verbindet mehrere ARK-Server.\n"
                 "Spieler können Charakter, Dinos und Items zwischen Maps transferieren.",
            font=("Arial", 11),
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
            font=("Arial", 14, "bold")
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
            font=("Arial", 14, "bold")
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
                    frame = ctk.CTkFrame(cluster_list_frame, fg_color="#2a2a3e")
                    frame.pack(fill="x", pady=3)
                    
                    # Cluster-Name
                    name_btn = ctk.CTkButton(
                        frame,
                        text=f"🔗 {cluster_info.get('name', cluster_id)}",
                        fg_color="transparent",
                        hover_color="#3a3a4e",
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
                frame = ctk.CTkFrame(server_list_frame, fg_color="#2a2a3e")
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
                    font=("Arial", 12, "bold"),
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
                        font=("Arial", 12)
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
                font=("Arial", 16, "bold")
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

    def show_rcon_dashboard(self, server_id):
        """Öffnet das RCON Dashboard mit Karte"""
        server_config = self.config_manager.servers.get(server_id, {})
        instance = self.server_instances.get(server_id)
        
        if not instance:
            return
        
        # Dialog erstellen
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"📊 Dashboard - {server_config.get('name', 'Server')}")
        dialog.geometry("1200x800")
        dialog.transient(self)
        
        # Zentrieren
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 1200) // 2
        y = (dialog.winfo_screenheight() - 800) // 2
        dialog.geometry(f"1200x800+{x}+{y}")
        
        # RCON Settings
        rcon_port = server_config.get("rcon_port", 27020)
        rcon_password = server_config.get("admin_password", server_config.get("rcon_password", ""))
        
        # Map aus Server-Config extrahieren
        current_map = "TheIsland_WP"  # Default
        
        # Aus Config
        if server_config.get("map") and server_config.get("map") in ARK_MAP_DATA:
            current_map = server_config.get("map")
        
        # Aus Start-Params
        start_params = server_config.get("start_params", "")
        for map_param in ARK_MAP_DATA.keys():
            if map_param in start_params:
                current_map = map_param
                break
        
        # Aus SavedArks Ordner
        server_dir = instance.get_server_dir()
        game_info = SUPPORTED_GAMES.get(server_config.get("game", ""), {})
        save_path = os.path.join(server_dir, game_info.get("save_path", ""))
        
        if os.path.exists(save_path):
            for item in os.listdir(save_path):
                item_path = os.path.join(save_path, item)
                if os.path.isdir(item_path):
                    for map_param in ARK_MAP_DATA.keys():
                        clean_param = map_param.replace("_WP", "")
                        if clean_param.lower() in item.lower():
                            current_map = map_param
                            break
        
        # RCON Client
        rcon_client = RCONClient(host="127.0.0.1", port=rcon_port, password=rcon_password)
        
        # Map Manager
        map_manager = ArkMapManager(PATHS.get("base", "."))
        
        # Save Parser
        save_parser = ArkSaveParser(save_path)
        
        # Status-Variablen
        rcon_connected = ctk.BooleanVar(value=False)
        online_players = []
        map_image = None
        map_photo = None
        save_data = {"players": [], "tamed_dinos": [], "tribes": []}
        canvas_size = [800, 600]
        show_players = ctk.BooleanVar(value=True)
        show_dinos = ctk.BooleanVar(value=True)
        show_offline = ctk.BooleanVar(value=True)
        pw_visible = ctk.BooleanVar(value=False)
        
        # Layout: Links = Karte, Rechts = Controls
        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Linke Seite: Karte
        left_frame = ctk.CTkFrame(main_frame, fg_color="#1a1a2e")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # Map Header
        map_header = ctk.CTkFrame(left_frame, fg_color="#252545")
        map_header.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(map_header, text=f"🗺️ {ARK_MAP_DATA.get(current_map, {}).get('name', current_map)}",
            font=("Arial", 16, "bold")).pack(side="left", padx=10, pady=5)
        
        map_status_label = ctk.CTkLabel(map_header, text="", font=("Arial", 11))
        map_status_label.pack(side="right", padx=10)
        
        # Filter
        filter_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        filter_frame.pack(fill="x", padx=5)
        
        ctk.CTkCheckBox(filter_frame, text="👤 Spieler", variable=show_players,
            height=25, checkbox_height=18, checkbox_width=18
        ).pack(side="left", padx=10, pady=5)
        
        ctk.CTkCheckBox(filter_frame, text="🦖 Dinos", variable=show_dinos,
            height=25, checkbox_height=18, checkbox_width=18
        ).pack(side="left", padx=10, pady=5)
        
        ctk.CTkCheckBox(filter_frame, text="👻 Offline", variable=show_offline,
            height=25, checkbox_height=18, checkbox_width=18
        ).pack(side="left", padx=10, pady=5)
        
        # Buttons (rechts in filter_frame)
        def import_map_image():
            """Importiert ein Map-Bild manuell"""
            file_path = filedialog.askopenfilename(
                title=f"Map-Bild für {ARK_MAP_DATA.get(current_map, {}).get('name', current_map)} auswählen",
                filetypes=[("Bilder", "*.jpg *.jpeg *.png *.webp"), ("Alle Dateien", "*.*")]
            )
            if file_path:
                success, msg = map_manager.import_map_manually(current_map, file_path)
                if success:
                    messagebox.showinfo("Erfolg", f"Map-Bild importiert!")
                    load_map()
                else:
                    messagebox.showerror("Fehler", f"Import fehlgeschlagen:\n{msg}")
        
        def show_debug_info():
            """Zeigt Debug-Infos an"""
            found_save = save_parser.find_save_file(current_map)
            info = f"""📂 Save-Pfad: {save_parser.save_dir}
📁 Existiert: {os.path.exists(save_parser.save_dir)}
🗺️ Map: {current_map} ({ARK_MAP_DATA.get(current_map, {}).get('name', '?')})
💾 Save-Datei: {found_save if found_save else 'Nicht gefunden'}
🖼️ PIL: {PIL_AVAILABLE}
📍 Map gecacht: {map_manager.is_cached(current_map)}

👥 Geladene Spieler: {len(save_data.get('players', []))}"""
            
            for p in save_data.get('players', [])[:5]:
                info += f"\n   • {p.get('name', '?')} (Lvl {p.get('level', '?')})"
            
            messagebox.showinfo("Debug Info", info)
        
        ctk.CTkButton(filter_frame, text="📥", width=30, height=25, 
            command=import_map_image, fg_color="#555555"
        ).pack(side="right", padx=2, pady=5)
        
        ctk.CTkButton(filter_frame, text="ℹ️", width=30, height=25, 
            command=show_debug_info, fg_color="gray"
        ).pack(side="right", padx=2, pady=5)
        
        def update_save_data():
            nonlocal save_data
            map_status_label.configure(text="⏳ Lade...")
            data = save_parser.get_all_data(current_map, force_refresh=True,
                progress_callback=lambda s: dialog.after(0, lambda: map_status_label.configure(text=s)))
            save_data = data
            
            # Status aktualisieren
            save_info = data.get("save_info")
            if save_info:
                save_time = save_info.get("last_save", datetime.now()).strftime("%H:%M:%S")
                status = f"✓ {ARK_MAP_DATA.get(current_map, {}).get('name', '?')} | Save: {save_time} | {len(data['players'])} Spieler"
            else:
                status = f"⚠️ Keine Save-Daten"
            
            dialog.after(0, lambda: map_status_label.configure(text=status))
            dialog.after(0, update_map_markers)
        
        ctk.CTkButton(filter_frame, text="🔄 Save laden", width=100, height=25,
            command=lambda: threading.Thread(target=update_save_data, daemon=True).start()
        ).pack(side="right", padx=5, pady=5)
        
        # Karten-Canvas
        canvas_frame = ctk.CTkFrame(left_frame, fg_color="#0a0a15")
        canvas_frame.pack(fill="both", expand=True)
        
        map_canvas = tk.Canvas(canvas_frame, bg="#0a0a15", highlightthickness=0)
        map_canvas.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Rechte Seite: Controls
        right_frame = ctk.CTkFrame(main_frame, fg_color="#1a1a2e", width=300)
        right_frame.pack(side="right", fill="y", padx=(5, 0))
        right_frame.pack_propagate(False)
        
        # RCON Verbindung
        rcon_frame = ctk.CTkFrame(right_frame)
        rcon_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(rcon_frame, text="📡 RCON Verbindung", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=5)
        
        rcon_status = ctk.CTkLabel(rcon_frame, text="⚠️ RCON muss in GameUserSettings.ini aktiviert sein!",
            text_color="orange", font=("Arial", 12))
        rcon_status.pack(anchor="w", padx=10)
        
        # Port
        port_frame = ctk.CTkFrame(rcon_frame, fg_color="transparent")
        port_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(port_frame, text="RCON Port:", width=80).pack(side="left")
        port_entry = ctk.CTkEntry(port_frame, width=80)
        port_entry.insert(0, str(rcon_port))
        port_entry.pack(side="left", padx=5)
        
        # Password mit Toggle
        pw_frame = ctk.CTkFrame(rcon_frame, fg_color="transparent")
        pw_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(pw_frame, text="RCON Passwort:", width=80).pack(side="left")
        
        pw_entry = ctk.CTkEntry(pw_frame, width=120, show="*")
        pw_entry.insert(0, rcon_password)
        pw_entry.pack(side="left", padx=5)
        
        def toggle_pw_visibility():
            if pw_visible.get():
                pw_entry.configure(show="")
                pw_toggle_btn.configure(text="🙈")
            else:
                pw_entry.configure(show="*")
                pw_toggle_btn.configure(text="👁")
            pw_visible.set(not pw_visible.get())
        
        pw_toggle_btn = ctk.CTkButton(pw_frame, text="👁", width=30, height=28, command=toggle_pw_visibility)
        pw_toggle_btn.pack(side="left", padx=2)
        
        # Connect/Disconnect Buttons
        btn_frame_rcon = ctk.CTkFrame(rcon_frame, fg_color="transparent")
        btn_frame_rcon.pack(fill="x", padx=10, pady=10)
        
        def connect_rcon():
            nonlocal online_players
            try:
                port = int(port_entry.get())
                password = pw_entry.get()
            except:
                messagebox.showerror("Fehler", "Ungültiger Port")
                return
            
            rcon_client.port = port
            rcon_client.password = password
            
            players, error = rcon_client.list_players()
            if error:
                rcon_status.configure(text=f"❌ {error}", text_color="red")
                rcon_connected.set(False)
            else:
                rcon_connected.set(True)
                online_players = players
                rcon_status.configure(text=f"✓ RCON Verbunden ✓", text_color="green")
                update_player_list()
                update_map_markers()
                start_rcon_polling()
        
        def disconnect_rcon():
            nonlocal online_players
            rcon_connected.set(False)
            online_players = []
            rcon_status.configure(text="⚪ Getrennt", text_color="gray")
            update_player_list()
            update_map_markers()
        
        ctk.CTkButton(btn_frame_rcon, text="🔗 Verbinden", command=connect_rcon,
            fg_color="green", hover_color="darkgreen", width=100).pack(side="left", padx=5)
        
        ctk.CTkButton(btn_frame_rcon, text="⛔ Trennen", command=disconnect_rcon,
            fg_color="red", hover_color="darkred", width=100).pack(side="left", padx=5)
        
        # Online Spieler Liste
        players_frame = ctk.CTkFrame(right_frame)
        players_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(players_frame, text="👥 Online Spieler", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=5)
        
        player_list_frame = ctk.CTkScrollableFrame(players_frame, height=150)
        player_list_frame.pack(fill="x", padx=5, pady=5)
        
        def update_player_list():
            for widget in player_list_frame.winfo_children():
                widget.destroy()
            
            if online_players:
                for player in online_players:
                    name = player.get("name", "?")
                    pf = ctk.CTkFrame(player_list_frame, fg_color="#2a2a4a")
                    pf.pack(fill="x", pady=2)
                    ctk.CTkLabel(pf, text=f"🟢 {name}", font=("Arial", 11)).pack(side="left", padx=10, pady=5)
            else:
                ctk.CTkLabel(player_list_frame, text="Keine Spieler online", text_color="gray").pack(pady=10)
        
        update_player_list()
        
        # Quick Actions
        actions_frame = ctk.CTkFrame(right_frame)
        actions_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(actions_frame, text="⚡ Quick Actions", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=5)
        
        actions_grid = ctk.CTkFrame(actions_frame, fg_color="transparent")
        actions_grid.pack(fill="x", padx=10, pady=5)
        
        def send_broadcast():
            msg = broadcast_entry.get()
            if msg and rcon_connected.get():
                response, err = rcon_client.broadcast(msg)
                if not err:
                    broadcast_entry.delete(0, "end")
                    add_to_chat(f"[SERVER] {msg}")
        
        def save_world():
            if rcon_connected.get():
                rcon_client.save_world()
                add_to_chat("[SYSTEM] Welt gespeichert!")
        
        def destroy_wild_dinos():
            if rcon_connected.get() and messagebox.askyesno("Bestätigung", "Alle wilden Dinos löschen?"):
                rcon_client.destroy_wild_dinos()
                add_to_chat("[SYSTEM] Wilde Dinos gelöscht!")
        
        broadcast_frame = ctk.CTkFrame(actions_grid, fg_color="transparent")
        broadcast_frame.pack(fill="x", pady=2)
        
        broadcast_entry = ctk.CTkEntry(broadcast_frame, placeholder_text="Nachricht...", width=180)
        broadcast_entry.pack(side="left", padx=(0, 5))
        
        ctk.CTkButton(broadcast_frame, text="📢", command=send_broadcast, width=40, fg_color="#4CAF50").pack(side="left")
        
        btn_row = ctk.CTkFrame(actions_grid, fg_color="transparent")
        btn_row.pack(fill="x", pady=5)
        
        ctk.CTkButton(btn_row, text="💾 Save", command=save_world, width=70, height=30, fg_color="#2196F3").pack(side="left", padx=2)
        ctk.CTkButton(btn_row, text="🦖 Dino Wipe", command=destroy_wild_dinos, width=90, height=30, fg_color="#FF9800").pack(side="left", padx=2)
        
        # RCON Konsole
        console_frame = ctk.CTkFrame(right_frame)
        console_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        ctk.CTkLabel(console_frame, text="💻 RCON Konsole", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=5)
        
        console_output = ctk.CTkTextbox(console_frame, height=120, font=("Consolas", 10))
        console_output.pack(fill="both", expand=True, padx=5, pady=5)
        console_output.configure(state="disabled")
        
        def add_to_chat(msg):
            console_output.configure(state="normal")
            timestamp = datetime.now().strftime("%H:%M:%S")
            console_output.insert("end", f"[{timestamp}] {msg}\n")
            console_output.see("end")
            console_output.configure(state="disabled")
        
        cmd_frame = ctk.CTkFrame(console_frame, fg_color="transparent")
        cmd_frame.pack(fill="x", padx=5, pady=5)
        
        cmd_entry = ctk.CTkEntry(cmd_frame, placeholder_text="RCON Befehl...", width=220)
        cmd_entry.pack(side="left", padx=(0, 5))
        
        def send_command():
            cmd = cmd_entry.get()
            if cmd and rcon_connected.get():
                add_to_chat(f"> {cmd}")
                response, err = rcon_client.send_command(cmd)
                if err:
                    add_to_chat(f"[ERROR] {err}")
                elif response:
                    add_to_chat(response)
                cmd_entry.delete(0, "end")
        
        ctk.CTkButton(cmd_frame, text="Senden", command=send_command, width=70).pack(side="left")
        cmd_entry.bind("<Return>", lambda e: send_command())
        
        # Funktionen
        def update_map_markers():
            map_canvas.delete("marker")
            canvas_size[0] = max(map_canvas.winfo_width(), 600)
            canvas_size[1] = max(map_canvas.winfo_height(), 500)
            
            online_names = [p.get("name", "").lower() for p in online_players]
            
            # Online-Spieler Liste anzeigen
            y_offset = 20
            if online_players:
                map_canvas.create_text(15, y_offset, text=f"👥 Online ({len(online_players)}):", fill="#00ff88",
                    font=("Arial", 12, "bold"), tags="marker", anchor="nw")
                y_offset += 22
                
                for player in online_players[:10]:
                    name = player.get("name", "?")
                    # Level aus save_data
                    level = 1
                    for p in save_data.get("players", []):
                        if p.get("name", "").lower() == name.lower():
                            level = p.get("level", 1)
                            break
                    
                    label = f"  🟢 {name}" + (f" (Lvl {level})" if level > 1 else "")
                    map_canvas.create_text(15, y_offset, text=label, fill="#00ff88",
                        font=("Arial", 12), tags="marker", anchor="nw")
                    y_offset += 18
            else:
                map_canvas.create_text(15, y_offset, text="👥 Keine Spieler online", fill="#666666",
                    font=("Arial", 11), tags="marker", anchor="nw")
                y_offset += 22
            
            # Offline-Spieler (wenn aktiviert)
            if show_offline.get() and save_data.get("players"):
                offline_players = [p for p in save_data["players"] 
                                   if p.get("name", "").lower() not in online_names 
                                   and p.get("name", "") != "Unknown"]
                
                if offline_players:
                    y_offset += 10
                    map_canvas.create_text(15, y_offset, text=f"👻 Offline ({len(offline_players)}):", fill="#888888",
                        font=("Arial", 11, "bold"), tags="marker", anchor="nw")
                    y_offset += 20
                    
                    for player in offline_players[:5]:
                        name = player.get("name", "?")
                        level = player.get("level", 1)
                        label = f"  ⚫ {name}" + (f" (Lvl {level})" if level > 1 else "")
                        map_canvas.create_text(15, y_offset, text=label, fill="#666666",
                            font=("Arial", 12), tags="marker", anchor="nw")
                        y_offset += 16
            
            # Hinweis
            map_canvas.create_text(15, canvas_size[1] - 15, 
                text="ℹ️ Positionen nicht verfügbar (ARK ASA Limit)", fill="#444444",
                font=("Arial", 12), tags="marker", anchor="nw")
        
        def draw_fallback_map(w, h, error_msg=""):
            """Zeichnet Fallback-Map wenn kein Bild verfügbar"""
            map_canvas.delete("all")
            
            # Dunkler Hintergrund
            map_canvas.create_rectangle(0, 0, w, h, fill="#0a0a15", outline="")
            
            # Grid
            grid_color = "#1a1a2a"
            for i in range(0, w, 50):
                map_canvas.create_line(i, 0, i, h, fill=grid_color)
            for i in range(0, h, 50):
                map_canvas.create_line(0, i, w, i, fill=grid_color)
            
            # Info-Text
            map_canvas.create_text(w//2, h//2 - 20, text=f"🗺️ {ARK_MAP_DATA.get(current_map, {}).get('name', current_map)}",
                fill="#555555", font=("Arial", 16, "bold"))
            
            if error_msg:
                map_canvas.create_text(w//2, h//2 + 10, text=error_msg, fill="#ff6666", font=("Arial", 12))
            
            map_canvas.create_text(w//2, h//2 + 40, text="Klicke 📥 um ein Map-Bild zu importieren",
                fill="#444444", font=("Arial", 12))
        
        def load_map():
            nonlocal map_image, map_photo
            map_status_label.configure(text="⏳ Lade Karte...")
            
            def do_load():
                nonlocal map_image, map_photo
                try:
                    success, msg = map_manager.ensure_map(current_map, 
                        lambda s: dialog.after(0, lambda: map_status_label.configure(text=s)))
                    
                    if success:
                        dialog.update_idletasks()
                        canvas_w = max(map_canvas.winfo_width(), 600)
                        canvas_h = max(map_canvas.winfo_height(), 500)
                        
                        if PIL_AVAILABLE:
                            map_image = map_manager.get_map_image(current_map, (canvas_w, canvas_h))
                            
                            if map_image:
                                map_photo = ImageTk.PhotoImage(map_image)
                                def update_canvas():
                                    map_canvas.delete("all")
                                    map_canvas.create_image(canvas_w//2, canvas_h//2, image=map_photo, anchor="center")
                                    map_status_label.configure(text=f"✓ {ARK_MAP_DATA[current_map]['name']}", text_color="green")
                                    update_map_markers()
                                dialog.after(0, update_canvas)
                            else:
                                dialog.after(0, lambda: draw_fallback_map(canvas_w, canvas_h, "Bild konnte nicht geladen werden"))
                        else:
                            dialog.after(0, lambda: draw_fallback_map(canvas_w, canvas_h, "PIL nicht installiert"))
                    else:
                        canvas_w = max(map_canvas.winfo_width(), 600)
                        canvas_h = max(map_canvas.winfo_height(), 500)
                        dialog.after(0, lambda: draw_fallback_map(canvas_w, canvas_h, f"Download fehlgeschlagen: {msg}"))
                        dialog.after(0, lambda: map_status_label.configure(
                            text=f"⚠️ {ARK_MAP_DATA.get(current_map, {}).get('name', '?')} | 📥 = Import"))
                except Exception as e:
                    dialog.after(0, lambda: map_status_label.configure(text=f"❌ Fehler: {e}"))
            
            threading.Thread(target=do_load, daemon=True).start()
        
        def start_rcon_polling():
            def poll():
                nonlocal online_players
                while rcon_connected.get() and dialog.winfo_exists():
                    try:
                        players, error = rcon_client.list_players()
                        if not error:
                            online_players = players
                            dialog.after(0, update_player_list)
                            dialog.after(0, update_map_markers)
                    except:
                        pass
                    time.sleep(30)
            
            threading.Thread(target=poll, daemon=True).start()
        
        # Initial: Karte laden + Spieler laden
        dialog.after(500, load_map)
        dialog.after(1000, lambda: threading.Thread(target=update_save_data, daemon=True).start())

    def show_log_viewer(self, server_id):
        """Öffnet den Log-Viewer für einen Server"""
        t = self.config_manager.get_text
        instance = self.server_instances.get(server_id)
        server_config = self.config_manager.servers.get(server_id, {})
        
        if not instance:
            return
        
        # Dialog erstellen
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"📜 {t('server_logs')} - {server_config.get('name', 'Server')}")
        dialog.geometry("900x600")
        dialog.transient(self)
        
        # Zentrieren
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 900) // 2
        y = (dialog.winfo_screenheight() - 600) // 2
        dialog.geometry(f"900x600+{x}+{y}")
        
        # Toolbar
        toolbar = ctk.CTkFrame(dialog, height=50)
        toolbar.pack(fill="x", padx=10, pady=10)
        toolbar.pack_propagate(False)
        
        # Suche
        ctk.CTkLabel(toolbar, text=f"🔍 {t('search')}:").pack(side="left", padx=(10, 5))
        search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(toolbar, textvariable=search_var, width=200)
        search_entry.pack(side="left", padx=5)
        
        # Filter
        filter_var = ctk.StringVar(value="all")
        ctk.CTkLabel(toolbar, text="Filter:").pack(side="left", padx=(20, 5))
        filter_menu = ctk.CTkOptionMenu(
            toolbar,
            variable=filter_var,
            values=[t("log_level_all"), t("log_level_errors"), t("log_level_warnings")],
            width=120
        )
        filter_menu.pack(side="left", padx=5)
        
        # Auto-Scroll Checkbox
        auto_scroll_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(toolbar, text=t("auto_scroll"), variable=auto_scroll_var).pack(side="left", padx=20)
        
        # Log-Textbox
        log_frame = ctk.CTkFrame(dialog)
        log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        log_text = ctk.CTkTextbox(log_frame, font=("Consolas", 11), wrap="none")
        log_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        def update_logs():
            """Aktualisiert die Log-Anzeige"""
            # Filter-Wert umwandeln
            filter_val = filter_var.get()
            if filter_val == t("log_level_errors"):
                level = "errors"
            elif filter_val == t("log_level_warnings"):
                level = "warnings"
            else:
                level = "all"
            
            logs = instance.get_server_logs(
                max_lines=500,
                search_filter=search_var.get(),
                level_filter=level
            )
            
            log_text.configure(state="normal")
            log_text.delete("1.0", "end")
            
            for log in logs:
                # Farbcodierung
                if any(x in log.lower() for x in ["error", "fail", "exception", "❌", "critical"]):
                    log_text.insert("end", log + "\n")  # Rot wäre besser, aber CTkTextbox unterstützt das nicht einfach
                elif any(x in log.lower() for x in ["warn", "⚠️", "warning"]):
                    log_text.insert("end", log + "\n")
                else:
                    log_text.insert("end", log + "\n")
            
            log_text.configure(state="disabled")
            
            if auto_scroll_var.get():
                log_text.see("end")
        
        # Initial laden
        update_logs()
        
        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(
            btn_frame,
            text=f"🔄 {t('refresh')}",
            command=update_logs,
            width=120
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text=f"🗑️ {t('clear')}",
            command=lambda: instance.log_messages.clear() or update_logs(),
            width=120,
            fg_color="gray"
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text=t("cancel"),
            command=dialog.destroy,
            width=100,
            fg_color="gray"
        ).pack(side="right", padx=5)
        
        # Auto-Update alle 3 Sekunden
        def auto_update():
            if dialog.winfo_exists():
                update_logs()
                dialog.after(3000, auto_update)
        
        dialog.after(3000, auto_update)
        
        # Such-Binding
        search_entry.bind("<Return>", lambda e: update_logs())
        search_entry.bind("<KeyRelease>", lambda e: dialog.after(300, update_logs))
        filter_var.trace("w", lambda *args: update_logs())
    
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
            font=("Arial", 18, "bold")
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
            font=("Arial", 18, "bold")
        ).pack(pady=(15, 5))
        
        # Status Label
        status_label = ctk.CTkLabel(dialog, text="Starte Update...", font=("Arial", 12))
        status_label.pack(pady=5)
        
        # Progress Bar
        progress = ctk.CTkProgressBar(dialog, width=550)
        progress.pack(pady=10)
        progress.set(0)
        
        # Prozent-Label
        percent_label = ctk.CTkLabel(dialog, text="0%", font=("Arial", 14, "bold"))
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
                    self.after(0, lambda: add_output(f"⚠️ Cache-Löschung fehlgeschlagen: {e}"))
            
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
            font=("Arial", 20, "bold")
        ).pack(pady=20)
        
        ctk.CTkLabel(
            dialog,
            text=f"{server_config['game']} benötigt einen Steam-Account\nfür die Installation.",
            font=("Arial", 12),
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
            font=("Arial", 12),
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
        """Führt die eigentliche Server-Installation durch"""
        def do_install():
            try:
                instance = self.server_instances.get(server_id)
                if instance:
                    instance.log(f"📥 Installiere {server_config['game']}...")
                
                server_dir = os.path.join(PATHS["servers"], server_id)
                os.makedirs(server_dir, exist_ok=True)
                
                # SteamCMD Befehl als Liste (shell=False für Sicherheit)
                cmd_list = [steamcmd_exe, "+force_install_dir", server_dir]
                if username == "anonymous":
                    cmd_list.extend(["+login", "anonymous"])
                else:
                    cmd_list.extend(["+login", username, password])
                cmd_list.extend(["+app_update", str(app_id), "validate", "+quit"])
                
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
                    self.after(0, lambda: self.select_server(server_id))
                else:
                    if instance:
                        instance.log(f"❌ Installation fehlgeschlagen! (Exit Code: {process.returncode})")
                
            except Exception as e:
                if instance:
                    instance.log(f"❌ Fehler: {str(e)}")
        
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
                self.after(0, lambda: messagebox.showerror("Fehler", str(e)))
        
        threading.Thread(target=do_install, daemon=True).start()
    
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
    
    def delete_server(self, server_id):
        """Löscht einen Server"""
        t = self.config_manager.get_text
        
        if not messagebox.askyesno(t("warning"), t("confirm_delete")):
            return
        
        # Server stoppen falls läuft
        instance = self.server_instances.get(server_id)
        if instance and instance.is_running():
            instance.stop()
        
        # Aus Config entfernen
        self.config_manager.remove_server(server_id)
        
        # Instanz entfernen
        if server_id in self.server_instances:
            del self.server_instances[server_id]
        
        # UI aktualisieren
        self.refresh_server_list()
        
        if self.config_manager.servers:
            first_server = list(self.config_manager.servers.keys())[0]
            self.select_server(first_server)
        else:
            self.show_no_servers_message()
    
    def add_mod(self, server_id):
        """Fügt eine Mod hinzu"""
        mod_id = self.mod_entry.get().strip()
        if not mod_id:
            return
        
        server_config = self.config_manager.servers.get(server_id)
        if server_config:
            if "mods" not in server_config:
                server_config["mods"] = []
            
            if mod_id not in server_config["mods"]:
                server_config["mods"].append(mod_id)
                if "mod_names" not in server_config or not isinstance(server_config.get("mod_names"), dict):
                    server_config["mod_names"] = {}
                fetched = fetch_workshop_mod_names([mod_id])
                if fetched.get(mod_id):
                    server_config["mod_names"][mod_id] = fetched[mod_id]
                self.config_manager.save_servers()
                
                instance = self.server_instances.get(server_id)
                if instance:
                    instance.config = server_config
                    instance.log(f"🧩 Mod {mod_id} hinzugefügt")
                
                self.mod_entry.delete(0, "end")
                self.select_server(server_id)
    
    def remove_mod(self, server_id, mod_id):
        """Entfernt eine Mod"""
        server_config = self.config_manager.servers.get(server_id)
        if server_config and "mods" in server_config:
            if mod_id in server_config["mods"]:
                server_config["mods"].remove(mod_id)
                if isinstance(server_config.get("mod_names"), dict) and mod_id in server_config["mod_names"]:
                    del server_config["mod_names"][mod_id]
                self.config_manager.save_servers()
                
                instance = self.server_instances.get(server_id)
                if instance:
                    instance.config = server_config
                    instance.log(f"🗑️ Mod {mod_id} entfernt")
                
                self.select_server(server_id)
    
    def open_web_interface(self):
        """Öffnet das Web-Interface im Browser"""
        import webbrowser
        port = self.config_manager.app_config.get("web", {}).get("port", 5001)
        webbrowser.open(f"http://localhost:{port}")
    
    def start_services(self):
        """Startet Hintergrund-Services"""
        # Laufzeit für Chat/Stream initialisieren
        self.init_chat_runtime()

        # Web-Server starten
        self.start_web_server()
        
        # Server-Instanzen für existierende Server erstellen
        for server_id, server_config in self.config_manager.servers.items():
            if server_id not in self.server_instances:
                self.server_instances[server_id] = ServerInstance(server_id, server_config, self.config_manager, self.discord_notifier)
        
        # Autostart für Server wenn aktiviert
        if self.config_manager.app_config.get("autostart_servers", False):
            autostart_list = self.config_manager.app_config.get("autostart_server_list", [])
            if autostart_list:
                print(f"🚀 Autostart: {len(autostart_list)} Server werden gestartet...")
                self.after(2000, lambda: self.autostart_servers(autostart_list))
    
    def autostart_servers(self, server_ids):
        """Startet Server aus der Autostart-Liste"""
        for server_id in server_ids:
            if server_id in self.server_instances:
                server_config = self.config_manager.servers.get(server_id, {})
                if server_config.get("installed", False):
                    print(f"  ▶ Starte: {server_config.get('name', server_id)}")
                    self.start_server(server_id)
                    time.sleep(1)  # Kurze Pause zwischen Server-Starts
    
    def save_running_servers(self):
        """Speichert die Liste der laufenden Server für Autostart"""
        running_servers = []
        for server_id, instance in self.server_instances.items():
            if instance.is_running():
                running_servers.append(server_id)
        
        self.config_manager.app_config["autostart_server_list"] = running_servers
        self.config_manager.save_app_config()
    
    def start_web_server(self):
        """Startet den Flask Web-Server (ausgelagert nach gsm/web/server.py)"""
        _create_and_start_web_server(self, self.config_manager)
    
    def check_for_updates(self):
        """Prüft auf Updates"""
        t = self.config_manager.get_text
        
        self.update_btn.configure(text="⏳ Prüfe...")
        self.update()
        
        def check():
            result = self.updater.check_for_updates()
            self.after(0, lambda: self.handle_update_result(result))
        
        threading.Thread(target=check, daemon=True).start()
    
    def handle_update_result(self, result):
        """Verarbeitet das Update-Ergebnis"""
        t = self.config_manager.get_text
        
        self.update_btn.configure(text=f"🔄 {t('check_updates')}")
        
        if 'error' in result:
            messagebox.showerror(t("error"), result['error'])
            return
        
        if result.get('available'):
            self.show_update_dialog(result)
        else:
            messagebox.showinfo(
                t("info"),
                f"✅ {t('no_updates')}\n\n"
                f"Aktuelle Version: v{result['current']}"
            )
    
    def show_update_dialog(self, update_info):
        """Zeigt den Update-Dialog"""
        t = self.config_manager.get_text
        
        dialog = ctk.CTkToplevel(self)
        dialog.title(t("update_available"))
        dialog.geometry("500x400")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        
        # Zentrieren
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 500) // 2
        y = (dialog.winfo_screenheight() - 400) // 2
        dialog.geometry(f"500x400+{x}+{y}")
        
        # Content
        ctk.CTkLabel(
            dialog,
            text="🎉 Update verfügbar!",
            font=("Arial", 24, "bold")
        ).pack(pady=20)
        
        ctk.CTkLabel(
            dialog,
            text=f"Aktuelle Version: v{update_info['current']}\n"
                 f"Neue Version: v{update_info['latest']}",
            font=("Arial", 14)
        ).pack(pady=10)
        
        # Release Notes
        if update_info.get('release_notes'):
            notes_frame = ctk.CTkFrame(dialog)
            notes_frame.pack(fill="both", expand=True, padx=20, pady=10)
            
            ctk.CTkLabel(
                notes_frame,
                text="📋 Änderungen:",
                font=("Arial", 12, "bold")
            ).pack(anchor="w", padx=10, pady=5)
            
            notes_text = ctk.CTkTextbox(notes_frame, height=120)
            notes_text.pack(fill="both", expand=True, padx=10, pady=5)
            notes_text.insert("1.0", update_info['release_notes'][:500])
            notes_text.configure(state="disabled")
        
        # Progress Bar (versteckt)
        self.update_progress = ctk.CTkProgressBar(dialog, width=400)
        self.update_progress.set(0)
        
        self.update_status = ctk.CTkLabel(dialog, text="", font=("Arial", 11))
        
        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkButton(
            btn_frame,
            text=t("cancel"),
            command=dialog.destroy,
            fg_color="gray",
            width=100
        ).pack(side="left")
        
        self.install_btn = ctk.CTkButton(
            btn_frame,
            text=f"⬇️ {t('download_update')}",
            command=lambda: self.download_and_install_update(dialog),
            fg_color="green",
            width=200
        )
        self.install_btn.pack(side="right")
    
    def download_and_install_update(self, dialog):
        """Lädt Update herunter und installiert es"""
        t = self.config_manager.get_text
        
        self.install_btn.configure(state="disabled", text="⏳ Download...")
        self.update_progress.pack(pady=5)
        self.update_status.pack()
        
        def update_progress(percent):
            self.after(0, lambda: self.update_progress.set(percent / 100))
            self.after(0, lambda: self.update_status.configure(text=f"Download: {percent}%"))
        
        def do_download():
            # Download
            result = self.updater.download_update(progress_callback=update_progress)
            
            if 'error' in result:
                self.after(0, lambda: messagebox.showerror(t("error"), result['error']))
                self.after(0, lambda: self.install_btn.configure(state="normal", text=f"⬇️ {t('download_update')}"))
                return
            
            # Installation (umbenennen + kopieren)
            self.after(0, lambda: self.update_status.configure(text="Installiere Update..."))
            install_result = self.updater.install_update(result['file'])
            
            if 'error' in install_result:
                self.after(0, lambda: messagebox.showerror(t("error"), install_result['error']))
                self.after(0, lambda: self.install_btn.configure(state="normal", text=f"⬇️ {t('download_update')}"))
                return
            
            if install_result.get('restart'):
                # Update erfolgreich - Programm SOFORT beenden
                # Das Updater-Script wartet und startet dann die neue Version
                def close_now():
                    try:
                        dialog.destroy()
                    except:
                        pass
                    # Alle Server-Referenzen entfernen (laufen weiter)
                    for instance in self.server_instances.values():
                        instance.process = None
                    # SOFORT beenden - nicht warten!
                    os._exit(0)
                
                # Sofort schließen, keine Verzögerung
                self.after(100, close_now)
            else:
                self.after(0, lambda: messagebox.showinfo(t("success"), install_result.get('message', 'Update installiert!')))
                self.after(0, dialog.destroy)
        
        threading.Thread(target=do_download, daemon=True).start()
    
    def on_close(self):
        """Wird aufgerufen wenn das Fenster geschlossen wird"""
        # Prüfe ob Server laufen
        running_servers = [sid for sid, inst in self.server_instances.items() if inst.is_running()]
        
        if running_servers:
            result = messagebox.askyesno(
                "Beenden?",
                f"{len(running_servers)} Server läuft/laufen noch!\n\n"
                "Wirklich beenden?\n"
                "(Server laufen im Hintergrund weiter)"
            )
            if not result:
                return
        
        # Laufende Server für Autostart speichern
        if self.config_manager.app_config.get("autostart_servers", False):
            self.save_running_servers()
        
        self.destroy()


# ==================== MAIN ====================
if __name__ == "__main__":
    app = GameServerManagerApp()
    app.mainloop()
