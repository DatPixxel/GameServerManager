"""
Game Server Manager Pro - Auth Manager
Sicheres Passwort-Management mit Argon2id und Hash-Migration
"""

import json
import os
import logging
from typing import Dict, Optional
from security_utils import PasswordHasher

logger = logging.getLogger(__name__)

class AuthManager:
    """
    Verwaltet Benutzer-Authentifizierung mit sicherem Passwort-Hashing.
    Unterstützt automatische Migration von alten SHA256-Hashes.
    """
    
    def __init__(self, users_file: str):
        """
        Args:
            users_file: Pfad zur users.json Datei
        """
        self.users_file = users_file
        self.hasher = PasswordHasher()
        self.users: Dict[str, Dict] = {}
        self.load_users()
    
    def load_users(self):
        """Lädt Benutzer aus Datei"""
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    self.users = json.load(f)
                logger.info(f"✅ {len(self.users)} Benutzer geladen")
            except Exception as e:
                logger.error(f"❌ Fehler beim Laden der Benutzer: {e}")
                self.users = {}
        else:
            logger.info("ℹ️ Keine Benutzerdatei gefunden - erstelle neue")
            self.users = {}
    
    def save_users(self):
        """Speichert Benutzer in Datei"""
        try:
            os.makedirs(os.path.dirname(self.users_file), exist_ok=True)
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, indent=4)
            logger.info("✅ Benutzer gespeichert")
        except Exception as e:
            logger.error(f"❌ Fehler beim Speichern der Benutzer: {e}")
    
    def verify_password(self, username: str, password: str) -> bool:
        """
        Verifiziert ein Passwort und migriert ggf. alte Hashes.
        
        Args:
            username: Benutzername
            password: Passwort
        
        Returns:
            bool: True wenn Passwort korrekt
        """
        if username not in self.users:
            return False
        
        user = self.users[username]
        password_hash = user.get('password_hash', '')
        
        # Verifiziere Passwort
        is_valid = self.hasher.verify_password(password, password_hash)
        
        if is_valid:
            # Prüfe ob Hash aktualisiert werden sollte (Migration)
            if self.hasher.needs_rehash(password_hash):
                logger.info(f"🔄 Migriere Passwort-Hash für {username}")
                new_hash = self.hasher.hash_password(password)
                user['password_hash'] = new_hash
                self.save_users()
        
        return is_valid
    
    def set_password(self, username: str, password: str):
        """
        Setzt/Aktualisiert ein Passwort.
        
        Args:
            username: Benutzername
            password: Neues Passwort
        """
        password_hash = self.hasher.hash_password(password)
        
        if username not in self.users:
            self.users[username] = {}
        
        self.users[username]['password_hash'] = password_hash
        self.save_users()
        logger.info(f"✅ Passwort für {username} gesetzt")
    
    def create_user(self, username: str, password: str, role: str = 'user') -> bool:
        """
        Erstellt einen neuen Benutzer.
        
        Args:
            username: Benutzername
            password: Passwort
            role: Rolle (z.B. 'admin', 'user')
        
        Returns:
            bool: True wenn erfolgreich
        """
        if username in self.users:
            logger.warning(f"⚠️ Benutzer {username} existiert bereits")
            return False
        
        password_hash = self.hasher.hash_password(password)
        
        self.users[username] = {
            'password_hash': password_hash,
            'role': role,
            'created_at': __import__('datetime').datetime.now().isoformat()
        }
        
        self.save_users()
        logger.info(f"✅ Benutzer {username} erstellt")
        return True
    
    def delete_user(self, username: str) -> bool:
        """Löscht einen Benutzer"""
        if username in self.users:
            del self.users[username]
            self.save_users()
            logger.info(f"✅ Benutzer {username} gelöscht")
            return True
        return False
    
    def get_user(self, username: str) -> Optional[Dict]:
        """Gibt Benutzer-Informationen zurück (ohne Hash)"""
        if username in self.users:
            user = self.users[username].copy()
            user.pop('password_hash', None)  # Entferne Hash
            return user
        return None
    
    def list_users(self) -> Dict[str, Dict]:
        """Listet alle Benutzer (ohne Hashes)"""
        users_list = {}
        for username, user_data in self.users.items():
            user_copy = user_data.copy()
            user_copy.pop('password_hash', None)
            users_list[username] = user_copy
        return users_list

# ==================== LEGACY SUPPORT ====================
class LegacyPasswordMigration:
    """
    Hilfsklasse für die Migration von alten Passwort-Systemen.
    Kann in die Hauptanwendung integriert werden.
    """
    
    @staticmethod
    def migrate_from_sha256(old_hash: str, password: str, auth_manager: AuthManager, username: str):
        """
        Migriert von SHA256 zu Argon2id.
        
        Args:
            old_hash: Alter SHA256-Hash
            password: Klartext-Passwort (nur bei erfolgreichem Login verfügbar)
            auth_manager: AuthManager-Instanz
            username: Benutzername
        """
        import hashlib
        
        # Verifiziere alten Hash
        if hashlib.sha256(password.encode()).hexdigest() == old_hash:
            # Erstelle neuen Hash
            auth_manager.set_password(username, password)
            logger.info(f"✅ Passwort für {username} von SHA256 zu Argon2id migriert")
            return True
        
        return False
