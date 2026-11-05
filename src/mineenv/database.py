"""SQLite store. Raw measurements accumulate (idempotent); derived tables are rebuilt from ALL raw data each run."""
import sqlite3
from datetime import datetime, timezone

import pandas as pd

from . import __version__

RAW_COLS = ["timestamp", "instrument_id", "parameter", "raw_value", "raw_unit", "quality_supplied", "source", "entered_by", "comment",
            "location_id", "source_file"]
SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_measurements (timestamp TEXT, instrument_id TEXT, parameter TEXT, raw_value REAL, raw_unit TEXT,
  quality_supplied TEXT, source TEXT, entered_by TEXT, comment TEXT, location_id TEXT, source_file TEXT,
  UNIQUE (timestamp, instrument_id, parameter, location_id, raw_value, raw_unit, source));
CREATE TABLE IF NOT EXISTS run_info (key TEXT PRIMARY KEY, value TEXT);
"""
DATE_COLS = {"readings": ["ts"], "channels": ["last_ts"], "events": ["start_ts", "end_ts", "recovered_ts"],
             "gaps": ["gap_start", "gap_end"], "availability": ["bin_start"],
             "instruments": ["last_calibration_date", "cal_due_date"], "criteria": ["effective_from", "effective_to", "approval_date"]}


def connect(path):
    con = sqlite3.connect(str(path))
    con.executescript(SCHEMA)
    return con


def upsert_raw(con, parsed):
    before = con.execute("SELECT COUNT(*) FROM raw_measurements").fetchone()[0]
    rows = parsed[RAW_COLS].astype(object).where(parsed[RAW_COLS].notna(), "").values.tolist()
    con.executemany(f"INSERT OR IGNORE INTO raw_measurements ({','.join(RAW_COLS)}) VALUES ({','.join('?' * len(RAW_COLS))})", rows)
    con.commit()
    return con.execute("SELECT COUNT(*) FROM raw_measurements").fetchone()[0] - before


def load_raw(con):
    return pd.read_sql_query(f"SELECT {','.join(RAW_COLS)} FROM raw_measurements", con)


def store_analysis(con, A, cfg):
    def put(name, df):
        df = df.copy()
        for c in df.columns:
            if str(df[c].dtype).startswith("datetime"):
                df[c] = df[c].dt.strftime("%Y-%m-%d %H:%M:%S")
        df.to_sql(name, con, if_exists="replace", index=False)
    put("readings", A.readings.drop(columns=["raw_unit", "quality_supplied"], errors="ignore"))
    for name in ("channels", "events", "gaps", "availability", "instruments", "locations", "criteria", "rejected"):
        put(name, getattr(A, name))
    con.execute("CREATE INDEX IF NOT EXISTS ix_readings_ch ON readings (location_id, instrument_id, parameter, ts)")
    info = {"as_of": A.as_of.strftime("%Y-%m-%d %H:%M:%S"), "run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "version": __version__, "demo_criteria": str(A.notes.get("demo_criteria")), "n_readings": str(A.notes["n_readings"]),
            "n_rejected": str(A.notes["n_rejected"]), "config": repr(cfg.to_dict())}
    con.executemany("INSERT OR REPLACE INTO run_info VALUES (?,?)", list(info.items()))
    con.commit()


def read(con, name, where="", params=()):
    df = pd.read_sql_query(f"SELECT * FROM {name} {where}", con, params=params)
    for c in DATE_COLS.get(name, []):
        if c in df.columns:
            df[c] = pd.to_datetime(df[c])
    return df


def run_info(con):
    return dict(con.execute("SELECT key, value FROM run_info").fetchall())


def readings_for(con, location_id, instrument_id, parameter, start=None, end=None):
    q, p = "WHERE location_id=? AND instrument_id=? AND parameter=?", [location_id, instrument_id, parameter]
    if start:
        q += " AND ts>=?"; p.append(str(start))
    if end:
        q += " AND ts<=?"; p.append(str(end))
    return read(con, "readings", q + " ORDER BY ts", p)
