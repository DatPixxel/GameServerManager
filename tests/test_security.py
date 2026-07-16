"""Charakterisierungstests für die Sicherheits-Helfer."""

import hashlib
import os
import zipfile


def test_hash_password_roundtrip(gsm_module):
    g = gsm_module
    h = g.hash_password("Geheim123!")
    assert h.startswith("pbkdf2_sha256$")
    assert g.verify_password("Geheim123!", h) is True
    assert g.verify_password("falsch", h) is False


def test_verify_legacy_sha256(gsm_module):
    g = gsm_module
    legacy = hashlib.sha256("altpass".encode()).hexdigest()
    assert g.verify_password("altpass", legacy) is True
    assert g.verify_password("nope", legacy) is False
    assert g.is_legacy_hash(legacy) is True
    assert g.is_legacy_hash(g.hash_password("x")) is False


def test_encrypt_secret_roundtrip_and_idempotency(gsm_module):
    g = gsm_module
    enc = g.encrypt_secret("Rc0nPäss!")
    assert g.decrypt_secret(enc) == "Rc0nPäss!"
    # bereits verschlüsselt -> nicht doppelt verschlüsseln
    assert g.encrypt_secret(enc) == enc
    # Legacy-Klartext ohne Präfix bleibt beim Entschlüsseln erhalten
    assert g.decrypt_secret("klartext") == "klartext"
    # leere Werte unverändert
    assert g.encrypt_secret("") == ""


def test_is_safe_path(gsm_module, tmp_path):
    g = gsm_module
    base = str(tmp_path)
    inside = os.path.join(base, "sub", "file.txt")
    outside = os.path.join(str(tmp_path.parent), "evil.txt")
    assert g.is_safe_path(base, inside) is True
    assert g.is_safe_path(base, base) is True
    assert g.is_safe_path(base, outside) is False


def test_validate_config_path(gsm_module, tmp_path):
    g = gsm_module
    server_dir = str(tmp_path)
    ok, _ = g.validate_config_path(server_dir, os.path.join(server_dir, "server.json"))
    assert ok is True
    bad_ext, msg = g.validate_config_path(server_dir, os.path.join(server_dir, "evil.exe"))
    assert bad_ext is False
    traversal, _ = g.validate_config_path(server_dir, os.path.join(server_dir, "..", "x.json"))
    assert traversal is False


def test_validate_backup_path(gsm_module, tmp_path):
    g = gsm_module
    backups = str(tmp_path)
    sid = "srv1"
    good = os.path.join(backups, sid, "backup1.zip")
    ok, _ = g.validate_backup_path(backups, sid, good)
    assert ok is True
    # außerhalb des Server-Backup-Ordners
    outside = os.path.join(backups, "other", "backup1.zip")
    bad, _ = g.validate_backup_path(backups, sid, outside)
    assert bad is False
    # keine ZIP
    notzip = os.path.join(backups, sid, "backup1.txt")
    bad2, _ = g.validate_backup_path(backups, sid, notzip)
    assert bad2 is False


def test_safe_extract_zip_normal(gsm_module, tmp_path):
    g = gsm_module
    zip_path = tmp_path / "good.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr("folder/hello.txt", "hi")
    target = tmp_path / "out"
    target.mkdir()
    ok, err = g.safe_extract_zip(str(zip_path), str(target))
    assert ok is True, err
    assert (target / "folder" / "hello.txt").read_text() == "hi"


def test_safe_extract_zip_rejects_traversal(gsm_module, tmp_path):
    g = gsm_module
    zip_path = tmp_path / "evil.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr("../evil.txt", "pwned")
    target = tmp_path / "out"
    target.mkdir()
    ok, err = g.safe_extract_zip(str(zip_path), str(target))
    assert ok is False
    assert not (tmp_path / "evil.txt").exists()


def test_generate_session_token(gsm_module):
    g = gsm_module
    t1 = g.generate_session_token()
    t2 = g.generate_session_token()
    assert len(t1) == 64 and t1 != t2
