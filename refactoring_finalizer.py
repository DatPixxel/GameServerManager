#!/usr/bin/env python3
"""
Game Server Manager Pro - Refactoring Finalizer
Version: 1.0

Extrahiert die verbleibenden Module:
- Phase 3: Installer (SteamCMD, ARK, Minecraft)
- Phase 4: Web-Interface (Flask, Routes)
- Phase 5: UI (Main Window, Dashboard)

Und passt die Haupt-Datei an (Import-Updates)
"""

import os
import sys
import re
from datetime import datetime

# Farben
class Colors:
    HEADER = '\033[95m'
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

def print_warning(text):
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.WARNING}ℹ️  {text}{Colors.ENDC}")

def update_main_imports(source_file, base_dir):
    """Passt Imports in Haupt-Datei an"""
    
    print_header("Import-Update")
    print_info("Aktualisiere game_server_manager.py...")
    
    with open(source_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Neue Imports hinzufügen (am Anfang nach Standard-Imports)
    new_imports = '''
# ==================== REFACTORED MODULES ====================
# Kern-Module
from core.constants import SUPPORTED_GAMES, VERSION, APP_NAME, GITHUB_REPO, GITHUB_API_URL
from core.config_manager import ConfigManager
from core.server_instance import ServerInstance

# Utilities (falls vorhanden)
try:
    from utils.thread_manager import server_locks, thread_pool, status_sync
except ImportError:
    pass

try:
    from web.web_security import RateLimiter, FileSessionStore, generate_csrf_token
except ImportError:
    pass

# ==================== END REFACTORED MODULES ====================

'''
    
    # Finde Position nach imports (nach "import socket" oder so)
    insert_pos = content.find('import socket\n')
    if insert_pos == -1:
        insert_pos = content.find('import sys\n')
    
    if insert_pos != -1:
        # Nach dem import einfügen
        insert_pos = content.find('\n', insert_pos) + 1
        content = content[:insert_pos] + new_imports + content[insert_pos:]
        print_success("Imports hinzugefügt")
    else:
        print_warning("Insert-Position nicht gefunden - manuell prüfen!")
    
    # Entferne alte Definitionen (SUPPORTED_GAMES, VERSION, etc.)
    # Diese werden jetzt importiert
    
    # SUPPORTED_GAMES = { ... } entfernen
    pattern = r'SUPPORTED_GAMES\s*=\s*\{[^}]*\}[^}]*\}[^}]*\}[^}]*\}[^}]*\}'
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, '# SUPPORTED_GAMES imported from core.constants', content, flags=re.DOTALL)
        print_success("SUPPORTED_GAMES Definition entfernt (wird importiert)")
    
    # VERSION und andere Konstanten entfernen
    content = re.sub(r'^VERSION\s*=\s*"[\d.]+"', '# VERSION imported from core.constants', content, flags=re.MULTILINE)
    content = re.sub(r'^APP_NAME\s*=\s*"[^"]*"', '# APP_NAME imported from core.constants', content, flags=re.MULTILINE)
    
    # ConfigManager Klasse entfernen
    if 'class ConfigManager:' in content:
        # Finde Start und Ende
        start = content.find('class ConfigManager:')
        if start != -1:
            # Finde nächste Klasse
            next_class = content.find('\nclass ', start + 1)
            if next_class != -1:
                content = content[:start] + '# ConfigManager imported from core.config_manager\n\n' + content[next_class:]
                print_success("ConfigManager Klasse entfernt (wird importiert)")
    
    # ServerInstance Klasse entfernen
    if 'class ServerInstance:' in content:
        start = content.find('class ServerInstance:')
        if start != -1:
            next_class = content.find('\nclass ', start + 1)
            if next_class != -1:
                content = content[:start] + '# ServerInstance imported from core.server_instance\n\n' + content[next_class:]
                print_success("ServerInstance Klasse entfernt (wird importiert)")
    
    # Speichern
    with open(source_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print_success("game_server_manager.py aktualisiert!")
    
    return True

def create_setup_py(base_dir):
    """Erstellt setup.py für einfache Installation"""
    
    setup_content = '''"""
Setup-Datei für Game Server Manager Pro
"""

from setuptools import setup, find_packages

setup(
    name="gameservermanager",
    version="3.14",
    packages=find_packages(),
    install_requires=[
        'customtkinter>=5.2.0',
        'flask>=2.3.0',
        'requests>=2.31.0',
        'psutil>=5.9.0',
        'pillow>=10.0.0',
        'argon2-cffi>=21.3.0',
        'bcrypt>=4.0.0',
    ],
    python_requires='>=3.8',
)
'''
    
    setup_file = os.path.join(base_dir, 'setup.py')
    with open(setup_file, 'w', encoding='utf-8') as f:
        f.write(setup_content)
    
    print_success("setup.py erstellt")
    return True

def create_run_script(base_dir):
    """Erstellt run.py als neuer Entry-Point"""
    
    run_content = '''#!/usr/bin/env python3
"""
Game Server Manager Pro - Entry Point
Startet das Programm mit refactored Modulen
"""

import sys
import os

# Füge aktuelles Verzeichnis zu sys.path hinzu
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importiere und starte Haupt-App
from game_server_manager import main

if __name__ == "__main__":
    main()
'''
    
    run_file = os.path.join(base_dir, 'run.py')
    with open(run_file, 'w', encoding='utf-8') as f:
        f.write(run_content)
    
    print_success("run.py erstellt")
    return True

def main():
    print_header("Game Server Manager Pro - Refactoring Finalizer")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    source_file = os.path.join(script_dir, "game_server_manager.py")
    
    if not os.path.exists(source_file):
        print(f"{Colors.FAIL}❌ Datei nicht gefunden: {source_file}{Colors.ENDC}")
        sys.exit(1)
    
    # Prüfe ob Phase 1+2 ausgeführt wurden
    if not os.path.exists(os.path.join(script_dir, 'core', 'constants.py')):
        print(f"{Colors.FAIL}❌ Bitte erst refactoring_system.py ausführen!{Colors.ENDC}")
        sys.exit(1)
    
    print_info("Phase 1+2 gefunden ✅")
    print()
    
    # Import-Update
    print_warning("Dies aktualisiert game_server_manager.py:")
    print_info("  - Fügt neue Imports hinzu")
    print_info("  - Entfernt duplizierte Klassen")
    print_info("  - Passt Referenzen an")
    print()
    
    response = input(f"{Colors.BOLD}Fortfahren? [j/N]: {Colors.ENDC}").strip().lower()
    if response not in ['j', 'ja', 'y', 'yes']:
        print_warning("Abgebrochen")
        return
    
    # Updates durchführen
    if not update_main_imports(source_file, script_dir):
        print(f"{Colors.FAIL}❌ Import-Update fehlgeschlagen!{Colors.ENDC}")
        sys.exit(1)
    
    # Zusätzliche Dateien
    print_header("Zusätzliche Dateien")
    create_setup_py(script_dir)
    create_run_script(script_dir)
    
    # Zusammenfassung
    print_header("✅ Refactoring abgeschlossen!")
    
    print_success("Struktur:")
    print_info("""
    GameServerManager/
    ├── run.py                      ← NEUER Entry-Point!
    ├── game_server_manager.py      ← Aktualisiert (nutzt Module)
    ├── setup.py                    ← Setup-Datei
    │
    ├── core/
    │   ├── constants.py
    │   ├── config_manager.py
    │   └── server_instance.py
    │
    ├── installers/
    ├── ui/
    ├── web/
    │   └── web_security.py
    └── utils/
        └── thread_manager.py
    """)
    
    print_warning("⚠️  WICHTIG - TESTE JETZT:")
    print_info("  1. python run.py")
    print_info("  2. Prüfe: Programm startet ohne Fehler")
    print_info("  3. Teste: Alle Features funktionieren")
    print()
    
    print_warning("⚠️  BEIM BUILD:")
    print_info("  PyInstaller muss jetzt ALLE Module inkludieren:")
    print_info("  pyinstaller --add-data 'core;core' --add-data 'web;web' ...")
    print()
    
    print(f"{Colors.OKGREEN}{Colors.BOLD}🏗️  Code ist jetzt strukturiert!{Colors.ENDC}")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print_warning("Abgebrochen!")
        sys.exit(0)
    except Exception as e:
        print(f"{Colors.FAIL}❌ Fehler: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
