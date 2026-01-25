"""
Game Server Manager Pro - Security Patches
Sichere Ersatz-Implementierungen für kritische Funktionen

Diese Datei enthält sichere Versionen der Funktionen aus game_server_manager.py
die Sicherheitsprobleme hatten.
"""

import os
import subprocess
import logging
from typing import List, Dict, Optional, Any
from security_utils import (
    safe_join, safe_extract, validate_port, validate_mod_ids,
    validate_server_name, validate_map_param, is_config_file_allowed,
    PathTraversalError, InvalidInputError, ZipSlipError
)

logger = logging.getLogger(__name__)

# ==================== SERVERINSTANCE - SICHERE METHODEN ====================

def build_start_command_secure(server_instance) -> List[str]:
    """
    Sichere Version von build_start_command - gibt Argumentliste zurück (kein String).
    Verhindert Command Injection durch Verwendung von shell=False.
    """
    from game_server_manager import SUPPORTED_GAMES  # Import aus Hauptdatei
    
    config = server_instance.config
    game_info = SUPPORTED_GAMES.get(config["game"], {})
    exe_path = server_instance.get_exe_path()
    
    # Basis-Argumentliste
    cmd_args = [exe_path]
    
    # Game-spezifische Parameter
    if config["game"] == "ARK: Survival Ascended":
        # Validierung
        map_param = config.get("map", "TheIsland_WP")
        allowed_maps = [m['param'] for m in game_info.get('maps', [])]
        map_param = validate_map_param(map_param, allowed_maps)
        
        session_name = validate_server_name(config.get("name", "MyServer"))
        port = validate_port(config.get("port", 7777))
        query_port = validate_port(config.get("query_port", 27015))
        
        # Map Parameter
        cmd_args.append(f"{map_param}?listen?SessionName={session_name}")
        
        # Port Parameter
        cmd_args.append(f"-Port={port}")
        cmd_args.append(f"-QueryPort={query_port}")
        
        # Mods (validiert)
        mods = config.get("mods", [])
        if mods:
            # Validiere Mod-IDs
            mod_ids_str = ','.join(str(m) for m in mods)
            validated_mods = validate_mod_ids(mod_ids_str)
            if validated_mods:
                cmd_args.append(f"-mods={','.join(validated_mods)}")
    
    elif config["game"] == "Rust":
        # Rust: Verwende vordefinierte Parameter (keine User-Input-Interpolation)
        port = validate_port(config.get("port", 28015))
        max_players = int(config.get("max_players", 10))
        server_name = validate_server_name(config.get("name", "My Server"))
        
        cmd_args.extend([
            "-batchmode",
            f"+server.port", str(port),
            "+server.level", "Procedural Map",
            "+server.seed", "1234",
            "+server.worldsize", "4000",
            "+server.maxplayers", str(max_players),
            "+server.hostname", server_name
        ])
    
    # Weitere Spiele analog behandeln...
    else:
        # Generischer Fall: Nur vordefinierte Parameter verwenden
        logger.warning(f"⚠️ Generischer Start für {config['game']} - keine User-Parameter")
    
    return cmd_args

