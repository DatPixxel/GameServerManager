"""Charakterisierungstests fuer die Flask-App-Factory (gsm/web/server.py).

Phase 2 hat `start_web_server` aus der God-Class in `create_web_app(app_instance,
config_manager)` ausgelagert. Diese Tests bauen die App mit leichten Stubs, ohne
einen echten Server (Thread/Port) zu starten, und pruefen die unveraenderten
Kern-Eigenschaften: Routen sind registriert und der Auth-Guard antwortet mit 401.
"""

from gsm.web.server import create_web_app


class _StubConfigManager:
    """Minimaler config_manager – die Auth-Guards laufen, bevor er benoetigt wird."""

    def __init__(self):
        self.servers = {}
        self.app_config = {"web": {"port": 5001}}

    def verify_password(self, password):
        return False

    def get_text(self, key, *args, **kwargs):
        return key


class _StubApp:
    def __init__(self):
        self.server_instances = {}


def _build_app():
    flask_app = create_web_app(_StubApp(), _StubConfigManager())
    flask_app.config.update(TESTING=True)
    return flask_app


def test_factory_returns_flask_app():
    from flask import Flask
    assert isinstance(_build_app(), Flask)


def test_expected_routes_registered():
    app = _build_app()
    rules = {r.rule for r in app.url_map.iter_rules()}
    for expected in (
        "/",
        "/login",
        "/logout",
        "/chat",
        "/api/servers",
        "/api/server/<server_id>/details",
        "/api/server/<server_id>/<action>",
        "/api/status",
    ):
        assert expected in rules, f"Route fehlt: {expected}"


def test_api_requires_authentication():
    """Ohne gueltige Session liefert die API 401 – zentraler Schutz, unveraendert."""
    client = _build_app().test_client()
    for path in ("/api/servers", "/api/status", "/api/services/status"):
        resp = client.get(path)
        assert resp.status_code == 401, f"{path} sollte 401 liefern"


def test_index_redirects_to_login_when_unauthenticated():
    client = _build_app().test_client()
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/login" in resp.headers.get("Location", "")
