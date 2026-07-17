"""Setup-Wizard für die Ersteinrichtung.

Aus game_server_manager.py ausgelagert.
"""

import os

import customtkinter as ctk
from tkinter import messagebox, filedialog

from gsm.paths import PATHS, set_base_dir, save_base_dir, ensure_directories
from gsm.i18n import TRANSLATIONS
from gsm.config import ConfigManager


class SetupWizard(ctk.CTkToplevel):
    """Setup-Wizard für die Ersteinrichtung"""
    
    def __init__(self, parent, on_complete):
        super().__init__(parent)
        
        self.on_complete = on_complete
        self.current_step = 0
        self.selected_path = ""
        
        self.title("Game Server Manager Pro - Setup")
        self.geometry("700x650")
        self.resizable(False, False)
        
        # Modal machen
        self.transient(parent)
        self.grab_set()
        
        # Zentrieren
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 700) // 2
        y = (self.winfo_screenheight() - 650) // 2
        self.geometry(f"700x650+{x}+{y}")
        
        # Prevent closing without completing
        self.protocol("WM_DELETE_WINDOW", self.on_close_attempt)
        
        self.create_ui()
    
    def on_close_attempt(self):
        """Verhindert Schließen ohne Setup abzuschließen"""
        if messagebox.askyesno("Setup abbrechen?", "Setup wirklich abbrechen?\nDas Programm wird beendet."):
            self.destroy()
            self.master.destroy()
    
    def create_ui(self):
        """Erstellt die UI"""
        # Container
        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Progress indicator
        self.progress_frame = ctk.CTkFrame(self.container, fg_color="transparent", height=30)
        self.progress_frame.pack(fill="x", pady=(0, 10))
        self.progress_frame.pack_propagate(False)
        
        # Header
        self.header = ctk.CTkLabel(
            self.container,
            text="🎮 Willkommen!",
            font=("Segoe UI", 28, "bold")
        )
        self.header.pack(pady=10)
        
        # Button Frame - ZUERST packen mit side=bottom damit er immer sichtbar ist
        self.button_frame = ctk.CTkFrame(self.container, fg_color="transparent", height=50)
        self.button_frame.pack(side="bottom", fill="x", pady=10)
        self.button_frame.pack_propagate(False)
        
        self.back_btn = ctk.CTkButton(
            self.button_frame,
            text="← Zurück",
            command=self.prev_step,
            width=100,
            fg_color="gray"
        )
        
        self.next_btn = ctk.CTkButton(
            self.button_frame,
            text="Weiter →",
            command=self.next_step,
            width=120
        )
        self.next_btn.pack(side="right", pady=5)
        
        # Content Frame (wird pro Step gewechselt) - NACH button_frame packen
        self.content_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, pady=10)
        
        # Step 0 anzeigen
        self.show_step(0)
    
    def update_progress(self):
        """Aktualisiert die Progress-Anzeige"""
        for widget in self.progress_frame.winfo_children():
            widget.destroy()
        
        steps = ["Willkommen", "Ordner", "Sprache", "Passwort", "Fertig"]
        
        for i, step_name in enumerate(steps):
            color = "#4c9aff" if i <= self.current_step else "gray"
            ctk.CTkLabel(
                self.progress_frame,
                text=f"● {step_name}" if i == self.current_step else "●",
                text_color=color,
                font=("Segoe UI", 11)
            ).pack(side="left", padx=8)
    
    def clear_content(self):
        """Leert den Content-Frame"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def show_step(self, step):
        """Zeigt einen bestimmten Step an"""
        self.current_step = step
        self.clear_content()
        self.update_progress()
        
        # Back-Button nur ab Step 1
        if step > 0:
            self.back_btn.pack(side="left", pady=5)
        else:
            self.back_btn.pack_forget()
        
        if step == 0:
            self.show_welcome()
        elif step == 1:
            self.show_folder_selection()
        elif step == 2:
            self.show_language()
        elif step == 3:
            self.show_password()
        elif step == 4:
            self.show_complete()
    
    def show_welcome(self):
        """Step 0: Willkommen"""
        self.header.configure(text="🎮 Willkommen!")
        
        ctk.CTkLabel(
            self.content_frame,
            text="Willkommen beim Game Server Manager Pro!",
            font=("Segoe UI", 20, "bold")
        ).pack(pady=20)
        
        features_text = """
Dieses Tool hilft dir, deine Game-Server zu verwalten.

