@echo off
title Game Server Manager - Moderne Oberflaeche
cd /d "%~dp0"
python app_web.py
if errorlevel 1 (
    echo.
    echo Es ist ein Fehler aufgetreten. Fenster bleibt offen.
    pause
)
