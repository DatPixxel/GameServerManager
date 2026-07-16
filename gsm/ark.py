"""ARK-spezifisch: Map-Bilder und Savegame-Parser.

Aus game_server_manager.py ausgelagert.
"""

import os
import shutil
import struct
import time
from datetime import datetime, timedelta

import requests

from gsm.constants import SSL_VERIFY

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    Image = None
    PIL_AVAILABLE = False


ARK_MAP_DATA = {
    "TheIsland_WP": {
        "name": "The Island",
        "size": (100, 100),
        "urls": [
            "https://ark.wiki.gg/images/a/a5/The_Island_Topographic_Map.jpg",
        ]
    },
    "ScorchedEarth_WP": {
        "name": "Scorched Earth",
        "size": (100, 100),
        "urls": [
            "https://ark.wiki.gg/images/5/5c/Scorched_Earth_Topographic_Map.jpg",
        ]
    },
    "Aberration_WP": {
        "name": "Aberration",
        "size": (100, 100),
        "urls": [
            "https://ark.wiki.gg/images/a/ab/Aberration_Topographic_Map.jpg",
        ]
    },
    "Extinction_WP": {
        "name": "Extinction",
        "size": (100, 100),
        "urls": [
            "https://ark.wiki.gg/images/8/86/Extinction_Topographic_Map.jpg",
        ]
    },
    "TheCenter_WP": {
        "name": "The Center",
        "size": (100, 100),
        "urls": [
            "https://ark.wiki.gg/images/0/0e/The_Center_Topographic_Map.jpg",
        ]
    },
    "Ragnarok_WP": {
        "name": "Ragnarok",
        "size": (100, 100),
        "urls": [
            "https://ark.wiki.gg/images/7/7b/Ragnarok_Topographic_Map.jpg",
        ]
    },
    "Valguero_WP": {
        "name": "Valguero",
        "size": (100, 100),
        "urls": [
            "https://ark.wiki.gg/images/6/6c/Valguero_Topographic_Map.jpg",
        ]
    },
    "CrystalIsles_WP": {
        "name": "Crystal Isles",
        "size": (100, 100),
        "urls": [
            "https://ark.wiki.gg/images/5/5d/Crystal_Isles_Topographic_Map.jpg",
        ]
    },
}