✓ Mehrere Server gleichzeitig verwalten
✓ Unterstützt: ARK, Rust, Valheim, Palworld & mehr
✓ Automatische Backups
✓ Web-Interface für Remote-Zugriff
✓ Discord Benachrichtigungen
✓ Auto-Restart bei Crashes
"""
        
        ctk.CTkLabel(
            self.content_frame,
            text=features_text,
            font=("Segoe UI", 14),
            justify="left"
        ).pack(pady=10)
        
        self.next_btn.configure(text="Los geht's! →")
    
    def show_folder_selection(self):
        """Step 1: Installations-Ordner wählen"""
        self.header.configure(text="📁 Installations-Ordner")
        self.next_btn.configure(text="Weiter →")
        
        ctk.CTkLabel(
            self.content_frame,
            text="Wo sollen Server, Backups & Configs gespeichert werden?",
            font=("Segoe UI", 16)
        ).pack(pady=10)
        
        ctk.CTkLabel(
            self.content_frame,
            text="💡 Wähle einen Ordner mit genügend Speicherplatz (20-100 GB pro Spiel)",
            font=("Segoe UI", 12),
            text_color="gray"
        ).pack(pady=5)
        
        # Pfad-Auswahl Frame
        path_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        path_frame.pack(fill="x", padx=20, pady=15)
        
        # Standard-Pfad vorschlagen
        default_path = os.path.join(os.path.expanduser("~"), "GameServerManager")
        self.path_var = ctk.StringVar(value=self.selected_path or default_path)
        
        self.path_entry = ctk.CTkEntry(
            path_frame,
            textvariable=self.path_var,
            width=420,
            height=40,
            font=("Segoe UI", 13)
        )
        self.path_entry.pack(side="left", padx=(0, 10))
        
        ctk.CTkButton(
            path_frame,
            text="📂 Durchsuchen",
            command=self.browse_folder,
            width=130,
            height=40
        ).pack(side="left")
        
        # Info was erstellt wird - kompakter
        info_frame = ctk.CTkFrame(self.content_frame)
        info_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            info_frame,
            text="📋 Folgende Unterordner werden erstellt:",
            font=("Segoe UI", 12, "bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))
        
        # Alle Ordner in einer Zeile
        folders_text = "servers • backups • config • steamcmd • logs"
        ctk.CTkLabel(
            info_frame,
            text=folders_text,
            font=("Segoe UI", 11),
            text_color="gray"
        ).pack(anchor="w", padx=15, pady=(0, 10))
        
        # Fehler-Label
        self.folder_error = ctk.CTkLabel(
            self.content_frame,
            text="",
            text_color="red",
            font=("Segoe UI", 12)
        )
        self.folder_error.pack(pady=10)
    
    def browse_folder(self):
        """Öffnet den Ordner-Dialog"""
        folder = filedialog.askdirectory(
            title="Installations-Ordner wählen",
            initialdir=os.path.expanduser("~")
        )
        if folder:
            # Füge "GameServerManager" hinzu wenn nicht vorhanden
            if not folder.endswith("GameServerManager"):
                folder = os.path.join(folder, "GameServerManager")
            self.path_var.set(folder)
    
    def show_language(self):
        """Step 2: Sprache wählen"""
        self.header.configure(text="🌍 Sprache / Language")
        self.next_btn.configure(text="Weiter / Next →")
        
        ctk.CTkLabel(
            self.content_frame,
            text="Wähle deine Sprache\nSelect your language",
            font=("Segoe UI", 16)
        ).pack(pady=30)
        
        self.language_var = ctk.StringVar(value="de")
        
        lang_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        lang_frame.pack(pady=20)
        
        de_btn = ctk.CTkRadioButton(
            lang_frame,
            text="🇩🇪  Deutsch",
            variable=self.language_var,
            value="de",
            font=("Segoe UI", 18)
        )
        de_btn.pack(pady=15)
        
        en_btn = ctk.CTkRadioButton(
            lang_frame,
            text="🇬🇧  English",
            variable=self.language_var,
            value="en",
            font=("Segoe UI", 18)
        )
        en_btn.pack(pady=15)
    
    def show_password(self):
        """Step 3: Web-Passwort setzen"""
        lang = self.language_var.get() if hasattr(self, 'language_var') else "de"
        t = TRANSLATIONS[lang]
        
        self.header.configure(text="🔒 Web-Interface Passwort")
        self.next_btn.configure(text=t["finish"])
        
        ctk.CTkLabel(
            self.content_frame,
            text="Setze ein Passwort für das Web-Interface.\n"
                 "Damit kannst du den Server auch von anderen Geräten steuern.",
            font=("Segoe UI", 14)
        ).pack(pady=20)
        
        self.password_var = ctk.StringVar()
        self.password_entry = ctk.CTkEntry(
            self.content_frame,
            textvariable=self.password_var,
            placeholder_text="Passwort (min. 6 Zeichen)",
            show="*",
            width=300,
            height=45,
            font=("Segoe UI", 14)
        )
        self.password_entry.pack(pady=10)
        
        self.password_confirm_var = ctk.StringVar()
        self.password_confirm_entry = ctk.CTkEntry(
            self.content_frame,
            textvariable=self.password_confirm_var,
            placeholder_text="Passwort bestätigen",
            show="*",
            width=300,
            height=45,
            font=("Segoe UI", 14)
        )
        self.password_confirm_entry.pack(pady=10)
        
        self.password_error = ctk.CTkLabel(
            self.content_frame,
            text="",
            text_color="red",
            font=("Segoe UI", 12)
        )
        self.password_error.pack(pady=10)
        
        ctk.CTkLabel(
            self.content_frame,
            text="💡 Das Web-Interface erreichst du unter:\n"
                 "http://localhost:5001 oder über Tailscale",
            font=("Segoe UI", 12),
            text_color="gray"
        ).pack(pady=20)
    
    def show_complete(self):
        """Step 4: Fertig"""
        lang = getattr(self, 'language_var', ctk.StringVar(value="de")).get()
        t = TRANSLATIONS[lang]
        
        self.header.configure(text="✅ Setup abgeschlossen!")
        self.next_btn.configure(text="🚀 Starten!")
        self.back_btn.pack_forget()
        
        ctk.CTkLabel(
            self.content_frame,
            text="Alles eingerichtet!",
            font=("Segoe UI", 20, "bold")
        ).pack(pady=20)
        
        summary = f"""
