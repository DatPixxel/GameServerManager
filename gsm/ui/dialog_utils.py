"""Kleine Helfer für Dialog-Bedienbarkeit (Tastatur/Fokus)."""


def bind_dialog_keys(dialog, on_submit=None, focus_widget=None):
    """Bindet Standard-Tasten an einen Dialog.

    - Escape schließt den Dialog.
    - Enter/Return löst on_submit aus (falls angegeben).
    - focus_widget bekommt beim Öffnen den Eingabefokus (falls angegeben).
    """
    dialog.bind("<Escape>", lambda e: dialog.destroy())
    if on_submit is not None:
        dialog.bind("<Return>", lambda e: on_submit())
    if focus_widget is not None:
        try:
            focus_widget.focus_set()
        except Exception:
            pass
