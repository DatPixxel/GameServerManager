"""Tests fuer die Fortschrittsanzeige beim SteamCMD-Update.

Hintergrund: In der Web-Oberflaeche war ein Server-Update unsichtbar - der Klick
startete zwar SteamCMD, aber weder Fortschritt noch Ergebnis waren zu sehen, und
im Logs-Tab wurden die eigenen Meldungen von den Server-Logdateien verdraengt.

Diese Tests halten das Verhalten fest, ohne Windows oder ein echtes SteamCMD:
`subprocess.Popen` wird durch eine Attrappe ersetzt, die echte SteamCMD-Ausgabe
liefert.
"""

import io

import pytest

import gsm.server as gs
from gsm.server import ServerInstance, UPDATE_LOG_LINES
from gsm.web.server import _update_snapshot, _update_summary


STEAMCMD_OK = """Logging in user 'anonymous' to Steam Public...OK
 Update state (0x61) downloading, progress: 0.00 (0 / 2947761)
 Update state (0x61) downloading, progress: 42.35 (1248277 / 2947761)
 Update state (0x81) verifying update, progress: 96.00 (2830000 / 2947761)
Success! App '2278520' fully installed.
"""


class _FakeProcess:
    """Ersetzt den SteamCMD-Prozess: liefert Zeilen und einen Exit-Code."""

    def __init__(self, output, returncode=0):
        self.stdout = io.StringIO(output)
        self.returncode = None
        self._returncode = returncode

    def wait(self):
        self.returncode = self._returncode
        return self._returncode


class _StubConfigManager:
    def __init__(self, config):
        self.servers = {"keks": config}
        self.save_calls = 0

    def save_servers(self):
        self.save_calls += 1


@pytest.fixture
def instance(monkeypatch):
    """Eine ServerInstance fuer Enshrouded, ohne echten Prozess/Platte."""
    config = {"name": "KeKsShrouded", "game": "Enshrouded"}
    inst = ServerInstance.__new__(ServerInstance)
    inst.server_id = "keks"
    inst.config = config
    inst.config_manager = _StubConfigManager(config)
    inst.discord_notifier = None
    inst.process = None
    inst.log_messages = []
    inst.update_state = ServerInstance._empty_update_state()

    monkeypatch.setattr(inst, "is_running", lambda: False, raising=False)
    monkeypatch.setattr(inst, "stop", lambda: None, raising=False)
    monkeypatch.setattr(inst, "start", lambda: None, raising=False)
    monkeypatch.setattr(inst, "get_server_dir", lambda: "/srv/keks", raising=False)

    monkeypatch.setitem(gs.PATHS, "steamcmd", "/fake/steamcmd")
    # Nur den SteamCMD-Pfad vortaeuschen - der Rest des Dateisystems bleibt echt,
    # sonst stolpern tmp_path und die Fehlerausgabe von pytest darueber
    echt_vorhanden = gs.os.path.exists
    monkeypatch.setattr(gs.os.path, "exists",
                        lambda path: True if "steamcmd" in str(path) else echt_vorhanden(path))
    monkeypatch.setattr(gs.time, "sleep", lambda seconds: None)
    return inst


def _run(monkeypatch, inst, output, returncode=0):
    monkeypatch.setattr(gs.subprocess, "Popen",
                        lambda *args, **kwargs: _FakeProcess(output, returncode))
    return inst.update_server()


# --- Fortschritt lesen ---------------------------------------------------

@pytest.mark.parametrize("line, expected", [
    # SteamCMD meldet den Fortschritt OHNE Prozentzeichen - genau daran scheiterte
    # die alte Auswertung, die nur nach "%" suchte
    ("Update state (0x61) downloading, progress: 42.35 (1248277 / 2947761)", 42.35),
    ("Downloading update 87 %", 87.0),
    ("PROGRESS: 7.5", 7.5),
    ("Logging in user 'anonymous' to Steam Public...OK", None),
])
def test_parse_update_percent(line, expected):
    assert ServerInstance._parse_update_percent(line) == expected


def test_update_meldet_fortschritt_und_ergebnis(monkeypatch, instance):
    seen = []
    monkeypatch.setattr(gs.subprocess, "Popen",
                        lambda *args, **kwargs: _FakeProcess(STEAMCMD_OK))

    assert instance.update_server(progress_callback=seen.append) is True

    state = instance.update_state
    assert state["running"] is False
    assert state["success"] is True
    assert state["percent"] == 100.0
    assert state["finished_at"]
    assert seen[:2] == [0.0, 42.35]
    assert any("progress: 42.35" in line for line in state["lines"])


def test_zeitpunkt_wird_dauerhaft_gemerkt(monkeypatch, instance):
    _run(monkeypatch, instance, STEAMCMD_OK)

    assert instance.config["last_update"] == instance.update_state["finished_at"]
    assert instance.config_manager.save_calls == 1


