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
from gsm.ui.mixins.install import InstallUpdateMixin
from gsm.ui.mixins.game_ops import GameServerOpsMixin
from gsm.ui.mixins.settings import SettingsMixin
from gsm.ui.mixins.rcon import RconLogMixin

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
class GameServerManagerApp(TeamSpeakServicesMixin, BackupsMixin, InstallUpdateMixin, GameServerOpsMixin, SettingsMixin, RconLogMixin, ctk.CTk):
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
            font=("Segoe UI", 18, "bold"),
            text_color="#4c9aff"
        ).pack(side="left", padx=20, pady=12)
        
        ctk.CTkLabel(
            header,
            text=f"v{VERSION}",
            font=("Segoe UI", 12),
            text_color="#555555"
        ).pack(side="left", padx=5)
        
        # Mitte-Links: Web Interface + Update
        mid_frame = ctk.CTkFrame(header, fg_color="transparent")
        mid_frame.pack(side="left", padx=30, pady=10)
        
        web_port = self.config_manager.app_config.get("web", {}).get("port", 5001)
        ctk.CTkButton(
            mid_frame,
            text=f"🌐 localhost:{web_port}",
            font=("Segoe UI", 13),
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
            font=("Segoe UI", 13),
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
            font=("Segoe UI", 13),
            fg_color="#6a3a8a",
            hover_color="#7a4a9a",
            command=self.show_cluster_settings
        ).pack(side="right", padx=3)
        
        ctk.CTkButton(
            right_frame,
            text="🔔 Discord",
            width=110,
            height=35,
            font=("Segoe UI", 13),
            fg_color="#5865F2",
            hover_color="#4752C4",
            command=self.show_discord_settings
        ).pack(side="right", padx=3)
        
        ctk.CTkButton(
            right_frame,
            text="⚙️ Settings",
            width=110,
            height=35,
            font=("Segoe UI", 13),
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
        self.resize_handle.bind("<Enter>", lambda e: self.resize_handle.configure(fg_color="#4c9aff"))
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
            font=("Segoe UI", 28)
        ).pack(side="left")
        
        ctk.CTkLabel(
            brand_frame,
            text="GSM Pro",
            font=("Segoe UI", 18, "bold"),
            text_color="#4c9aff"
        ).pack(side="left", padx=8)
        
        # Trennlinie
        ctk.CTkFrame(self.sidebar, height=1, fg_color="#2a2a3a").pack(fill="x", padx=10, pady=5)
        
        # --- MENU Section ---
        ctk.CTkLabel(
            self.sidebar,
            text="MENU",
            font=("Segoe UI", 12, "bold"),
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
            font=("Segoe UI", 12, "bold"),
            text_color="#666666",
            anchor="w"
        ).pack(fill="x", padx=20, pady=(5, 8))
        
        # Add Server Button
        add_server_btn = ctk.CTkButton(
            self.sidebar,
            text="+ Add Server",
            font=("Segoe UI", 13),
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
            font=("Segoe UI", 12),
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
                font=("Segoe UI", 13, "bold") if is_active else ("Segoe UI", 13),
                height=42,
                anchor="w",
                fg_color="#1e3a5f" if is_active else "transparent",
                hover_color="#2a2a3e",
                text_color="#ffffff" if is_active else "#aaaaaa",
                border_width=2 if is_active else 0,
                border_color="#4c9aff",
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
            font=("Segoe UI", 18, "bold"),
            text_color="#4c9aff"
        ).pack(side="left", padx=20, pady=12)
        
        # Server Count
        total = len(self.config_manager.servers)
        running = sum(1 for sid in self.config_manager.servers 
                     if self.server_instances.get(sid) and self.server_instances[sid].is_running())
        
        ctk.CTkLabel(
            header,
            text=f"🟢 {running} Online  |  📦 {total} Total",
            font=("Segoe UI", 13),
            text_color="#888888"
        ).pack(side="right", padx=20)
        
        # Scrollable Liste
        scroll = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=15, pady=10)
        
        if not self.config_manager.servers:
            ctk.CTkLabel(
                scroll,
                text="Keine Server vorhanden",
                font=("Segoe UI", 16),
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
            status_color = "#3fb771" if is_running else "#ff4444"
            ctk.CTkLabel(
                row_inner,
                text="●",
                font=("Segoe UI", 20),
                text_color=status_color,
                width=30
            ).pack(side="left")
            
            # Icon + Name
            ctk.CTkLabel(
                row_inner,
                text=f"{icon} {server_config.get('name', 'Server')}",
                font=("Segoe UI", 14, "bold"),
                anchor="w"
            ).pack(side="left", padx=10)
            
            # Game
            ctk.CTkLabel(
                row_inner,
                text=server_config.get("game", ""),
                font=("Segoe UI", 12),
                text_color="#888888"
            ).pack(side="left", padx=20)
            
            # Port
            ctk.CTkLabel(
                row_inner,
                text=f":{server_config.get('port', '?')}",
                font=("Segoe UI", 12),
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
                font=("Segoe UI", 12),
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
                    font=("Segoe UI", 12),
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
                    font=("Segoe UI", 12),
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
            font=("Segoe UI", 11),
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
            font=("Segoe UI", 22, "bold"),
            text_color="#4c9aff"
        ).pack(side="left", padx=20, pady=15)
        
        # Scrollable Content
        scroll = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Tools Grid (2 Spalten)
        scroll.grid_columnconfigure((0, 1), weight=1, uniform="tool")
        
        # Tool Cards
        tools = [
            ("🔄", "Auto-Updates", "SteamCMD Updates für alle Server", self.check_for_updates),
            ("💾", "Backup Manager", "Backups erstellen und verwalten", self.open_backup_manager_tool),
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
            font=("Segoe UI", 36)
        ).pack(pady=(20, 10))
        
        # Title
        ctk.CTkLabel(
            card,
            text=title,
            font=("Segoe UI", 14, "bold")
        ).pack()
        
        # Description
        ctk.CTkLabel(
            card,
            text=desc,
            font=("Segoe UI", 12),
            text_color="#666666"
        ).pack(pady=5)
        
        # Button
        ctk.CTkButton(
            card,
            text="Öffnen",
            width=100,
            height=32,
            fg_color="#4c9aff",
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
            font=("Segoe UI", 22, "bold"),
            text_color="#4c9aff"
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
                             cpu_percent/100, "#3fb771" if cpu_percent < 70 else "#ff4444", 0)
        
        # RAM Card
        if ram:
            ram_percent = ram.percent
            ram_used = ram.used / (1024**3)
            ram_total = ram.total / (1024**3)
            self.create_stat_card(content, "RAM", f"{ram_used:.1f} / {ram_total:.1f} GB",
                                 ram_percent/100, "#4c9aff" if ram_percent < 80 else "#ff4444", 1)
        
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
            font=("Segoe UI", 16, "bold")
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
            font=("Segoe UI", 12),
            text_color="#666666"
        ).pack(pady=(20, 5))
        
        ctk.CTkLabel(
            card,
            text=value,
            font=("Segoe UI", 24, "bold"),
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
            font=("Segoe UI", 11),
            width=150,
            anchor="w"
        ).pack(side="left")
        
        # CPU
        cpu = resources.get("cpu", 0)
        ctk.CTkLabel(
            content,
            text=f"CPU: {cpu:.0f}%",
            font=("Segoe UI", 12),
            text_color="#3fb771" if cpu < 50 else "#ffaa00" if cpu < 80 else "#ff4444",
            width=80
        ).pack(side="left", padx=10)
        
        # RAM
        ram = resources.get("ram_gb", 0)
        ctk.CTkLabel(
            content,
            text=f"RAM: {ram:.1f} GB",
            font=("Segoe UI", 12),
            text_color="#4c9aff",
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
            font=("Segoe UI", 12),
            text_color="#888888",
            width=15
        )
        expand_label.pack(side="left")
        
        # Game Icon + Name
        ctk.CTkLabel(
            header_content,
            text=f"{icon} {game}",
            font=("Segoe UI", 13, "bold"),
            anchor="w"
        ).pack(side="left", padx=(5, 0))
        
        # Server-Anzahl Badge
        badge_color = "#2d5a2d" if running_count > 0 else "#4a4a5a"
        badge_text_color = "#3fb771" if running_count > 0 else "#888888"
        
        badge = ctk.CTkFrame(header_content, fg_color=badge_color, corner_radius=10)
        badge.pack(side="right")
        
        ctk.CTkLabel(
            badge,
            text=f"{running_count}/{len(servers)}",
            font=("Segoe UI", 10, "bold"),
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
        border_color = "#3fb771" if is_running else "#3a3a4a"
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
            font=("Segoe UI", 12, "bold"),
            anchor="w"
        ).pack(side="left")
        
        # Status Badge
        status_color = "#3fb771" if is_running else "#ff4444"
        status_text = "●" if is_running else "○"
        
        status_badge = ctk.CTkLabel(
            top_row,
            text=status_text,
            text_color=status_color,
            font=("Segoe UI", 12)
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
                font=("Segoe UI", 12),
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
                font=("Segoe UI", 12),
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
            font=("Segoe UI", 72)
        ).pack(pady=20)
        
        ctk.CTkLabel(
            msg_frame,
            text=t("no_servers"),
            font=("Segoe UI", 24, "bold")
        ).pack(pady=10)
        
        ctk.CTkLabel(
            msg_frame,
            text=t("add_first_server"),
            font=("Segoe UI", 16),
            text_color="gray"
        ).pack(pady=10)
        
        ctk.CTkButton(
            msg_frame,
            text="+ " + t("add_server"),
            command=self.show_add_server_dialog,
            font=("Segoe UI", 16),
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
            font=("Segoe UI", 16, "bold"),
            text_color="#4c9aff"
        ).pack(side="left", padx=15, pady=10)
        
        # Refresh Button (klein)
        ctk.CTkButton(
            header_frame,
            text="🔄",
            width=28,
            height=28,
            font=("Segoe UI", 11),
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
            font=("Segoe UI", 12),
            text_color="#3fb771",
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
            font=("Segoe UI", 12),
            text_color="#3fb771",
            padx=8,
            pady=3
        ).pack()
        
        # Total Badge
        total_badge = ctk.CTkFrame(stats_frame, fg_color="#2a2a3a", corner_radius=8)
        total_badge.pack(side="left", padx=3)
        ctk.CTkLabel(
            total_badge,
            text=f"📦 {total_servers}",
            font=("Segoe UI", 12),
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
            border_color="#3fb771" if is_running else "#2a2a3a"
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
            font=("Segoe UI", 12),
            text_color="#888888"
        ).pack(side="left")
        
        # Status Text
        status_text = "●" if is_running else "○"
        status_color = "#3fb771" if is_running else "#ff4444"
        ctk.CTkLabel(
            header_content,
            text=status_text,
            font=("Segoe UI", 12),
            text_color=status_color
        ).pack(side="right")
        
        # === Server Name ===
        name = server_config.get("name", "Server")
        if len(name) > 20:
            name = name[:18] + "..."
        ctk.CTkLabel(
            card,
            text=name,
            font=("Segoe UI", 13, "bold"),
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
            font=("Segoe UI", 12),
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
            
            cpu_color = "#3fb771" if cpu_value < 50 else "#ffaa00" if cpu_value < 80 else "#ff4444"
            
            ctk.CTkLabel(
                stats_inner,
                text=f"CPU {cpu_value:.0f}%",
                font=("Segoe UI", 12),
                text_color=cpu_color
            ).pack(side="left")
            
            ctk.CTkLabel(
                stats_inner,
                text=f"RAM {ram_gb:.1f}G",
                font=("Segoe UI", 12),
                text_color="#4c9aff"
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
            font=("Segoe UI", 12),
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
                font=("Segoe UI", 12),
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
                font=("Segoe UI", 12),
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
            font=("Segoe UI", 12),
            text_color="#666666",
            width=60,
            anchor="w"
        ).pack(side="left")
        
        ctk.CTkLabel(
            row,
            text=value[:25] + "..." if len(value) > 25 else value,
            font=("Segoe UI", 12),
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
            font=("Segoe UI", 32)
        ).pack(side="left")
        
        ctk.CTkLabel(
            name_frame,
            text=server_config.get('name', 'Server'),
            font=("Segoe UI", 22, "bold"),
            text_color="#ffffff"
        ).pack(side="left", padx=10)
        
        # Game Name
        ctk.CTkLabel(
            left_frame,
            text=server_config.get("game", "Unknown"),
            font=("Segoe UI", 11),
            text_color="#666666"
        ).pack(anchor="w", padx=45)
        
        # Right: Status Badge + Actions
        right_frame = ctk.CTkFrame(header_inner, fg_color="transparent")
        right_frame.pack(side="right")
        
        # Status Badge
        status_bg = "#1a4a1a" if is_running else "#4a1a1a"
        status_color = "#3fb771" if is_running else "#ff4444"
        status_text = "● ONLINE" if is_running else "○ OFFLINE"
        
        status_badge = ctk.CTkFrame(right_frame, fg_color=status_bg, corner_radius=15)
        status_badge.pack(pady=5)
        
        ctk.CTkLabel(
            status_badge,
            text=status_text,
            font=("Segoe UI", 11, "bold"),
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
                font=("Segoe UI", 12),
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
            font=("Segoe UI", 14, "bold")
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
                font=("Segoe UI", 12),
                text_color="#666666"
            ).pack(anchor="w", padx=12, pady=(0, 10))
        
        # Tailscale Hinweis
        if tailscale_ip:
            hint_frame = ctk.CTkFrame(connect_card, fg_color="#1a3a1a", corner_radius=8)
            hint_frame.pack(fill="x", padx=15, pady=(0, 15))
            ctk.CTkLabel(
                hint_frame,
                text="✅ Tailscale aktiv - Kein Port-Forwarding nötig!",
                font=("Segoe UI", 12),
                text_color="#3fb771",
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
                font=("Segoe UI", 14, "bold")
            ).pack(side="left")
            
            mods = server_config.get("mods", [])
            ctk.CTkLabel(
                mods_header,
                text=f"{len(mods)} installed",
                font=("Segoe UI", 12),
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
                        font=("Segoe UI", 12)
                    ).pack(side="left")
                    
                    ctk.CTkButton(
                        mod_row,
                        text="✕",
                        width=24,
                        height=24,
                        font=("Segoe UI", 12),
                        fg_color="#4a2a2a",
                        hover_color="#6a3a3a",
                        command=lambda mid=mod_id: self.remove_mod(server_id, mid)
                    ).pack(side="right")
            else:
                ctk.CTkLabel(
                    mods_content,
                    text="No mods installed",
                    text_color="#666666",
                    font=("Segoe UI", 12),
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
                font=("Segoe UI", 12)
            )
            self.mod_entry.pack(side="left")
            
            ctk.CTkButton(
                add_frame,
                text="+ Add",
                width=60,
                height=30,
                font=("Segoe UI", 12),
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
            font=("Segoe UI", 14, "bold")
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
            font=("Segoe UI", 12)
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
                font=("Segoe UI", 12)
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
                font=("Segoe UI", 12)
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
            font=("Segoe UI", 12)
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
                font=("Segoe UI", 18, "bold")
            ).pack(side="left")
            
            # Version Info
            mc_version = server_config.get("mc_version", "?")
            forge_version = server_config.get("forge_version", "?")
            ram = server_config.get("ram", "4G")
            
            ctk.CTkLabel(
                header_mc,
                text=f"MC {mc_version} | Forge {forge_version} | RAM: {ram}",
                font=("Segoe UI", 12),
                text_color="#4c9aff"
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
                font=("Segoe UI", 14, "bold")
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
                            font=("Segoe UI", 11),
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
                        font=("Segoe UI", 12),
                        text_color="gray"
                    ).pack(anchor="w", padx=15, pady=(5, 10))
                else:
                    ctk.CTkLabel(
                        mods_list_frame,
                        text="Keine Mods installiert.\nKopiere .jar Dateien in den Mods-Ordner!",
                        font=("Segoe UI", 11),
                        text_color="gray"
                    ).pack(padx=15, pady=15)
            else:
                ctk.CTkLabel(
                    mods_list_frame,
                    text="⚠️ Mods-Ordner nicht gefunden.\nServer zuerst installieren!",
                    font=("Segoe UI", 11),
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
                font=("Segoe UI", 18, "bold")
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
                    font=("Segoe UI", 11),
                    text_color="#7dcfff"
                ).pack(anchor="w", padx=20, pady=(2, 8))

                if status.get("configured"):
                    ctk.CTkLabel(
                        conan_frame,
                        text="Mod-Auswahl",
                        font=("Segoe UI", 10, "bold"),
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
                    font=("Segoe UI", 10),
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
                    font=("Segoe UI", 11),
                    text_color="#3fb771"
                ).pack(anchor="w", padx=20, pady=(5, 15))
            else:
                ctk.CTkLabel(
                    conan_frame,
                    text="⚠️ Noch kein Savegame vorhanden",
                    font=("Segoe UI", 11),
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
                font=("Segoe UI", 18, "bold")
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
                        font=("Segoe UI", 11),
                        text_color="#3fb771"
                    ).pack(anchor="w")
                except:
                    pass
            else:
                ctk.CTkLabel(
                    enshrouded_frame,
                    text="⚠️ Config-Datei nicht gefunden. Server zuerst starten!",
                    font=("Segoe UI", 11),
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
            font=("Segoe UI", 18, "bold"),
            text_color="#4c9aff"
        ).pack(side="left")
        
        # Live Indicator
        if instance.is_running():
            live_badge = ctk.CTkFrame(log_header, fg_color="#2d5a2d", corner_radius=8)
            live_badge.pack(side="left", padx=10)
            ctk.CTkLabel(
                live_badge,
                text="● LIVE",
                font=("Segoe UI", 9, "bold"),
                text_color="#3fb771",
                padx=8,
                pady=2
            ).pack()
        
        # Clear Button
        ctk.CTkButton(
            log_header,
            text="🗑️ Clear",
            width=70,
            height=28,
            font=("Segoe UI", 12),
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
            text_color = "#3fb771"
        # Info - Cyan
        elif any(x in log_lower for x in ["info", "ℹ️", "📋", "installing", "downloading", "updating"]):
            text_color = "#4c9aff"
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
            font=("Segoe UI", font_size),
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
            font=("Segoe UI", 22)
        ).pack()
        
        # Value
        ctk.CTkLabel(
            content,
            text=str(value),
            font=("Segoe UI", 16, "bold"),
            text_color="#4c9aff"
        ).pack()
        
        # Title
        ctk.CTkLabel(
            content,
            text=title,
            font=("Segoe UI", 12),
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
            font=("Segoe UI", 13),
            text_color="#aaaaaa",
            width=100,
            anchor="w"
        ).pack(side="left")
        
        # Value Entry
        entry = ctk.CTkEntry(
            row,
            width=200,
            height=34,
            font=("Segoe UI", 13),
            fg_color="#1a1a2a",
            border_color="#3a3a4a" if not highlight else "#4c9aff"
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
            font=("Segoe UI", 12),
            fg_color="#3a3a4a",
            hover_color="#4a4a5a",
            command=lambda v=value: self.copy_to_clipboard(v)
        ).pack(side="left", padx=2)
        
        # Highlight Badge
        if highlight:
            ctk.CTkLabel(
                row,
                text="✓",
                font=("Segoe UI", 12),
                text_color="#3fb771"
            ).pack(side="left", padx=5)
    
    def create_info_card(self, parent, col, title, value, icon):
        """Erstellt eine Info-Card"""
        card = ctk.CTkFrame(parent)
        card.grid(row=0, column=col, padx=5, pady=5, sticky="nsew")
        
        ctk.CTkLabel(
            card,
            text=icon,
            font=("Segoe UI", 32)
        ).pack(pady=(15, 5))
        
        ctk.CTkLabel(
            card,
            text=value,
            font=("Segoe UI", 20, "bold"),
            text_color="#4c9aff"
        ).pack()
        
        ctk.CTkLabel(
            card,
            text=title,
            font=("Segoe UI", 12),
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
            font=("Segoe UI", 20, "bold")
        ).pack(pady=(0, 20))
        
        # === ALLGEMEIN ===
        ctk.CTkLabel(scroll, text="📋 Allgemein", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(10, 5))
        
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
        ctk.CTkLabel(scroll, text="🔌 Ports", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(20, 5))
        
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
        ctk.CTkLabel(scroll, text="🔐 Passwörter", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(20, 5))
        
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
        ctk.CTkLabel(scroll, text="💾 Backup-Einstellungen", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(20, 5))
        
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
            ctk.CTkLabel(scroll, text="🔗 Cluster", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(20, 5))
            
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
            font=("Segoe UI", 20, "bold")
        ).pack(pady=20)
        
        ctk.CTkLabel(
            dialog,
            text=f"Original: {server_config.get('name', 'Server')}",
            font=("Segoe UI", 12),
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
            font=("Segoe UI", 12),
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
                err_msg = str(e)
                self.after(0, lambda: messagebox.showerror(t("error"), f"{t('clone_failed')}: {err_msg}"))
        
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
            font=("Segoe UI", 18, "bold")
        ).pack(side="left")
        
        if not config_files:
            ctk.CTkLabel(
                dialog,
                text=f"📭 {t('config_no_files')}",
                font=("Segoe UI", 14),
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
        status_label = ctk.CTkLabel(dialog, text="", font=("Segoe UI", 12))
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
            font=("Segoe UI", 24, "bold")
        ).pack(pady=20)
        
        ctk.CTkLabel(
            dialog,
            text=f"Aktuelle Version: v{update_info['current']}\n"
                 f"Neue Version: v{update_info['latest']}",
            font=("Segoe UI", 14)
        ).pack(pady=10)
        
        # Release Notes
        if update_info.get('release_notes'):
            notes_frame = ctk.CTkFrame(dialog)
            notes_frame.pack(fill="both", expand=True, padx=20, pady=10)
            
            ctk.CTkLabel(
                notes_frame,
                text="📋 Änderungen:",
                font=("Segoe UI", 12, "bold")
            ).pack(anchor="w", padx=10, pady=5)
            
            notes_text = ctk.CTkTextbox(notes_frame, height=120)
            notes_text.pack(fill="both", expand=True, padx=10, pady=5)
            notes_text.insert("1.0", update_info['release_notes'][:500])
            notes_text.configure(state="disabled")
        
        # Progress Bar (versteckt)
        self.update_progress = ctk.CTkProgressBar(dialog, width=400)
        self.update_progress.set(0)
        
        self.update_status = ctk.CTkLabel(dialog, text="", font=("Segoe UI", 11))
        
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
