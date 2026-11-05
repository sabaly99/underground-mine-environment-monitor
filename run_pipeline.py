"""Load registers + measurements, analyse, store history, write outputs. Edit CONFIG, then run:  python run_pipeline.py
Reporting and visualisation only: not an alarm, gas monitor or ventilation control. It sets no limits."""
# ============================== CONFIG ==============================
CONFIG = {
    # --- input files (see docs/DATA_FORMAT.md) ---
    "INPUT_DIR": "data/demo",
    "LOCATIONS_CSV": "locations.csv",
    "INSTRUMENTS_CSV": "instruments.csv",
    "CRITERIA_CSV": "review_criteria.csv",    # approved review criteria from qualified personnel (never invented here)
    "MEASUREMENT_GLOBS": ["measurements*.csv", "manual_entries/*.csv"],   # relative to INPUT_DIR
    "COLUMN_MAP": {},                          # map your column names, e.g. {"timestamp": "DateTime", "value": "Reading"}
    # --- as-of time used for stale / gap checks ---
    "AS_OF": "2026-11-04 06:00",               # "now", "auto" (latest reading), or a timestamp. Demo data end at the value shown.
    # --- outputs ---
    "OUTPUT_DIR": "outputs",
    "DB_PATH": "outputs/environment.sqlite",   # raw measurements accumulate here across runs (duplicates ignored)
    "WRITE_CSV": True,
    "WRITE_REPORT": True,                      # environment_report.html (print to PDF from a browser)
    "WRITE_OFFLINE_DASHBOARD": True,           # dashboard_offline.html (single file, double-click to open)
    "WRITE_MANUAL_FORM": True,                 # manual_entry_form.html
    "PROJECT_NAME": "DEMONSTRATION - synthetic data",
    "PREPARED_BY": "",
    # --- method settings: override any EnvConfig default (see src/mineenv/config.py). None of these are safety limits. ---
    "ENV": {
        "site_timezone": "UTC",
    },
}
# ====================================================================
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from mineenv import database as db                                          # noqa: E402
from mineenv.analysis import analyse, parse_raw, resolve_as_of                              # noqa: E402
from mineenv.config import EnvConfig                                         # noqa: E402
from mineenv.loaders import (load_locations, load_instruments, load_criteria, load_measurements, DataError)  # noqa: E402
from mineenv.manual_entry import build_form                                  # noqa: E402
from mineenv.offline_html import build_offline_html                          # noqa: E402
from mineenv.report import build_report                                      # noqa: E402


def main():
    c = CONFIG
    cfg = EnvConfig.from_dict(c["ENV"])
    inp, out = ROOT / c["INPUT_DIR"], ROOT / c["OUTPUT_DIR"]
    out.mkdir(parents=True, exist_ok=True)
    try:
        loc = load_locations(inp / c["LOCATIONS_CSV"])
        ins = load_instruments(inp / c["INSTRUMENTS_CSV"], loc)
        crit = load_criteria(inp / c["CRITERIA_CSV"]) if c["CRITERIA_CSV"] else None
        raw = load_measurements(c["MEASUREMENT_GLOBS"], inp, c["COLUMN_MAP"])
    except (DataError, FileNotFoundError) as e:
        raise SystemExit(f"Input problem: {e}\nIf you have not created data yet, run make_demo_data.py first.")
    if crit is None or crit.empty:
        print("Note: no review criteria supplied. Every channel will show 'no criterion configured'; nothing will be flagged.")

    parsed, rej = parse_raw(raw, cfg)
    con = db.connect(ROOT / c["DB_PATH"])
    added = db.upsert_raw(con, parsed)
    all_parsed, _ = parse_raw(_raw_from_db(db.load_raw(con)), cfg)
    as_of = resolve_as_of(os.environ.get("MINEENV_AS_OF", c["AS_OF"]), all_parsed, cfg)
    A = analyse(all_parsed, rej, ins, loc, crit, cfg, as_of)
    db.store_analysis(con, A, cfg)
    con.close()

    if c["WRITE_CSV"]:
        A.channels.to_csv(out / "channel_status.csv", index=False)
        A.events.to_csv(out / "review_events.csv", index=False)
        A.gaps.to_csv(out / "missing_data_gaps.csv", index=False)
        A.instruments.to_csv(out / "instrument_calibration.csv", index=False)
        A.rejected.to_csv(out / "rejected_rows.csv", index=False)
    if c["WRITE_REPORT"]:
        con = db.connect(ROOT / c["DB_PATH"])
        (out / "environment_report.html").write_text(build_report(A, lambda l, i, p: db.readings_for(con, l, i, p), c["PROJECT_NAME"], c["PREPARED_BY"]), encoding="utf-8")
        con.close()
    if c["WRITE_OFFLINE_DASHBOARD"]:
        (out / "dashboard_offline.html").write_text(build_offline_html(A, "Environmental monitoring dashboard", cfg.gap_factor, cfg.offline_max_points_per_series), encoding="utf-8")
    if c["WRITE_MANUAL_FORM"]:
        (out / "manual_entry_form.html").write_text(build_form(ins, loc, "Manual environmental measurement entry"), encoding="utf-8")

    ch = A.channels
    print(f"As-of {A.as_of:%Y-%m-%d %H:%M}. New raw rows stored: {added:,}. Rejected rows: {len(A.rejected)}.")
    print(ch["state"].value_counts().to_string())
    print(f"Review events: {len(A.events)} ({int(A.events['active'].sum()) if len(A.events) else 0} active). Gaps: {len(A.gaps)}.")
    if A.notes.get("demo_criteria"):
        print("\nWARNING: DEMONSTRATION criteria in use. They are placeholders, NOT approved limits.")
    print("\nReminder: missing / stale / out-of-service data = conditions UNKNOWN, not safe. This tool is not an alarm system.")
    print(f"Outputs in {out}/")


def _raw_from_db(df):
    r = df.rename(columns={"raw_value": "value", "raw_unit": "unit", "quality_supplied": "quality"}).astype(object)
    r["value"] = df["raw_value"].astype(str)
    return r.where(r.notna(), "").reset_index(drop=True)


if __name__ == "__main__":
    main()
