#!/usr/bin/env python3
"""
Game Server Manager Pro - Refactoring System
Version: 1.0
Datum: 2026-01-25

Refactored 12.000 Zeilen Monolith in saubere Modul-Struktur.

Phasen:
1. Vorbereitung (Ordner-Struktur)
2. Kern-Module (constants, config_manager, server_instance)
3. Installer (steamcmd, ark, minecraft, etc.)
4. Web-Interface (flask app, routes)
5. UI-Module (main_window, dashboard, dialogs)

WICHTIG: Erstellt Backup und arbeitet schrittweise!
"""

import os
import sys
import shutil
import json
from datetime import datetime

# Farben
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(70)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")

def create_backup(file_path):
    """Erstellt Backup"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.refactoring_backup_{timestamp}"
    
    try:
        shutil.copy2(file_path, backup_path)
        print_success(f"Backup: {backup_path}")
        return backup_path
    except Exception as e:
        print_error(f"Backup fehlgeschlagen: {e}")
        return None

def create_directory_structure(base_dir):
    """Erstellt Ordner-Struktur"""
    
    structure = {
        'core': 'Kern-Logik (ServerInstance, ConfigManager, etc.)',
        'installers': 'Server-Installer (SteamCMD, ARK, Minecraft, etc.)',
        'ui': 'GUI-Komponenten (Hauptfenster, Dashboard, Dialoge)',
        'web': 'Web-Interface (Flask App, Routes, Templates)',
        'utils': 'Utilities (RCON, Discord, Updater, Security)'
    }
    
    print_info("Erstelle Ordner-Struktur...")
    
    for folder, description in structure.items():
        folder_path = os.path.join(base_dir, folder)
        os.makedirs(folder_path, exist_ok=True)
        
        # __init__.py erstellen
        init_file = os.path.join(folder_path, '__init__.py')
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write(f'"""{description}"""\n')
        
        print_success(f"  {folder}/ erstellt")
    
    return True

def extract_constants(source_file, target_dir):
    """Extrahiert SUPPORTED_GAMES und andere Konstanten"""
    
    print_info("Extrahiere constants.py...")
    
    with open(source_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Finde SUPPORTED_GAMES Block
    start_line = None
    end_line = None
    
    for i, line in enumerate(lines):
        if 'SUPPORTED_GAMES = {' in line:
            start_line = i
        if start_line is not None and line.strip() == '}' and i > start_line + 100:
            end_line = i + 1
            break
    
    if not start_line or not end_line:
        print_error("SUPPORTED_GAMES nicht gefunden!")
        return False
    
    # Extrahiere auch andere Konstanten
    constants_content = '''"""
Konstanten für Game Server Manager Pro
Enthält SUPPORTED_GAMES und andere globale Definitionen
"""

VERSION = "3.14"
APP_NAME = "Game Server Manager Pro"

# GitHub für Auto-Updates
GITHUB_REPO = "DatPixxel/GameServerManager"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

'''
    
    # SUPPORTED_GAMES hinzufügen
    constants_content += ''.join(lines[start_line:end_line])
    constants_content += '\n'
    
    # Speichern
    target_file = os.path.join(target_dir, 'core', 'constants.py')
    with open(target_file, 'w', encoding='utf-8') as f:
        f.write(constants_content)
    
    print_success(f"  constants.py erstellt ({end_line - start_line} Zeilen)")
    
    return {
        'file': target_file,
        'removed_lines': (start_line, end_line)
    }

def extract_config_manager(source_file, target_dir):
    """Extrahiert ConfigManager Klasse"""
    
    print_info("Extrahiere config_manager.py...")
    
    with open(source_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Finde ConfigManager Klasse
    start_line = None
    end_line = None
    
    for i, line in enumerate(lines):
        if 'class ConfigManager:' in line:
            start_line = i
        if start_line and i > start_line and line.startswith('class ') and 'ConfigManager' not in line:
            end_line = i
            break
    
    if not start_line:
        print_error("ConfigManager Klasse nicht gefunden!")
        return False
    
    if not end_line:
        # Bis Ende der Datei oder nächste Hauptklasse
        end_line = len(lines)
    
    # Extrahiere
    config_content = '''"""
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

'''
    
    # Klasse hinzufügen
    config_content += ''.join(lines[start_line:end_line])
    
    # Speichern
    target_file = os.path.join(target_dir, 'core', 'config_manager.py')
    with open(target_file, 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    print_success(f"  config_manager.py erstellt ({end_line - start_line} Zeilen)")
    
    return {
        'file': target_file,
        'removed_lines': (start_line, end_line)
    }

def extract_server_instance(source_file, target_dir):
    """Extrahiert ServerInstance Klasse"""
    
    print_info("Extrahiere server_instance.py...")
    
    with open(source_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Finde ServerInstance Klasse
    start_line = None
    end_line = None
    
    for i, line in enumerate(lines):
        if 'class ServerInstance:' in line:
            start_line = i
        if start_line and i > start_line and line.startswith('class ') and 'ServerInstance' not in line:
            end_line = i
            break
    
    if not start_line:
        print_error("ServerInstance Klasse nicht gefunden!")
        return False
    
    if not end_line:
        end_line = len(lines)
    
    # Extrahiere
    server_content = '''"""
Server Instance für Game Server Manager Pro
Repräsentiert einen einzelnen Game-Server
"""

