#!/usr/bin/env python3
"""
Game Server Manager Pro - Bug Fix Patch
Version: 1.0
Datum: 2026-01-25

Behebt 4 kritische Bugs:
1. restore_backup / delete_backup: self.id → self.server_id
2. import_server_config: Falsche ServerInstance Parameter
3. save_settings: self.web_label existiert nicht
4. _auto_refresh_dashboard: auto_refresh_label → _dashboard_refresh_id

WICHTIG: Erstellt automatisch Backup vor Patch!
"""

import os
import sys
import shutil
from datetime import datetime

# Farben für Terminal
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
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")

def create_backup(file_path):
    """Erstellt Backup der Datei"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.backup_{timestamp}"
    
    try:
        shutil.copy2(file_path, backup_path)
        print_success(f"Backup erstellt: {backup_path}")
        return backup_path
    except Exception as e:
        print_error(f"Backup fehlgeschlagen: {e}")
        return None

def apply_fixes(file_path):
    """Wendet alle Bug-Fixes an"""
    
    print_info("Lese Datei...")
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    total_lines = len(lines)
    fixes_applied = 0
    
    # BUG FIX 1: restore_backup - self.id → self.server_id (Zeile 2162)
    print_info("Bug Fix 1: restore_backup (Zeile 2162)")
    if total_lines > 2161:
        original = lines[2161]
        if 'validate_backup_path(PATHS["backups"], self.id, backup_path)' in original:
            lines[2161] = original.replace('self.id', 'self.server_id')
            print_success(f"  Zeile 2162: self.id → self.server_id")
            fixes_applied += 1
        else:
            print_warning("  Zeile 2162: Bereits gefixt oder Code geändert")
    
    # BUG FIX 2: delete_backup - self.id → self.server_id (Zeile 2193)
    print_info("Bug Fix 2: delete_backup (Zeile 2193)")
    if total_lines > 2192:
        original = lines[2192]
        if 'validate_backup_path(PATHS["backups"], self.id, backup_path)' in original:
            lines[2192] = original.replace('self.id', 'self.server_id')
            print_success(f"  Zeile 2193: self.id → self.server_id")
            fixes_applied += 1
        else:
            print_warning("  Zeile 2193: Bereits gefixt oder Code geändert")
    
    # BUG FIX 3: import_server_config - ServerInstance Parameter (Zeilen 7259-7265)
    print_info("Bug Fix 3: import_server_config (Zeilen 7259-7265)")
    if total_lines > 7264:
        # Suche nach dem fehlerhaften Block
        found_block = False
        for i in range(7258, min(7268, total_lines)):
            if 'self.server_instances[new_id] = ServerInstance(' in lines[i]:
                # Prüfe ob der falsche Code noch da ist
                block = ''.join(lines[i:min(i+7, total_lines)])
                if 'game_info,' in block and 'self.config_manager.get_text,' in block:
                    # Ersetze den kompletten Block (7 Zeilen)
                    lines[i] = '                self.server_instances[new_id] = ServerInstance(\n'
                    lines[i+1] = '                    new_id,\n'
                    lines[i+2] = '                    server_config,\n'
                    lines[i+3] = '                    self.config_manager,\n'
                    lines[i+4] = '                    discord_notifier=self.discord_notifier\n'
                    lines[i+5] = '                )\n'
                    lines[i+6] = '                \n'
                    print_success(f"  Zeilen 7259-7265: Parameter korrigiert")
                    print_info("    Entfernt: game_info, self.config_manager.get_text")
                    print_info("    Korrigiert: self.config_manager als 3. Parameter")
                    fixes_applied += 1
                    found_block = True
                    break
        
        if not found_block:
            print_warning("  Zeilen 7259-7265: Bereits gefixt oder Code geändert")
    
    # BUG FIX 4: save_settings - self.web_label entfernen (Zeile 7578)
    print_info("Bug Fix 4: save_settings (Zeile 7578)")
    if total_lines > 7577:
        original = lines[7577]
        if 'self.web_label.configure(text=f"🌐 localhost:{new_port}")' in original:
            # Kommentiere die Zeile aus statt zu löschen
            lines[7577] = '            # TODO: web_label als Attribut speichern oder entfernen\n'
            lines[7577] += '            # self.web_label.configure(text=f"🌐 localhost:{new_port}")\n'
            print_success(f"  Zeile 7578: self.web_label auskommentiert")
            print_info("    Grund: web_label wird nie als self.web_label gespeichert")
            fixes_applied += 1
        else:
            print_warning("  Zeile 7578: Bereits gefixt oder Code geändert")
    
    # BUG FIX 5: _auto_refresh_dashboard - auto_refresh_label → _dashboard_refresh_id (Zeile 4798)
    print_info("Bug Fix 5: _auto_refresh_dashboard (Zeile 4798)")
    if total_lines > 4797:
        original = lines[4797]
        if "hasattr(self, 'auto_refresh_label')" in original:
            lines[4797] = original.replace("'auto_refresh_label'", "'_dashboard_refresh_id'")
            print_success(f"  Zeile 4798: auto_refresh_label → _dashboard_refresh_id")
            fixes_applied += 1
        else:
            print_warning("  Zeile 4798: Bereits gefixt oder Code geändert")
    
    return lines, fixes_applied

def main():
    print_header("Game Server Manager Pro - Bug Fix Patch")
    
    # Datei finden
    script_dir = os.path.dirname(os.path.abspath(__file__))
    target_file = os.path.join(script_dir, "game_server_manager.py")
    
    if not os.path.exists(target_file):
        print_error(f"Datei nicht gefunden: {target_file}")
        print_info("Bitte stelle sicher, dass bugfix_patch.py im gleichen Ordner wie game_server_manager.py liegt!")
        sys.exit(1)
    
    print_info(f"Ziel-Datei: {target_file}")
    
    # Backup erstellen
    print_header("Schritt 1: Backup erstellen")
    backup_path = create_backup(target_file)
    if not backup_path:
        print_error("Patch abgebrochen - Backup fehlgeschlagen!")
        sys.exit(1)
    
    # Fixes anwenden
    print_header("Schritt 2: Bug-Fixes anwenden")
    try:
        fixed_lines, fixes_count = apply_fixes(target_file)
    except Exception as e:
        print_error(f"Fehler beim Anwenden der Fixes: {e}")
        print_warning("Datei wurde NICHT verändert!")
        sys.exit(1)
    
    # Bestätigung
    print_header("Schritt 3: Bestätigung")
    print_info(f"Gefundene Fixes: {fixes_count}/5")
    
    if fixes_count == 0:
        print_warning("Keine Fixes angewendet - Code scheint bereits gepatcht zu sein!")
        print_info("Backup wurde trotzdem erstellt.")
        return
    
    print()
    print(f"{Colors.WARNING}Möchtest du die Änderungen speichern?{Colors.ENDC}")
    print(f"{Colors.WARNING}Backup: {backup_path}{Colors.ENDC}")
    response = input(f"{Colors.BOLD}Fortfahren? [j/N]: {Colors.ENDC}").strip().lower()
    
    if response not in ['j', 'ja', 'y', 'yes']:
        print_warning("Patch abgebrochen - Keine Änderungen gespeichert!")
        return
    
    # Speichern
    print_header("Schritt 4: Änderungen speichern")
    try:
        with open(target_file, 'w', encoding='utf-8') as f:
            f.writelines(fixed_lines)
        print_success(f"Datei gespeichert: {target_file}")
        print_success(f"{fixes_count} Bug-Fixes erfolgreich angewendet!")
    except Exception as e:
        print_error(f"Fehler beim Speichern: {e}")
        print_warning("Du kannst das Backup wiederherstellen:")
        print_info(f"  cp {backup_path} {target_file}")
        sys.exit(1)
    
    # Zusammenfassung
    print_header("✅ Patch erfolgreich!")
    print_success("Folgende Bugs wurden behoben:")
    print_info("  1. restore_backup: self.id → self.server_id")
    print_info("  2. delete_backup: self.id → self.server_id")
    print_info("  3. import_server_config: ServerInstance Parameter korrigiert")
    print_info("  4. save_settings: self.web_label auskommentiert")
    print_info("  5. _auto_refresh_dashboard: Attribut-Name korrigiert")
    print()
    print_success(f"Backup gespeichert: {backup_path}")
    print_info("Falls Probleme auftreten, kannst du das Backup wiederherstellen!")
    print()
    print(f"{Colors.OKGREEN}{Colors.BOLD}🎉 Programm ist jetzt stabiler!{Colors.ENDC}")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print_warning("Patch abgebrochen durch Benutzer!")
        sys.exit(0)
    except Exception as e:
        print_error(f"Unerwarteter Fehler: {e}")
        sys.exit(1)