class ArkMapManager:
    """Verwaltet Map-Bilder für ARK"""
    
    def __init__(self, base_dir):
        self.cache_dir = os.path.join(base_dir, "map_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def get_map_path(self, map_param):
        return os.path.join(self.cache_dir, f"{map_param}.jpg")
    
    def is_cached(self, map_param):
        path = self.get_map_path(map_param)
        return os.path.exists(path) and os.path.getsize(path) > 10000
    
    def download_map(self, map_param, progress_callback=None):
        """Lädt Map-Bild herunter"""
        if map_param not in ARK_MAP_DATA:
            return False, f"Unbekannte Map: {map_param}"
        
        map_info = ARK_MAP_DATA[map_param]
        urls = map_info.get("urls", [])
        
        if not urls:
            return False, "Keine Download-URLs"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'image/*,*/*',
        }
        
        last_error = "Unbekannter Fehler"
        
        for i, url in enumerate(urls):
            try:
                if progress_callback:
                    progress_callback(f"⬇️ Download {map_info['name']}... ({i+1}/{len(urls)})")
                
                response = requests.get(url, headers=headers, stream=True, timeout=15, 
                                        allow_redirects=True, verify=SSL_VERIFY)
                
                if response.status_code != 200:
                    last_error = f"HTTP {response.status_code}"
                    continue
                
                content_type = response.headers.get('Content-Type', '')
                if 'image' not in content_type.lower() and 'octet-stream' not in content_type.lower():
                    last_error = f"Kein Bild: {content_type}"
                    continue
                
                map_path = self.get_map_path(map_param)
                with open(map_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                if os.path.getsize(map_path) < 10000:
                    os.remove(map_path)
                    last_error = "Datei zu klein"
                    continue
                
                if progress_callback:
                    progress_callback(f"✓ {map_info['name']} geladen")
                
                return True, "OK"
                
            except Exception as e:
                last_error = str(e)
                continue
        
        return False, last_error
    
    def ensure_map(self, map_param, progress_callback=None):
        """Stellt sicher dass Map verfügbar ist"""
        if self.is_cached(map_param):
            return True, "Aus Cache"
        return self.download_map(map_param, progress_callback)
    
    def get_map_image(self, map_param, size=None):
        """Lädt Map-Bild als PIL Image"""
        if not PIL_AVAILABLE:
            return None
        
        path = self.get_map_path(map_param)
        if not os.path.exists(path):
            return None
        
        try:
            img = Image.open(path)
            if size:
                img = img.resize(size, Image.Resampling.LANCZOS)
            return img
        except:
            return None
    
    def import_map_manually(self, map_param, source_path):
        """Importiert ein Map-Bild manuell"""
        try:
            dest_path = self.get_map_path(map_param)
            shutil.copy2(source_path, dest_path)
            return True, "OK"
        except Exception as e:
            return False, str(e)


class ArkSaveParser:
    """Parser für ARK Save-Dateien"""
    
    def __init__(self, save_dir):
        self.save_dir = save_dir
        self._cache = {}
        self._cache_time = 0
    
    def find_save_file(self, map_param):
        """Findet die .ark Save-Datei"""
        if not os.path.exists(self.save_dir):
            return None
        
        map_name = map_param.replace("_WP", "")
        
        # Unterordner prüfen (ARK ASA Standard)
        map_subdir = os.path.join(self.save_dir, map_param)
        if os.path.exists(map_subdir):
            for f in os.listdir(map_subdir):
                if f.endswith(".ark") and not f.endswith("_AntiCorruptionBackup.ark"):
                    return os.path.join(map_subdir, f)
        
        # Alle Unterordner durchsuchen
        for subdir in os.listdir(self.save_dir):
            subdir_path = os.path.join(self.save_dir, subdir)
            if os.path.isdir(subdir_path):
                if map_name.lower() in subdir.lower():
                    for f in os.listdir(subdir_path):
                        if f.endswith(".ark") and not f.endswith("_AntiCorruptionBackup.ark"):
                            return os.path.join(subdir_path, f)
        
        return None
    
    def _find_string_property(self, data, property_name):
        """Findet einen String-Property Wert"""
        marker = property_name.encode() if isinstance(property_name, str) else property_name
        idx = data.find(marker)
        
        if idx == -1:
            return None
        
        search_start = idx + len(marker)
        search_end = min(search_start + 100, len(data))
        
        str_prop_idx = data.find(b"StrProperty", search_start, search_end)
        if str_prop_idx != -1:
            for extra_offset in [9, 13, 17, 21]:
                offset = str_prop_idx + 11 + extra_offset
                if offset + 4 > len(data):
                    continue
                
                str_len = struct.unpack('<i', data[offset:offset+4])[0]
                
                if 0 < str_len < 200:
                    try:
                        result = data[offset+4:offset+4+str_len-1].decode('utf-8', errors='ignore')
                        if result and result.isprintable() and len(result) > 0:
                            return result
                    except:
                        pass
        
        return None
    
    def parse_profile(self, profile_path):
        """Parst eine .arkprofile Datei"""
        try:
            with open(profile_path, 'rb') as f:
                data = f.read()
            
            player = {
                "file": os.path.basename(profile_path),
                "name": "Unknown",
                "level": 1,
                "tribe_id": 0,
                "tribe_name": "",
                "last_seen": datetime.fromtimestamp(os.path.getmtime(profile_path)),
            }
            
            # Name suchen
            for prop_name in ["PlayerName", "MyPlayerName", "PlayerCharacterName"]:
                name = self._find_string_property(data, prop_name)
                if name and len(name) > 1 and name != "Unknown":
                    player["name"] = name
                    break
            
            # Level suchen
            for level_prop in [b"CharacterLevel", b"MyCharacterLevel"]:
                level_idx = data.find(level_prop)
                if level_idx != -1:
                    for offset in range(15, 50):
                        if level_idx + offset + 4 > len(data):
                            break
                        try:
                            val = struct.unpack('<i', data[level_idx + offset:level_idx + offset + 4])[0]
                            if 1 <= val <= 200:
                                player["level"] = val
                                break
                        except:
                            pass
                    if player["level"] > 1:
                        break
            
            # Tribe ID suchen
            tribe_idx = data.find(b"TribeId")
            if tribe_idx != -1:
                for i in range(tribe_idx + 15, min(tribe_idx + 50, len(data) - 4)):
                    try:
                        val = struct.unpack('<I', data[i:i+4])[0]
                        if val > 1000:
                            player["tribe_id"] = val
                            break
                    except:
                        pass
            
            return player
            
        except Exception as e:
            return None
    
    def get_all_data(self, map_param, force_refresh=False, progress_callback=None):
        """Holt alle Spielerdaten"""
        current_time = time.time()
        
        if not force_refresh and self._cache and (current_time - self._cache_time) < 60:
            return self._cache
        
        result = {"players": [], "tamed_dinos": [], "tribes": [], "save_info": None}
        
        if not os.path.exists(self.save_dir):
            return result
        
        if progress_callback:
            progress_callback("📂 Lade Spielerdaten...")
        
        # Profil-Ordner bestimmen (ARK ASA: Unterordner)
        profile_dir = self.save_dir
        map_subdir = os.path.join(self.save_dir, map_param)
        if os.path.exists(map_subdir):
            profile_dir = map_subdir
        
        # Profile laden
        try:
            for f in os.listdir(profile_dir):
                if f.endswith(".arkprofile"):
                    player = self.parse_profile(os.path.join(profile_dir, f))
                    if player and player.get("name") != "Unknown":
                        result["players"].append(player)
        except:
            pass
        
        # Save-Info
        save_file = self.find_save_file(map_param)
        if save_file:
            try:
                stat = os.stat(save_file)
                result["save_info"] = {
                    "file": os.path.basename(save_file),
                    "size_mb": round(stat.st_size / 1024 / 1024, 1),
                    "last_save": datetime.fromtimestamp(stat.st_mtime)
                }
            except:
                pass
        
        self._cache = result
        self._cache_time = current_time
        
        if progress_callback:
            progress_callback(f"✓ {len(result['players'])} Spieler geladen")
        
        return result



