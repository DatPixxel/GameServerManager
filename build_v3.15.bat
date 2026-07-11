@echo off
title Game Server Manager Pro v3.15 - BUILD
color 0A

echo ============================================================
echo   Game Server Manager Pro v3.15 - EXE BUILD
echo ============================================================
echo

:: ─── Prüfe ob game_server_manager.py existiert ───────────────
if not exist "game_server_manager.py" (
    echo [FEHLER] game_server_manager.py nicht gefunden!
    echo Führe dieses Skript im GameServerManager-Verzeichnis aus!
    echo
    pause
    exit /b 1
)

:: ─── Prüfe ob platform_utils.py existiert ────────────────────
if not exist "platform_utils.py" (
    echo [FEHLER] platform_utils.py nicht gefunden!
    echo Kopiere platform_utils.py in diesen Ordner!
    echo
    pause
    exit /b 1
)

echo [OK] Alle Dateien gefunden.
echo

:: ─── Lösche altes Build ──────────────────────────────────────
echo [*] Altes Build wird gelöscht...
if exist "dist" (
    rmdir /s /q "dist"
)
if exist "build" (
    rmdir /s /q "build"
)
if exist "GameServerManager.spec" (
    del "GameServerManager.spec"
)
echo [OK] Altes Build gelöscht.
echo

:: ─── PyInstaller Build starten ────────────────────────────────
echo [*] Build wird gestartet... (dauert 30-60 Sekunden)
echo

pyinstaller ^
    --name=GameServerManager ^
    --onefile ^
    --windowed ^
    --add-data "platform_utils.py;." ^
    --hidden-import=platform_utils ^
    --collect-all customtkinter ^
    --collect-all flask ^
    --noconfirm ^
    game_server_manager.py > build_log.txt 2>&1

echo [*] Build-Ausgabe wurde in build_log.txt gespeichert
echo

:: ─── Prüfe ob Build erfolgreich ──────────────────────────────
if exist "dist\GameServerManager.exe" (
    echo
    echo ============================================================
    echo   BUILD ERFOLGREICH!
    echo ============================================================
    echo
    echo   Deine EXE liegt hier:
    echo   dist\GameServerManager.exe
    echo
    echo   Teste jetzt die EXE!
    echo ============================================================
    echo
) else (
    echo
    echo ============================================================
    echo   BUILD FEHLGESCHLAGEN!
    echo ============================================================
    echo
    echo   Überprüfe die Fehlermeldungen oben!
    echo   Häufige Fehler:
    echo     - PyInstaller nicht installiert:
    echo       pip install pyinstaller
    echo     - Customtkinter nicht installiert:
    echo       pip install customtkinter
    echo     - Flask nicht installiert:
    echo       pip install flask
    echo ============================================================
    echo
)

pause
