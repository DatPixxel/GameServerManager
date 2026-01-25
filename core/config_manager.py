"""
Configuration Manager für Game Server Manager Pro
Verwaltet App-Config und Server-Configs
"""

import os
import json
import hashlib
from datetime import datetime

# Password Hashing
try:
    import argon2
    ARGON2_AVAILABLE = True
except ImportError:
    ARGON2_AVAILABLE = False

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False

class ConfigManager:
    """Verwaltet alle Konfigurationsdateien"""
    
    def __init__(self):
        global PATHS
        ensure_directories()
        self.app_config = self.load_app_config()
        self.servers = self.load_servers()
        self.users = self.load_users()
    
    def load_app_config(self):
        """Lädt oder erstellt die App-Konfiguration"""
        default_config = {
            "first_run": True,
            "language": "de",
            "theme": "dark",
            "minimize_to_tray": True,
            "start_minimized": False,
            "auto_start_servers": False,
            "discord": {
                "enabled": False,
                "webhook_url": "",
                "notify_start": True,
                "notify_stop": True,
                "notify_crash": True,
                "notify_backup": True
            },
            "web": {
                "enabled": True,
                "port": 5001
            },
            "steamcmd_installed": False,
            "clusters": {}
        }
        
        config_file = PATHS.get("app_config", "")
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                print(f"⚠️ WARNUNG: app_config.json ist beschädigt: {e.msg}")
                print(f"   Verwende Standard-Einstellungen...")
                return default_config
            except Exception as e:
                print(f"⚠️ Fehler beim Laden von app_config.json: {e}")
                return default_config
        else:
            return default_config
    
    def save_app_config(self):
        """Speichert die App-Konfiguration"""
        config_file = PATHS.get("app_config", "")
        if config_file:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.app_config, f, indent=4, ensure_ascii=False)
    
    def load_servers(self):
        """Lädt die Server-Konfigurationen"""
        config_file = PATHS.get("servers_config", "")
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                print(f"⚠️ WARNUNG: servers.json ist beschädigt (Zeile {e.lineno}): {e.msg}")
                print(f"   Datei: {config_file}")
                print(f"   Erstelle Backup und starte mit leerer Server-Liste...")
                # Backup erstellen
                try:
                    backup_file = config_file + ".broken"
                    shutil.copy(config_file, backup_file)
                    print(f"   Backup erstellt: {backup_file}")
                except:
                    pass
                return {}
            except Exception as e:
                print(f"⚠️ Fehler beim Laden von servers.json: {e}")
                return {}
        else:
            return {}
    
    def save_servers(self):
        """Speichert die Server-Konfigurationen"""
        config_file = PATHS.get("servers_config", "")
        if config_file:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.servers, f, indent=4, ensure_ascii=False)
    
    def load_users(self):
        """Lädt die Benutzer-Konfiguration"""
        default_users = {
            "admin": {
                "password_hash": "",
                "role": "admin"
            }
        }
        
        config_file = PATHS.get("users_config", "")
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                print(f"⚠️ WARNUNG: users.json ist beschädigt: {e.msg}")
                return default_users
            except Exception as e:
                print(f"⚠️ Fehler beim Laden von users.json: {e}")
                return default_users
        else:
            return default_users
    
    def save_users(self):
        """Speichert die Benutzer-Konfiguration"""
        config_file = PATHS.get("users_config", "")
        if config_file:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, indent=4, ensure_ascii=False)
    
    def set_admin_password(self, password):
        """Setzt das Admin-Passwort mit sicherem PBKDF2-Hash"""
        self.users["admin"]["password_hash"] = hash_password(password)
        self.save_users()
    
    def verify_password(self, password):
        """
        Überprüft das Passwort.
        Unterstützt Legacy SHA-256 und neues PBKDF2 Format.
        Bei Legacy-Hash: automatisches Upgrade auf PBKDF2.
        """
        stored_hash = self.users["admin"].get("password_hash", "")
        
        # Passwort verifizieren (unterstützt beide Formate)
        if verify_password(password, stored_hash):
            # Wenn Legacy-Hash: automatisch auf PBKDF2 upgraden
            if is_legacy_hash(stored_hash):
                print("🔐 Upgrade von SHA-256 auf PBKDF2...")
                self.set_admin_password(password)
            return True
        return False
    
    def add_server(self, server_id, server_config):
        """Fügt einen neuen Server hinzu"""
        self.servers[server_id] = server_config
        
        # Erstelle Server-Verzeichnisse
        server_dir = os.path.join(PATHS["servers"], server_id)
        backup_dir = os.path.join(PATHS["backups"], server_id)
        os.makedirs(server_dir, exist_ok=True)
        os.makedirs(backup_dir, exist_ok=True)
        
        self.save_servers()
    
    def remove_server(self, server_id):
        """Entfernt einen Server"""
        if server_id in self.servers:
            del self.servers[server_id]
            self.save_servers()
    
    def get_text(self, key):
        """Holt übersetzten Text"""
        lang = self.app_config.get("language", "de")
        return TRANSLATIONS.get(lang, TRANSLATIONS["de"]).get(key, key)


# ==================== SERVER MANAGER ====================
