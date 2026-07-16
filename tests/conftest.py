"""Gemeinsame Test-Fixtures.

Die Tests laufen gegen das laufende Hauptmodul `game_server_manager`. Nach dem
Refactoring re-exportiert dieses Modul dieselben Namen, sodass die Tests unverändert
grün bleiben müssen (Charakterisierungs-/Regressionstests).
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import game_server_manager as gsm  # noqa: E402


@pytest.fixture
def gsm_module():
    return gsm


@pytest.fixture
def temp_paths(tmp_path):
    """Setzt PATHS in place auf ein temporäres Verzeichnis und stellt es danach wieder her.

    Nutzt bewusst den echten Setter set_base_dir() (in-place-Mutation), damit alle
    Module dasselbe geteilte Dict sehen – Rebinding via monkeypatch würde die
    Module-übergreifende Referenz zerreißen.
    """
    import copy
    original = copy.deepcopy(gsm.PATHS)
    gsm.set_base_dir(str(tmp_path))
    try:
        yield gsm.PATHS
    finally:
        gsm.PATHS.clear()
        gsm.PATHS.update(original)
