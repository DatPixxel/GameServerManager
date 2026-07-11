#!/usr/bin/env python3
"""Kleiner Schnelltest fuer GameServerManager_v3."""

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


def test_core_imports():
    import core.config_manager  # noqa: F401
    import core.server_instance  # noqa: F401


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


def test_files_present():
    required = [
        ROOT / "templates" / "web_dashboard.html",
        ROOT / "static" / "web_dashboard.js",
        ROOT / "security_utils.py",
        ROOT / "web_security.py",
        ROOT / "auth_manager.py",
        ROOT / "security_patches.py",
    ]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
    if missing:
        raise RuntimeError(f"Fehlende Dateien: {', '.join(missing)}")


def test_modular_config_manager():
    from core.config_manager import ConfigManager

    cfg = ConfigManager()
    if not hasattr(cfg, "app_config"):
        raise RuntimeError("ConfigManager ohne app_config")


def main() -> int:
    print("Game Server Manager v3 - Selbsttest")
    print(f"Pfad: {ROOT}")
    print("-" * 56)

    tests = [
        ("Core-Module importieren", test_core_imports),
        ("Hauptmodul laden", test_main_module),
        ("run.py Entrypoint", test_run_entrypoint),
        ("Pflichtdateien vorhanden", test_files_present),
        ("Modularer ConfigManager", test_modular_config_manager),
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
