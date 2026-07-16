"""Sicherheits-Helfer: Passwort-Hashing, Secret-Verschlüsselung (DPAPI),
Pfad-/ZIP-Validierung, Session-Token.

Aus game_server_manager.py ausgelagert.
"""

import os
import hashlib
import secrets
import zipfile

from gsm.constants import SENSITIVE_SERVER_KEYS


PBKDF2_ITERATIONS = 300000  # Hohe Iteration für Sicherheit

def hash_password(password):
    """
    Erstellt einen sicheren Hash des Passworts mit PBKDF2-HMAC-SHA256.
    Format: pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>
    """
    salt = secrets.token_bytes(32)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"

def verify_password(password, stored_hash):
    """
    Verifiziert ein Passwort gegen einen gespeicherten Hash.
    Unterstützt sowohl neues PBKDF2-Format als auch Legacy SHA-256.
    """
    if not stored_hash:
        return False
    
    # Neues PBKDF2-Format
    if stored_hash.startswith("pbkdf2_sha256$"):
        try:
            parts = stored_hash.split("$")
            if len(parts) != 4:
                return False
            _, iterations, salt_hex, hash_hex = parts
            salt = bytes.fromhex(salt_hex)
            expected_hash = bytes.fromhex(hash_hex)
            dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, int(iterations))
            return secrets.compare_digest(dk, expected_hash)
        except (ValueError, TypeError):
            return False
    
    # Legacy SHA-256 Format (für Abwärtskompatibilität)
    legacy_hash = hashlib.sha256(password.encode()).hexdigest()
    return secrets.compare_digest(legacy_hash, stored_hash)

def is_legacy_hash(stored_hash):
    """Prüft ob ein Hash im alten SHA-256 Format ist"""
    if not stored_hash:
        return False
    return not stored_hash.startswith("pbkdf2_sha256$")


# ==================== SECRET-VERSCHLÜSSELUNG (at-rest) ====================
# Server-Geheimnisse (RCON-/Admin-/Server-Passwörter) werden verschlüsselt in
# servers.json abgelegt. Unter Windows via DPAPI (an das Benutzerkonto gebunden,
# kein separater Schlüssel nötig). Auf anderen Plattformen bleibt der Wert als
# Klartext erhalten (dann gibt es keine at-rest-Verschlüsselung).
SECRET_ENC_PREFIX = "enc:v1:"

# Optionaler Zusatz-Entropie-Kontext für DPAPI (bindet Chiffre an diese App)
_DPAPI_ENTROPY = b"GameServerManager::servers"


def _dpapi_available():
    return os.name == "nt"


def _dpapi_protect(plaintext_bytes):
    """Verschlüsselt Bytes mit Windows DPAPI (CryptProtectData). Gibt Bytes zurück."""
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    def _to_blob(data):
        buf = ctypes.create_string_buffer(data, len(data))
        return DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), buf

    in_blob, _in_buf = _to_blob(plaintext_bytes)
    entropy_blob, _ent_buf = _to_blob(_DPAPI_ENTROPY)
    out_blob = DATA_BLOB()

    ok = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(in_blob), None, ctypes.byref(entropy_blob),
        None, None, 0, ctypes.byref(out_blob)
    )
    if not ok:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def _dpapi_unprotect(cipher_bytes):
    """Entschlüsselt DPAPI-Bytes (CryptUnprotectData). Gibt Bytes zurück."""
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    def _to_blob(data):
        buf = ctypes.create_string_buffer(data, len(data))
        return DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), buf

    in_blob, _in_buf = _to_blob(cipher_bytes)
    entropy_blob, _ent_buf = _to_blob(_DPAPI_ENTROPY)
    out_blob = DATA_BLOB()

    ok = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(in_blob), None, ctypes.byref(entropy_blob),
        None, None, 0, ctypes.byref(out_blob)
    )
    if not ok:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def encrypt_secret(value):
    """
    Verschlüsselt einen Geheimwert für die Ablage in servers.json.
    Rückgabe: 'enc:v1:<base64>' unter Windows, sonst der unveränderte Klartext.
    Bereits verschlüsselte oder leere Werte werden unverändert zurückgegeben.
    """
    if not value or not isinstance(value, str):
        return value
    if value.startswith(SECRET_ENC_PREFIX):
        return value
    if not _dpapi_available():
        return value  # Kein at-rest-Schutz auf dieser Plattform
    try:
        import base64
        cipher = _dpapi_protect(value.encode("utf-8"))
        return SECRET_ENC_PREFIX + base64.b64encode(cipher).decode("ascii")
    except Exception as e:
        print(f"⚠️ Konnte Geheimnis nicht verschlüsseln (bleibt Klartext): {e}")
        return value


def decrypt_secret(value):
    """
    Entschlüsselt einen Wert aus servers.json.
    Werte ohne 'enc:v1:'-Präfix gelten als Legacy-Klartext und werden unverändert
    zurückgegeben (werden beim nächsten Speichern automatisch migriert).
    """
    if not value or not isinstance(value, str):
        return value
    if not value.startswith(SECRET_ENC_PREFIX):
        return value  # Legacy-Klartext
    try:
        import base64
        cipher = base64.b64decode(value[len(SECRET_ENC_PREFIX):])
        return _dpapi_unprotect(cipher).decode("utf-8")
    except Exception as e:
        print(f"⚠️ Konnte Geheimnis nicht entschlüsseln: {e}")
        return value


