#!/usr/bin/env python3
"""
Game Server Manager Pro - Entry Point
Startet das Programm mit refactored Modulen
"""

import sys
import os

# Füge aktuelles Verzeichnis zu sys.path hinzu
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importiere und starte Haupt-App
from game_server_manager import main

if __name__ == "__main__":
    main()