import os
import subprocess
import threading
import time
import psutil
import zipfile
import shutil
from datetime import datetime, timedelta

'''
    
    # Klasse hinzufügen
    server_content += ''.join(lines[start_line:end_line])
    
    # Speichern
    target_file = os.path.join(target_dir, 'core', 'server_instance.py')
    with open(target_file, 'w', encoding='utf-8') as f:
        f.write(server_content)
    
    print_success(f"  server_instance.py erstellt ({end_line - start_line} Zeilen)")
    
    return {
        'file': target_file,
        'removed_lines': (start_line, end_line)
    }

def create_refactoring_state(base_dir):
    """Erstellt State-Datei für schrittweises Refactoring"""
    
    state = {
        'version': '1.0',
        'started': datetime.now().isoformat(),
        'current_phase': 0,
        'phases': [
            {
                'id': 1,
                'name': 'Vorbereitung',
                'status': 'pending',
                'steps': ['directory_structure']
            },
            {
                'id': 2,
                'name': 'Kern-Module',
                'status': 'pending',
                'steps': ['constants', 'config_manager', 'server_instance']
            },
            {
                'id': 3,
                'name': 'Installer',
                'status': 'pending',
                'steps': ['steamcmd', 'ark', 'minecraft', 'others']
            },
            {
                'id': 4,
                'name': 'Web-Interface',
                'status': 'pending',
                'steps': ['flask_app', 'routes', 'templates']
            },
            {
                'id': 5,
                'name': 'UI-Module',
                'status': 'pending',
                'steps': ['main_window', 'dashboard', 'dialogs']
            }
        ],
        'extracted_modules': [],
        'backup_file': None
    }
    
    state_file = os.path.join(base_dir, 'refactoring_state.json')
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)
    
    return state_file

def main():
    print_header("Game Server Manager Pro - Refactoring System")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    source_file = os.path.join(script_dir, "game_server_manager.py")
    
    if not os.path.exists(source_file):
        print_error(f"Datei nicht gefunden: {source_file}")
        sys.exit(1)
    
    print_info(f"Quell-Datei: {source_file}")
    
    # Warnung
    print_header("⚠️  WICHTIGER HINWEIS")
    print_warning("Dieses Refactoring ist EXPERIMENTELL!")
    print_info("Es wird empfohlen:")
    print_info("  1. Aktuellen Stand in Git committen")
    print_info("  2. Separates Backup erstellen")
    print_info("  3. Nach jeder Phase testen")
    print()
    
    response = input(f"{Colors.BOLD}Trotzdem fortfahren? [j/N]: {Colors.ENDC}").strip().lower()
    if response not in ['j', 'ja', 'y', 'yes']:
        print_warning("Abgebrochen")
        return
    
    # Backup
    print_header("Schritt 1: Backup erstellen")
    backup_path = create_backup(source_file)
    if not backup_path:
        sys.exit(1)
    
    # Ordner-Struktur
    print_header("Schritt 2: Ordner-Struktur erstellen")
    if not create_directory_structure(script_dir):
        sys.exit(1)
    
    # State erstellen
    state_file = create_refactoring_state(script_dir)
    print_success(f"State-Datei: {state_file}")
    
    # Phase 2: Kern-Module extrahieren
    print_header("Schritt 3: Kern-Module extrahieren")
    
    print()
    print(f"{Colors.WARNING}Dies extrahiert die wichtigsten Klassen:{Colors.ENDC}")
    print_info("  - constants.py (SUPPORTED_GAMES)")
    print_info("  - config_manager.py (ConfigManager)")
    print_info("  - server_instance.py (ServerInstance)")
    print()
    response = input(f"{Colors.BOLD}Fortfahren? [j/N]: {Colors.ENDC}").strip().lower()
    
    if response in ['j', 'ja', 'y', 'yes']:
        # Constants
        result = extract_constants(source_file, script_dir)
        if result:
            print_success("✅ constants.py extrahiert")
        
        # ConfigManager  
        result = extract_config_manager(source_file, script_dir)
        if result:
            print_success("✅ config_manager.py extrahiert")
        
        # ServerInstance
        result = extract_server_instance(source_file, script_dir)
        if result:
            print_success("✅ server_instance.py extrahiert")
    
    # Zusammenfassung
    print_header("✅ Refactoring Phase 1+2 abgeschlossen!")
    
    print_success("Erstellt:")
    print_info("  📁 core/")
    print_info("     ├── __init__.py")
    print_info("     ├── constants.py")
    print_info("     ├── config_manager.py")
    print_info("     └── server_instance.py")
    print_info("  📁 installers/")
    print_info("  📁 ui/")
    print_info("  📁 web/")
    print_info("  📁 utils/")
    print()
    
    print_warning("⚠️  NÄCHSTE SCHRITTE:")
    print_info("  1. Nutze 'refactoring_finalizer.py' um den Rest zu machen")
    print_info("  2. Oder: Entwickle weiter mit der Modul-Struktur")
    print_info("  3. Alte game_server_manager.py muss imports anpassen")
    print()
    
    print(f"{Colors.OKGREEN}{Colors.BOLD}🏗️  Basis-Struktur steht!{Colors.ENDC}")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print_warning("Abgebrochen!")
        sys.exit(0)
    except Exception as e:
        print_error(f"Fehler: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
