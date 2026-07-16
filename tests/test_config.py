"""Charakterisierungstests für den ConfigManager (temporäres PATHS)."""


def test_config_roundtrip_and_password(gsm_module, temp_paths):
    g = gsm_module
    cm = g.ConfigManager()

    # Default-App-Config vorhanden
    assert "web" in cm.app_config
    assert cm.servers == {}

    # Admin-Passwort setzen + verifizieren (mit Persistenz)
    cm.set_admin_password("SuperGeheim1")
    assert cm.verify_password("SuperGeheim1") is True
    assert cm.verify_password("falsch") is False

    # Server hinzufügen -> wird persistiert und neu geladen
    cm.add_server("srv1", {"game": "Rust", "name": "Testserver"})
    cm2 = g.ConfigManager()
    assert "srv1" in cm2.servers
    assert cm2.servers["srv1"]["name"] == "Testserver"

    # Passwort übersteht Neuladen
    assert cm2.verify_password("SuperGeheim1") is True

    # Entfernen
    cm2.remove_server("srv1")
    cm3 = g.ConfigManager()
    assert "srv1" not in cm3.servers


def test_server_secret_encrypted_at_rest(gsm_module, temp_paths):
    g = gsm_module
    cm = g.ConfigManager()
    cm.add_server("srv2", {"game": "ARK: Survival Ascended", "admin_password": "topsecret"})

    # In-Memory bleibt Klartext
    assert cm.servers["srv2"]["admin_password"] == "topsecret"

    # Auf Platte: verschlüsselt (nur wenn DPAPI verfügbar, sonst Klartext-Fallback)
    import json
    with open(temp_paths["servers_config"], "r", encoding="utf-8") as f:
        raw = json.load(f)
    stored = raw["srv2"]["admin_password"]
    if g._dpapi_available():
        assert stored.startswith(g.SECRET_ENC_PREFIX)
    # Neu laden liefert wieder Klartext
    cm2 = g.ConfigManager()
    assert cm2.servers["srv2"]["admin_password"] == "topsecret"
