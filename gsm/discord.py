"""Discord-Webhook-Benachrichtigungen.

Aus game_server_manager.py ausgelagert.
"""

import json
from datetime import datetime, timedelta

import requests

from gsm.constants import VERSION


class DiscordNotifier:
    """Sendet Benachrichtigungen an Discord"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
    
    def get_discord_config(self):
        """Holt Discord-Konfiguration"""
        return self.config_manager.app_config.get("discord", {})
    
    def is_enabled(self):
        """Prüft ob Discord aktiviert ist"""
        config = self.get_discord_config()
        return config.get("enabled", False) and config.get("webhook_url", "")
    
    def send_notification(self, title, message, color=0x00ff88, server_name=None):
        """Sendet eine Discord-Nachricht"""
        if not self.is_enabled():
            return False
        
        config = self.get_discord_config()
        webhook_url = config.get("webhook_url", "")
        
        if not webhook_url:
            return False
        
        try:
            embed = {
                "title": title,
                "description": message,
                "color": color,
                "timestamp": datetime.now().isoformat(),
                "footer": {
                    "text": f"Game Server Manager Pro v{VERSION}"
                }
            }
            
            if server_name:
                embed["author"] = {"name": f"🖥️ {server_name}"}
            
            payload = {
                "embeds": [embed]
            }
            
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=10
            )
            
            return response.status_code == 204
            
        except Exception as e:
            print(f"Discord Fehler: {e}")
            return False
    
    def notify_server_start(self, server_name):
        """Benachrichtigung: Server gestartet"""
        config = self.get_discord_config()
        if config.get("notify_start", True):
            self.send_notification(
                "🟢 Server gestartet",
                f"Der Server wurde erfolgreich gestartet.",
                color=0x00ff88,
                server_name=server_name
            )
    
    def notify_server_stop(self, server_name):
        """Benachrichtigung: Server gestoppt"""
        config = self.get_discord_config()
        if config.get("notify_stop", True):
            self.send_notification(
                "⚫ Server gestoppt",
                f"Der Server wurde gestoppt.",
                color=0x808080,
                server_name=server_name
            )
    
    def notify_server_crash(self, server_name):
        """Benachrichtigung: Server abgestürzt"""
        config = self.get_discord_config()
        if config.get("notify_crash", True):
            self.send_notification(
                "🔴 Server abgestürzt!",
                f"Der Server ist unerwartet abgestürzt!",
                color=0xff0000,
                server_name=server_name
            )
    
    def notify_backup(self, server_name, backup_name):
        """Benachrichtigung: Backup erstellt"""
        config = self.get_discord_config()
        if config.get("notify_backup", True):
            self.send_notification(
                "💾 Backup erstellt",
                f"Backup: `{backup_name}`",
                color=0x2196F3,
                server_name=server_name
            )
    
    def notify_update(self, server_name):
        """Benachrichtigung: Server aktualisiert"""
        config = self.get_discord_config()
        if config.get("notify_update", True):
            self.send_notification(
                "📦 Server aktualisiert",
                f"Der Server wurde erfolgreich aktualisiert.",
                color=0x9c27b0,
                server_name=server_name
            )
    
    def send_test(self):
        """Sendet eine Test-Nachricht"""
        return self.send_notification(
            "🧪 Test-Nachricht",
            "Discord-Benachrichtigungen funktionieren!",
            color=0xffaa00
        )
