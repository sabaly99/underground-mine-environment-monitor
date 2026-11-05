"""Create SYNTHETIC demonstration inputs. Edit CONFIG, then run:  python make_demo_data.py"""
# ============================== CONFIG ==============================
CONFIG = {
    "OUTPUT_DIR": "data/demo",
    "DAYS": 10,        # days of history to generate
    "SEED": 7,
}
# ====================================================================
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from mineenv.demo import write_demo  # noqa: E402

if __name__ == "__main__":
    out = write_demo(ROOT / CONFIG["OUTPUT_DIR"], days=CONFIG["DAYS"], seed=CONFIG["SEED"])
    print(f"Wrote SYNTHETIC data to {out}.")
    print("All values and the DEMO review criteria are invented placeholders, not limits. Replace the CSV files with your own,")
    print("and supply your own approved review_criteria.csv (source_reference, approved_by, approval_date are required).")
