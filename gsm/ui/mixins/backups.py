"""Mixin: Backup-Verwaltung (Erstellen, Auflisten, Wiederherstellen, Loeschen).

Aus game_server_manager.py ausgelagert (Phase 3b, verhaltenserhaltend). Nur
Methoden, kein __init__; teilt sich self mit GameServerManagerApp.
"""

import threading

import customtkinter as ctk
from tkinter import messagebox

from gsm.games import SUPPORTED_GAMES


class BackupsMixin:
    """Backup-Verwaltung (Mixin fuer GameServerManagerApp)."""

    def open_backup_manager_tool(self):
        """Globaler Backup-Manager (Tools-Menue): Server waehlen, dann Dialog oeffnen."""
        t = self.config_manager.get_text
        servers = self.config_manager.servers
        if not servers:
            messagebox.showinfo(t("info"), t("no_servers"))
            return
        # Genau ein Server -> direkt oeffnen
        if len(servers) == 1:
            self.show_backup_manager(next(iter(servers)))
            return

        # Mehrere Server -> Auswahldialog
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"💾 {t('backup_manager')}")
        dialog.geometry("420x480")
        dialog.transient(self)
        dialog.grab_set()
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 420) // 2
        y = (dialog.winfo_screenheight() - 480) // 2
        dialog.geometry(f"420x480+{x}+{y}")

        ctk.CTkLabel(dialog, text=f"💾 {t('backup_manager')}", font=("Segoe UI", 18, "bold")).pack(pady=(20, 5))
        ctk.CTkLabel(dialog, text="Server auswählen:", font=("Segoe UI", 12), text_color="#888888").pack(pady=(0, 10))

        scroll = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        def _choose(server_id):
            dialog.destroy()
            self.show_backup_manager(server_id)

        for server_id, cfg in servers.items():
            icon = SUPPORTED_GAMES.get(cfg.get("game", ""), {}).get("icon", "🎮")
            name = cfg.get("name", server_id)
            ctk.CTkButton(
                scroll,
                text=f"{icon}  {name}",
                anchor="w",
                height=40,
                fg_color="#161b22",
                hover_color="#2a323d",
                command=lambda sid=server_id: _choose(sid),
            ).pack(fill="x", pady=4)

    def backup_server(self, server_id):
        """Öffnet den Backup-Manager für einen Server"""
        self.show_backup_manager(server_id)
    
    def show_backup_manager(self, server_id):
        """Zeigt den Backup-Manager Dialog"""
        t = self.config_manager.get_text
        instance = self.server_instances.get(server_id)
        server_config = self.config_manager.servers.get(server_id, {})
        
        if not instance:
            return
        
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"💾 {t('backup_manager')} - {server_config.get('name', 'Server')}")
        dialog.geometry("700x500")
        dialog.transient(self)
        
        # Zentrieren
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 700) // 2
        y = (dialog.winfo_screenheight() - 500) // 2
        dialog.geometry(f"700x500+{x}+{y}")
        
        # Header mit Aktionen
        header = ctk.CTkFrame(dialog)
        header.pack(fill="x", padx=15, pady=15)
        
        ctk.CTkLabel(
            header,
            text=f"💾 {t('backup_manager')}",
            font=("Segoe UI", 18, "bold")
        ).pack(side="left")
        
        # Jetzt Backup erstellen Button
        ctk.CTkButton(
            header,
            text=f"➕ {t('backup')} erstellen",
            command=lambda: self._create_backup_and_refresh(instance, backup_list_frame),
            width=150,
            fg_color="green"
        ).pack(side="right")
        
        # Info-Frame (Auto-Backup Status)
        info_frame = ctk.CTkFrame(dialog, fg_color=("#e8e8e8", "#2a2a2a"))
        info_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        # Auto-Backup Status
        interval = server_config.get("backup_interval_hours", 0)
        if interval > 0 and server_config.get("auto_backup", False):
            if instance.next_backup_time:
                next_time = instance.next_backup_time.strftime("%H:%M:%S")
                status_text = f"🔄 Auto-Backup aktiv (alle {interval}h) | {t('backup_auto_next')}: {next_time}"
            else:
                status_text = f"🔄 Auto-Backup aktiv (alle {interval}h) | Startet mit Server"
        else:
            status_text = f"⏸️ Auto-Backup deaktiviert"
        
        ctk.CTkLabel(
            info_frame,
            text=status_text,
            font=("Segoe UI", 11)
        ).pack(pady=8)
        
        # Backup-Liste
        list_header = ctk.CTkFrame(dialog, fg_color="transparent")
        list_header.pack(fill="x", padx=15)
        
        ctk.CTkLabel(list_header, text=t("backup_date"), font=("Segoe UI", 12, "bold"), width=180).pack(side="left")
        ctk.CTkLabel(list_header, text=t("backup_size"), font=("Segoe UI", 12, "bold"), width=100).pack(side="left")
        ctk.CTkLabel(list_header, text="Dateiname", font=("Segoe UI", 12, "bold")).pack(side="left", padx=10)
        
        # Scrollbare Liste
        backup_list_frame = ctk.CTkScrollableFrame(dialog)
        backup_list_frame.pack(fill="both", expand=True, padx=15, pady=10)
        
        def refresh_backup_list():
            # Liste leeren
            for widget in backup_list_frame.winfo_children():
                widget.destroy()
            
            backups = instance.get_backups()
            
            if not backups:
                ctk.CTkLabel(
                    backup_list_frame,
                    text=f"📭 {t('backup_no_backups')}",
                    font=("Segoe UI", 14),
                    text_color="gray"
                ).pack(pady=50)
                return
            
            for backup in backups:
                row = ctk.CTkFrame(backup_list_frame)
                row.pack(fill="x", pady=3)
                
                # Datum
                date_str = backup["date"].strftime("%d.%m.%Y %H:%M")
                ctk.CTkLabel(row, text=date_str, width=180, anchor="w").pack(side="left", padx=5)
                
                # Größe
                size_mb = backup["size"] / (1024 * 1024)
                size_str = f"{size_mb:.1f} MB"
                ctk.CTkLabel(row, text=size_str, width=100, anchor="w").pack(side="left")
                
                # Dateiname
                ctk.CTkLabel(row, text=backup["filename"], anchor="w", text_color="gray").pack(side="left", padx=10, fill="x", expand=True)
                
                # Buttons
                btn_frame = ctk.CTkFrame(row, fg_color="transparent")
                btn_frame.pack(side="right", padx=5)
                
                # Wiederherstellen
                ctk.CTkButton(
                    btn_frame,
                    text=t("backup_restore"),
                    width=100,
                    height=28,
                    fg_color="#2196F3",
                    command=lambda p=backup["path"]: self._restore_backup(instance, p, dialog, refresh_backup_list)
                ).pack(side="left", padx=2)
                
                # Löschen
                ctk.CTkButton(
                    btn_frame,
                    text="🗑️",
                    width=40,
                    height=28,
                    fg_color="#f44336",
                    command=lambda p=backup["path"]: self._delete_backup(instance, p, refresh_backup_list)
                ).pack(side="left", padx=2)
        
        # Initial laden
        refresh_backup_list()
        
        # Schließen Button
        ctk.CTkButton(
            dialog,
            text=t("cancel"),
            command=dialog.destroy,
            width=100,
            fg_color="gray"
        ).pack(pady=15)
    
    def _create_backup_and_refresh(self, instance, backup_list_frame):
        """Erstellt Backup und aktualisiert Liste"""
        def do_backup():
            instance.create_backup()
            # Liste aktualisieren (in Main-Thread)
            self.after(1000, lambda: self._refresh_backup_list_widget(backup_list_frame, instance))
        
        threading.Thread(target=do_backup, daemon=True).start()
    
    def _refresh_backup_list_widget(self, backup_list_frame, instance):
        """Aktualisiert die Backup-Liste Widget"""
        t = self.config_manager.get_text
        
        for widget in backup_list_frame.winfo_children():
            widget.destroy()
        
        backups = instance.get_backups()
        
        if not backups:
            ctk.CTkLabel(
                backup_list_frame,
                text=f"📭 {t('backup_no_backups')}",
                font=("Segoe UI", 14),
                text_color="gray"
            ).pack(pady=50)
            return
        
        for backup in backups:
            row = ctk.CTkFrame(backup_list_frame)
            row.pack(fill="x", pady=3)
            
            date_str = backup["date"].strftime("%d.%m.%Y %H:%M")
            ctk.CTkLabel(row, text=date_str, width=180, anchor="w").pack(side="left", padx=5)
            
            size_mb = backup["size"] / (1024 * 1024)
            size_str = f"{size_mb:.1f} MB"
            ctk.CTkLabel(row, text=size_str, width=100, anchor="w").pack(side="left")
            
            ctk.CTkLabel(row, text=backup["filename"], anchor="w", text_color="gray").pack(side="left", padx=10, fill="x", expand=True)
            
            btn_frame = ctk.CTkFrame(row, fg_color="transparent")
            btn_frame.pack(side="right", padx=5)
            
            ctk.CTkButton(
                btn_frame,
                text=t("backup_restore"),
                width=100,
                height=28,
                fg_color="#2196F3",
                command=lambda p=backup["path"]: self._restore_backup_simple(instance, p)
            ).pack(side="left", padx=2)
            
            ctk.CTkButton(
                btn_frame,
                text="🗑️",
                width=40,
                height=28,
                fg_color="#f44336",
                command=lambda p=backup["path"], bf=backup_list_frame, inst=instance: self._delete_backup_simple(inst, p, bf)
            ).pack(side="left", padx=2)
    
    def _restore_backup(self, instance, backup_path, dialog, refresh_callback):
        """Stellt ein Backup wieder her"""
        t = self.config_manager.get_text
        
        if instance.is_running():
            messagebox.showwarning(t("warning"), "Server muss gestoppt sein für Wiederherstellung!")
            return
        
        if messagebox.askyesno(t("warning"), t("backup_confirm_restore")):
            if instance.restore_backup(backup_path):
                messagebox.showinfo(t("success"), t("backup_restored"))
            else:
                messagebox.showerror(t("error"), t("backup_restore_failed"))
    
    def _restore_backup_simple(self, instance, backup_path):
        """Einfache Backup-Wiederherstellung"""
        t = self.config_manager.get_text
        
        if instance.is_running():
            messagebox.showwarning(t("warning"), "Server muss gestoppt sein für Wiederherstellung!")
            return
        
        if messagebox.askyesno(t("warning"), t("backup_confirm_restore")):
            if instance.restore_backup(backup_path):
                messagebox.showinfo(t("success"), t("backup_restored"))
            else:
                messagebox.showerror(t("error"), t("backup_restore_failed"))
    
    def _delete_backup(self, instance, backup_path, refresh_callback):
        """Löscht ein Backup"""
        t = self.config_manager.get_text
        
        if messagebox.askyesno(t("warning"), t("backup_confirm_delete")):
            if instance.delete_backup(backup_path):
                refresh_callback()
    
    def _delete_backup_simple(self, instance, backup_path, backup_list_frame):
        """Einfaches Backup löschen"""
        t = self.config_manager.get_text
        
        if messagebox.askyesno(t("warning"), t("backup_confirm_delete")):
            if instance.delete_backup(backup_path):
                self._refresh_backup_list_widget(backup_list_frame, instance)
