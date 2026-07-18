"""HTML-Template-Erzeugung für Login, Dashboard und Chat.

Aus game_server_manager.py ausgelagert.
"""

import os
import json

from gsm.constants import VERSION, APP_NAME, CONAN_UPLOAD_MAX_BYTES

# Projekt-/Bundle-Root (templates.py liegt unter gsm/web/, daher drei Ebenen hoch)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_login_template(config_manager, error=False):
    t = config_manager.get_text
    error_html = '<p style="color: #ff6b6b; margin-bottom: 20px;">❌ ' + t("login_error") + '</p>' if error else ''
    
    return f'''
<!DOCTYPE html>
<html>
<head>
    <title>{APP_NAME} - Login</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .login-box {{
            background: rgba(255,255,255,0.05);
            padding: 40px;
            border-radius: 15px;
            border: 1px solid rgba(255,255,255,0.1);
            text-align: center;
            width: 350px;
        }}
        h1 {{ color: #00d4ff; margin-bottom: 30px; }}
        input {{
            width: 100%;
            padding: 15px;
            margin-bottom: 20px;
            border: 1px solid #333;
            border-radius: 8px;
            background: rgba(0,0,0,0.3);
            color: #fff;
            font-size: 16px;
        }}
        button {{
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #00d4ff, #0099cc);
            border: none;
            border-radius: 8px;
            color: #000;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
        }}
        button:hover {{ transform: translateY(-2px); }}
    </style>
</head>
<body>
    <div class="login-box">
        <h1>🎮 {APP_NAME}</h1>
        {error_html}
        <form method="POST">
            <input type="password" name="password" placeholder="{t("password")}" autofocus>
            <button type="submit">{t("login")}</button>
        </form>
    </div>
</body>
</html>
'''


