"""Zentrale Design-Tokens für die Desktop-GUI.

Ein Ort für Farben, Schrift, Radien und Abstände, damit das Aussehen konsistent
bleibt und sich zentral anpassen lässt. Palette: neutraler, kühler „Kontrollraum"-
Look mit EINEM Akzent (Azur) und entsättigten Ampel-Statusfarben.

Ebenen-Staffelung (dunkel -> hell):
    GROUND  < SURFACE < SURFACE_2 < SURFACE_3
"""

# ---- Neutrale Flächen (leicht kühler Stich, bewusst gewählt) ----
GROUND    = "#0e1116"   # Fenster-/Sidebar-Hintergrund
SURFACE   = "#161b22"   # Karten, Panels
SURFACE_2 = "#1c222b"   # erhöhte Flächen, Header von Karten
SURFACE_3 = "#232b36"   # Buttons/Chips auf Flächen
BORDER    = "#2a323d"   # dezente Rahmen
HOVER     = "#2f3947"   # Hover-Fläche

# ---- Text ----
TEXT       = "#e8ecf2"
TEXT_MUTED = "#9099a6"
TEXT_FAINT = "#626b78"

# ---- Ein Interaktions-Akzent ----
ACCENT      = "#4c9aff"
ACCENT_HOVER = "#3d84e0"
ACCENT_WEAK = "#1d2f4a"

# ---- Semantische Statusfarben (entsättigt, kein Neon) ----
OK       = "#3fb771"
OK_BG    = "#14301f"
WARN     = "#d8a23a"
WARN_BG  = "#33280f"
CRIT     = "#e5574e"
CRIT_BG  = "#35191a"

# ---- Schrift ----
FONT = "Segoe UI"
MONO = "Consolas"

# ---- Radien / Abstände ----
RADIUS   = 14
RADIUS_S = 10
RADIUS_XS = 7
GAP = 16
