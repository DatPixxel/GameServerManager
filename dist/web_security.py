"""
Web Security Module für Game Server Manager Pro
Implementiert Rate-Limiting, CSRF-Protection und Session-Management
"""

import time
import secrets
import hashlib
import json
import os
from functools import wraps
from flask import request, session, jsonify
from datetime import datetime, timedelta

# ==================== RATE LIMITING ====================

class RateLimiter:
    """Einfacher Rate-Limiter für Login-Versuche"""
    
    def __init__(self):
        self.attempts = {}  # {ip: [(timestamp, success), ...]}
        self.lockouts = {}  # {ip: lockout_until}
    
    def is_locked_out(self, ip):
        """Prüft ob IP gesperrt ist"""
        if ip in self.lockouts:
            if time.time() < self.lockouts[ip]:
                return True
            else:
                # Sperre abgelaufen
                del self.lockouts[ip]
        return False
    
    def record_attempt(self, ip, success=False):
        """Zeichnet Login-Versuch auf"""
        now = time.time()
        
        # Alte Einträge löschen (älter als 15 Min)
        if ip in self.attempts:
            self.attempts[ip] = [(t, s) for t, s in self.attempts[ip] 
                                if now - t < 900]
        else:
            self.attempts[ip] = []
        
        # Neuen Versuch hinzufügen
        self.attempts[ip].append((now, success))
        
        # Fehlversuche zählen (letzte 5 Min)
        recent_failures = sum(1 for t, s in self.attempts[ip] 
                             if not s and now - t < 300)
        
        # Nach 5 Fehlversuchen: 5 Min Sperre
        if recent_failures >= 5:
            self.lockouts[ip] = now + 300  # 5 Minuten
            print(f"🔒 IP {ip} gesperrt für 5 Minuten (zu viele Fehlversuche)")
            return True
        
        return False
    
    def get_remaining_lockout(self, ip):
        """Gibt verbleibende Sperrzeit zurück"""
        if ip in self.lockouts:
            remaining = int(self.lockouts[ip] - time.time())
            return max(0, remaining)
        return 0

# ==================== CSRF PROTECTION ====================

def generate_csrf_token():
    """Generiert ein CSRF-Token"""
    return secrets.token_hex(32)

def validate_csrf_token(token):
    """Validiert CSRF-Token"""
    if 'csrf_token' not in session:
        return False
    return secrets.compare_digest(session['csrf_token'], token)

def csrf_protect(f):
    """Decorator für CSRF-geschützte Routen"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'DELETE']:
            token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
            if not token or not validate_csrf_token(token):
                return jsonify({'error': 'CSRF-Token ungültig'}), 403
        return f(*args, **kwargs)
    return decorated_function

# ==================== SESSION STORAGE ====================

class FileSessionStore:
    """Speichert Sessions persistent in Datei"""
    
    def __init__(self, config_dir):
        self.session_file = os.path.join(config_dir, 'web_sessions.json')
        self.sessions = self.load()
    
    def load(self):
        """Lädt Sessions aus Datei"""
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, 'r') as f:
                    data = json.load(f)
                    # Alte Sessions löschen (älter als 12h)
                    now = time.time()
                    return {k: v for k, v in data.items() 
                           if now - v.get('created', 0) < 43200}
            except:
                return {}
        return {}
    
    def save(self):
        """Speichert Sessions in Datei"""
        try:
            with open(self.session_file, 'w') as f:
                json.dump(self.sessions, f, indent=2)
        except Exception as e:
            print(f"⚠️  Session-Speicherung fehlgeschlagen: {e}")
    
    def add(self, token, ip):
        """Fügt Session hinzu"""
        self.sessions[token] = {
            'created': time.time(),
            'ip': ip,
            'last_activity': time.time()
        }
        self.save()
    
    def remove(self, token):
        """Entfernt Session"""
        if token in self.sessions:
            del self.sessions[token]
            self.save()
    
    def validate(self, token, ip=None):
        """Validiert Session"""
        if token not in self.sessions:
            return False
        
        session_data = self.sessions[token]
        
        # Zeitprüfung (12h)
        if time.time() - session_data.get('created', 0) > 43200:
            self.remove(token)
            return False
        
        # IP-Prüfung (optional)
        if ip and session_data.get('ip') != ip:
            print(f"⚠️  Session-IP stimmt nicht überein: {ip} != {session_data.get('ip')}")
            # Optional: return False (strenger)
        
        # Aktivität aktualisieren
        session_data['last_activity'] = time.time()
        self.save()
        
        return True
    
    def cleanup(self):
        """Löscht alte Sessions"""
        now = time.time()
        old_count = len(self.sessions)
        self.sessions = {k: v for k, v in self.sessions.items() 
                        if now - v.get('created', 0) < 43200}
        if len(self.sessions) < old_count:
            self.save()
            print(f"🧹 {old_count - len(self.sessions)} alte Sessions gelöscht")

# ==================== SECURITY HEADERS ====================

def add_security_headers(response):
    """Fügt Security-Headers zu Response hinzu"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

# ==================== IP UTILITIES ====================

def get_client_ip():
    """Holt echte Client-IP (auch hinter Proxy)"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    return request.remote_addr or '0.0.0.0'
