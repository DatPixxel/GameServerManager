"""Headless-Backend für die moderne Web-Oberfläche (ohne CustomTkinter).

Stellt genau das bereit, was die Flask-Web-API vom `app_instance` erwartet:
`config_manager`, `server_instances`, `chat_runtime` sowie die TeamSpeak-/Chat-/
Service-Methoden (geerbt aus `TeamSpeakServicesMixin`). Dadurch kann die neue
Oberfläche laufen, ohne dass die alte Tkinter-App (GameServerManagerApp) gestartet
werden muss. Die UI-Methoden des Mixins (Dialoge) werden hier nie aufgerufen.
"""

from gsm.config import ConfigManager
from gsm.server import ServerInstance
from gsm.discord import DiscordNotifier
from gsm.ui.mixins.services import TeamSpeakServicesMixin


class GsmCore(TeamSpeakServicesMixin):
    """Schlanker Backend-Kern: Config + Server-Instanzen + Dienste, kein Tkinter."""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.discord_notifier = DiscordNotifier(self.config_manager)
        self.server_instances = {}

        # TeamSpeak/Chat-Laufzeit (wie in GameServerManagerApp.__init__)
        self.chat_runtime = {}
        self.ts3_process = None
        self.ts3_log_path = ""
        self.ts3_log_handle = None
        self.init_chat_runtime()

        self._build_instances()

    def _build_instances(self):
        """Erstellt für jeden konfigurierten Server eine ServerInstance."""
        for server_id, cfg in self.config_manager.servers.items():
            self.server_instances[server_id] = ServerInstance(
                server_id, cfg, self.config_manager, self.discord_notifier
            )
