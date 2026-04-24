@echo off
echo ============================================================
echo   AI SCREEN PRIVACY GUARD - Backend Server
echo   Version 4.0.0
echo ============================================================
echo.

set PYTHONPATH=C:\lib\site-packages
cd /d "%~dp0"

echo Starting FastAPI server on port 5000...
echo Press Ctrl+C to stop.
echo.

python main.py
pause