def get_web_template(config_manager):
    t = config_manager.get_text
    
    return f'''
<!DOCTYPE html>
<html>
<head>
    <title>{APP_NAME}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 0;
            border-bottom: 1px solid #333;
            margin-bottom: 30px;
        }}
        header h1 {{ color: #00d4ff; font-size: 1.8em; }}
        .header-right {{ display: flex; align-items: center; gap: 15px; }}
        .header-btn {{
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
            font-size: 0.85em;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }}
        .header-btn.settings {{ background: #444; color: #fff; }}
        .header-btn.settings:hover {{ background: #555; }}
        .header-btn.update {{ background: #9c27b0; color: #fff; }}
        .header-btn.update:hover {{ background: #7b1fa2; }}
        .logout {{ color: #888; text-decoration: none; padding: 8px 16px; }}
        .logout:hover {{ color: #fff; }}
        .version {{ color: #666; font-size: 0.9em; }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        .stat-box {{
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }}
        .stat-value {{ font-size: 1.8em; color: #00d4ff; font-weight: bold; }}
        .stat-label {{ color: #888; margin-top: 5px; font-size: 0.85em; }}
        .services-panel {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .service-card {{
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.14);
            border-radius: 12px;
            padding: 14px;
        }}
        .service-title {{ font-weight: bold; color: #00d4ff; margin-bottom: 8px; }}
        .service-state {{ font-size: 0.9em; margin-bottom: 10px; }}
        .service-state.online {{ color: #00ff88; }}
        .service-state.offline {{ color: #ff7b7b; }}
        .service-buttons {{ display: flex; gap: 8px; flex-wrap: wrap; }}
        .game-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            padding: 20px;
        }}
        .game-tile {{
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-radius: 15px;
            padding: 30px;
            cursor: pointer;
            transition: all 0.3s;
            border: 2px solid rgba(0,212,255,0.1);
        }}
        .game-tile:hover {{
            transform: translateY(-5px);
            border-color: rgba(0,212,255,0.5);
            box-shadow: 0 10px 30px rgba(0,212,255,0.2);
        }}
        .game-tile-icon {{
            font-size: 3em;
            margin-bottom: 15px;
            text-align: center;
        }}
        .game-tile-name {{
            font-size: 1.4em;
            font-weight: bold;
            color: #00d4ff;
            text-align: center;
            margin-bottom: 10px;
        }}
        .game-tile-count {{
            display: flex;
            justify-content: space-between;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid rgba(255,255,255,0.1);
        }}
        .count-item {{ text-align: center; }}
        .count-value {{
            font-size: 1.8em;
            font-weight: bold;
        }}
        .count-label {{
            font-size: 0.8em;
            opacity: 0.6;
            margin-top: 5px;
        }}
        .count-total {{ color: #00d4ff; }}
        .count-online {{ color: #00ff88; }}
        .count-offline {{ color: #ff4444; }}
        .view-toolbar {{
            display: flex;
            justify-content: flex-start;
            margin: 0 0 16px 0;
            padding: 0 20px;
        }}
        .btn-overview {{
            background: #37474F;
            color: #fff;
        }}
        .btn-overview:hover {{
            background: #455A64;
        }}
        .servers {{ display: grid; gap: 20px; }}
        .server-card {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .server-top {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 15px;
            flex-wrap: wrap;
            gap: 15px;
        }}
        .server-title-area {{ flex: 1; min-width: 300px; }}
        .server-header {{
            display: flex;
            align-items: center;
            gap: 15px;
            flex-wrap: wrap;
        }}
        .server-name {{ font-size: 1.4em; font-weight: bold; }}
        .server-game {{ color: #888; font-size: 0.9em; }}
        .status {{ padding: 5px 15px; border-radius: 20px; font-size: 0.85em; white-space: nowrap; }}
        .status.online {{ background: rgba(0,255,136,0.2); color: #00ff88; }}
        .status.offline {{ background: rgba(255,255,255,0.1); color: #888; }}
        .status.not-installed {{ background: rgba(255,170,0,0.2); color: #ffaa00; }}
        .connection-info {{
            margin-top: 8px;
            font-family: monospace;
            font-size: 0.9em;
            color: #00d4ff;
        }}
        .connection-info span {{ cursor: pointer; padding: 2px 8px; background: rgba(0,212,255,0.1); border-radius: 4px; margin-right: 10px; }}
        .connection-info span:hover {{ background: rgba(0,212,255,0.3); }}
        .buttons {{ display: flex; flex-wrap: wrap; gap: 8px; }}
        .btn {{
            padding: 10px 16px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            font-size: 0.85em;
            transition: transform 0.2s, opacity 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }}
        .btn:hover {{ transform: translateY(-2px); }}
        .btn:disabled {{ opacity: 0.5; cursor: not-allowed; transform: none; }}
        .btn-start {{ background: #00ff88; color: #000; }}
        .btn-stop {{ background: #ff6b6b; color: #fff; }}
        .btn-restart {{ background: #ffaa00; color: #000; }}
        .btn-update {{ background: #20c997; color: #062b22; }}
        .btn-backup {{ background: #2196F3; color: #fff; }}
        .btn-config {{ background: #795548; color: #fff; }}
        .btn-logs {{ background: #607D8B; color: #fff; }}
        .server-info {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
            gap: 10px;
            margin: 15px 0;
        }}
        .info-item {{ background: rgba(0,0,0,0.2); padding: 10px; border-radius: 8px; text-align: center; }}
        .info-label {{ color: #888; font-size: 0.75em; text-transform: uppercase; }}
        .info-value {{ font-weight: bold; color: #00d4ff; font-size: 0.95em; margin-top: 3px; }}
        .features {{
            display: flex;
            gap: 10px;
            margin: 10px 0;
            flex-wrap: wrap;
        }}
        .feature {{
            font-size: 0.75em;
            padding: 3px 8px;
            border-radius: 10px;
            background: rgba(255,255,255,0.1);
            color: #888;
        }}
        .feature.active {{ background: rgba(0,255,136,0.2); color: #00ff88; }}
        .mods-section {{
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
            padding: 12px;
            margin-top: 15px;
        }}
        .mods-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .mods-title {{ color: #888; font-size: 0.85em; text-transform: uppercase; }}
        .mods-list {{ display: flex; flex-wrap: wrap; gap: 8px; }}
        .mod-tag {{
            background: rgba(156,39,176,0.3);
            color: #e1bee7;
            padding: 4px 10px;
            border-radius: 15px;
            font-size: 0.8em;
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        .mod-row {{
            background: rgba(52, 62, 97, 0.35);
            border: 1px solid rgba(133, 171, 255, 0.2);
            border-radius: 8px;
            padding: 6px 10px;
            font-size: 0.82em;
            display: flex;
            align-items: center;
            gap: 8px;
            color: #d6e4ff;
        }}
        .mod-row .mod-id {{ color: #8fb4ff; font-family: Consolas, monospace; }}
        .mod-row .mod-name {{ color: #e6f0ff; }}
        .mod-row .mod-state {{ margin-left: auto; font-size: 0.78em; opacity: 0.85; }}
        .mod-row .mod-state.ok {{ color: #64ff9a; }}
        .mod-row .mod-state.missing {{ color: #ffb86c; }}
        .mod-row .remove {{ cursor: pointer; color: #ff6b6b; font-weight: bold; margin-left: 6px; }}
        .mod-row .remove:hover {{ color: #ff8d8d; }}
        .mod-actions {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }}
        .btn-small {{ padding: 7px 10px; font-size: 0.78em; border-radius: 6px; }}
        .mod-sync-meta {{ margin-top: 8px; font-size: 0.78em; color: #8ea3c8; }}
        .mod-upload {{ margin-top: 10px; padding: 10px; border: 1px dashed rgba(133,171,255,0.35); border-radius: 8px; background: rgba(20,30,54,0.4); }}
        .mod-upload-title {{ font-size: 0.82em; color: #9fc0ff; margin-bottom: 6px; }}
        .mod-upload-row {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
        .mod-upload-row input[type="file"] {{ color: #d7e6ff; font-size: 0.8em; max-width: 360px; }}
        .mod-dropdown {{ margin-top: 10px; border: 1px solid rgba(133,171,255,0.22); border-radius: 8px; background: rgba(19,29,50,0.45); }}
        .mod-dropdown summary {{ cursor: pointer; list-style: none; padding: 8px 10px; color: #cfe1ff; font-size: 0.82em; font-weight: 600; }}
        .mod-dropdown summary::-webkit-details-marker {{ display: none; }}
        .mod-dropdown summary::before {{ content: '▸'; margin-right: 6px; color: #8fb4ff; }}
        .mod-dropdown[open] summary::before {{ content: '▾'; }}
        .mod-dropdown-body {{ padding: 0 10px 10px 10px; }}
        .mod-tag .remove {{ cursor: pointer; color: #ff6b6b; font-weight: bold; }}
        .mod-tag .remove:hover {{ color: #ff0000; }}
        .add-mod {{ display: flex; gap: 8px; margin-top: 10px; }}
        .add-mod input {{
            flex: 1;
            padding: 8px;
            border: 1px solid #444;
            border-radius: 5px;
            background: rgba(0,0,0,0.3);
            color: #fff;
            font-size: 0.85em;
        }}
        .add-mod button {{
            padding: 8px 15px;
            background: #9c27b0;
            border: none;
            border-radius: 5px;
            color: #fff;
            cursor: pointer;
        }}
        .notification {{
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 25px;
            border-radius: 10px;
            background: #00d4ff;
            color: #000;
            font-weight: bold;
            display: none;
            z-index: 1001;
        }}
        .modal {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }}
        .modal-content {{
            background: #1a1a2e;
            border-radius: 15px;
            padding: 25px;
            max-width: 900px;
            width: 95%;
            max-height: 85vh;
            overflow-y: auto;
        }}
        .modal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}
        .modal-close {{
            background: none;
            border: none;
            color: #888;
            font-size: 1.5em;
            cursor: pointer;
        }}
        .modal-close:hover {{ color: #fff; }}
        .logs-container, .config-editor {{
            background: #000;
            border-radius: 8px;
            padding: 15px;
            font-family: monospace;
            font-size: 0.85em;
            max-height: 400px;
            overflow-y: auto;
        }}
        .config-editor {{
            max-height: none;
            min-height: 300px;
        }}
        .config-editor textarea {{
            width: 100%;
            min-height: 350px;
            background: #000;
            color: #0f0;
            border: none;
            font-family: 'Consolas', monospace;
            font-size: 0.9em;
            resize: vertical;
        }}
        .config-select {{
            margin-bottom: 15px;
            display: flex;
            gap: 10px;
            align-items: center;
        }}
        .config-select select {{
            flex: 1;
            padding: 10px;
            background: #333;
            color: #fff;
            border: 1px solid #555;
            border-radius: 5px;
        }}
        .backup-list {{
            max-height: 400px;
            overflow-y: auto;
        }}
        .backup-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px;
            background: rgba(0,0,0,0.3);
            border-radius: 8px;
            margin-bottom: 8px;
        }}
        .backup-info {{ flex: 1; }}
        .backup-name {{ font-weight: bold; color: #00d4ff; }}
        .backup-meta {{ font-size: 0.8em; color: #888; margin-top: 4px; }}
        .backup-actions {{ display: flex; gap: 8px; }}
        .backup-actions button {{ padding: 6px 12px; font-size: 0.8em; }}
        .log-line {{ margin: 2px 0; }}
        .log-line.error {{ color: #ff6b6b; }}
        .log-line.warning {{ color: #ffaa00; }}
        .log-line.info {{ color: #00d4ff; }}
        .settings-form {{ }}
        .settings-group {{
            margin-bottom: 20px;
        }}
        .settings-group label {{
            display: block;
            color: #888;
            margin-bottom: 8px;
            font-size: 0.9em;
        }}
        .settings-group input, .settings-group select {{
            width: 100%;
            padding: 10px;
            background: #333;
            color: #fff;
            border: 1px solid #555;
            border-radius: 5px;
            font-size: 0.95em;
        }}
        .settings-hint {{
            font-size: 0.8em;
            color: #666;
            margin-top: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎮 {APP_NAME}</h1>
            <div class="header-right">
                <span class="version">v{VERSION}</span>
                <a class="header-btn settings" href="/chat">💬 Chat & Stream</a>
                <button class="header-btn settings" onclick="openTeamSpeakClient()">🎙️ TeamSpeak öffnen</button>
                <button class="header-btn update" onclick="checkForUpdates()">📦 Update</button>
                <button class="header-btn settings" onclick="showSettings()">⚙️ Einstellungen</button>
                <a href="/logout" class="logout">🚪 Ausloggen</a>
            </div>
        </header>
        
        <div class="stats">
            <div class="stat-box">
                <div class="stat-value" id="server-count">-</div>
                <div class="stat-label">{t("servers")}</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" id="online-count">-</div>
                <div class="stat-label">Online</div>
            </div>
        </div>

        <div class="services-panel">
            <div class="service-card">
                <div class="service-title">💬 Chat & Stream Dienst</div>
                <div class="service-state offline" id="chat-service-state">Status lädt...</div>
                <div class="service-buttons">
                    <button class="btn btn-start" onclick="serviceAction('chat','start')">▶ Start</button>
                    <button class="btn btn-stop" onclick="serviceAction('chat','stop')">⏹ Stop</button>
                    <a class="btn btn-config" href="/chat" style="text-decoration:none;">🌐 Öffnen</a>
                </div>
            </div>
            <div class="service-card">
                <div class="service-title">🎙️ TeamSpeak Dienst</div>
                <div class="service-state offline" id="ts-service-state">Status lädt...</div>
                <div class="service-buttons">
                    <button class="btn btn-start" onclick="serviceAction('teamspeak','start')">▶ Start</button>
                    <button class="btn btn-stop" onclick="serviceAction('teamspeak','stop')">⏹ Stop</button>
                    <button class="btn btn-config" onclick="openTeamSpeakClient()">🔗 Verbinden</button>
                </div>
            </div>
        </div>
        
        <div id="game-grid" class="game-grid"></div>

        <div class="view-toolbar" id="view-toolbar" style="display:none;">
            <button class="btn btn-overview" onclick="showTilesMode=true;filterGame='';loadServers();">← Zur Übersicht</button>
        </div>
        
        <div class="servers" id="servers" style="display:none;">
            <p style="text-align:center;color:#888;">Loading...</p>
        </div>
    </div>
    
    <div class="notification" id="notification"></div>
    
    <!-- Logs Modal -->
    <div class="modal" id="logsModal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="logsTitle">📜 Server Logs</h2>
                <button class="modal-close" onclick="closeModal('logsModal')">&times;</button>
            </div>
            <div class="logs-container" id="logsContent">Loading...</div>
        </div>
    </div>
    
    <!-- Config Editor Modal -->
    <div class="modal" id="configModal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="configTitle">📝 Config Editor</h2>
                <button class="modal-close" onclick="closeModal('configModal')">&times;</button>
            </div>
            <div class="config-select">
                <select id="configSelect" onchange="loadConfigFile()"></select>
                <button class="btn btn-start" onclick="saveConfig()">💾 Speichern</button>
            </div>
            <div class="config-editor">
                <textarea id="configContent" placeholder="Wähle eine Datei..."></textarea>
            </div>
        </div>
    </div>
    
    <!-- Backup Manager Modal -->
    <div class="modal" id="backupModal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="backupTitle">💾 Backup Manager</h2>
                <button class="modal-close" onclick="closeModal('backupModal')">&times;</button>
            </div>
            <div style="margin-bottom:15px;">
                <button class="btn btn-start" onclick="createBackupNow()">➕ Neues Backup erstellen</button>
            </div>
            <div class="backup-list" id="backupList">Loading...</div>
        </div>
    </div>
    
    <!-- Settings Modal -->
    <div class="modal" id="settingsModal">
        <div class="modal-content" style="max-width:500px;">
            <div class="modal-header">
                <h2>⚙️ Einstellungen</h2>
                <button class="modal-close" onclick="closeModal('settingsModal')">&times;</button>
            </div>
            <div class="settings-form">
                <div class="settings-group">
                    <label>🌐 Web-Interface Port</label>
                    <input type="number" id="settingsPort" min="1" max="65535" value="5001">
                    <div class="settings-hint">Standard: 5001 (Neustart erforderlich)</div>
                </div>
                <div class="settings-group">
                    <label>🎨 Design</label>
                    <select id="settingsTheme">
                        <option value="dark">Dunkel</option>
                        <option value="light">Hell</option>
                    </select>
                </div>
                <div class="settings-group">
                    <label>🌍 Sprache</label>
                    <select id="settingsLanguage">
                        <option value="de">Deutsch</option>
                        <option value="en">English</option>
                    </select>
                </div>
                <div style="margin-top:25px; display:flex; gap:10px; justify-content:flex-end;">
                    <button class="btn" style="background:#666;" onclick="closeModal('settingsModal')">Abbrechen</button>
                    <button class="btn btn-start" onclick="saveSettings()">💾 Speichern</button>
                </div>
                <div class="settings-hint" style="margin-top:15px; text-align:center;">
                    ⚠️ Einstellungen werden im Desktop-Programm geändert.<br>
                    Port-Änderungen erfordern einen Neustart.
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let currentServerId = null;
        let currentConfigPath = null;
        
        function showNotification(msg, isError = false) {{
            const n = document.getElementById('notification');
            n.textContent = msg || 'Unbekannter Fehler';
            n.style.background = isError ? '#dc3545' : '#4caf50';
            n.style.display = 'block';
            setTimeout(() => n.style.display = 'none', 3000);
        }}
        
        // Hilfsfunktion für API-Responses
        function handleResponse(data, res) {{
            if (!res.ok || data.error) {{
                showNotification(data.error || data.message || 'Fehler: ' + res.status, true);
                return false;
            }}
            if (data.message) {{
                showNotification(data.message);
            }}
            return true;
        }}
        
        function copyToClipboard(text) {{
            navigator.clipboard.writeText(text);
            showNotification('📋 Kopiert: ' + text);
        }}
        
        function closeModal(id) {{
            document.getElementById(id).style.display = 'none';
        }}
        
        function checkForUpdates() {{
            showNotification('📦 Update-Prüfung im Desktop-Programm starten');
        }}
        
        function showSettings() {{
            document.getElementById('settingsModal').style.display = 'flex';
        }}

        function openTeamSpeakClient() {{
            const host = (location.hostname && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1')
                ? location.hostname
                : '100.112.243.124';
            const tsUrl = `ts3server://${{host}}?port=9987`;
            window.location.href = tsUrl;
        }}
        
        function saveSettings() {{
            showNotification('⚙️ Einstellungen im Desktop-Programm ändern');
            closeModal('settingsModal');
        }}

        async function loadServiceStatus() {{
            try {{
                const res = await fetch('/api/services/status');
                const data = await res.json();
                if (!res.ok || data.error) return;

                const chatState = document.getElementById('chat-service-state');
                const tsState = document.getElementById('ts-service-state');

                if (chatState) {{
                    const chatOn = !!data.chat_enabled;
                    chatState.className = 'service-state ' + (chatOn ? 'online' : 'offline');
                    chatState.textContent = (chatOn ? '🟢 Aktiv' : '🔴 Inaktiv') + ' | ' + (data.chat_url || '');
                }}

                if (tsState) {{
                    const tsOn = !!data.teamspeak_running;
                    tsState.className = 'service-state ' + (tsOn ? 'online' : 'offline');
                    tsState.textContent = (tsOn ? '🟢 Online' : '🔴 Offline') + ' | ' + (data.teamspeak_label || 'TeamSpeak');
                }}
            }} catch (e) {{
                console.error('Service-Status Fehler:', e);
            }}
        }}

        async function serviceAction(serviceName, action) {{
            try {{
                const res = await fetch(`/api/services/${{serviceName}}/${{action}}`, {{ method: 'POST' }});
                const data = await res.json();
                handleResponse(data, res);
                await loadServiceStatus();
            }} catch (e) {{
                showNotification('Netzwerkfehler: ' + e.message, true);
            }}
        }}
        
        // ===== LOGS =====
        async function showLogs(serverId, serverName) {{
            currentServerId = serverId;
            document.getElementById('logsTitle').textContent = '📜 ' + serverName + ' - Logs';
            document.getElementById('logsContent').innerHTML = 'Lade Logs...';
            document.getElementById('logsModal').style.display = 'flex';
            
            try {{
                const res = await fetch('/api/server/' + serverId + '/logs');
                const data = await res.json();
                
                if (!res.ok || data.error) {{
                    document.getElementById('logsContent').innerHTML = '<span style="color:#dc3545;">Fehler: ' + (data.error || 'Unauthorized') + '</span>';
                    return;
                }}
                
                if (data.logs && data.logs.length > 0) {{
                    document.getElementById('logsContent').innerHTML = data.logs.map(log => {{
                        let cls = 'log-line';
                        const text = log.message || log;
                        const lower = text.toLowerCase();
                        if (lower.includes('error') || lower.includes('fail')) cls += ' error';
                        else if (lower.includes('warn')) cls += ' warning';
                        else if (lower.includes('start') || lower.includes('success') || lower.includes('✅')) cls += ' info';
                        return '<div class="' + cls + '">' + text + '</div>';
                    }}).join('');
                }} else {{
                    document.getElementById('logsContent').innerHTML = '<span style="color:#888;">Keine Logs verfügbar</span>';
                }}
            }} catch (e) {{
                document.getElementById('logsContent').innerHTML = '<span style="color:#dc3545;">Netzwerkfehler: ' + e.message + '</span>';
            }}
        }}
        
        // ===== CONFIG EDITOR =====
        async function showConfig(serverId, serverName) {{
            currentServerId = serverId;
            document.getElementById('configTitle').textContent = '📝 ' + serverName + ' - Config';
            document.getElementById('configModal').style.display = 'flex';
            document.getElementById('configContent').value = 'Lade Config-Dateien...';
            
            try {{
                const res = await fetch('/api/server/' + serverId + '/configs');
                const data = await res.json();
                
                if (!res.ok || data.error) {{
                    document.getElementById('configContent').value = 'Fehler: ' + (data.error || 'Unauthorized');
                    showNotification(data.error || 'Fehler beim Laden', true);
                    return;
                }}
                
                const select = document.getElementById('configSelect');
                select.innerHTML = '';
                
                if (data.configs && data.configs.length > 0) {{
                    data.configs.forEach(c => {{
                        const opt = document.createElement('option');
                        opt.value = c.path;
                        opt.textContent = c.name;
                        select.appendChild(opt);
                    }});
                    loadConfigFile();
                }} else {{
                    select.innerHTML = '<option>Keine Config-Dateien gefunden</option>';
                    document.getElementById('configContent').value = 'Keine Config-Dateien in diesem Server-Verzeichnis gefunden.\\n\\nMögliche Gründe:\\n- Server ist noch nicht installiert\\n- Noch keine Config-Dateien erstellt';
                }}
            }} catch (e) {{
                document.getElementById('configContent').value = 'Netzwerkfehler: ' + e.message;
                showNotification('Netzwerkfehler', true);
            }}
        }}
        
        async function loadConfigFile() {{
            const select = document.getElementById('configSelect');
            currentConfigPath = select.value;
            
            if (!currentConfigPath || currentConfigPath === 'Keine Config-Dateien gefunden') return;
            
            document.getElementById('configContent').value = 'Lade Datei...';
            
            try {{
                const res = await fetch('/api/server/' + currentServerId + '/config/read', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{file_path: currentConfigPath}})
                }});
                const data = await res.json();
                
                if (!res.ok || data.error) {{
                    document.getElementById('configContent').value = 'Fehler: ' + (data.error || data.message || 'Unauthorized');
                    return;
                }}
                
                if (data.success) {{
                    document.getElementById('configContent').value = data.content;
                }} else {{
                    document.getElementById('configContent').value = 'Fehler: ' + (data.message || 'Unbekannt');
                }}
            }} catch (e) {{
                document.getElementById('configContent').value = 'Netzwerkfehler: ' + e.message;
            }}
        }}
        
        async function saveConfig() {{
            if (!currentConfigPath || currentConfigPath === 'Keine Config-Dateien gefunden') {{
                showNotification('Keine Datei ausgewählt', true);
                return;
            }}
            
            try {{
                const content = document.getElementById('configContent').value;
                const res = await fetch('/api/server/' + currentServerId + '/config/save', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{file_path: currentConfigPath, content: content}})
                }});
                const data = await res.json();
                handleResponse(data, res);
            }} catch (e) {{
                showNotification('Netzwerkfehler: ' + e.message, true);
            }}
        }}
        
        // ===== BACKUP MANAGER =====
        async function showBackups(serverId, serverName) {{
            currentServerId = serverId;
            document.getElementById('backupTitle').textContent = '💾 ' + serverName + ' - Backups';
            document.getElementById('backupModal').style.display = 'flex';
            await loadBackupList();
        }}
        
        async function loadBackupList() {{
            try {{
                const res = await fetch('/api/server/' + currentServerId + '/backups');
                const data = await res.json();
                
                if (!res.ok || data.error) {{
                    document.getElementById('backupList').innerHTML = '<p style="color:#dc3545;padding:20px;">Fehler: ' + (data.error || 'Unauthorized') + '</p>';
                    return;
                }}
                
                const container = document.getElementById('backupList');
                
                if (data.backups && data.backups.length > 0) {{
                    container.innerHTML = data.backups.map(b => `
                        <div class="backup-item">
                            <div class="backup-info">
                                <div class="backup-name">${{b.name}}</div>
                                <div class="backup-meta">${{b.date}} | ${{b.size}}</div>
                            </div>
                            <div class="backup-actions">
                                <button class="btn btn-start" onclick="restoreBackup('${{b.path.replace(/\\\\/g, '\\\\\\\\')}}')">🔄 Wiederherstellen</button>
                                <button class="btn btn-stop" onclick="deleteBackup('${{b.path.replace(/\\\\/g, '\\\\\\\\')}}')">🗑️ Löschen</button>
                            </div>
                        </div>
                    `).join('');
                }} else {{
                    container.innerHTML = '<p style="text-align:center;color:#888;padding:30px;">Keine Backups vorhanden</p>';
                }}
            }} catch (e) {{
                document.getElementById('backupList').innerHTML = '<p style="color:#dc3545;padding:20px;">Netzwerkfehler: ' + e.message + '</p>';
            }}
        }}
        
        async function createBackupNow() {{
            try {{
                const res = await fetch('/api/server/' + currentServerId + '/backup', {{method: 'POST'}});
                const data = await res.json();
                handleResponse(data, res);
                setTimeout(loadBackupList, 2000);
            }} catch (e) {{
                showNotification('Netzwerkfehler: ' + e.message, true);
            }}
        }}
        
        async function restoreBackup(backupPath) {{
            if (!confirm('Backup wirklich wiederherstellen?\\n\\n⚠️ Server muss gestoppt sein!')) return;
            
            try {{
                const res = await fetch('/api/server/' + currentServerId + '/backups/restore', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{backup_path: backupPath}})
                }});
                const data = await res.json();
                handleResponse(data, res);
            }} catch (e) {{
                showNotification('Netzwerkfehler: ' + e.message, true);
            }}
        }}
        
        async function deleteBackup(backupPath) {{
            if (!confirm('Backup wirklich löschen?')) return;
            
            try {{
                const res = await fetch('/api/server/' + currentServerId + '/backups/delete', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{backup_path: backupPath}})
                }});
                const data = await res.json();
                handleResponse(data, res);
                loadBackupList();
            }} catch (e) {{
                showNotification('Netzwerkfehler: ' + e.message, true);
            }}
        }}
        
        // ===== MODS =====
        async function addMod(serverId) {{
            const input = document.getElementById('mod-input-' + serverId);
            const modId = input.value.trim();
            if (!modId) return;
            
            try {{
                const res = await fetch('/api/server/' + serverId + '/mods', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{mod_id: modId}})
                }});
                const data = await res.json();
                handleResponse(data, res);
                input.value = '';
                loadServers();
            }} catch (e) {{
                showNotification('Netzwerkfehler: ' + e.message, true);
            }}
        }}
        
        async function removeMod(serverId, modId) {{
            try {{
                const res = await fetch('/api/server/' + serverId + '/mods/' + modId, {{method: 'DELETE'}});
                const data = await res.json();
                handleResponse(data, res);
                loadServers();
            }} catch (e) {{
                showNotification('Netzwerkfehler: ' + e.message, true);
            }}
        }}

        async function syncConanMods(serverId) {{
            try {{
                const res = await fetch('/api/server/' + serverId + '/conan/mods/sync', {{ method: 'POST' }});
                const data = await res.json();
                handleResponse(data, res);
                setTimeout(loadServers, 2500);
            }} catch (e) {{
                showNotification('Netzwerkfehler: ' + e.message, true);
            }}
        }}

        async function toggleConanAutoModUpdate(serverId, enabled) {{
            try {{
                const res = await fetch('/api/server/' + serverId + '/conan/mods/auto-start', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{ enabled: !!enabled }})
                }});
                const data = await res.json();
                handleResponse(data, res);
                setTimeout(loadServers, 500);
            }} catch (e) {{
                showNotification('Netzwerkfehler: ' + e.message, true);
            }}
        }}

        async function uploadConanMod(serverId) {{
            const input = document.getElementById('conan-upload-' + serverId);
            if (!input || !input.files || !input.files.length) {{
                showNotification('Bitte .pak Datei auswählen', true);
                return;
            }}

            const file = input.files[0];
            if (!file.name.toLowerCase().endsWith('.pak')) {{
                showNotification('Nur .pak Dateien sind erlaubt', true);
                return;
            }}

            const limit = {CONAN_UPLOAD_MAX_BYTES};
            if (file.size > limit) {{
                showNotification('Datei zu groß (max. 8 GB)', true);
                return;
            }}

            const form = new FormData();
            form.append('mod_file', file, file.name);

            const statusEl = document.getElementById('conan-upload-status-' + serverId);
            const setStatus = (text, isError = false) => {{
                if (!statusEl) return;
                statusEl.textContent = text;
                statusEl.style.color = isError ? '#ffb4b4' : '#8ea3c8';
            }};
            const formatBytes = (n) => {{
                const v = Number(n || 0);
                if (v < 1024) return v + ' B';
                if (v < 1024 * 1024) return (v / 1024).toFixed(1) + ' KB';
                if (v < 1024 * 1024 * 1024) return (v / (1024 * 1024)).toFixed(1) + ' MB';
                return (v / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
            }};

            setStatus('Upload startet: ' + file.name);
            showNotification('Upload läuft: ' + file.name);

            const xhr = new XMLHttpRequest();
            xhr.open('POST', '/api/server/' + serverId + '/conan/mods/upload', true);
            xhr.withCredentials = true;

            xhr.upload.onprogress = (ev) => {{
                if (!ev.lengthComputable) {{
                    setStatus('Upload läuft: ' + file.name + ' (' + formatBytes(ev.loaded) + ')');
                    return;
                }}
                const pct = Math.max(0, Math.min(100, (ev.loaded / ev.total) * 100));
                setStatus('Upload läuft: ' + file.name + ' - ' + pct.toFixed(1) + '% (' + formatBytes(ev.loaded) + ' / ' + formatBytes(ev.total) + ')');
            }};

            xhr.onerror = () => {{
                setStatus('Upload fehlgeschlagen (Netzwerkfehler)', true);
                showNotification('Upload-Fehler: Netzwerkfehler', true);
            }};

            xhr.onabort = () => {{
                setStatus('Upload abgebrochen', true);
                showNotification('Upload abgebrochen', true);
            }};

            xhr.onreadystatechange = () => {{
                if (xhr.readyState !== 4) return;
                let data = {{ success: false, message: 'Ungültige Serverantwort' }};
                try {{
                    data = JSON.parse(xhr.responseText || '{{}}');
                }} catch (_) {{}}

                if (xhr.status >= 200 && xhr.status < 300 && data.success) {{
                    setStatus('Upload abgeschlossen: ' + file.name);
                    handleResponse(data, {{ ok: true }});
                    input.value = '';
                    setTimeout(loadServers, 800);
                    return;
                }}

                const errMsg = data.message || ('Fehler: HTTP ' + xhr.status);
                setStatus('Upload fehlgeschlagen: ' + errMsg, true);
                handleResponse(data, {{ ok: false, status: xhr.status }});
            }};

            xhr.send(form);
        }}

        function renderModRows(server) {{
            const status = server.conan_mod_status || {{}};
            const configured = Array.isArray(status.configured) ? status.configured : [];
            if (!configured.length) return '<p style="color:#888; font-size:0.82em;">Keine Mods konfiguriert</p>';

            return configured.map(m => {{
                const isMissing = Array.isArray(status.missing) && status.missing.some(x => x.id === m.id);
                return `<div class="mod-row">
                    <span class="mod-id">${{m.id}}</span>
                    <span class="mod-name">${{m.name || ('Mod ' + m.id)}}</span>
                    <span class="mod-state ${{isMissing ? 'missing' : 'ok'}}">${{isMissing ? 'fehlt auf Server' : 'ok'}}</span>
                </div>`;
            }}).join('');
        }}

        function renderConanModOptions(server) {{
            const status = server.conan_mod_status || {{}};
            const configured = Array.isArray(status.configured) ? status.configured : [];
            if (!configured.length) return '<option>Keine Mods konfiguriert</option>';
            return configured.map(m => `<option>${{m.name || m.id}}</option>`).join('');
        }}
        
        // ===== KACHELN =====
        var showTilesMode = true;
        var filterGame = '';
        
        function makeTiles(servers) {{
            const grid = document.getElementById('game-grid');
            const list = document.getElementById('servers');
            const toolbar = document.getElementById('view-toolbar');
            grid.style.display = 'grid';
            list.style.display = 'none';
            toolbar.style.display = 'none';
            
            const groups = {{}};
            servers.forEach(s => {{
                const g = s.game || 'Unknown';
                if (!groups[g]) groups[g] = {{ icon: s.icon || '🎮', total: 0, online: 0, offline: 0 }};
                groups[g].total++;
                if (s.running) groups[g].online++; else groups[g].offline++;
            }});
            
            let html = '';
            Object.keys(groups).sort((a, b) => a.localeCompare(b, 'de', {{ sensitivity: 'base' }})).forEach(name => {{
                const d = groups[name];
                const safeName = name.replace(/'/g, "\\'");
                html += "<div class=\\"game-tile\\" onclick=\\"showTilesMode=false;filterGame='" + safeName + "';loadServers();\\">";
                html += "<div class=\\"game-tile-icon\\">" + d.icon + "</div>";
                html += "<div class=\\"game-tile-name\\">" + name + "</div>";
                html += "<div class=\\"game-tile-count\\">";
                html += "<div class=\\"count-item\\"><div class=\\"count-value count-total\\">" + d.total + "</div><div class=\\"count-label\\">Total</div></div>";
                html += "<div class=\\"count-item\\"><div class=\\"count-value count-online\\">" + d.online + "</div><div class=\\"count-label\\">Online</div></div>";
                html += "<div class=\\"count-item\\"><div class=\\"count-value count-offline\\">" + d.offline + "</div><div class=\\"count-label\\">Offline</div></div>";
                html += "</div></div>";
            }});
            
            grid.innerHTML = html || '<p style="text-align:center;opacity:0.5;padding:50px;">Keine Server</p>';
        }}
        
        // ===== SERVER LIST =====
        async function loadServers() {{
            try {{
                const res = await fetch('/api/servers');
                const data = await res.json();
                
                if (!res.ok || data.error) {{
                    console.error('Fehler beim Laden der Server:', data.error);
                    return;
                }}
                
                const all = data.servers || [];
                document.getElementById('server-count').textContent = all.length;
                document.getElementById('online-count').textContent = all.filter(s => s.running).length;
                
                if (showTilesMode) {{
                    makeTiles(all);
                    return;
                }}
                
                const filtered = filterGame ? all.filter(s => s.game === filterGame) : all;
                document.getElementById('game-grid').style.display = 'none';
                document.getElementById('view-toolbar').style.display = 'flex';
                const container = document.getElementById('servers');
                container.style.display = 'block';
                
                if (filtered.length === 0) {{
                    container.innerHTML = '<p style="text-align:center;color:#888;padding:50px;">{t("no_servers")}</p>';
                    return;
                }}
            
            container.innerHTML = filtered.map(s => `
                <div class="server-card">
                    <div class="server-top">
                        <div class="server-title-area">
                            <div class="server-header">
                                <span class="server-name">${{s.name}}</span>
                                <span class="server-game">${{s.game}}</span>
                                <span class="status ${{!s.installed ? 'not-installed' : (s.running ? 'online' : 'offline')}}">
                                    ${{!s.installed ? '⚠️ Nicht installiert' : (s.running ? '🟢 Online' : '⚫ Offline')}}
                                </span>
                            </div>
                            <div class="connection-info">
                                🔗 <span onclick="copyToClipboard('${{s.port}}')" title="Klicken zum Kopieren">Port: ${{s.port}}</span>
                                ${{s.query_port ? '<span onclick="copyToClipboard(\\'' + s.query_port + '\\')" title="Klicken zum Kopieren">Query: ' + s.query_port + '</span>' : ''}}
                            </div>
                        </div>
                        <div class="buttons">
                            <button class="btn btn-start" onclick="serverAction('${{s.id}}', 'start')" ${{!s.installed ? 'disabled' : ''}}>▶ Starten</button>
                            <button class="btn btn-stop" onclick="serverAction('${{s.id}}', 'stop')" ${{!s.installed ? 'disabled' : ''}}>⏹ Stoppen</button>
                            <button class="btn btn-restart" onclick="serverAction('${{s.id}}', 'restart')" ${{!s.installed ? 'disabled' : ''}}>🔄 Neustarten</button>
                            <button class="btn btn-update" onclick="updateServer('${{s.id}}')" ${{!s.installed ? 'disabled' : ''}}>⬆ Update</button>
                            <button class="btn btn-backup" onclick="showBackups('${{s.id}}', '${{s.name}}')">💾 Backups</button>
                            <button class="btn btn-config" onclick="showConfig('${{s.id}}', '${{s.name}}')">📝 Config</button>
                            <button class="btn btn-logs" onclick="showLogs('${{s.id}}', '${{s.name}}')">📜 Logs</button>
                        </div>
                    </div>
                    
                    <div class="features">
                        ${{s.auto_restart ? '<span class="feature active">🔄 Auto-Restart</span>' : ''}}
                        ${{s.auto_backup ? '<span class="feature active">💾 Auto-Backup (' + s.backup_interval + 'h)</span>' : ''}}
                    </div>
                    
                    <div class="server-info">
                        <div class="info-item">
                            <div class="info-label">{t("max_players")}</div>
                            <div class="info-value">${{s.max_players || '-'}}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">{t("map")}</div>
                            <div class="info-value">${{s.map || '-'}}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">{t("uptime")}</div>
                            <div class="info-value">${{s.uptime}}</div>
                        </div>
                    </div>
                    
                    ${{(s.game.includes('ARK') || s.game === 'Conan Exiles' || (s.mods && s.mods.length > 0)) ? `
                    <div class="mods-section">
                        <div class="mods-header">
                            <span class="mods-title">🧩 Mods (${{s.mods ? s.mods.length : 0}})</span>
                        </div>

                        ${{s.game === 'Conan Exiles' ? `
                        <div class="mod-actions" style="margin-top:8px;">
                            <select style="min-width:300px; max-width:100%; background:#16233d; color:#dce8ff; border:1px solid #2f446c; border-radius:6px; padding:6px 8px;">
                                ${{renderConanModOptions(s)}}
                            </select>
                        </div>
                        <details class="mod-dropdown">
                            <summary>Mod-Liste anzeigen (${{s.conan_mod_status && s.conan_mod_status.configured ? s.conan_mod_status.configured.length : 0}})</summary>
                            <div class="mod-dropdown-body">
                                <div class="mods-list">
                                    ${{renderModRows(s)}}
                                </div>
                            </div>
                        </details>
                        <div class="mod-actions">
                            <button class="btn btn-small btn-restart" onclick="syncConanMods('${{s.id}}')">🧩 Mods jetzt syncen</button>
                            <button class="btn btn-small ${{s.conan_auto_mod_update ? 'btn-start' : 'btn-stop'}}" onclick="toggleConanAutoModUpdate('${{s.id}}', ${{!s.conan_auto_mod_update}})">
                                ${{s.conan_auto_mod_update ? '✅ Auto-Mod-Update beim Start: AN' : '⏸️ Auto-Mod-Update beim Start: AUS'}}
                            </button>
                        </div>
                        <div class="mod-sync-meta">
                            ${{s.conan_mod_sync && s.conan_mod_sync.last_run ? ('Letzter Sync: ' + s.conan_mod_sync.last_run + ' - ' + (s.conan_mod_sync.message || '')) : 'Noch kein Mod-Sync ausgeführt'}}
                        </div>
                        <div class="mod-sync-meta" id="conan-upload-status-${{s.id}}">
                            ${{s.conan_mod_upload && s.conan_mod_upload.last_run ? ('Letzter Upload: ' + s.conan_mod_upload.last_run + ' - ' + (s.conan_mod_upload.message || '')) : 'Noch kein Mod-Upload ausgeführt'}}
                        </div>
                        <div class="mod-upload">
                            <div class="mod-upload-title">⬆ Manueller Mod-Upload (.pak, max. 8 GB, erstellt Backup vor Überschreiben)</div>
                            <div class="mod-upload-row">
                                <input type="file" id="conan-upload-${{s.id}}" accept=".pak">
                                <button class="btn btn-small btn-config" onclick="uploadConanMod('${{s.id}}')">Upload .pak</button>
                            </div>
                        </div>
                        ` : (s.mods && s.mods.length > 0 ? `
                        <div class="mods-list">
                            ${{s.mods.map(m => `<span class="mod-tag">${{m}} <span class="remove" onclick="removeMod('${{s.id}}', '${{m}}')">&times;</span></span>`).join('')}}
                        </div>
                        ` : '')}}
                        <div class="add-mod">
                            <input type="text" id="mod-input-${{s.id}}" placeholder="Mod-ID eingeben..." onkeypress="if(event.key==='Enter')addMod('${{s.id}}')">
                            <button onclick="addMod('${{s.id}}')">+ Hinzufügen</button>
                        </div>
                    </div>
                    ` : ''}}
                </div>
            `).join('');
            }} catch (e) {{
                console.error('Fehler beim Laden der Server:', e);
            }}
        }}
        
        async function serverAction(id, action) {{
            try {{
                const res = await fetch(`/api/server/${{id}}/${{action}}`, {{method: 'POST'}});
                const data = await res.json();
                handleResponse(data, res);
                setTimeout(loadServers, 2000);
            }} catch (e) {{
                showNotification('Netzwerkfehler: ' + e.message, true);
            }}
        }}

        async function updateServer(serverId) {{
            if (!confirm('Server jetzt updaten?\\n\\nHinweis: Bei laufendem Server wird er für das Update kurz gestoppt.')) return;

            try {{
                const res = await fetch('/api/server/' + serverId + '/update', {{method: 'POST'}});
                const data = await res.json();
                handleResponse(data, res);
                setTimeout(loadServers, 2000);
            }} catch (e) {{
                showNotification('Netzwerkfehler: ' + e.message, true);
            }}
        }}
        
        // Modal schließen bei Klick außerhalb
        document.querySelectorAll('.modal').forEach(modal => {{
            modal.addEventListener('click', function(e) {{
                if (e.target === this) closeModal(this.id);
            }});
        }});
        
        loadServers();
        loadServiceStatus();
        setInterval(loadServiceStatus, 5000);
    </script>
</body>
</html>
'''


