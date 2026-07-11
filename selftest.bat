@echo off
echo ========================================
echo   Game Server Manager - Selbsttest
echo ========================================
echo.

python selftest.py
if errorlevel 1 (
    echo.
    echo Mindestens ein Test ist fehlgeschlagen.
    pause
    exit /b 1
)

echo.
echo Alle Tests erfolgreich.
pause
