"""
Game Server Manager Pro - Security Utilities
Sicherheitsfunktionen für Pfad-Validierung, Passwort-Hashing, etc.
"""

import os
import re
import hashlib
import secrets
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any
import zipfile

# Logging Setup
logger = logging.getLogger(__name__)

# ==================== ERROR CODES ====================
class SecurityError(Exception):
    """Basis-Klasse für Sicherheitsfehler"""
    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(f"[{error_code}] {message}")

class PathTraversalError(SecurityError):
    """Pfad-Traversal wurde erkannt"""
    def __init__(self, message: str):
        super().__init__("PATH_TRAVERSAL", message)

class InvalidInputError(SecurityError):
    """Ungültige Eingabe"""
    def __init__(self, message: str):
        super().__init__("INVALID_INPUT", message)

class ZipSlipError(SecurityError):
    """Zip-Slip Angriff wurde erkannt"""
    def __init__(self, message: str):
        super().__init__("ZIP_SLIP", message)

# ==================== PASSWORT-HASHING ====================
class PasswordHasher:
    """
    Sichere Passwort-Hashing mit Argon2id (empfohlen) oder bcrypt als Fallback.
    Unterstützt Migration von alten SHA256-Hashes.
    """
    
    def __init__(self):
        # Versuche Argon2 zu importieren (bevorzugt)
        try:
            from argon2 import PasswordHasher as Argon2PH
            from argon2.exceptions import VerifyMismatchError, InvalidHash
            self.argon2 = Argon2PH()
            self.hasher_type = "argon2"
            self.VerifyMismatchError = VerifyMismatchError
            self.InvalidHash = InvalidHash
            logger.info("✅ Argon2id Passwort-Hashing aktiviert")
        except ImportError:
            # Fallback auf bcrypt
            try:
                import bcrypt
                self.bcrypt = bcrypt
                self.hasher_type = "bcrypt"
                logger.warning("⚠️ Argon2 nicht verfügbar - nutze bcrypt")
            except ImportError:
                # Letzter Fallback auf scrypt (in Python Standard Library)
                self.hasher_type = "scrypt"
                logger.warning("⚠️ Kein Argon2/bcrypt - nutze scrypt (weniger sicher)")
    
    def hash_password(self, password: str) -> str:
        """Erstellt einen sicheren Hash des Passworts"""
        if self.hasher_type == "argon2":
            return f"argon2${self.argon2.hash(password)}"
        
        elif self.hasher_type == "bcrypt":
            salt = self.bcrypt.gensalt()
            hashed = self.bcrypt.hashpw(password.encode('utf-8'), salt)
            return f"bcrypt${hashed.decode('utf-8')}"
        
        else:  # scrypt
            salt = secrets.token_bytes(16)
            hashed = hashlib.scrypt(
                password.encode('utf-8'),
                salt=salt,
                n=16384,  # CPU cost
                r=8,      # Block size
                p=1,      # Parallelization
                dklen=32  # Key length
            )
            return f"scrypt${salt.hex()}${hashed.hex()}"
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verifiziert ein Passwort gegen einen Hash"""
        # Erkenne Hash-Typ
        if password_hash.startswith("argon2$"):
            if self.hasher_type != "argon2":
                logger.error("❌ Argon2-Hash gefunden aber Argon2 nicht verfügbar")
                return False
            try:
                actual_hash = password_hash[7:]  # Remove "argon2$" prefix
                self.argon2.verify(actual_hash, password)
                return True
            except (self.VerifyMismatchError, self.InvalidHash):
                return False
        
        elif password_hash.startswith("bcrypt$"):
            if self.hasher_type != "bcrypt":
                logger.error("❌ bcrypt-Hash gefunden aber bcrypt nicht verfügbar")
                return False
            actual_hash = password_hash[7:]  # Remove "bcrypt$" prefix
            return self.bcrypt.checkpw(password.encode('utf-8'), actual_hash.encode('utf-8'))
        
        elif password_hash.startswith("scrypt$"):
            parts = password_hash.split('$')
            if len(parts) != 3:
                return False
            salt = bytes.fromhex(parts[1])
            expected_hash = bytes.fromhex(parts[2])
            
            computed_hash = hashlib.scrypt(
                password.encode('utf-8'),
                salt=salt,
                n=16384,
                r=8,
                p=1,
                dklen=32
            )
            return computed_hash == expected_hash
        
        else:
            # Legacy SHA256-Hash (Migration)
            return self._verify_legacy_sha256(password, password_hash)
    
    def _verify_legacy_sha256(self, password: str, password_hash: str) -> bool:
        """Verifiziert alte SHA256-Hashes (nur für Migration)"""
        computed = hashlib.sha256(password.encode()).hexdigest()
        return computed == password_hash
    
    def needs_rehash(self, password_hash: str) -> bool:
        """Prüft ob ein Hash aktualisiert werden sollte"""
        # Alle SHA256-Hashes müssen migriert werden
        if not password_hash.startswith(("argon2$", "bcrypt$", "scrypt$")):
            return True
        
        # Wenn wir Argon2 haben, aber Hash ist bcrypt/scrypt -> optional migrieren
        if self.hasher_type == "argon2" and not password_hash.startswith("argon2$"):
            return True
        
        return False

# ==================== PFAD-SICHERHEIT ====================
def safe_join(base_dir: str, user_path: str) -> str:
    """
    Sicherer Pfad-Join der Pfad-Traversal verhindert.
    
    Args:
        base_dir: Das Basis-Verzeichnis (z.B. Server-Ordner)
        user_path: Der vom Benutzer bereitgestellte Pfad (relativ)
    
    Returns:
        str: Der sichere absolute Pfad
    
    Raises:
        PathTraversalError: Wenn Pfad-Traversal erkannt wurde
    """
    # Normalisiere Basis-Verzeichnis
    base_dir = os.path.abspath(base_dir)
    
    # Blockiere absolute Pfade
    if os.path.isabs(user_path):
        raise PathTraversalError(f"Absolute Pfade nicht erlaubt: {user_path}")
    
    # Blockiere Windows-Laufwerke (C:, D:, etc.)
    if len(user_path) >= 2 and user_path[1] == ':':
        raise PathTraversalError(f"Laufwerksbuchstaben nicht erlaubt: {user_path}")
    
    # Normalisiere den Pfad
    user_path = os.path.normpath(user_path)
    
    # Erstelle den vollständigen Pfad
    full_path = os.path.normpath(os.path.join(base_dir, user_path))
    
    # Verwende realpath für symbolische Links
    try:
        real_full_path = os.path.realpath(full_path)
        real_base_dir = os.path.realpath(base_dir)
    except (OSError, ValueError) as e:
        raise PathTraversalError(f"Pfad-Auflösung fehlgeschlagen: {str(e)}")
    
    # Prüfe ob der Pfad innerhalb des Basis-Verzeichnisses liegt
    if not real_full_path.startswith(real_base_dir + os.sep) and real_full_path != real_base_dir:
        raise PathTraversalError(
            f"Pfad verlässt Basis-Verzeichnis: {user_path} -> {real_full_path} (Basis: {real_base_dir})"
        )
    
    return real_full_path

# ==================== CONFIG-DATEI WHITELIST ====================
ALLOWED_CONFIG_EXTENSIONS = {
    '.ini', '.cfg', '.json', '.txt', '.yaml', '.yml', 
    '.conf', '.properties', '.xml', '.toml'
}

ALLOWED_CONFIG_FILENAMES = {
    'Game.ini', 'GameUserSettings.ini', 'serverconfig.txt',
    'server.properties', 'config.json', 'settings.ini'
}

def is_config_file_allowed(filename: str) -> bool:
    """
    Prüft ob eine Config-Datei zum Lesen/Schreiben erlaubt ist.
    
    Args:
        filename: Der Dateiname (kann Pfad enthalten)
    
    Returns:
        bool: True wenn erlaubt
    """
    basename = os.path.basename(filename)
    _, ext = os.path.splitext(basename)
    
    # Prüfe Whitelist
    if basename in ALLOWED_CONFIG_FILENAMES:
        return True
    
    # Prüfe Endung
    if ext.lower() in ALLOWED_CONFIG_EXTENSIONS:
        return True
    
    return False

# ==================== ZIP SAFE EXTRACT ====================
def safe_extract(zip_path: str, dest_dir: str, max_files: int = 10000, max_size: int = 10*1024*1024*1024) -> None:
    """
    Extrahiert ein ZIP-Archiv sicher (Zip-Slip Protection).
    
    Args:
        zip_path: Pfad zur ZIP-Datei
        dest_dir: Ziel-Verzeichnis
        max_files: Maximale Anzahl Dateien
        max_size: Maximale Gesamtgröße in Bytes (default: 10 GB)
    
    Raises:
        ZipSlipError: Wenn Zip-Slip erkannt wurde
        ValueError: Wenn Limits überschritten wurden
    """
    dest_dir = os.path.abspath(dest_dir)
    total_size = 0
    file_count = 0
    
    with zipfile.ZipFile(zip_path, 'r') as zipf:
        for info in zipf.infolist():
            file_count += 1
            
            # Limit: Anzahl Dateien
            if file_count > max_files:
                raise ValueError(f"ZIP enthält zu viele Dateien (>{max_files})")
            
            # Limit: Gesamtgröße
            total_size += info.file_size
            if total_size > max_size:
                raise ValueError(f"ZIP ist zu groß (>{max_size / (1024**3):.1f} GB)")
            
            # Extrahiere Member-Name
            member_path = info.filename
            
            # Normalisiere Pfad
            member_path = os.path.normpath(member_path)
            
            # Erstelle Zielpfad
            target_path = os.path.join(dest_dir, member_path)
            
            # Verwende realpath für symlinks
            try:
                real_target = os.path.realpath(target_path)
                real_dest = os.path.realpath(dest_dir)
            except (OSError, ValueError) as e:
                raise ZipSlipError(f"Pfad-Auflösung fehlgeschlagen für {member_path}: {str(e)}")
            
            # Prüfe Zip-Slip
            if not real_target.startswith(real_dest + os.sep) and real_target != real_dest:
                raise ZipSlipError(
                    f"Zip-Slip erkannt: {member_path} würde außerhalb von {dest_dir} extrahiert werden"
                )
            
            # Symlinks blockieren (optional aber empfohlen)
            if info.external_attr & 0x20000000:  # Symlink flag
                logger.warning(f"⚠️ Symlink in ZIP ignoriert: {member_path}")
                continue
            
            # Extrahiere sicher
            zipf.extract(info, dest_dir)
    
    logger.info(f"✅ ZIP sicher extrahiert: {file_count} Dateien, {total_size / (1024**2):.1f} MB")

# ==================== INPUT-VALIDIERUNG ====================
def validate_port(port: Any) -> int:
    """
    Validiert einen Port-Wert.
    
    Args:
        port: Port-Wert (kann String oder Int sein)
    
    Returns:
        int: Validierter Port
    
    Raises:
        InvalidInputError: Wenn Port ungültig ist
    """
    try:
        port_int = int(port)
    except (ValueError, TypeError):
        raise InvalidInputError(f"Port muss eine Zahl sein: {port}")
    
    if not (1 <= port_int <= 65535):
        raise InvalidInputError(f"Port muss zwischen 1 und 65535 liegen: {port_int}")
    
    return port_int

def validate_mod_ids(mod_ids_str: str) -> List[str]:
    """
    Validiert eine Mod-ID-Liste (nur Ziffern und Kommas erlaubt).
    
    Args:
        mod_ids_str: Komma-getrennte Mod-IDs
    
    Returns:
        List[str]: Liste der validierten Mod-IDs
    
    Raises:
        InvalidInputError: Wenn Mod-IDs ungültig sind
    """
    if not mod_ids_str:
        return []
    
    # Nur Ziffern und Kommas erlaubt
    if not re.match(r'^[\d,]+$', mod_ids_str):
        raise InvalidInputError(f"Mod-IDs dürfen nur Ziffern und Kommas enthalten: {mod_ids_str}")
    
    # Aufteilen und validieren
    mod_ids = [m.strip() for m in mod_ids_str.split(',') if m.strip()]
    
    for mod_id in mod_ids:
        if not mod_id.isdigit():
            raise InvalidInputError(f"Mod-ID muss eine Zahl sein: {mod_id}")
    
    return mod_ids

def validate_server_name(name: str) -> str:
    """
    Validiert einen Servernamen (alphanumerisch + Leerzeichen, Bindestriche, Unterstriche).
    
    Args:
        name: Servername
    
    Returns:
        str: Validierter Servername
    
    Raises:
        InvalidInputError: Wenn Name ungültig ist
    """
    if not name or len(name) > 100:
        raise InvalidInputError(f"Servername muss zwischen 1 und 100 Zeichen lang sein")
    
    # Erlaubte Zeichen: Buchstaben, Zahlen, Leerzeichen, -, _, öäüÄÖÜß
    if not re.match(r'^[\w\s\-öäüÄÖÜß]+$', name):
        raise InvalidInputError(
            f"Servername enthält ungültige Zeichen. Erlaubt: Buchstaben, Zahlen, Leerzeichen, -, _"
        )
    
    return name

def validate_map_param(map_param: str, allowed_maps: List[str]) -> str:
    """
    Validiert einen Map-Parameter gegen eine Whitelist.
    
    Args:
        map_param: Map-Parameter
        allowed_maps: Liste erlaubter Maps
    
    Returns:
        str: Validierter Map-Parameter
    
    Raises:
        InvalidInputError: Wenn Map ungültig ist
    """
    if map_param not in allowed_maps:
        raise InvalidInputError(f"Ungültige Map: {map_param}. Erlaubt: {', '.join(allowed_maps)}")
    
    return map_param

# ==================== SHA256 INTEGRITÄTSPRÜFUNG ====================
def compute_file_sha256(filepath: str) -> str:
    """
    Berechnet SHA256-Hash einer Datei.
    
    Args:
        filepath: Pfad zur Datei
    
    Returns:
        str: SHA256-Hash (hex)
    """
    sha256_hash = hashlib.sha256()
    
    with open(filepath, "rb") as f:
        # Lese in Chunks für große Dateien
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    
    return sha256_hash.hexdigest()

def verify_file_integrity(filepath: str, expected_hash: str) -> bool:
    """
    Verifiziert Datei-Integrität via SHA256.
    
    Args:
        filepath: Pfad zur Datei
        expected_hash: Erwarteter SHA256-Hash
    
    Returns:
        bool: True wenn Hash übereinstimmt
    """
    actual_hash = compute_file_sha256(filepath)
    return actual_hash.lower() == expected_hash.lower()

# ==================== TAILSCALE IP DETECTION ====================
def is_tailscale_ip(ip_address: str) -> bool:
    """
    Prüft ob eine IP-Adresse aus dem Tailscale-Bereich kommt (100.64.0.0/10).
    
    Args:
        ip_address: IP-Adresse als String
    
    Returns:
        bool: True wenn Tailscale-IP
    """
    try:
        from ipaddress import ip_address as parse_ip, ip_network
        ip = parse_ip(ip_address)
        tailscale_network = ip_network('100.64.0.0/10')
        return ip in tailscale_network
    except:
        return False

def is_localhost(ip_address: str) -> bool:
    """
    Prüft ob eine IP-Adresse localhost ist.
    
    Args:
        ip_address: IP-Adresse als String
    
    Returns:
        bool: True wenn localhost
    """
    return ip_address in ('127.0.0.1', '::1', 'localhost')

# ==================== SESSION TOKEN ====================
def generate_session_token() -> str:
    """Generiert einen sicheren Session-Token"""
    return secrets.token_hex(32)
