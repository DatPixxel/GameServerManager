"""Ermittelt die eigenen Netzwerkadressen für die Verbindungsanzeige.

Bewusst ohne Web- oder GUI-Abhängigkeit, damit die Einordnung der Adressen
testbar bleibt: Genau dort steckt die Logik, die man leicht falsch macht.
"""

import ipaddress
import socket

import psutil

# Tailscale vergibt Adressen aus diesem Bereich (CGNAT-Block).
TAILSCALE_NETZ = ipaddress.ip_network('100.64.0.0/10')

# Reihenfolge der Anzeige: So spielen die Leute tatsächlich.
REIHENFOLGE = {'tailscale': 0, 'heimnetz': 1, 'oeffentlich': 2}

BEZEICHNUNG = {
    'tailscale': 'Tailscale (von überall)',
    'heimnetz': 'Heimnetz (gleiches WLAN)',
    'oeffentlich': 'Öffentlich',
}


def art_der_adresse(adresse):
    """Ordnet eine IPv4-Adresse ein.

    Gibt 'tailscale', 'heimnetz', 'oeffentlich' oder None zurück; None heisst
    "nicht anzeigen" (Loopback, Link-Local, unbrauchbar).
    """
    try:
        ip = ipaddress.ip_address(adresse.strip())
    except (ValueError, AttributeError):
        return None

    if not isinstance(ip, ipaddress.IPv4Address):
        return None
    if ip.is_loopback or ip.is_link_local or ip.is_unspecified or ip.is_multicast:
        return None
    if ip in TAILSCALE_NETZ:
        return 'tailscale'
    if ip.is_private:
        return 'heimnetz'
    return 'oeffentlich'


def sortiere_adressen(adressen):
    """Bringt die Adressen in die Reihenfolge, in der sie angeboten werden."""
    return sorted(adressen, key=lambda a: (REIHENFOLGE.get(a['art'], 9), a['adresse']))


def eigene_adressen():
    """Alle brauchbaren IPv4-Adressen dieses Rechners.

    Liefert eine Liste aus {'adresse', 'art', 'bezeichnung'}. Ist nichts zu
    finden, bleibt die Liste leer — die Oberfläche zeigt dann einen Hinweis
    statt einer falschen Adresse.
    """
    gefunden = {}

    try:
        for eintraege in psutil.net_if_addrs().values():
            for eintrag in eintraege:
                if eintrag.family != socket.AF_INET:
                    continue
                art = art_der_adresse(eintrag.address)
                if art and eintrag.address not in gefunden:
                    gefunden[eintrag.address] = art
    except Exception:
        # Lieber keine Adresse als ein Absturz der Detailansicht
        pass

    return sortiere_adressen([
        {'adresse': adresse, 'art': art, 'bezeichnung': BEZEICHNUNG[art]}
        for adresse, art in gefunden.items()
    ])
