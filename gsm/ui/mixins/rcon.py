"""Mixin: RCON-Dashboard (mit ARK-Karte) und Log-Viewer.

Aus game_server_manager.py ausgelagert (Phase 3f, verhaltenserhaltend). Nur
Methoden, kein __init__; teilt sich self mit GameServerManagerApp.
"""

import os
import time
import threading
from datetime import datetime

import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox, filedialog

try:
    from PIL import ImageTk
    PIL_AVAILABLE = True
except ImportError:
    ImageTk = None
    PIL_AVAILABLE = False

from gsm.paths import PATHS
from gsm.games import SUPPORTED_GAMES
from gsm.rcon import RCONClient
from gsm.ark import ArkMapManager, ArkSaveParser, ARK_MAP_DATA


class RconLogMixin:
    """RCON-Dashboard + Log-Viewer (Mixin fuer GameServerManagerApp)."""

    def show_rcon_dashboard(self, server_id):
        """Öffnet das RCON Dashboard mit Karte"""
        server_config = self.config_manager.servers.get(server_id, {})
        instance = self.server_instances.get(server_id)
        
        if not instance:
            return
        
        # Dialog erstellen
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"📊 Dashboard - {server_config.get('name', 'Server')}")
        dialog.geometry("1200x800")
        dialog.transient(self)
        
        # Zentrieren
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 1200) // 2
        y = (dialog.winfo_screenheight() - 800) // 2
        dialog.geometry(f"1200x800+{x}+{y}")
        
        # RCON Settings
        rcon_port = server_config.get("rcon_port", 27020)
        rcon_password = server_config.get("admin_password", server_config.get("rcon_password", ""))
        
        # Map aus Server-Config extrahieren
        current_map = "TheIsland_WP"  # Default
        
        # Aus Config
        if server_config.get("map") and server_config.get("map") in ARK_MAP_DATA:
            current_map = server_config.get("map")
        
        # Aus Start-Params
        start_params = server_config.get("start_params", "")
        for map_param in ARK_MAP_DATA.keys():
            if map_param in start_params:
                current_map = map_param
                break
        
        # Aus SavedArks Ordner
        server_dir = instance.get_server_dir()
        game_info = SUPPORTED_GAMES.get(server_config.get("game", ""), {})
        save_path = os.path.join(server_dir, game_info.get("save_path", ""))
        
        if os.path.exists(save_path):
            for item in os.listdir(save_path):
                item_path = os.path.join(save_path, item)
                if os.path.isdir(item_path):
                    for map_param in ARK_MAP_DATA.keys():
                        clean_param = map_param.replace("_WP", "")
                        if clean_param.lower() in item.lower():
                            current_map = map_param
                            break
        
        # RCON Client
        rcon_client = RCONClient(host="127.0.0.1", port=rcon_port, password=rcon_password)
        
        # Map Manager
        map_manager = ArkMapManager(PATHS.get("base", "."))
        
        # Save Parser
        save_parser = ArkSaveParser(save_path)
        
        # Status-Variablen
        rcon_connected = ctk.BooleanVar(value=False)
        online_players = []
        map_image = None
        map_photo = None
        save_data = {"players": [], "tamed_dinos": [], "tribes": []}
        canvas_size = [800, 600]
        show_players = ctk.BooleanVar(value=True)
        show_dinos = ctk.BooleanVar(value=True)
        show_offline = ctk.BooleanVar(value=True)
        pw_visible = ctk.BooleanVar(value=False)
        
        # Layout: Links = Karte, Rechts = Controls
        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Linke Seite: Karte
        left_frame = ctk.CTkFrame(main_frame, fg_color="#1a1a2e")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # Map Header
        map_header = ctk.CTkFrame(left_frame, fg_color="#252545")
        map_header.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(map_header, text=f"🗺️ {ARK_MAP_DATA.get(current_map, {}).get('name', current_map)}",
            font=("Segoe UI", 16, "bold")).pack(side="left", padx=10, pady=5)
        
        map_status_label = ctk.CTkLabel(map_header, text="", font=("Segoe UI", 11))
        map_status_label.pack(side="right", padx=10)
        
        # Filter
        filter_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        filter_frame.pack(fill="x", padx=5)
        
        ctk.CTkCheckBox(filter_frame, text="👤 Spieler", variable=show_players,
            height=25, checkbox_height=18, checkbox_width=18
        ).pack(side="left", padx=10, pady=5)
        
        ctk.CTkCheckBox(filter_frame, text="🦖 Dinos", variable=show_dinos,
            height=25, checkbox_height=18, checkbox_width=18
        ).pack(side="left", padx=10, pady=5)
        
        ctk.CTkCheckBox(filter_frame, text="👻 Offline", variable=show_offline,
            height=25, checkbox_height=18, checkbox_width=18
        ).pack(side="left", padx=10, pady=5)
        
        # Buttons (rechts in filter_frame)
        def import_map_image():
            """Importiert ein Map-Bild manuell"""
            file_path = filedialog.askopenfilename(
                title=f"Map-Bild für {ARK_MAP_DATA.get(current_map, {}).get('name', current_map)} auswählen",
                filetypes=[("Bilder", "*.jpg *.jpeg *.png *.webp"), ("Alle Dateien", "*.*")]
            )
            if file_path:
                success, msg = map_manager.import_map_manually(current_map, file_path)
                if success:
                    messagebox.showinfo("Erfolg", f"Map-Bild importiert!")
                    load_map()
                else:
                    messagebox.showerror("Fehler", f"Import fehlgeschlagen:\n{msg}")
        
        def show_debug_info():
            """Zeigt Debug-Infos an"""
            found_save = save_parser.find_save_file(current_map)
            info = f"""📂 Save-Pfad: {save_parser.save_dir}
📁 Existiert: {os.path.exists(save_parser.save_dir)}
🗺️ Map: {current_map} ({ARK_MAP_DATA.get(current_map, {}).get('name', '?')})
💾 Save-Datei: {found_save if found_save else 'Nicht gefunden'}
🖼️ PIL: {PIL_AVAILABLE}
📍 Map gecacht: {map_manager.is_cached(current_map)}

👥 Geladene Spieler: {len(save_data.get('players', []))}"""
            
            for p in save_data.get('players', [])[:5]:
                info += f"\n   • {p.get('name', '?')} (Lvl {p.get('level', '?')})"
            
            messagebox.showinfo("Debug Info", info)
        
        ctk.CTkButton(filter_frame, text="📥", width=30, height=25, 
            command=import_map_image, fg_color="#555555"
        ).pack(side="right", padx=2, pady=5)
        
        ctk.CTkButton(filter_frame, text="ℹ️", width=30, height=25, 
            command=show_debug_info, fg_color="gray"
        ).pack(side="right", padx=2, pady=5)
        
        def update_save_data():
            nonlocal save_data
            map_status_label.configure(text="⏳ Lade...")
            data = save_parser.get_all_data(current_map, force_refresh=True,
                progress_callback=lambda s: dialog.after(0, lambda: map_status_label.configure(text=s)))
            save_data = data
            
            # Status aktualisieren
            save_info = data.get("save_info")
            if save_info:
                save_time = save_info.get("last_save", datetime.now()).strftime("%H:%M:%S")
                status = f"✓ {ARK_MAP_DATA.get(current_map, {}).get('name', '?')} | Save: {save_time} | {len(data['players'])} Spieler"
            else:
                status = f"⚠️ Keine Save-Daten"
            
            dialog.after(0, lambda: map_status_label.configure(text=status))
            dialog.after(0, update_map_markers)
        
        ctk.CTkButton(filter_frame, text="🔄 Save laden", width=100, height=25,
            command=lambda: threading.Thread(target=update_save_data, daemon=True).start()
        ).pack(side="right", padx=5, pady=5)
        
        # Karten-Canvas
        canvas_frame = ctk.CTkFrame(left_frame, fg_color="#0a0a15")
        canvas_frame.pack(fill="both", expand=True)
        
        map_canvas = tk.Canvas(canvas_frame, bg="#0a0a15", highlightthickness=0)
        map_canvas.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Rechte Seite: Controls
        right_frame = ctk.CTkFrame(main_frame, fg_color="#1a1a2e", width=300)
        right_frame.pack(side="right", fill="y", padx=(5, 0))
        right_frame.pack_propagate(False)
        
        # RCON Verbindung
        rcon_frame = ctk.CTkFrame(right_frame)
        rcon_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(rcon_frame, text="📡 RCON Verbindung", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=10, pady=5)
        
        rcon_status = ctk.CTkLabel(rcon_frame, text="⚠️ RCON muss in GameUserSettings.ini aktiviert sein!",
            text_color="orange", font=("Segoe UI", 12))
        rcon_status.pack(anchor="w", padx=10)
        
        # Port
        port_frame = ctk.CTkFrame(rcon_frame, fg_color="transparent")
        port_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(port_frame, text="RCON Port:", width=80).pack(side="left")
        port_entry = ctk.CTkEntry(port_frame, width=80)
        port_entry.insert(0, str(rcon_port))
        port_entry.pack(side="left", padx=5)
        
        # Password mit Toggle
        pw_frame = ctk.CTkFrame(rcon_frame, fg_color="transparent")
        pw_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(pw_frame, text="RCON Passwort:", width=80).pack(side="left")
        
        pw_entry = ctk.CTkEntry(pw_frame, width=120, show="*")
        pw_entry.insert(0, rcon_password)
        pw_entry.pack(side="left", padx=5)
        
        def toggle_pw_visibility():
            if pw_visible.get():
                pw_entry.configure(show="")
                pw_toggle_btn.configure(text="🙈")
            else:
                pw_entry.configure(show="*")
                pw_toggle_btn.configure(text="👁")
            pw_visible.set(not pw_visible.get())
        
        pw_toggle_btn = ctk.CTkButton(pw_frame, text="👁", width=30, height=28, command=toggle_pw_visibility)
        pw_toggle_btn.pack(side="left", padx=2)
        
        # Connect/Disconnect Buttons
        btn_frame_rcon = ctk.CTkFrame(rcon_frame, fg_color="transparent")
        btn_frame_rcon.pack(fill="x", padx=10, pady=10)
        
        def connect_rcon():
            nonlocal online_players
            try:
                port = int(port_entry.get())
                password = pw_entry.get()
            except:
                messagebox.showerror("Fehler", "Ungültiger Port")
                return
            
            rcon_client.port = port
            rcon_client.password = password
            
            players, error = rcon_client.list_players()
            if error:
                rcon_status.configure(text=f"❌ {error}", text_color="red")
                rcon_connected.set(False)
            else:
                rcon_connected.set(True)
                online_players = players
                rcon_status.configure(text=f"✓ RCON Verbunden ✓", text_color="green")
                update_player_list()
                update_map_markers()
                start_rcon_polling()
        
        def disconnect_rcon():
            nonlocal online_players
            rcon_connected.set(False)
            online_players = []
            rcon_status.configure(text="⚪ Getrennt", text_color="gray")
            update_player_list()
            update_map_markers()
        
        ctk.CTkButton(btn_frame_rcon, text="🔗 Verbinden", command=connect_rcon,
            fg_color="green", hover_color="darkgreen", width=100).pack(side="left", padx=5)
        
        ctk.CTkButton(btn_frame_rcon, text="⛔ Trennen", command=disconnect_rcon,
            fg_color="red", hover_color="darkred", width=100).pack(side="left", padx=5)
        
        # Online Spieler Liste
        players_frame = ctk.CTkFrame(right_frame)
        players_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(players_frame, text="👥 Online Spieler", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=10, pady=5)
        
        player_list_frame = ctk.CTkScrollableFrame(players_frame, height=150)
        player_list_frame.pack(fill="x", padx=5, pady=5)
        
        def update_player_list():
            for widget in player_list_frame.winfo_children():
                widget.destroy()
            
            if online_players:
                for player in online_players:
                    name = player.get("name", "?")
                    pf = ctk.CTkFrame(player_list_frame, fg_color="#2a2a4a")
                    pf.pack(fill="x", pady=2)
                    ctk.CTkLabel(pf, text=f"🟢 {name}", font=("Segoe UI", 11)).pack(side="left", padx=10, pady=5)
            else:
                ctk.CTkLabel(player_list_frame, text="Keine Spieler online", text_color="gray").pack(pady=10)
        
        update_player_list()
        
        # Quick Actions
        actions_frame = ctk.CTkFrame(right_frame)
        actions_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(actions_frame, text="⚡ Quick Actions", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=10, pady=5)
        
        actions_grid = ctk.CTkFrame(actions_frame, fg_color="transparent")
        actions_grid.pack(fill="x", padx=10, pady=5)
        
        def send_broadcast():
            msg = broadcast_entry.get()
            if msg and rcon_connected.get():
                response, err = rcon_client.broadcast(msg)
                if not err:
                    broadcast_entry.delete(0, "end")
                    add_to_chat(f"[SERVER] {msg}")
        
        def save_world():
            if rcon_connected.get():
                rcon_client.save_world()
                add_to_chat("[SYSTEM] Welt gespeichert!")
        
        def destroy_wild_dinos():
            if rcon_connected.get() and messagebox.askyesno("Bestätigung", "Alle wilden Dinos löschen?"):
                rcon_client.destroy_wild_dinos()
                add_to_chat("[SYSTEM] Wilde Dinos gelöscht!")
        
        broadcast_frame = ctk.CTkFrame(actions_grid, fg_color="transparent")
        broadcast_frame.pack(fill="x", pady=2)
        
        broadcast_entry = ctk.CTkEntry(broadcast_frame, placeholder_text="Nachricht...", width=180)
        broadcast_entry.pack(side="left", padx=(0, 5))
        
        ctk.CTkButton(broadcast_frame, text="📢", command=send_broadcast, width=40, fg_color="#4CAF50").pack(side="left")
        
        btn_row = ctk.CTkFrame(actions_grid, fg_color="transparent")
        btn_row.pack(fill="x", pady=5)
        
        ctk.CTkButton(btn_row, text="💾 Save", command=save_world, width=70, height=30, fg_color="#2196F3").pack(side="left", padx=2)
        ctk.CTkButton(btn_row, text="🦖 Dino Wipe", command=destroy_wild_dinos, width=90, height=30, fg_color="#FF9800").pack(side="left", padx=2)
        
        # RCON Konsole
        console_frame = ctk.CTkFrame(right_frame)
        console_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        ctk.CTkLabel(console_frame, text="💻 RCON Konsole", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=10, pady=5)
        
        console_output = ctk.CTkTextbox(console_frame, height=120, font=("Consolas", 10))
        console_output.pack(fill="both", expand=True, padx=5, pady=5)
        console_output.configure(state="disabled")
        
        def add_to_chat(msg):
            console_output.configure(state="normal")
            timestamp = datetime.now().strftime("%H:%M:%S")
            console_output.insert("end", f"[{timestamp}] {msg}\n")
            console_output.see("end")
            console_output.configure(state="disabled")
        
        cmd_frame = ctk.CTkFrame(console_frame, fg_color="transparent")
        cmd_frame.pack(fill="x", padx=5, pady=5)
        
        cmd_entry = ctk.CTkEntry(cmd_frame, placeholder_text="RCON Befehl...", width=220)
        cmd_entry.pack(side="left", padx=(0, 5))
        
        def send_command():
            cmd = cmd_entry.get()
            if cmd and rcon_connected.get():
                add_to_chat(f"> {cmd}")
                response, err = rcon_client.send_command(cmd)
                if err:
                    add_to_chat(f"[ERROR] {err}")
                elif response:
                    add_to_chat(response)
                cmd_entry.delete(0, "end")
        
        ctk.CTkButton(cmd_frame, text="Senden", command=send_command, width=70).pack(side="left")
        cmd_entry.bind("<Return>", lambda e: send_command())
        
        # Funktionen
        def update_map_markers():
            map_canvas.delete("marker")
            canvas_size[0] = max(map_canvas.winfo_width(), 600)
            canvas_size[1] = max(map_canvas.winfo_height(), 500)
            
            online_names = [p.get("name", "").lower() for p in online_players]
            
            # Online-Spieler Liste anzeigen
            y_offset = 20
            if online_players:
                map_canvas.create_text(15, y_offset, text=f"👥 Online ({len(online_players)}):", fill="#3fb771",
                    font=("Segoe UI", 12, "bold"), tags="marker", anchor="nw")
                y_offset += 22
                
                for player in online_players[:10]:
                    name = player.get("name", "?")
                    # Level aus save_data
                    level = 1
                    for p in save_data.get("players", []):
                        if p.get("name", "").lower() == name.lower():
                            level = p.get("level", 1)
                            break
                    
                    label = f"  🟢 {name}" + (f" (Lvl {level})" if level > 1 else "")
                    map_canvas.create_text(15, y_offset, text=label, fill="#3fb771",
                        font=("Segoe UI", 12), tags="marker", anchor="nw")
                    y_offset += 18
            else:
                map_canvas.create_text(15, y_offset, text="👥 Keine Spieler online", fill="#666666",
                    font=("Segoe UI", 11), tags="marker", anchor="nw")
                y_offset += 22
            
            # Offline-Spieler (wenn aktiviert)
            if show_offline.get() and save_data.get("players"):
                offline_players = [p for p in save_data["players"] 
                                   if p.get("name", "").lower() not in online_names 
                                   and p.get("name", "") != "Unknown"]
                
                if offline_players:
                    y_offset += 10
                    map_canvas.create_text(15, y_offset, text=f"👻 Offline ({len(offline_players)}):", fill="#888888",
                        font=("Segoe UI", 11, "bold"), tags="marker", anchor="nw")
                    y_offset += 20
                    
                    for player in offline_players[:5]:
                        name = player.get("name", "?")
                        level = player.get("level", 1)
                        label = f"  ⚫ {name}" + (f" (Lvl {level})" if level > 1 else "")
                        map_canvas.create_text(15, y_offset, text=label, fill="#666666",
                            font=("Segoe UI", 12), tags="marker", anchor="nw")
                        y_offset += 16
            
            # Hinweis
            map_canvas.create_text(15, canvas_size[1] - 15, 
                text="ℹ️ Positionen nicht verfügbar (ARK ASA Limit)", fill="#444444",
                font=("Segoe UI", 12), tags="marker", anchor="nw")
        
        def draw_fallback_map(w, h, error_msg=""):
            """Zeichnet Fallback-Map wenn kein Bild verfügbar"""
            map_canvas.delete("all")
            
            # Dunkler Hintergrund
            map_canvas.create_rectangle(0, 0, w, h, fill="#0a0a15", outline="")
            
            # Grid
            grid_color = "#1a1a2a"
            for i in range(0, w, 50):
                map_canvas.create_line(i, 0, i, h, fill=grid_color)
            for i in range(0, h, 50):
                map_canvas.create_line(0, i, w, i, fill=grid_color)
            
            # Info-Text
            map_canvas.create_text(w//2, h//2 - 20, text=f"🗺️ {ARK_MAP_DATA.get(current_map, {}).get('name', current_map)}",
                fill="#555555", font=("Segoe UI", 16, "bold"))
            
            if error_msg:
                map_canvas.create_text(w//2, h//2 + 10, text=error_msg, fill="#ff6666", font=("Segoe UI", 12))
            
            map_canvas.create_text(w//2, h//2 + 40, text="Klicke 📥 um ein Map-Bild zu importieren",
                fill="#444444", font=("Segoe UI", 12))
        
        def load_map():
            nonlocal map_image, map_photo
            map_status_label.configure(text="⏳ Lade Karte...")
            
            def do_load():
                nonlocal map_image, map_photo
                try:
                    success, msg = map_manager.ensure_map(current_map, 
                        lambda s: dialog.after(0, lambda: map_status_label.configure(text=s)))
                    
                    if success:
                        dialog.update_idletasks()
                        canvas_w = max(map_canvas.winfo_width(), 600)
                        canvas_h = max(map_canvas.winfo_height(), 500)
                        
                        if PIL_AVAILABLE:
                            map_image = map_manager.get_map_image(current_map, (canvas_w, canvas_h))
                            
                            if map_image:
                                map_photo = ImageTk.PhotoImage(map_image)
                                def update_canvas():
                                    map_canvas.delete("all")
                                    map_canvas.create_image(canvas_w//2, canvas_h//2, image=map_photo, anchor="center")
                                    map_status_label.configure(text=f"✓ {ARK_MAP_DATA[current_map]['name']}", text_color="green")
                                    update_map_markers()
                                dialog.after(0, update_canvas)
                            else:
                                dialog.after(0, lambda: draw_fallback_map(canvas_w, canvas_h, "Bild konnte nicht geladen werden"))
                        else:
                            dialog.after(0, lambda: draw_fallback_map(canvas_w, canvas_h, "PIL nicht installiert"))
                    else:
                        canvas_w = max(map_canvas.winfo_width(), 600)
                        canvas_h = max(map_canvas.winfo_height(), 500)
                        dialog.after(0, lambda: draw_fallback_map(canvas_w, canvas_h, f"Download fehlgeschlagen: {msg}"))
                        dialog.after(0, lambda: map_status_label.configure(
                            text=f"⚠️ {ARK_MAP_DATA.get(current_map, {}).get('name', '?')} | 📥 = Import"))
                except Exception as e:
                    err_msg = str(e)
                    dialog.after(0, lambda: map_status_label.configure(text=f"❌ Fehler: {err_msg}"))
            
            threading.Thread(target=do_load, daemon=True).start()
        
        def start_rcon_polling():
            def poll():
                nonlocal online_players
                while rcon_connected.get() and dialog.winfo_exists():
                    try:
                        players, error = rcon_client.list_players()
                        if not error:
                            online_players = players
                            dialog.after(0, update_player_list)
                            dialog.after(0, update_map_markers)
                    except:
                        pass
                    time.sleep(30)
            
            threading.Thread(target=poll, daemon=True).start()
        
        # Initial: Karte laden + Spieler laden
        dialog.after(500, load_map)
        dialog.after(1000, lambda: threading.Thread(target=update_save_data, daemon=True).start())

    def show_log_viewer(self, server_id):
        """Öffnet den Log-Viewer für einen Server"""
        t = self.config_manager.get_text
        instance = self.server_instances.get(server_id)
        server_config = self.config_manager.servers.get(server_id, {})
        
        if not instance:
            return
        
        # Dialog erstellen
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"📜 {t('server_logs')} - {server_config.get('name', 'Server')}")
        dialog.geometry("900x600")
        dialog.transient(self)
        
        # Zentrieren
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 900) // 2
        y = (dialog.winfo_screenheight() - 600) // 2
        dialog.geometry(f"900x600+{x}+{y}")
        
        # Toolbar
        toolbar = ctk.CTkFrame(dialog, height=50)
        toolbar.pack(fill="x", padx=10, pady=10)
        toolbar.pack_propagate(False)
        
        # Suche
        ctk.CTkLabel(toolbar, text=f"🔍 {t('search')}:").pack(side="left", padx=(10, 5))
        search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(toolbar, textvariable=search_var, width=200)
        search_entry.pack(side="left", padx=5)
        
        # Filter
        filter_var = ctk.StringVar(value="all")
        ctk.CTkLabel(toolbar, text="Filter:").pack(side="left", padx=(20, 5))
        filter_menu = ctk.CTkOptionMenu(
            toolbar,
            variable=filter_var,
            values=[t("log_level_all"), t("log_level_errors"), t("log_level_warnings")],
            width=120
        )
        filter_menu.pack(side="left", padx=5)
        
        # Auto-Scroll Checkbox
        auto_scroll_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(toolbar, text=t("auto_scroll"), variable=auto_scroll_var).pack(side="left", padx=20)
        
        # Log-Textbox
        log_frame = ctk.CTkFrame(dialog)
        log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        log_text = ctk.CTkTextbox(log_frame, font=("Consolas", 11), wrap="none")
        log_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        def update_logs():
            """Aktualisiert die Log-Anzeige"""
            # Filter-Wert umwandeln
            filter_val = filter_var.get()
            if filter_val == t("log_level_errors"):
                level = "errors"
            elif filter_val == t("log_level_warnings"):
                level = "warnings"
            else:
                level = "all"
            
            logs = instance.get_server_logs(
                max_lines=500,
                search_filter=search_var.get(),
                level_filter=level
            )
            
            log_text.configure(state="normal")
            log_text.delete("1.0", "end")
            
            for log in logs:
                # Farbcodierung
                if any(x in log.lower() for x in ["error", "fail", "exception", "❌", "critical"]):
                    log_text.insert("end", log + "\n")  # Rot wäre besser, aber CTkTextbox unterstützt das nicht einfach
                elif any(x in log.lower() for x in ["warn", "⚠️", "warning"]):
                    log_text.insert("end", log + "\n")
                else:
                    log_text.insert("end", log + "\n")
            
            log_text.configure(state="disabled")
            
            if auto_scroll_var.get():
                log_text.see("end")
        
        # Initial laden
        update_logs()
        
        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(
            btn_frame,
            text=f"🔄 {t('refresh')}",
            command=update_logs,
            width=120
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text=f"🗑️ {t('clear')}",
            command=lambda: instance.log_messages.clear() or update_logs(),
            width=120,
            fg_color="gray"
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text=t("cancel"),
            command=dialog.destroy,
            width=100,
            fg_color="gray"
        ).pack(side="right", padx=5)
        
        # Auto-Update alle 3 Sekunden
        def auto_update():
            if dialog.winfo_exists():
                update_logs()
                dialog.after(3000, auto_update)
        
        dialog.after(3000, auto_update)
        
        # Such-Binding
        search_entry.bind("<Return>", lambda e: update_logs())
        search_entry.bind("<KeyRelease>", lambda e: dialog.after(300, update_logs))
        filter_var.trace("w", lambda *args: update_logs())
