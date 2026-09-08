"""Tests der Adress-Einordnung fuer die Verbindungsanzeige.

Die Einordnung entscheidet, welche Adresse dem Nutzer zuerst angeboten wird.
Faellt Tailscale faelschlich unter "Heimnetz", bekommt er die falsche Adresse
zuerst - und wundert sich, warum ein Mitspieler von aussen nicht verbinden kann.
"""

import pytest

from gsm.netzwerk import art_der_adresse, sortiere_adressen


@pytest.mark.parametrize("adresse", [
    "100.64.0.1",       # untere Grenze des Tailscale-Bereichs
    "100.105.102.31",
    "100.127.255.254",  # obere Grenze
])
def test_tailscale_bereich(adresse):
    assert art_der_adresse(adresse) == "tailscale"


@pytest.mark.parametrize("adresse", [
    "192.168.1.50",
    "10.0.0.7",
    "172.16.3.4",
    "100.63.255.255",   # knapp unterhalb des Tailscale-Bereichs, aber privat
    "100.128.0.1",      # knapp oberhalb - kein Tailscale mehr
])
def test_private_und_grenzfaelle(adresse):
    art = art_der_adresse(adresse)
    # 100.63.x und 100.128.x liegen ausserhalb des CGNAT-Blocks und sind oeffentlich
    erwartet = "heimnetz" if adresse.startswith(("192.168", "10.", "172.16")) else "oeffentlich"
    assert art == erwartet


@pytest.mark.parametrize("adresse", [
    "127.0.0.1",        # Loopback
    "169.254.1.1",      # Link-Local
    "0.0.0.0",
    "224.0.0.1",        # Multicast
    "keine-adresse",
    "",
    None,
])
def test_nicht_anzeigbare_adressen(adresse):
    assert art_der_adresse(adresse) is None


def test_oeffentliche_adresse():
    assert art_der_adresse("81.62.14.9") == "oeffentlich"


def test_ipv6_wird_ausgelassen():
    # Die Anzeige beschraenkt sich bewusst auf IPv4 - Spielserver werden so verbunden
    assert art_der_adresse("fd7a:115c:a1e0::1") is None


def test_reihenfolge_tailscale_zuerst():
    eingabe = [
        {"adresse": "192.168.1.50", "art": "heimnetz"},
        {"adresse": "81.62.14.9", "art": "oeffentlich"},
        {"adresse": "100.105.102.31", "art": "tailscale"},
    ]
    assert [a["art"] for a in sortiere_adressen(eingabe)] == ["tailscale", "heimnetz", "oeffentlich"]


def test_gleiche_art_bleibt_stabil_sortiert():
    eingabe = [
        {"adresse": "192.168.1.90", "art": "heimnetz"},
        {"adresse": "192.168.1.20", "art": "heimnetz"},
    ]
    assert [a["adresse"] for a in sortiere_adressen(eingabe)] == ["192.168.1.20", "192.168.1.90"]