def _load_external_template(filename, fallback_html):
    try:
        template_path = os.path.join(_ROOT, 'templates', filename)
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
    except:
        pass
    return fallback_html


def get_chat_disabled_template(config_manager):
    fallback = '<html><body style="font-family:Segoe UI,sans-serif;background:#101826;color:#e5e7eb;padding:30px;"><h2>Chat/Stream ist deaktiviert</h2><p>Bitte im Desktop-Tool unter Tools -> Chat & Stream aktivieren.</p><p><a href="/" style="color:#5fb0ff;">Zurück</a></p></body></html>'
    return _load_external_template('chat_disabled.html', fallback)


def get_chat_forbidden_template(config_manager):
    fallback = '<html><body style="font-family:Segoe UI,sans-serif;background:#101826;color:#e5e7eb;padding:30px;"><h2>Zugriff nur via Tailscale</h2><p>Diese Seite ist nur aus dem Tailscale-Netz erreichbar.</p></body></html>'
    return _load_external_template('chat_forbidden.html', fallback)


def get_chat_template(config_manager):
    fallback = '<html><body style="font-family:Segoe UI,sans-serif;background:#101826;color:#e5e7eb;padding:30px;"><h2>Chat Template fehlt</h2><p>Datei templates/chat_stream.html wurde nicht gefunden.</p></body></html>'
    return _load_external_template('chat_stream.html', fallback)


def get_modern_template(config_manager=None):
    """Moderne Web-Oberfläche (SPA). Wird direkt ausgeliefert (kein Jinja)."""
    fallback = '<html><body style="font-family:Segoe UI,sans-serif;background:#0e1116;color:#e8ecf2;padding:30px;"><h2>Oberfläche fehlt</h2><p>Datei templates/modern.html wurde nicht gefunden.</p></body></html>'
    return _load_external_template('modern.html', fallback)


def get_modern_login_template(config_manager=None, error=False):
    """Modernes Login. Fehlerbanner wird per Platzhalter eingesetzt (kein Jinja)."""
    fallback = '<html><body style="font-family:Segoe UI,sans-serif;background:#0e1116;color:#e8ecf2;padding:30px;"><h2>Login fehlt</h2><p>Datei templates/modern_login.html wurde nicht gefunden.</p></body></html>'
    html = _load_external_template('modern_login.html', fallback)
    banner = ('<div class="err">Falsches Passwort. Bitte erneut versuchen.</div>' if error else '')
    return html.replace('<!--ERROR-->', banner)
