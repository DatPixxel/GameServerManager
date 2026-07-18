"""Wiederverwendbarer Fortschritts-Dialog für lange Operationen.

Zeigt Status, einen animierten Balken und einen Live-Log; am Ende einen klaren
Erfolg-/Fehlerzustand mit aktivem „Schließen". Aktualisierung ist thread-sicher
über self.after(0, ...) – so wie der Rest der GUI aus Worker-Threads updatet.
"""

import customtkinter as ctk

from gsm.ui import theme as th


class ProgressDialog(ctk.CTkToplevel):
    def __init__(self, parent, title="Vorgang läuft", status="Bitte warten…"):
        super().__init__(parent)
        self.title(title)
        self.geometry("640x430")
        self.transient(parent)
        self.configure(fg_color=th.GROUND)

        self.update_idletasks()
        x = (self.winfo_screenwidth() - 640) // 2
        y = (self.winfo_screenheight() - 430) // 2
        self.geometry(f"640x430+{x}+{y}")

        self._done = False
        self.protocol("WM_DELETE_WINDOW", self._on_close_request)

        ctk.CTkLabel(
            self, text=title, font=(th.FONT, 16, "bold"), text_color=th.TEXT, anchor="w"
        ).pack(fill="x", padx=20, pady=(18, 2))

        self.status_label = ctk.CTkLabel(
            self, text=status, font=(th.FONT, 12), text_color=th.TEXT_MUTED, anchor="w"
        )
        self.status_label.pack(fill="x", padx=20)

        self.bar = ctk.CTkProgressBar(
            self, height=8, progress_color=th.ACCENT, fg_color=th.SURFACE_3, corner_radius=999
        )
        self.bar.pack(fill="x", padx=20, pady=12)
        self.bar.configure(mode="indeterminate")
        self.bar.start()

        self.logbox = ctk.CTkTextbox(
            self, fg_color=th.SURFACE, text_color=th.TEXT_MUTED,
            font=(th.MONO, 11), corner_radius=th.RADIUS_S
        )
        self.logbox.pack(fill="both", expand=True, padx=20, pady=(0, 12))
        self.logbox.configure(state="disabled")

        self.close_btn = ctk.CTkButton(
            self, text="Schließen", command=self.destroy, state="disabled",
            fg_color=th.SURFACE_2, hover_color=th.HOVER, text_color=th.TEXT,
            border_width=1, border_color=th.BORDER, corner_radius=th.RADIUS_XS, width=120
        )
        self.close_btn.pack(anchor="e", padx=20, pady=(0, 16))

        self.grab_set()

    def _on_close_request(self):
        # Während der Vorgang läuft, nicht schließbar (sonst verwaiste Referenz)
        if self._done:
            self.destroy()

    def set_status(self, text):
        self.after(0, lambda: self.status_label.configure(text=text))

    def append_log(self, line):
        def _append():
            try:
                self.logbox.configure(state="normal")
                self.logbox.insert("end", line + "\n")
                self.logbox.see("end")
                self.logbox.configure(state="disabled")
            except Exception:
                pass
        self.after(0, _append)

    def finish(self, success, message=""):
        def _finish():
            self._done = True
            try:
                self.bar.stop()
                self.bar.configure(mode="determinate")
                self.bar.set(1.0)
                self.bar.configure(progress_color=(th.OK if success else th.CRIT))
                self.status_label.configure(
                    text=message or ("Fertig!" if success else "Fehlgeschlagen."),
                    text_color=(th.OK if success else th.CRIT)
                )
                self.close_btn.configure(state="normal")
            except Exception:
                pass
        self.after(0, _finish)
