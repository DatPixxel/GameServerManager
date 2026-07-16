"""Charakterisierungstests für die Mod-Helfer."""


def test_normalize_mod_id(gsm_module):
    g = gsm_module
    assert g._normalize_mod_id("  12345 ") == "12345"
    assert g._normalize_mod_id(67890) == "67890"
    assert g._normalize_mod_id("abc") == ""
    assert g._normalize_mod_id(None) == ""
    assert g._normalize_mod_id("") == ""


def test_sanitize_pak_filename(gsm_module):
    g = gsm_module
    assert g._sanitize_pak_filename("mod.pak") == "mod.pak"
    # Pfad-Anteile werden entfernt (basename)
    assert g._sanitize_pak_filename("../../evil.pak") == "evil.pak"
    # Sonderzeichen werden ersetzt
    assert g._sanitize_pak_filename("my;mod$.pak") == "my_mod_.pak"
    # keine .pak-Endung -> leer
    assert g._sanitize_pak_filename("mod.txt") == ""
    assert g._sanitize_pak_filename("") == ""
    assert g._sanitize_pak_filename(None) == ""
