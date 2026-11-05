@echo off
REM Windows launcher for the offline dashboard. Double-click after the one-time setup in docs/INSTALL_DEPLOY.md.
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
python dashboard_dash.py
pause
