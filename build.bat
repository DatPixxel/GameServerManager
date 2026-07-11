@echo off
echo ========================================
echo   Game Server Manager Pro - Build
echo ========================================
echo.

REM Python pruefen
python --version >nul 2>&1
if errorlevel 1 (
    echo FEHLER: Python nicht gefunden!
    pause
    exit /b 1
)

echo [1/4] Python gefunden
python --version

REM PyInstaller pruefen
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [2/4] PyInstaller installieren...
    pip install pyinstaller
)

echo [2/4] PyInstaller OK

REM Alte Builds loeschen
echo [3/4] Loesche alte Builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del /q *.spec

REM Build
echo [4/4] Erstelle EXE...
pyinstaller ^
    --name=GameServerManager ^
    --onefile ^
    --windowed ^
    --add-data "core;core" ^
    --add-data "web;web" ^
    --add-data "utils;utils" ^
    --add-data "templates;templates" ^
    --add-data "static;static" ^
    --hidden-import=core.constants ^
    --hidden-import=core.config_manager ^
    --hidden-import=core.server_instance ^
    --collect-all customtkinter ^
    --collect-all flask ^
    --noconfirm ^
    game_server_manager.py

if errorlevel 1 (
    echo.
    echo FEHLER beim Build!
    pause
    exit /b 1
)

echo.
echo ========================================
echo   BUILD ERFOLGREICH!
echo   Datei: dist\GameServerManager.exe
echo ========================================
echo.

REM Kopiere web_security.py falls vorhanden
if exist web_security.py (
    copy web_security.py dist\ >nul
    echo web_security.py nach dist\ kopiert
)

pause
