#!/usr/bin/env bash
# Linux/macOS launcher for the offline dashboard.
cd "$(dirname "$0")"
[ -f .venv/bin/activate ] && source .venv/bin/activate
python dashboard_dash.py