📁 Ordner: {self.selected_path}

Du kannst jetzt:
• Server hinzufügen und installieren
• Das Web-Interface nutzen (localhost:5001)
• Einstellungen anpassen

Viel Spaß beim Spielen! 🎮
"""
        
        ctk.CTkLabel(
            self.content_frame,
            text=summary,
            font=("Segoe UI", 14),
            justify="left"
        ).pack(pady=20)
    
    def next_step(self):
        """Geht zum nächsten Step"""
        global PATHS
        
        # Validierung je nach Step
        if self.current_step == 1:
            # Ordner validieren
            path = self.path_var.get().strip()
            
            if not path:
                self.folder_error.configure(text="❌ Bitte einen Ordner auswählen!")
                return
            
            # Prüfe ob Pfad gültig ist
            try:
                # Versuche Ordner zu erstellen
                os.makedirs(path, exist_ok=True)
                
                # Prüfe Schreibrechte
                test_file = os.path.join(path, ".test_write")
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                
                self.selected_path = path
                self.folder_error.configure(text="")
                
                # Pfade global setzen (in place, damit alle Module dasselbe Dict sehen)
                set_base_dir(path)
                
                # Config speichern
                if not save_base_dir(path):
                    self.folder_error.configure(text="❌ Konnte Einstellungen nicht speichern!")
                    return
                
                ensure_directories()
                
            except PermissionError:
                self.folder_error.configure(text="❌ Keine Schreibrechte für diesen Ordner!")
                return
            except Exception as e:
                self.folder_error.configure(text=f"❌ Fehler: {str(e)}")
                return
        
        elif self.current_step == 2:
            # Sprache speichern - Config Manager noch nicht verfügbar
            pass
        
        elif self.current_step == 3:
            # Passwort validieren
            pw = self.password_var.get()
            pw_confirm = self.password_confirm_var.get()
            
            if len(pw) < 6:
                self.password_error.configure(text="❌ Passwort muss mindestens 6 Zeichen haben!")
                return
            
            if pw != pw_confirm:
                self.password_error.configure(text="❌ Passwörter stimmen nicht überein!")
                return
            
            self.password_error.configure(text="")
            self.final_password = pw
        
        elif self.current_step == 4:
            # Alles speichern und fertig
            self.finish_setup()
            return
        
        self.show_step(self.current_step + 1)
    
    def prev_step(self):
        """Geht zum vorherigen Step"""
        if self.current_step > 0:
            self.show_step(self.current_step - 1)
    
    def finish_setup(self):
        """Schließt das Setup ab und speichert alles"""
        global PATHS
        
        # Config Manager erstellen
        config_manager = ConfigManager()
        
        # Sprache speichern
        config_manager.app_config["language"] = self.language_var.get()
        config_manager.app_config["first_run"] = False
        config_manager.save_app_config()
        
        # Passwort speichern
        config_manager.set_admin_password(self.final_password)
        
        # Fenster schließen und Callback aufrufen
        self.destroy()
        self.on_complete(config_manager)
