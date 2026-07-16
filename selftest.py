#!/usr/bin/env python3
"""Kleiner Schnelltest fuer GameServerManager_v3.

Prueft die tatsaechlich laufende Anwendung (game_server_manager.py),
nicht mehr abgekoppelte Parallel-Module.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def check(name: str, fn):
    try:
        fn()
        print(f"[OK]   {name}")
        return True
    except Exception as exc:
        print(f"[FAIL] {name}: {exc}")
        return False


def test_main_module():
    gsm = importlib.import_module("game_server_manager")
    version = getattr(gsm, "VERSION", "")
    games = getattr(gsm, "SUPPORTED_GAMES", {})
    if not version:
        raise RuntimeError("VERSION fehlt")
    if not isinstance(games, dict) or len(games) < 10:
        raise RuntimeError("SUPPORTED_GAMES ungueltig")


def test_run_entrypoint():
    run_mod = importlib.import_module("run")
    if not hasattr(run_mod, "main"):
        raise RuntimeError("run.main() fehlt")


def test_core_classes_present():
    gsm = importlib.import_module("game_server_manager")
    for cls in ("ConfigManager", "ServerInstance", "GameServerManagerApp"):
        if not hasattr(gsm, cls):
            raise RuntimeError(f"Klasse {cls} fehlt im Hauptmodul")


def test_files_present():
    required = [
        ROOT / "templates" / "web_dashboard.html",
        ROOT / "static" / "web_dashboard.js",
        ROOT / "game_server_manager.py",
        ROOT / "run.py",
    ]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
    if missing:
        raise RuntimeError(f"Fehlende Dateien: {', '.join(missing)}")


def test_secret_encryption_roundtrip():
    gsm = importlib.import_module("game_server_manager")
    secret = "MyRc0nPäss!"
    enc = gsm.encrypt_secret(secret)
    if gsm.decrypt_secret(enc) != secret:
        raise RuntimeError("Secret-Roundtrip fehlgeschlagen")
    # Idempotenz: bereits verschluesselte Werte nicht doppelt verschluesseln
    if gsm.encrypt_secret(enc) != enc:
        raise RuntimeError("encrypt_secret ist nicht idempotent")
    # Legacy-Klartext (ohne Praefix) bleibt beim Laden erhalten
    if gsm.decrypt_secret("klartext") != "klartext":
        raise RuntimeError("Legacy-Klartext wurde veraendert")


def main() -> int:
    print("Game Server Manager v3 - Selbsttest")
    print(f"Pfad: {ROOT}")
    print("-" * 56)

    tests = [
        ("Hauptmodul laden", test_main_module),
        ("run.py Entrypoint", test_run_entrypoint),
        ("Kernklassen vorhanden", test_core_classes_present),
        ("Pflichtdateien vorhanden", test_files_present),
        ("Secret-Verschluesselung", test_secret_encryption_roundtrip),
    ]

    passed = 0
    for name, fn in tests:
        if check(name, fn):
            passed += 1

    print("-" * 56)
    print(f"Ergebnis: {passed}/{len(tests)} Tests erfolgreich")
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    sys.exit(main())
