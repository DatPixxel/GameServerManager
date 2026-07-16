"""Vordefinierte, unterstützte Spiele (Katalog).

Reine Datendefinition, aus game_server_manager.py ausgelagert.
"""

SUPPORTED_GAMES = {
    "ARK: Survival Ascended": {
        "app_id": "2430930",
        "exe_path": "ShooterGame/Binaries/Win64/ArkAscendedServer.exe",
        "default_params": "TheIsland_WP?listen?SessionName=MyServer",
        "default_ports": {"game": 7777, "query": 27015},
        "icon": "🦖",
        "config_path": "ShooterGame/Saved/Config/WindowsServer",
        "save_path": "ShooterGame/Saved/SavedArks",
        "maps": [
            {"name": "The Island", "param": "TheIsland_WP"},
            {"name": "Scorched Earth", "param": "ScorchedEarth_WP"},
            {"name": "Aberration", "param": "Aberration_WP"},
            {"name": "Extinction", "param": "Extinction_WP"},
            {"name": "The Center", "param": "TheCenter_WP"},
            {"name": "Ragnarok", "param": "Ragnarok_WP"},
            {"name": "Valguero", "param": "Valguero_WP"},
            {"name": "Genesis Part 1", "param": "Genesis_WP"},
            {"name": "Genesis Part 2", "param": "Gen2_WP"},
            {"name": "Crystal Isles", "param": "CrystalIsles_WP"},
            {"name": "Lost Island", "param": "LostIsland_WP"},
            {"name": "Fjordur", "param": "Fjordur_WP"}
        ]
    },
    "Rust": {
        "app_id": "258550",
        "exe_path": "RustDedicated.exe",
        "default_params": "-batchmode +server.port 28015 +server.level \"Procedural Map\" +server.seed 1234 +server.worldsize 4000 +server.maxplayers 10 +server.hostname \"My Server\"",
        "default_ports": {"game": 28015, "query": 28016},
        "icon": "🔧",
        "config_path": "server/cfg",
        "save_path": "server"
    },
    "Valheim": {
        "app_id": "896660",
        "exe_path": "valheim_server.exe",
        "default_params": "-name \"My Server\" -port 2456 -world \"Dedicated\" -password \"secret\"",
        "default_ports": {"game": 2456, "query": 2457},
        "icon": "⚔️",
        "config_path": "",
        "save_path": "worlds"
    },
    "Enshrouded": {
        "app_id": "2278520",
        "exe_path": "enshrouded_server.exe",
        "default_params": "",
        "default_ports": {"game": 15636, "query": 15637},
        "icon": "🌑",
        "config_path": "enshrouded_server.json",
        "save_path": "savegame"
    },
    "Satisfactory": {
        "app_id": "1690800",
        "exe_path": "FactoryServer.exe",
        "default_params": "",
        "default_ports": {"game": 7777, "query": 15777},
        "icon": "🏭",
        "config_path": "FactoryGame/Saved/Config/WindowsServer",
        "save_path": "FactoryGame/Saved/SaveGames"
    },
    "Palworld": {
        "app_id": "2394010",
        "exe_path": "PalServer.exe",
        "default_params": "-port=8211 -players=32",
        "default_ports": {"game": 8211, "query": 27015},
        "icon": "🐾",
        "config_path": "Pal/Saved/Config/WindowsServer",
        "save_path": "Pal/Saved/SaveGames"
    },
    # ====== NEUE SPIELE ======
    "Minecraft Bedrock": {
        "app_id": "",  # Kein Steam - manueller Download
        "exe_path": "bedrock_server.exe",
        "default_params": "",
        "default_ports": {"game": 19132, "query": 19132},
        "icon": "⛏️",
        "config_path": "",
        "save_path": "worlds",
        "download_url": "https://www.minecraft.net/en-us/download/server/bedrock",
        "manual_install": True
    },
    "Minecraft Java (Forge)": {
        "app_id": "",  # Kein Steam - Java/Forge Download
        "exe_path": "run.bat",  # Wird von Forge Installer erstellt
        "default_params": "nogui",
        "default_ports": {"game": 25565, "query": 25565},
        "icon": "⛏️",
        "config_path": "",
        "save_path": "world",
        "special_install": "minecraft_forge",
        "requires_java": True,
        "mod_folder": "mods",
        "versions": [
            # Neueste zuerst - Format: (MC Version, Forge Version, empfohlen)
            # Stand: Januar 2026
            ("1.21.11", "61.0.6", False),  # Neueste
            ("1.21.10", "60.0.49", False),
            ("1.21.9", "59.0.11", False),
            ("1.21.8", "58.1.6", False),
            ("1.21.7", "57.0.7", False),
            ("1.21.6", "56.0.9", False),
            ("1.21.5", "55.0.6", False),
            ("1.21.4", "54.1.6", False),
            ("1.21.3", "53.0.29", False),
            ("1.21.1", "52.0.43", True),  # Empfohlen - viele Mods verfügbar
            ("1.20.1", "47.3.22", True),  # Sehr beliebt für Mods!
            ("1.19.2", "43.4.4", True),   # Beliebte Modding-Version
            ("1.18.2", "40.2.26", True),  # Klassiker
            ("1.16.5", "36.2.42", True),  # Legacy aber stabil
            ("1.12.2", "14.23.5.2860", True),  # Alte Mod-Klassiker
        ]
    },
    "7 Days to Die": {
        "app_id": "294420",
        "exe_path": "7DaysToDieServer.exe",
        "default_params": "-configfile=serverconfig.xml -logfile=output_log.txt -quit -batchmode -nographics -dedicated",
        "default_ports": {"game": 26900, "query": 26900},
        "icon": "🧟",
        "config_path": "",
        "save_path": "Saves"
    },
    "Project Zomboid": {
        "app_id": "380870",
        "exe_path": "StartServer64.bat",
        "default_params": "",
        "default_ports": {"game": 16261, "query": 16262},
        "icon": "🧠",
        "config_path": "Server",
        "save_path": "Saves",
        "requires_login": True
    },
    "Terraria": {
        "app_id": "105600",
        "exe_path": "TerrariaServer.exe",
        "default_params": "-config serverconfig.txt",
        "default_ports": {"game": 7777, "query": 7777},
        "icon": "🌳",
        "config_path": "",
        "save_path": "Worlds"
    },
    "Counter-Strike 2": {
        "app_id": "730",
        "exe_path": "cs2.exe",
        "default_params": "-dedicated +game_type 0 +game_mode 0 +map de_dust2 +sv_setsteamaccount \"\" -maxplayers 10",
        "default_ports": {"game": 27015, "query": 27015},
        "icon": "🔫",
        "config_path": "game/csgo/cfg",
        "save_path": ""
    },
    "Don't Starve Together": {
        "app_id": "343050",
        "exe_path": "bin64/dontstarve_dedicated_server_nullrenderer_x64.exe",
        "default_params": "-console -cluster MyDediServer -shard Master",
        "default_ports": {"game": 10999, "query": 27016},
        "icon": "🔥",
        "config_path": "DoNotStarveTogether/MyDediServer",
        "save_path": "DoNotStarveTogether/MyDediServer"
    },
    "V Rising": {
        "app_id": "1829350",
        "exe_path": "VRisingServer.exe",
        "default_params": "-persistentDataPath ./save-data -serverName \"My V Rising Server\" -saveName world1",
        "default_ports": {"game": 9876, "query": 9877},
        "icon": "🧛",
        "config_path": "VRisingServer_Data/StreamingAssets/Settings",
        "save_path": "save-data"
    },
    "Conan Exiles": {
        "app_id": "443030",
        "exe_path": "ConanSandboxServer.exe",
        "default_params": "-log -Port=7777 -QueryPort=27015",
        "default_ports": {"game": 7777, "query": 27015, "game2": 7778, "rcon": 25575},
        "icon": "⚔️",
        "config_path": "ConanSandbox/Saved/Config/WindowsServer",
        "save_path": "ConanSandbox/Saved",
        "port_note": "Server reserviert automatisch Port+1 (7778). Alle 3 Ports müssen offen sein!",
        "rcon_enabled": True
    },
    "DayZ": {
        "app_id": "223350",
        "exe_path": "DayZServer_x64.exe",
        "default_params": "-config=serverDZ.cfg -port=2302 -profiles=profile",
        "default_ports": {"game": 2302, "query": 27016},
        "icon": "🏚️",
        "config_path": "profile",
        "save_path": "mpmissions",
        "requires_login": True
    },
    "The Forest": {
        "app_id": "556450",
        "exe_path": "TheForestDedicatedServer.exe",
        "default_params": "-serverip 0.0.0.0 -serversteamport 8766 -servergameport 27015 -servername \"My Forest Server\" -serverplayers 8",
        "default_ports": {"game": 27015, "query": 27016},
        "icon": "🌲",
        "config_path": "",
        "save_path": ""
    },
    "Space Engineers": {
        "app_id": "298740",
        "exe_path": "DedicatedServer64/SpaceEngineersDedicated.exe",
        "default_params": "-console",
        "default_ports": {"game": 27016, "query": 27017},
        "icon": "🚀",
        "config_path": "",
        "save_path": "Saves"
    },
    "Unturned": {
        "app_id": "1110390",
        "exe_path": "Unturned.exe",
        "default_params": "-batchmode -nographics +secureserver/MyServer",
        "default_ports": {"game": 27015, "query": 27016},
        "icon": "🔰",
        "config_path": "Servers/MyServer",
        "save_path": "Servers/MyServer/Level"
    },
    "Left 4 Dead 2": {
        "app_id": "222860",
        "exe_path": "srcds.exe",
        "default_params": "-game left4dead2 +map c1m1_hotel +maxplayers 8",
        "default_ports": {"game": 27015, "query": 27015},
        "icon": "🧟‍♂️",
        "config_path": "left4dead2/cfg",
        "save_path": ""
    },
    "Team Fortress 2": {
        "app_id": "232250",
        "exe_path": "srcds.exe",
        "default_params": "-game tf +map ctf_2fort +maxplayers 24",
        "default_ports": {"game": 27015, "query": 27015},
        "icon": "🎩",
        "config_path": "tf/cfg",
        "save_path": ""
    },
    "Factorio": {
        "app_id": "427520",
        "exe_path": "bin/x64/factorio.exe",
        "default_params": "--start-server ./saves/my-save.zip --server-settings ./server-settings.json",
        "default_ports": {"game": 34197, "query": 34197},
        "icon": "⚙️",
        "config_path": "",
        "save_path": "saves"
    },
    "Garry's Mod": {
        "app_id": "4020",
        "exe_path": "srcds.exe",
        "default_params": "-game garrysmod +maxplayers 16 +map gm_flatgrass",
        "default_ports": {"game": 27015, "query": 27015},
        "icon": "🔧",
        "config_path": "garrysmod/cfg",
        "save_path": ""
    },
    "Icarus": {
        "app_id": "2089300",
        "exe_path": "Icarus/Binaries/Win64/IcarusServer-Win64-Shipping.exe",
        "default_params": "-Log -UserDir=\"IcarusServer\"",
        "default_ports": {"game": 17777, "query": 27015},
        "icon": "🪐",
        "config_path": "IcarusServer/Saved/Config/WindowsServer",
        "save_path": "IcarusServer/Saved/PlayerData"
        # Kein requires_login! Icarus kann mit "login anonymous" heruntergeladen werden
    },
    "StarRupture": {
        "app_id": "3809400",
        "exe_path": "StarRupture/Binaries/Win64/StarRuptureServerEOS-Win64-Shipping.exe",
        "default_params": "-Log -Port=7777 -QueryPort=27015",
        "default_ports": {"game": 7777, "query": 27015},
        "icon": "🌌",
        "config_path": "StarRupture/Saved/Config/WindowsServer",
        "save_path": "StarRupture/Saved/SaveGames",
        "ds_settings": True  # Braucht DSSettings.txt für Auto-Start
        # Experimenteller Dedicated Server (Early Access seit Januar 2026)
    },
    "RuneScape: Dragonwilds": {
        "app_id": "4019830",  # Eigene Dedicated-Server-App (nicht die Spiel-App)
        "exe_path": "RSDragonwilds/Binaries/Win64/RSDragonwildsServer-Win64-Shipping.exe",  # NICHT der Stub RSDragonwilds.exe im Wurzelordner!
        "default_params": "-log",  # Port wird aus der Server-Config injiziert (siehe build_start_command)
        "default_ports": {"game": 7777, "query": 7778, "game2": 7778},
        "icon": "🐉",
        "config_path": "RSDragonwilds/Saved/Config/WindowsServer",
        "save_path": "RSDragonwilds/Saved/Savegames",
        "port_note": "UDP! Server reserviert automatisch Port+1 (7778). Beide UDP-Ports müssen offen/weitergeleitet sein. Vor dem Start OwnerId in DedicatedServer.ini eintragen (Player-ID aus dem Spiel-Menü Einstellungen).",
        "max_players": 6  # Offiziell max. 6 Spieler; RAM: 2 GB + 1 GB pro Spieler
    }
}
