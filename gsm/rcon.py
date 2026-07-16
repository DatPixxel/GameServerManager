"""RCON-Client (Source-Protokoll, Single-Shot).

Aus game_server_manager.py ausgelagert.
"""

import socket
import struct
import threading
import time


class RCONClient:
    """RCON Client für ARK Server - Single-Shot Modus"""
    
    SERVERDATA_AUTH = 3
    SERVERDATA_EXECCOMMAND = 2
    
    def __init__(self, host="127.0.0.1", port=27020, password=""):
        self.host = host
        self.port = port
        self.password = password
        self._lock = threading.Lock()
        self._last_connect_time = 0
        self._min_connect_interval = 2.0
    
    def _create_packet(self, req_id, pkt_type, body):
        body_bytes = body.encode('utf-8') + b'\x00\x00'
        size = 4 + 4 + len(body_bytes)
        return struct.pack('<iii', size, req_id, pkt_type) + body_bytes
    
    def _read_packet(self, sock):
        try:
            size_data = sock.recv(4)
            if len(size_data) < 4:
                return None, None, ""
            size = struct.unpack('<i', size_data)[0]
            data = b''
            while len(data) < size:
                chunk = sock.recv(size - len(data))
                if not chunk:
                    break
                data += chunk
            if len(data) < 8:
                return None, None, ""
            req_id = struct.unpack('<i', data[0:4])[0]
            pkt_type = struct.unpack('<i', data[4:8])[0]
            body = data[8:-2].decode('utf-8', errors='ignore') if len(data) > 10 else ""
            return req_id, pkt_type, body
        except:
            return None, None, ""
    
    def _close_socket(self, sock):
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except:
                pass
            try:
                sock.close()
            except:
                pass
    
    def send_command(self, command):
        """Sendet einen Befehl (Single-Shot: neue Verbindung pro Befehl)"""
        with self._lock:
            now = time.time()
            time_since_last = now - self._last_connect_time
            if time_since_last < self._min_connect_interval:
                time.sleep(self._min_connect_interval - time_since_last)
            
            sock = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect((self.host, self.port))
                
                auth_packet = self._create_packet(1, self.SERVERDATA_AUTH, self.password)
                sock.send(auth_packet)
                
                req_id, pkt_type, body = self._read_packet(sock)
                if body == "":
                    req_id, pkt_type, body = self._read_packet(sock)
                
                if req_id == -1:
                    self._close_socket(sock)
                    return None, "Falsches RCON Passwort"
                
                cmd_packet = self._create_packet(2, self.SERVERDATA_EXECCOMMAND, command)
                sock.send(cmd_packet)
                
                req_id, pkt_type, body = self._read_packet(sock)
                
                self._last_connect_time = time.time()
                self._close_socket(sock)
                
                if req_id is None:
                    return None, "Keine Antwort vom Server"
                
                return body, None
                
            except socket.timeout:
                self._close_socket(sock)
                return None, "Timeout - RCON antwortet nicht"
            except ConnectionRefusedError:
                self._close_socket(sock)
                return None, "Verbindung abgelehnt - RCON Port nicht offen?"
            except Exception as e:
                self._close_socket(sock)
                return None, f"RCON Fehler: {e}"
    
    def list_players(self):
        """Gibt Liste der Online-Spieler zurück"""
        response, error = self.send_command("ListPlayers")
        if error:
            return [], error
        
        players = []
        if response:
            for line in response.strip().split('\n'):
                line = line.strip()
                if line and '. ' in line:
                    try:
                        parts = line.split('. ', 1)
                        if len(parts) > 1:
                            player_info = parts[1].split(', ')
                            name = player_info[0].strip()
                            steam_id = player_info[1].strip() if len(player_info) > 1 else ""
                            players.append({"name": name, "steam_id": steam_id})
                    except:
                        continue
        
        return players, None
    
    def broadcast(self, message):
        return self.send_command(f'ServerChat {message}')
    
    def save_world(self):
        return self.send_command('SaveWorld')
    
    def destroy_wild_dinos(self):
        return self.send_command('DestroyWildDinos')
    
    def kick_player(self, steam_id):
        return self.send_command(f'KickPlayer {steam_id}')