def test_bereits_aktuell_gilt_als_erfolg(monkeypatch, instance):
    output = "Success! App '2278520' already up to date.\n"
    assert _run(monkeypatch, instance, output) is True
    assert instance.update_state["success"] is True


def test_fehlschlag_wird_gemeldet_und_nicht_gemerkt(monkeypatch, instance):
    assert _run(monkeypatch, instance, "ERROR! Failed to install app\n", returncode=8) is False

    assert instance.update_state["success"] is False
    assert "8" in instance.update_state["message"]
    assert "last_update" not in instance.config
    assert instance.config_manager.save_calls == 0


def test_fehlendes_steamcmd_laesst_zustand_nicht_haengen(monkeypatch, instance):
    echt_vorhanden = gs.os.path.exists
    monkeypatch.setattr(gs.os.path, "exists",
                        lambda path: False if "steamcmd" in str(path) else echt_vorhanden(path))

    assert instance.update_server() is False
    assert instance.update_state["running"] is False
    assert "SteamCMD" in instance.update_state["message"]


def test_ausnahme_schliesst_den_zustand_ab(monkeypatch, instance):
    def boom(*args, **kwargs):
        raise OSError("Zugriff verweigert")

    monkeypatch.setattr(gs.subprocess, "Popen", boom)

    assert instance.update_server() is False
    assert instance.update_state["running"] is False
    assert "Zugriff verweigert" in instance.update_state["message"]


def test_spiel_ohne_steam_app_id(monkeypatch, instance):
    instance.config["game"] = "Minecraft Java"

    assert instance.update_server() is False
    assert instance.update_state["running"] is False


def test_begin_update_state_verwirft_das_alte_ergebnis(monkeypatch, instance):
    _run(monkeypatch, instance, STEAMCMD_OK)
    assert instance.update_state["success"] is True

    # Die Web-API ruft das synchron beim Klick auf, bevor der Thread laeuft
    instance.begin_update_state()

    assert instance.update_state["running"] is True
    assert instance.update_state["success"] is None
    assert instance.update_state["lines"] == []


def test_live_log_bleibt_begrenzt(instance):
    for i in range(UPDATE_LOG_LINES + 25):
        instance._update_line(f"Zeile {i}")

    assert len(instance.update_state["lines"]) == UPDATE_LOG_LINES
    assert instance.update_state["lines"][-1] == f"Zeile {UPDATE_LOG_LINES + 24}"


@pytest.mark.parametrize("value, expected", [(150, 100.0), (-5, 0.0), (42.349, 42.3)])
def test_prozent_wird_begrenzt_und_gerundet(instance, value, expected):
    instance._update_percent(value)
    assert instance.update_state["percent"] == expected


# --- Logs ----------------------------------------------------------------

def test_eigene_meldungen_werden_nicht_verdraengt(tmp_path, instance):
    """Der eigentliche Fehler: viele Server-Logzeilen schoben die Update-Meldungen
    aus dem 100-Zeilen-Fenster der Web-API."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    logs_dir.joinpath("enshrouded.log").write_text(
        "\n".join(f"server line {i}" for i in range(500)), encoding="utf-8")

    instance.log_messages = [f"[10:00:00] [KeKsShrouded] Meldung {i}" for i in range(60)]
    instance.log_messages[-1] = "[10:05:00] [KeKsShrouded] Server erfolgreich aktualisiert!"
    instance.get_server_dir = lambda: str(tmp_path)

    logs = instance.get_server_logs(max_lines=100)

    assert len(logs) == 100
    assert any("erfolgreich aktualisiert" in line for line in logs)
    assert any("[FILE]" in line for line in logs)


def test_logfilter_wirkt_auf_beide_quellen(tmp_path, instance):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    logs_dir.joinpath("enshrouded.log").write_text("server line 1\n", encoding="utf-8")

    instance.log_messages = ["[10:05:00] [KeKsShrouded] Server erfolgreich aktualisiert!"]
    instance.get_server_dir = lambda: str(tmp_path)

    treffer = instance.get_server_logs(max_lines=100, search_filter="erfolgreich")

    assert len(treffer) == 1
    assert "erfolgreich" in treffer[0]


# --- Web-API -------------------------------------------------------------

def test_snapshot_ist_eine_kopie(instance):
    """Der Update-Thread schreibt weiter, waehrend Flask serialisiert."""
    instance.update_state["lines"].append("eine Zeile")

    snapshot = _update_snapshot(instance)

    assert snapshot["lines"] == ["eine Zeile"]
    assert snapshot["lines"] is not instance.update_state["lines"]


def test_summary_ohne_live_log(instance):
    assert set(_update_summary(instance)) == {"running", "percent", "status"}
    assert _update_summary(None) == {"running": False, "percent": 0, "status": ""}
