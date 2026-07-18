"""Flask-Webserver als App-Factory.

Aus game_server_manager.py ausgelagert (Phase 2). Verhalten unveraendert:
`create_web_app(app_instance, config_manager)` baut die Flask-App inkl. aller
Routen und gibt sie zurueck; `start_web_server(app_instance)` startet sie im
Daemon-Thread. Alle Route-Closures greifen ausschliesslich ueber `app_instance`
und `config_manager` auf die Anwendung zu (kein `self`).
"""

import os
import shutil
import time
import ipaddress
import secrets
import threading
from datetime import datetime

import psutil
from flask import Flask, render_template_string, jsonify, request, session, redirect
from werkzeug.exceptions import RequestEntityTooLarge

from gsm.constants import CONAN_UPLOAD_MAX_BYTES, SENSITIVE_SERVER_KEYS
from gsm.paths import PATHS
from gsm.games import SUPPORTED_GAMES
from gsm.security import generate_session_token, validate_config_path
from gsm.mods import _sanitize_pak_filename, fetch_workshop_mod_names
from gsm.web.templates import (
    get_modern_template, get_modern_login_template,
    get_chat_disabled_template, get_chat_forbidden_template, get_chat_template,
)


def create_web_app(app_instance, config_manager):
    """Baut die Flask-App mit allen Routen und gibt sie zurueck."""
    flask_app = Flask(__name__)
    flask_app.secret_key = secrets.token_hex(32)
    flask_app.config['MAX_CONTENT_LENGTH'] = CONAN_UPLOAD_MAX_BYTES

    @flask_app.errorhandler(RequestEntityTooLarge)
    def handle_upload_too_large(_err):
        limit_gb = CONAN_UPLOAD_MAX_BYTES / (1024 * 1024 * 1024)
        return jsonify({
            'success': False,
            'message': f'Datei zu groß. Maximal {limit_gb:.0f} GB erlaubt.'
        }), 413
    
    # Logging deaktivieren
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    # Session Token speichern
    valid_sessions = {}

    def get_chat_user_id():
        token = session.get('token', '')
        if not token:
            return None
        return token[:12]

    def is_tailscale_client(ip_text):
        if not ip_text:
            return False
        ip_text = ip_text.strip()
        if ip_text in ('127.0.0.1', '::1'):
            return True
        try:
            ip_obj = ipaddress.ip_address(ip_text)
            if isinstance(ip_obj, ipaddress.IPv4Address):
                return ip_obj in ipaddress.ip_network('100.64.0.0/10')
            return ip_obj in ipaddress.ip_network('fd7a:115c:a1e0::/48')
        except Exception:
            return False

    def get_client_ip():
        """Ermittelt die Client-IP ohne ungeprueftem Proxy-Trust."""
        remote_addr = (request.remote_addr or '').strip()
        trusted_proxy_ips = {'127.0.0.1', '::1', '::ffff:127.0.0.1'}
        if remote_addr in trusted_proxy_ips:
            forwarded = request.headers.get('X-Forwarded-For', '')
            if forwarded:
                forwarded_ip = forwarded.split(',')[0].strip()
                if forwarded_ip:
                    return forwarded_ip
        return remote_addr

    def ensure_chat_access():
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401

        chat_cfg = app_instance.get_chat_stream_config()
        if not chat_cfg.get('enabled', False):
            return jsonify({'error': 'Chat/Stream ist deaktiviert'}), 503

        if chat_cfg.get('require_tailscale', True):
            remote_ip = get_client_ip()
            if not is_tailscale_client(remote_ip):
                return jsonify({'error': 'Zugriff nur über Tailscale erlaubt'}), 403
        return None
    
    @flask_app.route('/')
    def index():
        if 'token' not in session or session['token'] not in valid_sessions:
            return redirect('/login')
        # Moderne Oberfläche direkt ausliefern (kein Jinja, da SPA mit {}/${})
        return get_modern_template(config_manager)

    @flask_app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            password = request.form.get('password', '')
            if config_manager.verify_password(password):
                token = generate_session_token()
                valid_sessions[token] = True
                session['token'] = token
                return redirect('/')
            return get_modern_login_template(config_manager, error=True)
        return get_modern_login_template(config_manager)
    
    @flask_app.route('/logout')
    def logout():
        if 'token' in session:
            valid_sessions.pop(session['token'], None)
            session.pop('token', None)
        return redirect('/login')

    @flask_app.route('/chat')
    def chat_page():
        if 'token' not in session or session['token'] not in valid_sessions:
            return redirect('/login')

        chat_cfg = app_instance.get_chat_stream_config()
        if not chat_cfg.get('enabled', False):
            return render_template_string(get_chat_disabled_template(config_manager))

        if chat_cfg.get('require_tailscale', True):
            remote_ip = get_client_ip()
            if not is_tailscale_client(remote_ip):
                return render_template_string(get_chat_forbidden_template(config_manager))

        return render_template_string(get_chat_template(config_manager))

    @flask_app.route('/api/chat/bootstrap')
    def api_chat_bootstrap():
        denied = ensure_chat_access()
        if denied:
            return denied

        user_id = get_chat_user_id()
        if not user_id:
            return jsonify({'error': 'Unauthorized'}), 401

        now = time.time()
        with app_instance.chat_runtime['lock']:
            app_instance.chat_runtime['presence'][user_id] = now
            active_users = [uid for uid, ts in app_instance.chat_runtime['presence'].items() if now - ts <= 35]
            room_name = app_instance.get_chat_stream_config().get('room_name', 'Private Room')

        return jsonify({'success': True, 'user_id': user_id, 'room_name': room_name, 'active_users': active_users})

    @flask_app.route('/api/chat/ping', methods=['POST'])
    def api_chat_ping():
        denied = ensure_chat_access()
        if denied:
            return denied

        user_id = get_chat_user_id()
        if not user_id:
            return jsonify({'error': 'Unauthorized'}), 401

        now = time.time()
        with app_instance.chat_runtime['lock']:
            app_instance.chat_runtime['presence'][user_id] = now
            stale = [uid for uid, ts in app_instance.chat_runtime['presence'].items() if now - ts > 60]
            for uid in stale:
                app_instance.chat_runtime['presence'].pop(uid, None)

        return jsonify({'success': True})

    @flask_app.route('/api/chat/messages', methods=['GET', 'POST'])
    def api_chat_messages():
        denied = ensure_chat_access()
        if denied:
            return denied

        user_id = get_chat_user_id()
        if not user_id:
            return jsonify({'error': 'Unauthorized'}), 401

        if request.method == 'POST':
            payload = request.get_json(silent=True) or {}
            msg = str(payload.get('message', '')).strip()
            if not msg:
                return jsonify({'success': False, 'message': 'Leere Nachricht'})
            if len(msg) > 800:
                msg = msg[:800]

            with app_instance.chat_runtime['lock']:
                app_instance.chat_runtime['message_seq'] += 1
                item = {
                    'id': app_instance.chat_runtime['message_seq'],
                    'user_id': user_id,
                    'message': msg,
                    'ts': datetime.now().strftime('%H:%M:%S')
                }
                app_instance.chat_runtime['messages'].append(item)
                if len(app_instance.chat_runtime['messages']) > 500:
                    app_instance.chat_runtime['messages'] = app_instance.chat_runtime['messages'][-500:]
            return jsonify({'success': True})

        since = request.args.get('since', '0')
        try:
            since_id = int(since)
        except:
            since_id = 0

        with app_instance.chat_runtime['lock']:
            data = [m for m in app_instance.chat_runtime['messages'] if m['id'] > since_id]
        return jsonify({'success': True, 'messages': data})

    @flask_app.route('/api/chat/signals', methods=['GET', 'POST'])
    def api_chat_signals():
        denied = ensure_chat_access()
        if denied:
            return denied

        user_id = get_chat_user_id()
        if not user_id:
            return jsonify({'error': 'Unauthorized'}), 401

        if request.method == 'POST':
            payload = request.get_json(silent=True) or {}
            signal_type = str(payload.get('type', '')).strip()
            body = payload.get('data', {})
            target = str(payload.get('target', '')).strip() or None

            if signal_type not in ('offer', 'answer', 'ice', 'control'):
                return jsonify({'success': False, 'message': 'Ungültiger Signal-Typ'})

            with app_instance.chat_runtime['lock']:
                app_instance.chat_runtime['signal_seq'] += 1
                signal = {
                    'id': app_instance.chat_runtime['signal_seq'],
                    'from': user_id,
                    'target': target,
                    'type': signal_type,
                    'data': body,
                    'ts': time.time()
                }
                app_instance.chat_runtime['signals'].append(signal)
                if len(app_instance.chat_runtime['signals']) > 1200:
                    app_instance.chat_runtime['signals'] = app_instance.chat_runtime['signals'][-1200:]
            return jsonify({'success': True})

        since = request.args.get('since', '0')
        try:
            since_id = int(since)
        except:
            since_id = 0

        with app_instance.chat_runtime['lock']:
            out = []
            for s in app_instance.chat_runtime['signals']:
                if s['id'] <= since_id:
                    continue
                if s['from'] == user_id:
                    continue
                if s['target'] and s['target'] != user_id:
                    continue
                out.append(s)
        return jsonify({'success': True, 'signals': out})

    @flask_app.route('/api/chat/status')
    def api_chat_status():
        denied = ensure_chat_access()
        if denied:
            return denied

        now = time.time()
        with app_instance.chat_runtime['lock']:
            users = [uid for uid, ts in app_instance.chat_runtime['presence'].items() if now - ts <= 35]
        return jsonify({'success': True, 'active_users': users, 'ts3_running': app_instance.is_teamspeak3_running()})

    @flask_app.route('/api/services/status')
    def api_services_status():
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401
        payload = app_instance.get_service_status_payload()
        payload['success'] = True
        return jsonify(payload)

    @flask_app.route('/api/services/chat/start', methods=['POST'])
    def api_services_chat_start():
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401
        app_instance.set_chat_stream_enabled(True)
        payload = app_instance.get_service_status_payload()
        return jsonify({'success': True, 'message': 'Chat/Stream aktiviert', **payload})

    @flask_app.route('/api/services/chat/stop', methods=['POST'])
    def api_services_chat_stop():
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401
        app_instance.set_chat_stream_enabled(False)
        payload = app_instance.get_service_status_payload()
        return jsonify({'success': True, 'message': 'Chat/Stream deaktiviert', **payload})

    @flask_app.route('/api/services/teamspeak/start', methods=['POST'])
    def api_services_teamspeak_start():
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401
        ok, msg = app_instance.start_teamspeak3_server()
        payload = app_instance.get_service_status_payload()
        status = 200 if ok else 400
        return jsonify({'success': ok, 'message': msg, **payload}), status

    @flask_app.route('/api/services/teamspeak/stop', methods=['POST'])
    def api_services_teamspeak_stop():
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401
        ok, msg = app_instance.stop_teamspeak3_server()
        payload = app_instance.get_service_status_payload()
        status = 200 if ok else 400
        return jsonify({'success': ok, 'message': msg, **payload}), status

    
    @flask_app.route('/api/servers')
    def api_servers():
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401
        
        servers = []
        for server_id, server_config in config_manager.servers.items():
            instance = app_instance.server_instances.get(server_id)
            running = instance.is_running() if instance else False
            conan_status = None
            if server_config.get('game') == 'Conan Exiles' and instance:
                try:
                    conan_status = instance.get_conan_mod_status()
                except Exception:
                    conan_status = None
            res = {}
            if running:
                try:
                    res = instance.get_resource_usage() or {}
                except Exception:
                    res = {}
            servers.append({
                'id': server_id,
                'name': server_config.get('name', 'Server'),
                'icon': SUPPORTED_GAMES.get(server_config.get('game', ''), {}).get('icon', '🎮'),
                'game': server_config.get('game', ''),
                'map': server_config.get('map_name', server_config.get('map', '')),
                'port': server_config.get('port', 0),
                'query_port': server_config.get('query_port', 0),
                'max_players': server_config.get('max_players', 0),
                'running': running,
                'cpu': round(res.get('cpu', 0)),
                'ram_percent': round(res.get('ram_percent', 0)),
                'ram_gb': round(res.get('ram_gb', 0), 1),
                'installed': server_config.get('installed', False),
                'uptime': instance.get_uptime() if instance else '-',
                'mods': server_config.get('mods', []),
                'mod_names': server_config.get('mod_names', {}),
                'conan_auto_mod_update': server_config.get('conan_auto_mod_update', True if server_config.get('game') == 'Conan Exiles' else False),
                'conan_mod_sync': server_config.get('conan_mod_sync', {}),
                'conan_mod_upload': server_config.get('conan_mod_upload', {}),
                'conan_mod_status': conan_status,
                'auto_restart': server_config.get('auto_restart', True),
                'auto_backup': server_config.get('auto_backup', False),
                'backup_interval': server_config.get('backup_interval_hours', 0),
                'max_backups': server_config.get('max_backups', 10)
            })
        return jsonify({'servers': servers})

    @flask_app.route('/api/games')
    def api_games():
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401
        out = [{'name': k, 'icon': v.get('icon', '🎮'),
                'default_port': v.get('default_ports', {}).get('game', 7777)}
               for k, v in SUPPORTED_GAMES.items()]
        return jsonify({'games': out})

    @flask_app.route('/api/servers', methods=['POST'])
    def api_create_server():
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401

        data = request.get_json(silent=True) or {}
        name = str(data.get('name', '')).strip()
        game = str(data.get('game', '')).strip()
        if not name:
            return jsonify({'success': False, 'message': 'Bitte einen Servernamen angeben.'}), 400
        if game not in SUPPORTED_GAMES:
            return jsonify({'success': False, 'message': 'Unbekanntes Spiel.'}), 400
        try:
            port = int(data.get('port', 0))
            max_players = int(data.get('max_players', 10))
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Port und Max. Spieler müssen Zahlen sein.'}), 400
        if not (1 <= port <= 65535):
            return jsonify({'success': False, 'message': 'Port muss zwischen 1 und 65535 liegen.'}), 400

        import re as _re
        base_id = _re.sub(r'[^a-z0-9_]', '', name.lower().replace(' ', '_')) or 'server'
        server_id = base_id
        _n = 1
        while server_id in config_manager.servers:
            server_id = f"{base_id}_{_n}"
            _n += 1

        game_info = SUPPORTED_GAMES.get(game, {})
        try:
            query_port = int(data.get('query_port', 0))
        except (ValueError, TypeError):
            query_port = 0
        if not query_port:
            query_port = game_info.get('default_ports', {}).get('query', port + 1)

        from datetime import datetime as _dt
        server_config = {
            'name': name, 'game': game, 'map': '', 'map_name': '',
            'port': port, 'query_port': query_port, 'max_players': max_players,
            'server_password': '', 'admin_password': 'admin',
            'mods': [], 'mod_names': {},
            'conan_auto_mod_update': game == 'Conan Exiles',
            'conan_mod_sync': {}, 'conan_mod_upload': {},
            'auto_restart': True, 'auto_backup': True,
            'backup_interval_hours': 3, 'max_backups': 10,
            'installed': False, 'created_at': _dt.now().isoformat()
        }
        config_manager.add_server(server_id, server_config)
        try:
            from gsm.server import ServerInstance
            app_instance.server_instances[server_id] = ServerInstance(
                server_id, server_config, config_manager,
                getattr(app_instance, 'discord_notifier', None)
            )
        except Exception:
            pass
        return jsonify({'success': True, 'id': server_id, 'message': f'Server „{name}“ angelegt.'})

    @flask_app.route('/api/server/<server_id>/delete', methods=['POST'])
    def api_delete_server(server_id):
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401
        if server_id not in config_manager.servers:
            return jsonify({'success': False, 'message': 'Server nicht gefunden'}), 404
        instance = app_instance.server_instances.get(server_id)
        if instance and instance.is_running():
            try:
                instance.stop()
            except Exception:
                pass
        config_manager.remove_server(server_id)
        app_instance.server_instances.pop(server_id, None)
        return jsonify({'success': True, 'message': 'Server aus dem Manager entfernt (Dateien bleiben erhalten).'})

    @flask_app.route('/api/server/<server_id>/details')
    def api_server_details(server_id):
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401
        
        server_config = config_manager.servers.get(server_id, {})
        instance = app_instance.server_instances.get(server_id)
        game_info = SUPPORTED_GAMES.get(server_config.get('game', ''), {})

        # Klartext-Geheimnisse nicht über die Web-API ausliefern
        safe_config = {k: v for k, v in server_config.items() if k not in SENSITIVE_SERVER_KEYS}

        return jsonify({
            'id': server_id,
            'config': safe_config,
            'running': instance.is_running() if instance else False,
            'uptime': instance.get_uptime() if instance else '-',
            'game_info': {
                'default_port': game_info.get('default_port', 7777),
                'default_query_port': game_info.get('default_query_port', 27015)
            }
        })
    
    @flask_app.route('/api/server/<server_id>/mods', methods=['POST'])
    def api_add_mod(server_id):
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401
        
        data = request.get_json()
        mod_id = data.get('mod_id', '').strip()
        
        if not mod_id:
            return jsonify({'success': False, 'message': 'Mod-ID fehlt'})
        
        server_config = config_manager.servers.get(server_id)
        if not server_config:
            return jsonify({'success': False, 'message': 'Server nicht gefunden'})
        
        if 'mods' not in server_config:
            server_config['mods'] = []
        
        if mod_id in server_config['mods']:
            return jsonify({'success': False, 'message': 'Mod bereits vorhanden'})

        server_config['mods'].append(mod_id)
        if 'mod_names' not in server_config or not isinstance(server_config.get('mod_names'), dict):
            server_config['mod_names'] = {}
        fetched = fetch_workshop_mod_names([mod_id])
        if fetched.get(mod_id):
            server_config['mod_names'][mod_id] = fetched[mod_id]
        config_manager.save_servers()

        return jsonify({'success': True, 'message': f'Mod {mod_id} hinzugefügt', 'mods': server_config['mods']})
    
    @flask_app.route('/api/server/<server_id>/mods/<mod_id>', methods=['DELETE'])
    def api_remove_mod(server_id, mod_id):
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401
        
        server_config = config_manager.servers.get(server_id)
        if not server_config:
            return jsonify({'success': False, 'message': 'Server nicht gefunden'})
        
        if 'mods' not in server_config or mod_id not in server_config['mods']:
            return jsonify({'success': False, 'message': 'Mod nicht gefunden'})

        server_config['mods'].remove(mod_id)
        if isinstance(server_config.get('mod_names'), dict) and mod_id in server_config['mod_names']:
            del server_config['mod_names'][mod_id]
        config_manager.save_servers()

        return jsonify({'success': True, 'message': f'Mod {mod_id} entfernt', 'mods': server_config['mods']})

    @flask_app.route('/api/server/<server_id>/conan/mods/status')
    def api_conan_mod_status(server_id):
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401

        server_config = config_manager.servers.get(server_id)
        if not server_config or server_config.get('game') != 'Conan Exiles':
            return jsonify({'success': False, 'message': 'Kein Conan Exiles Server'})

        instance = app_instance.server_instances.get(server_id)
        if not instance:
            return jsonify({'success': False, 'message': 'Server nicht gefunden'})

        status = instance.get_conan_mod_status()
        return jsonify({'success': True, 'status': status, 'auto_mod_update': server_config.get('conan_auto_mod_update', True)})

    @flask_app.route('/api/server/<server_id>/conan/mods/sync', methods=['POST'])
    def api_conan_mod_sync(server_id):
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401

        server_config = config_manager.servers.get(server_id)
        if not server_config or server_config.get('game') != 'Conan Exiles':
            return jsonify({'success': False, 'message': 'Kein Conan Exiles Server'})

        instance = app_instance.server_instances.get(server_id)
        if not instance:
            return jsonify({'success': False, 'message': 'Server nicht gefunden'})

        def do_sync():
            instance.sync_conan_mods()

        threading.Thread(target=do_sync, daemon=True).start()
        return jsonify({'success': True, 'message': 'Conan Mod-Sync gestartet'})

    @flask_app.route('/api/server/<server_id>/conan/mods/auto-start', methods=['POST'])
    def api_conan_mod_auto_start(server_id):
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401

        server_config = config_manager.servers.get(server_id)
        if not server_config or server_config.get('game') != 'Conan Exiles':
            return jsonify({'success': False, 'message': 'Kein Conan Exiles Server'})

        data = request.get_json() or {}
        enabled = bool(data.get('enabled', True))
        server_config['conan_auto_mod_update'] = enabled
        config_manager.save_servers()
        status_text = 'aktiviert' if enabled else 'deaktiviert'
        return jsonify({'success': True, 'message': f'Conan Auto-Mod-Update {status_text}', 'enabled': enabled})

    @flask_app.route('/api/server/<server_id>/conan/mods/upload', methods=['POST'])
    def api_conan_mod_upload(server_id):
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401

        server_config = config_manager.servers.get(server_id)
        if not server_config or server_config.get('game') != 'Conan Exiles':
            return jsonify({'success': False, 'message': 'Kein Conan Exiles Server'})

        instance = app_instance.server_instances.get(server_id)
        if not instance:
            return jsonify({'success': False, 'message': 'Server nicht gefunden'})

        upload = request.files.get('mod_file')
        if not upload:
            return jsonify({'success': False, 'message': 'Keine Datei empfangen'})

        safe_name = _sanitize_pak_filename(upload.filename)
        if not safe_name:
            return jsonify({'success': False, 'message': 'Nur .pak Dateien sind erlaubt'})

        mods_dir = instance.get_conan_mods_dir()
        os.makedirs(mods_dir, exist_ok=True)

        target_path = os.path.join(mods_dir, safe_name)
        backup_created = None
        bytes_written = 0
        client_ip = get_client_ip() or '?'

        server_config['conan_mod_upload'] = {
            'last_run': datetime.now().isoformat(),
            'success': False,
            'message': f'Upload läuft: {safe_name}',
            'file': safe_name,
            'size_bytes': 0
        }
        config_manager.save_servers()
        instance.log(f"⬆ Conan Upload gestartet: {safe_name} von {client_ip}")

        try:
            if os.path.exists(target_path):
                backup_dir = os.path.join(mods_dir, '_backup')
                os.makedirs(backup_dir, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
                backup_name = f"{os.path.splitext(safe_name)[0]}_{timestamp}.pak"
                backup_path = os.path.join(backup_dir, backup_name)
                shutil.copy2(target_path, backup_path)
                backup_created = backup_path

            tmp_path = target_path + '.uploading'
            with open(tmp_path, 'wb') as out:
                while True:
                    chunk = upload.stream.read(2 * 1024 * 1024)
                    if not chunk:
                        break
                    bytes_written += len(chunk)
                    out.write(chunk)
            os.replace(tmp_path, target_path)
            added_to_modlist = instance.ensure_conan_modlist_entry(safe_name)

            msg = f'Mod hochgeladen: {safe_name}'
            if backup_created:
                msg += ' (vorherige Version gesichert)'
            if added_to_modlist:
                msg += ' (modlist aktualisiert)'
            instance.log(f"🧩 Conan Upload: {safe_name}")
            if backup_created:
                instance.log(f"💾 Backup erstellt: {backup_created}")
            if added_to_modlist:
                instance.log(f"📝 modlist.txt ergänzt: *{safe_name}")
            server_config['conan_mod_upload'] = {
                'last_run': datetime.now().isoformat(),
                'success': True,
                'message': f'Upload erfolgreich: {safe_name}',
                'file': safe_name,
                'size_bytes': bytes_written,
                'backup': backup_created or ''
            }
            config_manager.save_servers()
            return jsonify({'success': True, 'message': msg, 'file': safe_name, 'backup': backup_created})
        except Exception as e:
            try:
                tmp_path = target_path + '.uploading'
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            server_config['conan_mod_upload'] = {
                'last_run': datetime.now().isoformat(),
                'success': False,
                'message': f'Upload fehlgeschlagen: {e}',
                'file': safe_name,
                'size_bytes': bytes_written
            }
            config_manager.save_servers()
            return jsonify({'success': False, 'message': f'Upload fehlgeschlagen: {e}'})
    
    @flask_app.route('/api/server/<server_id>/logs')
    def api_server_logs(server_id):
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401
        
        instance = app_instance.server_instances.get(server_id)
        if not instance:
            return jsonify({'logs': []})
        
        logs = instance.get_server_logs(max_lines=100)
        return jsonify({'logs': logs})
    
    @flask_app.route('/api/server/<server_id>/update', methods=['POST'])
    def api_update_server(server_id):
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401

        server_config = config_manager.servers.get(server_id)
        if not server_config:
            return jsonify({'success': False, 'message': 'Server nicht gefunden'})
        
        instance = app_instance.server_instances.get(server_id)
        if not instance:
            return jsonify({'success': False, 'message': 'Server nicht gefunden'})

        if not instance.is_installed():
            return jsonify({'success': False, 'message': 'Server ist nicht installiert'})

        game_info = SUPPORTED_GAMES.get(server_config.get('game', ''), {})
        if not game_info.get('app_id'):
            return jsonify({'success': False, 'message': 'Für dieses Spiel ist kein SteamCMD-Update konfiguriert'})
        
        # Update in Thread starten
        def do_update():
            instance.update_server()
        threading.Thread(target=do_update, daemon=True).start()
        
        return jsonify({'success': True, 'message': 'Update gestartet...'})
    
    @flask_app.route('/api/server/<server_id>/<action>', methods=['POST'])
    def api_server_action(server_id, action):
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401
        
        instance = app_instance.server_instances.get(server_id)
        if not instance:
            return jsonify({'success': False, 'message': 'Server not found'})
        
        if action == 'start':
            # Direkt in Thread starten (nicht über after())
            def do_start():
                instance.start()
            threading.Thread(target=do_start, daemon=True).start()
            return jsonify({'success': True, 'message': 'Server wird gestartet...'})
        elif action == 'stop':
            def do_stop():
                instance.stop()
            threading.Thread(target=do_stop, daemon=True).start()
            return jsonify({'success': True, 'message': 'Server wird gestoppt...'})
        elif action == 'restart':
            def do_restart():
                instance.restart()
            threading.Thread(target=do_restart, daemon=True).start()
            return jsonify({'success': True, 'message': 'Server wird neu gestartet...'})
        elif action == 'backup':
            def do_backup():
                instance.create_backup()
            threading.Thread(target=do_backup, daemon=True).start()
            return jsonify({'success': True, 'message': 'Backup wird erstellt...'})
        elif action == 'update':
            def do_update():
                instance.update_server()
            threading.Thread(target=do_update, daemon=True).start()
            return jsonify({'success': True, 'message': 'Update gestartet...'})
        
        return jsonify({'success': False, 'message': 'Unknown action'})
    
    @flask_app.route('/api/server/<server_id>/backups')
    def api_get_backups(server_id):
        """Listet alle Backups eines Servers"""
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401
        
        instance = app_instance.server_instances.get(server_id)
        if not instance:
            return jsonify({'backups': []})
        
        raw_backups = instance.get_backups()
        
        # Formatieren für Web-Interface
        formatted_backups = []
        for b in raw_backups:
            size_mb = b['size'] / (1024 * 1024)
            formatted_backups.append({
                'name': b['filename'],
                'path': b['path'],
                'size': f"{size_mb:.1f} MB",
                'date': b['date'].strftime('%d.%m.%Y %H:%M')
            })
        
        return jsonify({'backups': formatted_backups})
    
    @flask_app.route('/api/server/<server_id>/backups/restore', methods=['POST'])
    def api_restore_backup(server_id):
        """Stellt ein Backup wieder her"""
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401
        
        instance = app_instance.server_instances.get(server_id)
        if not instance:
            return jsonify({'success': False, 'message': 'Server nicht gefunden'})
        
        if instance.is_running():
            return jsonify({'success': False, 'message': 'Server muss gestoppt sein!'})
        
        data = request.get_json()
        backup_path = data.get('backup_path', '')
        
        if not backup_path or not os.path.exists(backup_path):
            return jsonify({'success': False, 'message': 'Backup nicht gefunden'})
        
        if instance.restore_backup(backup_path):
            return jsonify({'success': True, 'message': 'Backup wiederhergestellt!'})
        else:
            return jsonify({'success': False, 'message': 'Wiederherstellung fehlgeschlagen'})
    
    @flask_app.route('/api/server/<server_id>/backups/delete', methods=['POST'])
    def api_delete_backup(server_id):
        """Löscht ein Backup"""
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401
        
        instance = app_instance.server_instances.get(server_id)
        if not instance:
            return jsonify({'success': False, 'message': 'Server nicht gefunden'})
        
        data = request.get_json()
        backup_path = data.get('backup_path', '')
        
        if instance.delete_backup(backup_path):
            return jsonify({'success': True, 'message': 'Backup gelöscht!'})
        else:
            return jsonify({'success': False, 'message': 'Löschen fehlgeschlagen'})
    
    @flask_app.route('/api/server/<server_id>/configs')
    def api_get_configs(server_id):
        """Listet alle Config-Dateien eines Servers"""
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401
        
        server_config = config_manager.servers.get(server_id, {})
        server_dir = os.path.join(PATHS["servers"], server_id)
        game_info = SUPPORTED_GAMES.get(server_config.get("game", ""), {})
        config_path = game_info.get("config_path", "")
        
        config_files = []
        
        # Im Config-Pfad suchen
        if config_path:
            full_config_path = os.path.join(server_dir, config_path.replace("/", os.sep))
            if os.path.exists(full_config_path):
                for root, dirs, files in os.walk(full_config_path):
                    for file in files:
                        if file.endswith(('.ini', '.cfg', '.txt', '.json', '.yaml', '.yml', '.conf', '.properties')):
                            full_path = os.path.join(root, file)
                            rel_path = os.path.relpath(full_path, server_dir)
                            config_files.append({'path': full_path, 'name': rel_path})
        
        # Auch im Hauptverzeichnis suchen
        if os.path.exists(server_dir):
            for file in os.listdir(server_dir):
                full_path = os.path.join(server_dir, file)
                if os.path.isfile(full_path) and file.endswith(('.ini', '.cfg', '.txt', '.json', '.yaml', '.yml', '.conf', '.properties')):
                    if not any(c['path'] == full_path for c in config_files):
                        config_files.append({'path': full_path, 'name': file})
        
        return jsonify({'configs': config_files})
    
    @flask_app.route('/api/server/<server_id>/config/read', methods=['POST'])
    def api_read_config(server_id):
        """Liest eine Config-Datei (mit Pfad-Validierung)"""
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401
        
        data = request.get_json()
        file_path = data.get('file_path', '')
        
        # Server-Verzeichnis ermitteln
        server_config = config_manager.servers.get(server_id, {})
        if not server_config:
            return jsonify({'success': False, 'message': 'Server nicht gefunden'}), 404
        
        server_dir = os.path.join(PATHS["servers"], server_id)
        
        # Pfad-Validierung (verhindert Path Traversal)
        is_valid, error_msg = validate_config_path(server_dir, file_path)
        if not is_valid:
            return jsonify({'success': False, 'message': error_msg}), 403
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': 'Datei nicht gefunden'})
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            return jsonify({'success': True, 'content': content})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})
    
    @flask_app.route('/api/server/<server_id>/config/save', methods=['POST'])
    def api_save_config(server_id):
        """Speichert eine Config-Datei (mit Pfad-Validierung)"""
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401
        
        data = request.get_json()
        file_path = data.get('file_path', '')
        content = data.get('content', '')
        
        # Server-Verzeichnis ermitteln
        server_config = config_manager.servers.get(server_id, {})
        if not server_config:
            return jsonify({'success': False, 'message': 'Server nicht gefunden'}), 404
        
        server_dir = os.path.join(PATHS["servers"], server_id)
        
        # Pfad-Validierung (verhindert Path Traversal)
        is_valid, error_msg = validate_config_path(server_dir, file_path)
        if not is_valid:
            return jsonify({'success': False, 'message': error_msg}), 403
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return jsonify({'success': True, 'message': 'Gespeichert!'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})
    
    @flask_app.route('/api/server/<server_id>/settings', methods=['POST'])
    def api_server_settings(server_id):
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401
        cfg = config_manager.servers.get(server_id)
        if not cfg:
            return jsonify({'success': False, 'message': 'Server nicht gefunden'}), 404
        data = request.get_json(silent=True) or {}

        def _int(v, default):
            try:
                return int(v)
            except (ValueError, TypeError):
                return default

        name = str(data.get('name', cfg.get('name', ''))).strip()
        if not name:
            return jsonify({'success': False, 'message': 'Name darf nicht leer sein.'}), 400
        port = _int(data.get('port'), cfg.get('port', 0))
        query_port = _int(data.get('query_port'), cfg.get('query_port', 0))
        max_players = _int(data.get('max_players'), cfg.get('max_players', 10))
        if not (1 <= port <= 65535) or not (1 <= query_port <= 65535):
            return jsonify({'success': False, 'message': 'Ports müssen zwischen 1 und 65535 liegen.'}), 400
        if max_players < 1:
            return jsonify({'success': False, 'message': 'Max. Spieler muss größer als 0 sein.'}), 400

        cfg['name'] = name
        cfg['port'] = port
        cfg['query_port'] = query_port
        cfg['max_players'] = max_players
        cfg['auto_restart'] = bool(data.get('auto_restart', cfg.get('auto_restart', True)))
        cfg['auto_backup'] = bool(data.get('auto_backup', cfg.get('auto_backup', False)))
        cfg['backup_interval_hours'] = _int(data.get('backup_interval_hours'), cfg.get('backup_interval_hours', 3))
        cfg['max_backups'] = _int(data.get('max_backups'), cfg.get('max_backups', 10))
        # Passwörter nur ändern, wenn ausgefüllt (leer = unverändert)
        sp = data.get('server_password')
        if sp:
            cfg['server_password'] = sp
        ap = data.get('admin_password')
        if ap:
            cfg['admin_password'] = ap
        config_manager.save_servers()
        inst = app_instance.server_instances.get(server_id)
        if inst:
            inst.config = cfg
        return jsonify({'success': True, 'message': 'Einstellungen gespeichert.'})

    @flask_app.route('/api/settings', methods=['GET', 'POST'])
    def api_settings():
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401
        ac = config_manager.app_config
        if request.method == 'GET':
            disc = ac.get('discord', {})
            return jsonify({
                'language': ac.get('language', 'de'),
                'auto_start_servers': ac.get('auto_start_servers', False),
                'web_port': ac.get('web', {}).get('port', 5001),
                'discord': {
                    'enabled': disc.get('enabled', False),
                    'webhook_url': disc.get('webhook_url', ''),
                    'notify_start': disc.get('notify_start', True),
                    'notify_stop': disc.get('notify_stop', True),
                    'notify_crash': disc.get('notify_crash', True),
                    'notify_backup': disc.get('notify_backup', True),
                },
                'chat_stream': ac.get('chat_stream', {}),
                'teamspeak3': dict(ac.get('teamspeak3', {})),
            })
        data = request.get_json(silent=True) or {}
        if 'language' in data:
            ac['language'] = str(data['language'])
        if 'auto_start_servers' in data:
            ac['auto_start_servers'] = bool(data['auto_start_servers'])
        if 'web_port' in data:
            try:
                p = int(data['web_port'])
                if 1 <= p <= 65535:
                    ac.setdefault('web', {})['port'] = p
            except (ValueError, TypeError):
                pass
        if isinstance(data.get('discord'), dict):
            ac.setdefault('discord', {}).update(data['discord'])
        config_manager.save_app_config()
        return jsonify({'success': True, 'message': 'Einstellungen gespeichert.'})

    @flask_app.route('/api/password', methods=['POST'])
    def api_change_password():
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401
        data = request.get_json(silent=True) or {}
        if not config_manager.verify_password(data.get('current', '')):
            return jsonify({'success': False, 'message': 'Aktuelles Passwort ist falsch.'}), 403
        new = data.get('new', '')
        if len(new) < 6:
            return jsonify({'success': False, 'message': 'Neues Passwort muss mindestens 6 Zeichen haben.'}), 400
        config_manager.set_admin_password(new)
        return jsonify({'success': True, 'message': 'Passwort geändert.'})

    @flask_app.route('/api/app/update', methods=['POST'])
    def api_app_update():
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401
        import subprocess as _sp
        from gsm.paths import PROGRAM_DIR
        try:
            r = _sp.run(['git', 'pull', '--ff-only'], cwd=PROGRAM_DIR,
                        capture_output=True, text=True, timeout=120)
            out = ((r.stdout or '') + (r.stderr or '')).strip()
            if r.returncode != 0:
                return jsonify({'success': False, 'message': 'git pull fehlgeschlagen (lokale Änderungen?).', 'output': out})
            low = out.lower()
            up_to_date = ('up to date' in low) or ('up-to-date' in low) or ('aktuell' in low)
            return jsonify({
                'success': True, 'up_to_date': up_to_date, 'output': out,
                'message': 'Bereits auf dem neuesten Stand.' if up_to_date
                           else 'Update geladen. Zum Übernehmen bitte neu starten.'
            })
        except FileNotFoundError:
            return jsonify({'success': False, 'message': 'git ist auf diesem System nicht verfügbar.'})
        except _sp.TimeoutExpired:
            return jsonify({'success': False, 'message': 'git pull hat zu lange gedauert (Timeout).'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})

    @flask_app.route('/api/app/restart', methods=['POST'])
    def api_app_restart():
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401
        import os as _os
        import sys as _sys
        import time as _time

        def _restart():
            _time.sleep(0.6)
            try:
                _os.execv(_sys.executable, [_sys.executable] + _sys.argv)
            except Exception:
                _os._exit(0)

        threading.Thread(target=_restart, daemon=True).start()
        return jsonify({'success': True, 'message': 'Neustart wird ausgeführt …'})

    @flask_app.route('/api/status')
    def api_status():
        if 'token' not in session or session['token'] not in valid_sessions:
            return jsonify({'error': 'Unauthorized'}), 401
        
        return jsonify({
            'cpu': psutil.cpu_percent(),
            'ram': psutil.virtual_memory().percent
        })

    return flask_app


def start_web_server(app_instance, config_manager=None):
    """Baut die Web-App und startet sie im Daemon-Thread (wie zuvor)."""
    if config_manager is None:
        config_manager = app_instance.config_manager
    flask_app = create_web_app(app_instance, config_manager)

    def run_server():
        port = config_manager.app_config.get("web", {}).get("port", 5001)
        flask_app.run(host='0.0.0.0', port=port, threaded=True, use_reloader=False)

    threading.Thread(target=run_server, daemon=True).start()
    return flask_app