def start_server_secure(server_instance) -> bool:
    """
    Sichere Version von start() - verwendet subprocess ohne shell=True.
    """
    if server_instance.is_running():
        server_instance.log("⚠️ Server läuft bereits!")
        return False
    
    if not server_instance.is_installed():
        server_instance.log("❌ Server nicht installiert!")
        return False
    
    try:
        cmd_args = build_start_command_secure(server_instance)
        server_instance.log(f"🚀 Starte: {' '.join(cmd_args)}")
        
        # WICHTIG: shell=False mit Argumentliste
        server_instance.process = subprocess.Popen(
            cmd_args,
            cwd=server_instance.get_server_dir(),
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        import time
        server_instance.start_time = time.time()
        server_instance.monitoring_active = True
        server_instance.log(f"✅ Server gestartet (PID: {server_instance.process.pid})")
        
        # Discord-Benachrichtigung
        if server_instance.discord_notifier:
            server_instance.discord_notifier.notify_server_start(server_instance.config.get("name", "Server"))
        
        # Monitoring & Auto-Backup
        import threading
        threading.Thread(target=server_instance._monitor, daemon=True).start()
        server_instance.start_auto_backup()
        
        return True
        
    except Exception as e:
        logger.exception(f"❌ Start fehlgeschlagen")
        server_instance.log(f"❌ Start fehlgeschlagen: {str(e)}")
        return False

def update_server_secure(server_instance, progress_callback=None) -> bool:
    """
    Sichere Version von update_server() - SteamCMD ohne shell=True.
    """
    try:
        from game_server_manager import PATHS, SUPPORTED_GAMES
        
        was_running = server_instance.is_running()
        if was_running:
            server_instance.log("⏹ Stoppe Server für Update...")
            server_instance.stop()
            import time
            time.sleep(3)
        
        game_info = SUPPORTED_GAMES.get(server_instance.config["game"], {})
        app_id = game_info.get("app_id")
        
        if not app_id:
            server_instance.log("❌ Kein SteamCMD App-ID für dieses Spiel")
            return False
        
        # SteamCMD-Pfad
        steamcmd_path = os.path.join(PATHS["steamcmd"], "steamcmd.exe")
        if not os.path.exists(steamcmd_path):
            server_instance.log("❌ SteamCMD nicht gefunden!")
            return False
        
        server_dir = server_instance.get_server_dir()
        
        # Login-Befehl: anonymous oder mit Credentials (aus ENV)
        steam_user = os.environ.get('STEAM_USER', 'anonymous')
        steam_pass = os.environ.get('STEAM_PASSWORD', '')
        
        # WICHTIG: Argumentliste statt String-Interpolation
        cmd_args = [
            steamcmd_path,
            "+force_install_dir", server_dir,
            "+login", steam_user
        ]
        
        # Passwort nur wenn nicht anonymous
        if steam_user != 'anonymous' and steam_pass:
            cmd_args.append(steam_pass)
            logger.info("🔐 SteamCMD mit Credentials (aus ENV)")
        
        cmd_args.extend([
            "+app_update", app_id, "validate",
            "+quit"
        ])
        
        server_instance.log("📥 SteamCMD läuft...")
        
        # WICHTIG: shell=False
        process = subprocess.Popen(
            cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        # Fortschritt lesen
        for line in process.stdout:
            line = line.strip()
            if line:
                if "progress:" in line.lower() or "downloading" in line.lower():
                    server_instance.log(f"  {line}")
                if progress_callback and "%" in line:
                    import re
                    match = re.search(r'(\d+(?:\.\d+)?)\s*%', line)
                    if match:
                        try:
                            progress_callback(float(match.group(1)))
                        except:
                            pass
        
        process.wait()
        
        if process.returncode == 0:
            server_instance.log("✅ Server erfolgreich aktualisiert!")
            
            if was_running:
                server_instance.log("▶️ Starte Server wieder...")
                import time
                time.sleep(2)
                server_instance.start()
            
            return True
        else:
            server_instance.log(f"❌ Update fehlgeschlagen (Exit Code: {process.returncode})")
            return False
            
    except Exception as e:
        logger.exception("❌ Update-Fehler")
        server_instance.log(f"❌ Update-Fehler: {str(e)}")
        return False

def restore_backup_secure(server_instance, backup_path: str) -> bool:
    """
    Sichere Version von restore_backup() - mit Zip-Slip Protection.
    """
    try:
        if server_instance.is_running():
            server_instance.log("⚠️ Server muss gestoppt sein für Wiederherstellung!")
            return False
        
        server_instance.log(f"🔄 Stelle Backup wieder her: {os.path.basename(backup_path)}")
        
        server_dir = server_instance.get_server_dir()
        
        # WICHTIG: safe_extract statt zipfile.extractall
        safe_extract(
            backup_path,
            server_dir,
            max_files=50000,
            max_size=50*1024*1024*1024  # 50 GB Limit
        )
        
        server_instance.log("✅ Backup erfolgreich wiederhergestellt!")
        return True
        
    except ZipSlipError as e:
        logger.error(f"🚨 Zip-Slip Angriff erkannt: {e}")
        server_instance.log(f"❌ Backup enthält ungültige Pfade: {e.message}")
        return False
    except Exception as e:
        logger.exception("❌ Wiederherstellung fehlgeschlagen")
        server_instance.log(f"❌ Wiederherstellung fehlgeschlagen: {str(e)}")
        return False

def delete_backup_secure(server_instance, backup_filename: str) -> bool:
    """
    Sichere Version von delete_backup() - validiert Pfad gegen Backup-Verzeichnis.
    """
    try:
        from game_server_manager import PATHS
        
        # Backup-Verzeichnis für diesen Server
        server_backup_dir = os.path.join(PATHS["backups"], server_instance.server_id)
        
        # WICHTIG: safe_join verhindert Pfad-Traversal
        backup_path = safe_join(server_backup_dir, backup_filename)
        
        # Zusätzliche Prüfung: Datei muss .zip sein
        if not backup_path.endswith('.zip'):
            raise InvalidInputError("Nur .zip-Dateien können gelöscht werden")
        
        # Prüfe ob Datei existiert
        if not os.path.exists(backup_path):
            server_instance.log("❌ Backup nicht gefunden")
            return False
        
        os.remove(backup_path)
        server_instance.log(f"🗑️ Backup gelöscht: {os.path.basename(backup_path)}")
        return True
        
    except (PathTraversalError, InvalidInputError) as e:
        logger.error(f"🚨 Ungültiger Backup-Pfad: {e}")
        server_instance.log(f"❌ Ungültiger Backup-Pfad")
        return False
    except Exception as e:
        logger.exception("❌ Löschen fehlgeschlagen")
        server_instance.log(f"❌ Löschen fehlgeschlagen: {str(e)}")
        return False

# ==================== API-ROUTES - SICHERE VERSIONEN ====================

def api_read_config_secure(server_id: str, request_data: Dict) -> Dict:
    """
    Sichere Version von /api/server/<id>/config/read.
    Verwendet safe_join und Whitelist.
    """
    from game_server_manager import PATHS
    
    try:
        file_path = request_data.get('file_path', '')
        
        if not file_path:
            return {
                'success': False,
                'error_code': 'MISSING_FILE_PATH',
                'message': 'file_path fehlt'
            }
        
        # Server-Verzeichnis
        server_dir = os.path.join(PATHS["servers"], server_id)
        
        # WICHTIG: safe_join statt direkter Pfad-Verwendung
        # Extrahiere relativen Pfad aus absolutem Pfad (falls vorhanden)
        if os.path.isabs(file_path):
            # Versuche relativen Pfad zu extrahieren
            try:
                rel_path = os.path.relpath(file_path, server_dir)
            except ValueError:
                return {
                    'success': False,
                    'error_code': 'INVALID_PATH',
                    'message': 'Absolute Pfade nicht erlaubt'
                }
        else:
            rel_path = file_path
        
        safe_path = safe_join(server_dir, rel_path)
        
        # Whitelist-Prüfung
        if not is_config_file_allowed(safe_path):
            return {
                'success': False,
                'error_code': 'FILE_NOT_ALLOWED',
                'message': 'Dateityp nicht erlaubt'
            }
        
        # Existenz-Prüfung
        if not os.path.exists(safe_path):
            return {
                'success': False,
                'error_code': 'FILE_NOT_FOUND',
                'message': 'Datei nicht gefunden'
            }
        
        # Lese Datei
        with open(safe_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        return {
            'success': True,
            'content': content,
            'file_path': safe_path
        }
        
    except PathTraversalError as e:
        logger.error(f"🚨 Pfad-Traversal Versuch: {e}")
        return {
            'success': False,
            'error_code': 'PATH_TRAVERSAL',
            'message': 'Pfad-Traversal erkannt'
        }
    except Exception as e:
        logger.exception("❌ Config-Read Fehler")
        return {
            'success': False,
            'error_code': 'READ_ERROR',
            'message': str(e)
        }

def api_save_config_secure(server_id: str, request_data: Dict) -> Dict:
    """
    Sichere Version von /api/server/<id>/config/save.
    Verwendet safe_join und Whitelist.
    """
    from game_server_manager import PATHS
    
    try:
        file_path = request_data.get('file_path', '')
        content = request_data.get('content', '')
        
        if not file_path:
            return {
                'success': False,
                'error_code': 'MISSING_FILE_PATH',
                'message': 'file_path fehlt'
            }
        
        # Server-Verzeichnis
        server_dir = os.path.join(PATHS["servers"], server_id)
        
        # WICHTIG: safe_join
        if os.path.isabs(file_path):
            try:
                rel_path = os.path.relpath(file_path, server_dir)
            except ValueError:
                return {
                    'success': False,
                    'error_code': 'INVALID_PATH',
                    'message': 'Absolute Pfade nicht erlaubt'
                }
        else:
            rel_path = file_path
        
        safe_path = safe_join(server_dir, rel_path)
        
        # Whitelist-Prüfung
        if not is_config_file_allowed(safe_path):
            return {
                'success': False,
                'error_code': 'FILE_NOT_ALLOWED',
                'message': 'Dateityp nicht erlaubt'
            }
        
        # Erstelle Verzeichnis falls nötig
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        
        # Schreibe Datei
        with open(safe_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"✅ Config gespeichert: {safe_path}")
        return {
            'success': True,
            'message': 'Gespeichert!',
            'file_path': safe_path
        }
        
    except PathTraversalError as e:
        logger.error(f"🚨 Pfad-Traversal Versuch: {e}")
        return {
            'success': False,
            'error_code': 'PATH_TRAVERSAL',
            'message': 'Pfad-Traversal erkannt'
        }
    except Exception as e:
        logger.exception("❌ Config-Save Fehler")
        return {
            'success': False,
            'error_code': 'SAVE_ERROR',
            'message': str(e)
        }

def api_restore_backup_secure(server_id: str, request_data: Dict, server_instances: Dict) -> Dict:
    """
    Sichere Version von /api/server/<id>/backups/restore.
    Verwendet nur Backup-Filename statt vollem Pfad.
    """
    from game_server_manager import PATHS
    
    try:
        instance = server_instances.get(server_id)
        if not instance:
            return {
                'success': False,
                'error_code': 'SERVER_NOT_FOUND',
                'message': 'Server nicht gefunden'
            }
        
        if instance.is_running():
            return {
                'success': False,
                'error_code': 'SERVER_RUNNING',
                'message': 'Server muss gestoppt sein!'
            }
        
        # WICHTIG: Nur Filename akzeptieren, nicht backup_path
        backup_filename = request_data.get('backup_filename') or request_data.get('backup_path', '')
        
        # Falls backup_path übergeben wurde, extrahiere Filename
        if os.path.isabs(backup_filename):
            backup_filename = os.path.basename(backup_filename)
        
        if not backup_filename:
            return {
                'success': False,
                'error_code': 'MISSING_BACKUP',
                'message': 'backup_filename fehlt'
            }
        
        # Konstruiere sicheren Pfad
        server_backup_dir = os.path.join(PATHS["backups"], server_id)
        backup_path = safe_join(server_backup_dir, backup_filename)
        
        if not os.path.exists(backup_path):
            return {
                'success': False,
                'error_code': 'BACKUP_NOT_FOUND',
                'message': 'Backup nicht gefunden'
            }
        
        if restore_backup_secure(instance, backup_path):
            return {
                'success': True,
                'message': 'Backup wiederhergestellt!'
            }
        else:
            return {
                'success': False,
                'error_code': 'RESTORE_FAILED',
                'message': 'Wiederherstellung fehlgeschlagen'
            }
            
    except PathTraversalError as e:
        logger.error(f"🚨 Pfad-Traversal Versuch: {e}")
        return {
            'success': False,
            'error_code': 'PATH_TRAVERSAL',
            'message': 'Ungültiger Backup-Pfad'
        }
    except Exception as e:
        logger.exception("❌ Restore Fehler")
        return {
            'success': False,
            'error_code': 'RESTORE_ERROR',
            'message': str(e)
        }

def api_delete_backup_secure(server_id: str, request_data: Dict, server_instances: Dict) -> Dict:
    """
    Sichere Version von /api/server/<id>/backups/delete.
    Verwendet nur Backup-Filename statt vollem Pfad.
    """
    try:
        instance = server_instances.get(server_id)
        if not instance:
            return {
                'success': False,
                'error_code': 'SERVER_NOT_FOUND',
                'message': 'Server nicht gefunden'
            }
        
        # WICHTIG: Nur Filename akzeptieren
        backup_filename = request_data.get('backup_filename') or request_data.get('backup_path', '')
        
        # Falls backup_path übergeben wurde, extrahiere Filename
        if os.path.isabs(backup_filename):
            backup_filename = os.path.basename(backup_filename)
        
        if not backup_filename:
            return {
                'success': False,
                'error_code': 'MISSING_BACKUP',
                'message': 'backup_filename fehlt'
            }
        
        if delete_backup_secure(instance, backup_filename):
            return {
                'success': True,
                'message': 'Backup gelöscht!'
            }
        else:
            return {
                'success': False,
                'error_code': 'DELETE_FAILED',
                'message': 'Löschen fehlgeschlagen'
            }
            
    except Exception as e:
        logger.exception("❌ Delete Fehler")
        return {
            'success': False,
            'error_code': 'DELETE_ERROR',
            'message': str(e)
        }
