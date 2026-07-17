"""Mixin: Chat/Stream- und TeamSpeak-Dienste sowie Service-Status.

Aus game_server_manager.py ausgelagert (Phase 3, verhaltenserhaltend). Die
Methoden teilen sich `self` mit GameServerManagerApp; hier stehen nur Methoden,
keine __init__. Modul-Level-Namen werden lokal importiert.
"""

import os
import socket
import subprocess
import threading
from datetime import datetime

import customtkinter as ctk
from tkinter import messagebox

from gsm.paths import PATHS


class TeamSpeakServicesMixin:
    """Chat/Stream + TeamSpeak3 + Service-Status (Mixin fuer GameServerManagerApp)."""

    def _get_local_tailscale_ip(self):
        # Versucht die lokale Tailscale-IP zu ermitteln
        try:
            hostname = socket.gethostname()
            for ip in socket.gethostbyname_ex(hostname)[2]:
                if ip.startswith("100."):
                    return ip
        except:
            pass
        return "127.0.0.1"

    def get_chat_stream_config(self):
        # Liefert Chat/Stream Konfiguration mit Defaults
        cfg = self.config_manager.app_config.get("chat_stream", {})
        if "enabled" not in cfg:
            cfg["enabled"] = False
        if "room_name" not in cfg:
            cfg["room_name"] = "Private Room"
        if "require_tailscale" not in cfg:
            cfg["require_tailscale"] = True
        self.config_manager.app_config["chat_stream"] = cfg
        return cfg

    def is_chat_stream_enabled(self):
        return self.get_chat_stream_config().get("enabled", False)

    def set_chat_stream_enabled(self, enabled):
        cfg = self.get_chat_stream_config()
        cfg["enabled"] = bool(enabled)
        self.config_manager.app_config["chat_stream"] = cfg
        self.config_manager.save_app_config()

    def init_chat_runtime(self):
        # Initialisiert Runtime-Container für RAM-Chat + Signaling
        if self.chat_runtime:
            return
        self.chat_runtime = {
            "lock": threading.Lock(),
            "message_seq": 0,
            "signal_seq": 0,
            "messages": [],
            "signals": [],
            "presence": {}
        }

    def open_web_page(self, route="/"):
        # Öffnet eine Web-Seite im Browser
        import webbrowser
        port = self.config_manager.app_config.get("web", {}).get("port", 5001)
        route = route if route.startswith("/") else "/" + route
        webbrowser.open(f"http://localhost:{port}{route}")


    def _get_teamspeak_exe_by_type(self, server_type):
        if server_type == "ts6":
            return "tsserver.exe"
        return "ts3server.exe"

    def _get_teamspeak_base_path_by_type(self, server_type):
        if server_type == "ts6":
            return r"C:\TeamSpeak6 Server"
        return r"C:\TeamSpeak3 Server"

    def _get_teamspeak_exe_candidates(self, server_type):
        if server_type == "ts6":
            return ["tsserver.exe", "ts6server.exe"]
        return ["ts3server.exe"]

    def _resolve_teamspeak_executable(self, cfg):
        base_path = cfg.get("base_path", "")
        server_type = cfg.get("server_type", "ts3")
        configured = str(cfg.get("exe_name", "")).strip()

        candidates = []
        if configured:
            candidates.append(configured)
        for name in self._get_teamspeak_exe_candidates(server_type):
            if name not in candidates:
                candidates.append(name)

        for name in candidates:
            candidate_path = os.path.join(base_path, name)
            if os.path.exists(candidate_path):
                return candidate_path, name, candidates, True

        fallback_name = configured or self._get_teamspeak_exe_by_type(server_type)
        return os.path.join(base_path, fallback_name), fallback_name, candidates, False

    def _get_teamspeak3_defaults(self):
        default_path = self._get_teamspeak_base_path_by_type("ts3")
        return {
            "enabled": False,
            "server_type": "ts3",
            "base_path": default_path,
            "exe_name": ""
        }

    def get_teamspeak3_config(self):
        defaults = self._get_teamspeak3_defaults()
        cfg = self.config_manager.app_config.get("teamspeak3", {})

        server_type = str(cfg.get("server_type", defaults["server_type"]))
        if server_type not in ("ts3", "ts6"):
            server_type = "ts3"

        exe_name = str(cfg.get("exe_name", "")).strip()
        if not exe_name:
            exe_name = self._get_teamspeak_exe_by_type(server_type)

        base_path = str(cfg.get("base_path", "")).strip()
        if not base_path:
            base_path = self._get_teamspeak_base_path_by_type(server_type)

        legacy_default = os.path.join(PATHS.get("base", ""), "tools", "teamspeak3")
        if os.path.normcase(base_path) == os.path.normcase(legacy_default):
            base_path = self._get_teamspeak_base_path_by_type(server_type)

        merged = {
            "enabled": cfg.get("enabled", defaults["enabled"]),
            "server_type": server_type,
            "base_path": base_path,
            "exe_name": exe_name
        }
        self.config_manager.app_config["teamspeak3"] = merged
        return merged

    def save_teamspeak3_config(self, cfg):
        self.config_manager.app_config["teamspeak3"] = cfg
        self.config_manager.save_app_config()

    def get_teamspeak3_executable_path(self):
        cfg = self.get_teamspeak3_config()
        exe_path, _, _, _ = self._resolve_teamspeak_executable(cfg)
        return exe_path

    def get_teamspeak_runtime_label(self):
        cfg = self.get_teamspeak3_config()
        return "TeamSpeak 6" if cfg.get("server_type") == "ts6" else "TeamSpeak 3"

    def get_teamspeak_runtime_short(self):
        cfg = self.get_teamspeak3_config()
        return "TS6" if cfg.get("server_type") == "ts6" else "TS3"

    def is_teamspeak3_running(self):
        if self.ts3_process is None:
            return False
        if self.ts3_process.poll() is not None:
            self.ts3_process = None
            if self.ts3_log_handle:
                try:
                    self.ts3_log_handle.close()
                except:
                    pass
                self.ts3_log_handle = None
            return False
        return True

    def start_teamspeak3_server(self):
        label = self.get_teamspeak_runtime_label()
        short = self.get_teamspeak_runtime_short()

        if self.is_teamspeak3_running():
            return True, f"{label} läuft bereits."

        cfg = self.get_teamspeak3_config()
        base_path = cfg.get("base_path", "")

        if not base_path:
            return False, f"{label} Pfad ist leer."

        os.makedirs(base_path, exist_ok=True)

        exe_path, detected_exe, tried_names, exists = self._resolve_teamspeak_executable(cfg)
        if not exists:
            tried = ", ".join(tried_names)
            return False, f"{short} Server nicht gefunden: {exe_path} (Gesucht: {tried})"

        if cfg.get("exe_name") != detected_exe:
            cfg["exe_name"] = detected_exe
            self.save_teamspeak3_config(cfg)

        log_name = "ts6server_runtime.log" if cfg.get("server_type") == "ts6" else "ts3server_runtime.log"
        self.ts3_log_path = os.path.join(base_path, log_name)

        try:
            flags = 0
            if os.name == "nt":
                flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

            self.ts3_log_handle = open(self.ts3_log_path, "a", encoding="utf-8", errors="replace")
            self.ts3_log_handle.write(f"\n===== {short} Start {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====\n")
            self.ts3_log_handle.flush()

            self.ts3_process = subprocess.Popen(
                [exe_path],
                cwd=base_path,
                stdout=self.ts3_log_handle,
                stderr=subprocess.STDOUT,
                creationflags=flags
            )
            cfg["enabled"] = True
            self.save_teamspeak3_config(cfg)
            return True, f"{label} wurde gestartet."
        except Exception as e:
            if self.ts3_log_handle:
                try:
                    self.ts3_log_handle.close()
                except:
                    pass
                self.ts3_log_handle = None
            self.ts3_process = None
            return False, f"{short} Start fehlgeschlagen: {e}"

    def stop_teamspeak3_server(self):
        label = self.get_teamspeak_runtime_label()
        short = self.get_teamspeak_runtime_short()

        if not self.is_teamspeak3_running():
            return True, f"{label} läuft nicht."

        try:
            self.ts3_process.terminate()
            try:
                self.ts3_process.wait(timeout=8)
            except:
                self.ts3_process.kill()
            self.ts3_process = None
            if self.ts3_log_handle:
                try:
                    self.ts3_log_handle.close()
                except:
                    pass
                self.ts3_log_handle = None

            cfg = self.get_teamspeak3_config()
            cfg["enabled"] = False
            self.save_teamspeak3_config(cfg)
            return True, f"{label} wurde gestoppt."
        except Exception as e:
            return False, f"{short} Stop fehlgeschlagen: {e}"

    def read_teamspeak3_log_tail(self, max_lines=120):
        path = self.ts3_log_path
        if not path:
            cfg = self.get_teamspeak3_config()
            log_name = "ts6server_runtime.log" if cfg.get("server_type") == "ts6" else "ts3server_runtime.log"
            path = os.path.join(cfg.get("base_path", ""), log_name)

        if not os.path.exists(path):
            return "Noch keine Logs vorhanden."

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            return "".join(lines[-max_lines:]) if lines else "Noch keine Logs vorhanden."
        except Exception as e:
            return f"Log-Datei konnte nicht gelesen werden: {e}"

    def get_service_status_payload(self):
        web_port = self.config_manager.app_config.get("web", {}).get("port", 5001)
        tail_ip = self._get_local_tailscale_ip()
        return {
            "chat_enabled": self.is_chat_stream_enabled(),
            "chat_url": f"http://{tail_ip}:{web_port}/chat",
            "teamspeak_running": self.is_teamspeak3_running(),
            "teamspeak_label": self.get_teamspeak_runtime_label()
        }

    def show_chat_stream_manager(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Chat & Stream Manager")
        dialog.geometry("760x460")

        ctk.CTkLabel(dialog, text="💬 Chat + Stream", font=("Segoe UI", 24, "bold"), text_color="#4c9aff").pack(pady=(18, 8))
        ctk.CTkLabel(
            dialog,
            text="Textchat + Dual Screen/Game-Stream (Chrome/Edge) über Tailscale",
            font=("Segoe UI", 13),
            text_color="#aaaaaa"
        ).pack(pady=(0, 14))

        status_frame = ctk.CTkFrame(dialog, fg_color="#161b22")
        status_frame.pack(fill="x", padx=20, pady=8)

        chat_status_var = ctk.StringVar(value="Chat: wird geladen...")
        ts_status_var = ctk.StringVar(value="TeamSpeak: wird geladen...")
        url_var = ctk.StringVar(value="")

        chat_status_lbl = ctk.CTkLabel(status_frame, textvariable=chat_status_var, font=("Segoe UI", 15, "bold"))
        chat_status_lbl.pack(anchor="w", padx=16, pady=(12, 4))
        ts_status_lbl = ctk.CTkLabel(status_frame, textvariable=ts_status_var, font=("Segoe UI", 14, "bold"))
        ts_status_lbl.pack(anchor="w", padx=16, pady=(0, 4))
        ctk.CTkLabel(status_frame, textvariable=url_var, font=("Consolas", 13), text_color="#4c9aff").pack(anchor="w", padx=16, pady=(0, 12))

        btns = ctk.CTkFrame(dialog, fg_color="transparent")
        btns.pack(fill="x", padx=20, pady=8)

        def refresh_state():
            payload = self.get_service_status_payload()

            chat_on = payload["chat_enabled"]
            chat_status_var.set(f"{'🟢' if chat_on else '🔴'} Chat/Stream: {'AKTIV' if chat_on else 'INAKTIV'}")
            chat_status_lbl.configure(text_color="#39d98a" if chat_on else "#ff7b7b")

            ts_on = payload["teamspeak_running"]
            ts_status_var.set(f"{'🟢' if ts_on else '🔴'} {payload['teamspeak_label']}: {'ONLINE' if ts_on else 'OFFLINE'}")
            ts_status_lbl.configure(text_color="#39d98a" if ts_on else "#ff7b7b")

            url_var.set(f"Tailscale URL: {payload['chat_url']}")

        def schedule_refresh():
            if not dialog.winfo_exists():
                return
            refresh_state()
            dialog.after(2000, schedule_refresh)

        def set_chat_state(enabled):
            self.set_chat_stream_enabled(enabled)
            refresh_state()
            messagebox.showinfo("Chat & Stream", "Chat/Stream aktiviert." if enabled else "Chat/Stream deaktiviert.")

        ctk.CTkButton(btns, text="▶ Aktivieren", width=130, fg_color="#2d5a2d", hover_color="#3d7a3d", command=lambda: set_chat_state(True)).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="⏹ Deaktivieren", width=130, fg_color="#aa3333", hover_color="#cc4444", command=lambda: set_chat_state(False)).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="🌐 Chat öffnen", width=140, fg_color="#005f8c", hover_color="#0077aa", command=lambda: self.open_web_page("/chat")).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="🎙️ TeamSpeak verwalten", width=190, command=self.show_teamspeak3_manager).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="🗕 Minimieren", width=120, command=dialog.iconify).pack(side="left", padx=5)

        ctk.CTkLabel(
            dialog,
            text="Hinweis: Chat-Nachrichten werden aktuell nur im RAM gehalten (beim Neustart gelöscht).",
            font=("Segoe UI", 12),
            text_color="#888888"
        ).pack(anchor="w", padx=24, pady=(12, 4))

        refresh_state()
        schedule_refresh()

    def show_teamspeak3_manager(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("TeamSpeak Server")
        dialog.geometry("940x700")

        cfg = self.get_teamspeak3_config()

        title_var = ctk.StringVar(value=f"🎙️ {self.get_teamspeak_runtime_label()} Server")
        ctk.CTkLabel(dialog, textvariable=title_var, font=("Segoe UI", 24, "bold"), text_color="#4c9aff").pack(pady=(16, 10))

        top = ctk.CTkFrame(dialog, fg_color="#161b22")
        top.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(top, text="Server-Typ", font=("Segoe UI", 12), text_color="#aaaaaa").pack(anchor="w", padx=16, pady=(12, 4))
        type_var = ctk.StringVar(value="TS6" if cfg.get("server_type") == "ts6" else "TS3")
        type_combo = ctk.CTkComboBox(top, values=["TS3", "TS6"], variable=type_var, width=180)
        type_combo.pack(anchor="w", padx=16, pady=(0, 8))

        ctk.CTkLabel(top, text="Basis-Pfad", font=("Segoe UI", 12), text_color="#aaaaaa").pack(anchor="w", padx=16, pady=(0, 4))
        path_var = ctk.StringVar(value=cfg.get("base_path", ""))
        ctk.CTkEntry(top, textvariable=path_var, height=34).pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(top, text="Exe-Datei (optional)", font=("Segoe UI", 12), text_color="#aaaaaa").pack(anchor="w", padx=16, pady=(0, 4))
        exe_var = ctk.StringVar(value=cfg.get("exe_name", ""))
        ctk.CTkEntry(top, textvariable=exe_var, height=34).pack(fill="x", padx=16, pady=(0, 8))

        hint_var = ctk.StringVar(value="")
        ctk.CTkLabel(top, textvariable=hint_var, font=("Consolas", 12), text_color="#7ec8ff").pack(anchor="w", padx=16, pady=(0, 8))

        status_var = ctk.StringVar(value="Status wird geladen...")
        status_lbl = ctk.CTkLabel(top, textvariable=status_var, font=("Segoe UI", 15, "bold"))
        status_lbl.pack(anchor="w", padx=16, pady=(0, 12))

        btns = ctk.CTkFrame(dialog, fg_color="transparent")
        btns.pack(fill="x", padx=20, pady=(0, 10))

        log_box = ctk.CTkTextbox(dialog, height=330)
        log_box.pack(fill="both", expand=True, padx=20, pady=(0, 14))

        def normalize_type(value):
            return "ts6" if str(value).strip().upper() == "TS6" else "ts3"

        def preview_cfg():
            server_type = normalize_type(type_var.get())
            configured_exe = exe_var.get().strip()
            exe_name = configured_exe or self._get_teamspeak_exe_by_type(server_type)
            return {
                "server_type": server_type,
                "base_path": path_var.get().strip(),
                "exe_name": exe_name
            }

        def persist_config(force_default_exe=False):
            cfg_now = self.get_teamspeak3_config()
            cfg_now["server_type"] = normalize_type(type_var.get())
            cfg_now["base_path"] = path_var.get().strip() or self._get_teamspeak_base_path_by_type(cfg_now["server_type"])
            path_var.set(cfg_now["base_path"])
            if force_default_exe or not exe_var.get().strip():
                exe_var.set(self._get_teamspeak_exe_by_type(cfg_now["server_type"]))
            cfg_now["exe_name"] = exe_var.get().strip()
            self.save_teamspeak3_config(cfg_now)
            return cfg_now

        def refresh():
            cfg_now = preview_cfg()
            label = "TeamSpeak 6" if cfg_now["server_type"] == "ts6" else "TeamSpeak 3"
            title_var.set(f"🎙️ {label} Server")

            exe_path, _, tried_names, exists = self._resolve_teamspeak_executable(cfg_now)
            running = self.is_teamspeak3_running()
            status_var.set(f"{'🟢 Läuft' if running else '🔴 Gestoppt'} | Exe: {exe_path}")
            status_lbl.configure(text_color="#39d98a" if running else "#ff7b7b")
            hint_var.set(f"Gesucht: {', '.join(tried_names)}")

            log_box.delete("1.0", "end")
            log_box.insert("1.0", self.read_teamspeak3_log_tail())

        def schedule_refresh():
            if not dialog.winfo_exists():
                return
            refresh()
            dialog.after(2000, schedule_refresh)

        def on_type_change(_=None):
            selected = normalize_type(type_var.get())
            path_var.set(self._get_teamspeak_base_path_by_type(selected))
            persist_config(force_default_exe=True)
            refresh()

        def start_server():
            persist_config(force_default_exe=False)
            ok, msg = self.start_teamspeak3_server()
            refresh()
            if ok:
                messagebox.showinfo("TeamSpeak", msg)
            else:
                messagebox.showerror("TeamSpeak", msg)

        def stop_server():
            ok, msg = self.stop_teamspeak3_server()
            refresh()
            if ok:
                messagebox.showinfo("TeamSpeak", msg)
            else:
                messagebox.showerror("TeamSpeak", msg)

        type_combo.configure(command=on_type_change)

        ctk.CTkButton(btns, text="▶ Start", width=110, fg_color="#2d5a2d", hover_color="#3d7a3d", command=start_server).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="⏹ Stop", width=110, fg_color="#aa3333", hover_color="#cc4444", command=stop_server).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="🔄 Aktualisieren", width=130, command=refresh).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="📁 Ordner öffnen", width=130, command=lambda: os.startfile(path_var.get()) if os.path.exists(path_var.get()) else None).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="🗕 Minimieren", width=120, command=dialog.iconify).pack(side="left", padx=5)

        refresh()
        schedule_refresh()

