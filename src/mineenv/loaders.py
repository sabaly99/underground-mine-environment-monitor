"""CSV loaders. Registers and criteria are validated strictly; measurements are parsed leniently and
anything unusable is kept in a rejected-rows table with the reason, never silently dropped."""
import glob
from pathlib import Path

import numpy as np
import pandas as pd

from .config import STD_UNITS, canonical_unit, CONVERSIONS


class DataError(ValueError):
    pass


def _read(path, required, label):
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    miss = [c for c in required if c not in df.columns]
    if miss:
        raise DataError(f"{path}: {label} is missing required columns {miss}. Found {list(df.columns)}")
    return df.apply(lambda s: s.str.strip())


def _num(df, col):
    return pd.to_numeric(df[col].replace("", np.nan), errors="coerce")


def load_locations(path):
    df = _read(path, ["location_id", "name", "level", "type", "x", "y"], "locations")
    problems = []
    if df["location_id"].duplicated().any():
        problems.append("duplicate location_id")
    for c in ("x", "y", "x1", "y1", "x2", "y2"):
        if c not in df.columns:
            df[c] = ""
        df[c] = _num(df, c)
    if df[["x", "y"]].isna().any().any():
        problems.append("x and y must be numeric for every location")
    for c in ("airway", "district"):
        if c not in df.columns:
            df[c] = ""
    if problems:
        raise DataError(f"{path}: " + "; ".join(problems))
    return df


def load_instruments(path, locations):
    df = _read(path, ["instrument_id", "instrument_type", "parameters", "status"], "instruments")
    problems = []
    if df["instrument_id"].duplicated().any():
        problems.append("duplicate instrument_id")
    for c in ("location_id", "serial_no", "model", "manufacturer", "calibration_ref", "responsible_party"):
        if c not in df.columns:
            df[c] = ""
    for c in ("expected_interval_min", "stale_after_min", "calibration_interval_days"):
        df[c] = _num(df, c) if c in df.columns else np.nan
    df["last_calibration_date"] = pd.to_datetime(df["last_calibration_date"].replace("", np.nan), errors="coerce") \
        if "last_calibration_date" in df.columns else pd.NaT
    df["parameters"] = df["parameters"].str.replace(",", ";")
    bad_loc = set(df.loc[df["location_id"] != "", "location_id"]) - set(locations["location_id"])
    if bad_loc:
        problems.append(f"unknown location_id {sorted(bad_loc)}")
    for r in df.itertuples():
        unknown = [p for p in r.parameters.split(";") if p.strip() and p.strip() not in STD_UNITS]
        if unknown:
            problems.append(f"{r.instrument_id}: unknown parameters {unknown} (known: {sorted(STD_UNITS)})")
    no_prog = df[df["expected_interval_min"].isna() & df["stale_after_min"].isna() & (df["status"] != "removed")]
    if len(no_prog):
        problems.append(f"{no_prog['instrument_id'].tolist()} have neither expected_interval_min nor stale_after_min: "
                        "without a monitoring-programme expectation, missing data cannot be identified")
    bad_status = set(df["status"]) - {"in_service", "out_of_service", "removed"}
    if bad_status:
        problems.append(f"status must be in_service, out_of_service or removed; got {sorted(bad_status)}")
    if problems:
        raise DataError(f"{path}: " + "; ".join(problems))
    df["stale_after_min"] = df["stale_after_min"]
    return df


COMPARATORS = {">", ">=", "<", "<="}


def load_criteria(path):
    """Review criteria. Every row must carry its source and approver: this tool never invents limits."""
    req = ["criterion_id", "parameter", "comparator", "threshold", "unit", "name", "source_reference", "approved_by", "approval_date"]
    df = _read(path, req, "review criteria")
    for c in ("location_id", "location_type", "effective_from", "effective_to", "procedure_reference"):
        if c not in df.columns:
            df[c] = ""
    problems = []
    if df["criterion_id"].duplicated().any():
        problems.append("duplicate criterion_id")
    for r in df.itertuples():
        miss = [c for c in ("source_reference", "approved_by", "approval_date") if not getattr(r, c)]
        if miss:
            problems.append(f"{r.criterion_id}: missing {miss} (criteria must come from qualified personnel with a source)")
        if r.parameter not in STD_UNITS:
            problems.append(f"{r.criterion_id}: unknown parameter {r.parameter!r}")
        if r.comparator not in COMPARATORS:
            problems.append(f"{r.criterion_id}: comparator must be one of {sorted(COMPARATORS)}")
    df["threshold"] = pd.to_numeric(df["threshold"], errors="coerce")
    if df["threshold"].isna().any():
        problems.append("non-numeric threshold")
    thr_std = []
    for r in df.itertuples():
        std = STD_UNITS.get(r.parameter)
        cu = canonical_unit(r.unit, r.parameter)
        if std is None or cu is None:
            problems.append(f"{r.criterion_id}: unrecognised unit {r.unit!r}"); thr_std.append(np.nan); continue
        if cu == std:
            thr_std.append(r.threshold)
        elif (cu, std) in CONVERSIONS:
            f, o = CONVERSIONS[(cu, std)]; thr_std.append(r.threshold * f + o)
        else:
            problems.append(f"{r.criterion_id}: unit {r.unit!r} cannot be converted exactly to {std}"); thr_std.append(np.nan)
    df["threshold_std"] = thr_std
    for c in ("effective_from", "effective_to", "approval_date"):
        df[c] = pd.to_datetime(df[c].replace("", np.nan), errors="coerce")
    df["is_demo"] = df["approved_by"].str.upper().str.startswith("SYNTHETIC")
    if problems:
        raise DataError(f"{path}: " + "; ".join(problems))
    return df


def load_measurements(patterns, base_dir, column_map=None):
    """Read one or more measurement CSVs (globs allowed). column_map maps OUR names -> the file's names."""
    column_map = column_map or {}
    files = []
    for p in patterns:
        files += sorted(glob.glob(str(Path(base_dir) / p)))
    if not files:
        raise DataError(f"No measurement files found for {patterns} in {base_dir}")
    parts = []
    for f in files:
        df = pd.read_csv(f, dtype=str, keep_default_na=False)
        df.columns = [c.strip() for c in df.columns]
        inv = {v: k for k, v in column_map.items() if v in df.columns}
        df = df.rename(columns=inv)
        miss = [c for c in ("timestamp", "instrument_id", "parameter", "value") if c not in df.columns]
        if miss:
            raise DataError(f"{f}: missing columns {miss} (use COLUMN_MAP in run_pipeline.py if your export names differ). Found {list(df.columns)}")
        for c in ("unit", "quality", "source", "entered_by", "comment", "location_id"):
            if c not in df.columns:
                df[c] = ""
        df["source"] = df["source"].replace("", "sensor")
        df["source_file"] = Path(f).name
        parts.append(df[["timestamp", "instrument_id", "parameter", "value", "unit", "quality", "source", "entered_by", "comment", "location_id", "source_file"]]
                     .apply(lambda s: s.str.strip()))
    return pd.concat(parts, ignore_index=True)
