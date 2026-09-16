"""Sanity-Checks für den Spielkatalog (schützt vor Datenverlust beim Refactoring)."""


def test_supported_games_structure(gsm_module):
    g = gsm_module
    games = g.SUPPORTED_GAMES
    assert isinstance(games, dict)
    assert len(games) >= 20
    # Zentrale Titel müssen vorhanden bleiben
    for title in ("ARK: Survival Ascended", "Rust", "Valheim", "Palworld"):
        assert title in games

    # Jeder Eintrag hat die Pflichtfelder
    for title, info in games.items():
        assert "exe_path" in info, f"{title} ohne exe_path"
        assert "default_ports" in info, f"{title} ohne default_ports"
        assert "icon" in info, f"{title} ohne icon"


def test_translations_present(gsm_module):
    g = gsm_module
    tr = g.TRANSLATIONS
    assert "de" in tr and "en" in tr
    assert isinstance(tr["de"], dict) and tr["de"]


def test_unreal_spiele_pfade_liegen_im_spielordner(gsm_module):
    """Bei Unreal-Servern liegen Konfiguration und Spielstaende im Spielordner.

    Bei Icarus fehlte dieses Praefix: config_path und save_path zeigten auf
    "IcarusServer/...", tatsaechlich liegt alles unter "Icarus/IcarusServer/...".
    Der Manager prueft mit os.path.exists und geht sonst kommentarlos weiter -
    die Folge waren leere Backups und ein leerer Konfigurations-Tab, ohne jede
    Fehlermeldung.
    """
    games = gsm_module.SUPPORTED_GAMES

    # Spiele, deren Server-exe in einem eigenen Spielordner liegt
    unreal = [
        "ARK: Survival Ascended",
        "Icarus",
        "StarRupture",
        "RuneScape: Dragonwilds",
    ]

    for titel in unreal:
        info = games.get(titel)
        assert info, f"{titel} fehlt im Katalog"
        ordner = info["exe_path"].split("/")[0]
        assert "/" in info["exe_path"], f"{titel}: exe_path ohne Spielordner"

        for feld in ("config_path", "save_path"):
            wert = info.get(feld, "")
            if not wert:
                continue
            assert wert.startswith(ordner + "/"), (
                f"{titel}: {feld} = '{wert}' liegt nicht unter '{ordner}/' - "
                f"der Manager wuerde dort nichts finden"
            )


def test_icarus_pfade_konkret(gsm_module):
    """Haelt die nachgemessenen Icarus-Pfade fest."""
    icarus = gsm_module.SUPPORTED_GAMES["Icarus"]
    assert icarus["save_path"] == "Icarus/IcarusServer/Saved/PlayerData"
    assert icarus["config_path"] == "Icarus/IcarusServer/Saved/Config/WindowsServer"
