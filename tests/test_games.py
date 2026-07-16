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
