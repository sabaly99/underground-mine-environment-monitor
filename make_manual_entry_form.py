"""Build the offline-first manual-entry form (one HTML file). Edit CONFIG, then run:  python make_manual_entry_form.py
Open the HTML on a tablet/laptop underground; entries are kept on the device until you export a CSV."""
# ============================== CONFIG ==============================
CONFIG = {
    "INPUT_DIR": "data/demo",
    "LOCATIONS_CSV": "locations.csv",
    "INSTRUMENTS_CSV": "instruments.csv",
    "OUTPUT_HTML": "outputs/manual_entry_form.html",
    "TITLE": "Manual environmental measurement entry",
}
# ====================================================================
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from mineenv.loaders import load_locations, load_instruments, DataError   # noqa: E402
from mineenv.manual_entry import build_form                                # noqa: E402

if __name__ == "__main__":
    inp = ROOT / CONFIG["INPUT_DIR"]
    try:
        loc = load_locations(inp / CONFIG["LOCATIONS_CSV"])
        ins = load_instruments(inp / CONFIG["INSTRUMENTS_CSV"], loc)
    except (DataError, FileNotFoundError) as e:
        raise SystemExit(f"Input problem: {e}")
    out = ROOT / CONFIG["OUTPUT_HTML"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_form(ins, loc, CONFIG["TITLE"]), encoding="utf-8")
    print(f"Wrote {out}. Exported CSVs go in <INPUT_DIR>/manual_entries/ and are picked up by run_pipeline.py.")
