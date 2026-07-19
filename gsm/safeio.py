"""Macht sys.stdout / sys.stderr absolut crash-sicher.

Hintergrund: Im kompilierten Windows-`.exe` (besonders im Fenster-Modus) ist die
Standardausgabe oft `None` oder auf cp1252 gesetzt. Ein `print()` mit Emojis
(z. B. „🚀", „🔐") wirft dann UnicodeEncodeError und kann den Aufrufer abschiessen
(Server-Start, Auto-Update ...). Dieser Wrapper faengt JEDEN Schreibfehler ab.

Nutzung ganz am Programmstart:  from gsm import safeio; safeio.install()
"""

import sys


class _SafeStream:
    def __init__(self, real):
        self._real = real

    def write(self, s):
        r = self._real
        if r is None:
            return
        try:
            r.write(s)
        except Exception:
            # Zeichen, die die Konsole nicht kann (Emojis unter cp1252), ersetzen
            try:
                r.write(s.encode("ascii", "replace").decode("ascii"))
            except Exception:
                pass

    def flush(self):
        r = self._real
        if r is not None:
            try:
                r.flush()
            except Exception:
                pass

    @property
    def encoding(self):
        return getattr(self._real, "encoding", "utf-8") if self._real is not None else "utf-8"

    def isatty(self):
        try:
            return bool(self._real and self._real.isatty())
        except Exception:
            return False

    def fileno(self):
        if self._real is not None and hasattr(self._real, "fileno"):
            return self._real.fileno()
        raise OSError("no fileno")


def install():
    for name in ("stdout", "stderr"):
        s = getattr(sys, name, None)
        if isinstance(s, _SafeStream):
            continue
        if s is not None:
            try:
                s.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
        try:
            setattr(sys, name, _SafeStream(s))
        except Exception:
            pass
