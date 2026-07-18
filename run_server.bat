@echo off
title Game Server Manager - Server-Modus (Web)
cd /d "%~dp0"
python run.py --serve
pause