def _encrypt_server_secrets(servers):
    """Gibt eine tiefe Kopie von servers zurück, in der sensible Felder verschlüsselt sind."""
    import copy
    result = copy.deepcopy(servers)
    for server_config in result.values():
        if not isinstance(server_config, dict):
            continue
        for key in SENSITIVE_SERVER_KEYS:
            if server_config.get(key):
                server_config[key] = encrypt_secret(server_config[key])
    return result


def _decrypt_server_secrets_inplace(servers):
    """Entschlüsselt sensible Felder im geladenen servers-Dict (in place)."""
    for server_config in servers.values():
        if not isinstance(server_config, dict):
            continue
        for key in SENSITIVE_SERVER_KEYS:
            if server_config.get(key):
                server_config[key] = decrypt_secret(server_config[key])
    return servers

# Pfad-Validierung für sichere Dateioperationen
ALLOWED_CONFIG_EXTENSIONS = {'.ini', '.cfg', '.json', '.yaml', '.yml', '.txt', '.conf'}

def is_safe_path(base_dir, requested_path):
    """
    Prüft ob ein Pfad sicher innerhalb eines Basisverzeichnisses liegt.
    Verhindert Path Traversal Angriffe (../ etc.)
    """
    try:
        # Absoluten Pfad berechnen
        base_real = os.path.realpath(base_dir)
        requested_real = os.path.realpath(requested_path)
        
        # Prüfen ob der angeforderte Pfad innerhalb des Basisverzeichnisses liegt
        return requested_real.startswith(base_real + os.sep) or requested_real == base_real
    except (ValueError, TypeError):
        return False

def validate_config_path(server_dir, file_path):
    """
    Validiert einen Config-Dateipfad für Read/Write-Operationen.
    Returns: (is_valid, error_message)
    """
    if not file_path:
        return False, "Kein Dateipfad angegeben"
    
    # Pfad normalisieren
    normalized_path = os.path.normpath(file_path)
    
    # Prüfen ob Pfad innerhalb des Server-Verzeichnisses liegt
    if not is_safe_path(server_dir, normalized_path):
        return False, "Zugriff verweigert: Pfad außerhalb des Server-Verzeichnisses"
    
    # Dateiendung prüfen
    _, ext = os.path.splitext(normalized_path)
    if ext.lower() not in ALLOWED_CONFIG_EXTENSIONS:
        return False, f"Nicht erlaubte Dateiendung: {ext}"
    
    return True, None

def validate_backup_path(backups_dir, server_id, backup_path):
    """
    Validiert einen Backup-Pfad für Restore/Delete-Operationen.
    Returns: (is_valid, error_message)
    """
    if not backup_path:
        return False, "Kein Backup-Pfad angegeben"
    
    if not backups_dir:
        return False, "Backup-Verzeichnis nicht konfiguriert"
    
    # Erwartetes Backup-Verzeichnis für diesen Server
    expected_backup_dir = os.path.join(backups_dir, server_id)
    
    # Pfade normalisieren (Windows: Backslash, lowercase für Vergleich)
    try:
        normalized_path = os.path.normcase(os.path.realpath(backup_path))
        expected_dir_real = os.path.normcase(os.path.realpath(expected_backup_dir))
    except (ValueError, TypeError, OSError):
        return False, "Ungültiger Pfad"
    
    # Prüfen ob Backup innerhalb des erlaubten Verzeichnisses liegt
    # os.path.normcase macht auf Windows alles lowercase
    if not normalized_path.startswith(expected_dir_real + os.sep) and normalized_path != expected_dir_real:
        return False, f"Zugriff verweigert: Backup außerhalb des erlaubten Verzeichnisses"
    
    # Prüfen ob es eine ZIP-Datei ist
    if not normalized_path.lower().endswith('.zip'):
        return False, "Nur ZIP-Backups erlaubt"
    
    return True, None

def safe_extract_zip(zip_path, target_dir):
    """
    Entpackt ein ZIP-Archiv sicher ohne Path Traversal.
    Returns: (success, error_message)
    """
    try:
        # Zielverzeichnis normalisieren
        target_real = os.path.normcase(os.path.realpath(target_dir))
        
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            for member in zipf.namelist():
                # ZIP verwendet immer Forward Slashes - konvertiere für OS
                member_normalized = member.replace('/', os.sep)
                member_path = os.path.normpath(member_normalized)
                
                # Prüfe auf absolute Pfade
                if os.path.isabs(member_path):
                    return False, f"Unsicheres ZIP: Absoluter Pfad gefunden: {member}"
                
                # Prüfe auf Path Traversal (..)
                # Splitten mit beiden möglichen Separatoren
                path_parts = member_path.replace('/', os.sep).replace('\\', os.sep).split(os.sep)
                if '..' in path_parts:
                    return False, f"Unsicheres ZIP: Path Traversal gefunden: {member}"
                
                # Berechne den finalen Pfad
                final_path = os.path.normcase(os.path.realpath(os.path.join(target_dir, member_path)))
                
                # Prüfe ob der finale Pfad innerhalb des Zielverzeichnisses liegt
                # Erlaube auch exakte Übereinstimmung für Verzeichnisse
                if not (final_path.startswith(target_real + os.sep) or final_path == target_real):
                    return False, f"Unsicheres ZIP: Pfad würde außerhalb extrahiert: {member}"
            
            # Alle Prüfungen bestanden - sicher extrahieren
            zipf.extractall(target_dir)
        
        return True, None
    except zipfile.BadZipFile:
        return False, "Ungültiges ZIP-Archiv"
    except Exception as e:
        return False, f"Fehler beim Entpacken: {str(e)}"

def generate_session_token():
    """Generiert einen sicheren Session-Token"""
    return secrets.token_hex(32)
