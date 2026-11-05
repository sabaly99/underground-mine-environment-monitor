"""Offline Dash dashboard. Edit CONFIG, then run:  python dashboard_dash.py
Reporting and visualisation only: not an alarm, gas monitor or ventilation control."""
# ============================== CONFIG ==============================
CONFIG = {
    "DB_PATH": "outputs/environment.sqlite",   # produced by run_pipeline.py
    "HOST": "127.0.0.1",                       # 127.0.0.1 = this computer only (recommended for mine data)
    "PORT": 8050,
    "OPEN_BROWSER": True,
    "DEFAULT_THEME": "midnight",   # midnight, daylight, ocean, forest, sand, contrast (the Theme menu in the app changes it live)
    "ENV": {},                                 # keep equal to run_pipeline.py if you changed gap_factor etc.
}
# ====================================================================
import sys
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from mineenv.config import EnvConfig          # noqa: E402
from mineenv.dash_app import create_app       # noqa: E402

if __name__ == "__main__":
    db = ROOT / CONFIG["DB_PATH"]
    if not db.exists():
        raise SystemExit(f"{db} not found. Run make_demo_data.py then run_pipeline.py first.")
    app = create_app(db, EnvConfig.from_dict(CONFIG["ENV"]), CONFIG["DEFAULT_THEME"])
    url = f"http://{CONFIG['HOST']}:{CONFIG['PORT']}"
    if CONFIG["OPEN_BROWSER"]:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    print(f"Dashboard at {url}  (Ctrl+C to stop). No internet needed.")
    app.run(host=CONFIG["HOST"], port=CONFIG["PORT"], debug=False)
