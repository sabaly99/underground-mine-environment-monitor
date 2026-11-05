"""Quality checks, review-criteria evaluation, channel status, gaps, calibration, availability.

Design rules (reporting tool, not a safety system):
  * Missing, stale, out-of-service and unevaluable data are separate states and are NEVER shown as "no criterion met".
  * Review criteria come only from the approved criteria file; nothing is defaulted or inferred.
  * Quality problems never hide a reading that meets a criterion: both facts are reported together.
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .config import STD_UNITS, QUALITY_MAP, CONVERSIONS, canonical_unit

STATE_RANK = {"CRITERION_MET": 0, "STALE": 1, "NO_DATA": 1, "OUT_OF_SERVICE": 2, "QUALITY_CONCERN": 3,
              "NO_CRITERIA_CONFIGURED": 4, "NO_CRITERION_MET": 5}
CHANNEL_COLS = ["location_id", "instrument_id", "parameter"]


@dataclass
class Analysis:
    as_of: pd.Timestamp
    readings: pd.DataFrame
    rejected: pd.DataFrame
    channels: pd.DataFrame
    events: pd.DataFrame
    gaps: pd.DataFrame
    availability: pd.DataFrame
    instruments: pd.DataFrame
    locations: pd.DataFrame
    criteria: pd.DataFrame
    notes: dict = field(default_factory=dict)


# ---------------------------------------------------------------- parsing
def parse_ts(s, tz):
    t = pd.to_datetime(s, errors="coerce", format="mixed")
    if t.dtype == object:
        t = pd.to_datetime(s, errors="coerce", utc=True)
    if getattr(t.dt, "tz", None) is not None:
        t = t.dt.tz_convert(tz).dt.tz_localize(None)
    return t


def parse_raw(raw, cfg):
    """Split raw rows into parsed rows and rejected rows (unparseable timestamp or value)."""
    ts = parse_ts(raw["timestamp"], cfg.site_timezone)
    val = pd.to_numeric(raw["value"].replace("", np.nan), errors="coerce")
    bad = ts.isna() | val.isna()
    rej = raw[bad].copy()
    rej["reason"] = np.where(ts[bad].isna(), "unparseable timestamp", "non-numeric value")
    ok = raw[~bad].copy()
    ok["timestamp"] = ts[~bad].dt.strftime("%Y-%m-%d %H:%M:%S")
    ok["raw_value"] = val[~bad]
    ok = ok.rename(columns={"unit": "raw_unit", "quality": "quality_supplied"}).drop(columns=["value"])
    return ok.reset_index(drop=True), rej.reset_index(drop=True)


def resolve_as_of(setting, parsed, cfg):
    if setting == "now":
        return pd.Timestamp.now(tz=cfg.site_timezone).tz_localize(None).floor("s")
    if setting == "auto":
        return pd.to_datetime(parsed["timestamp"]).max()
    return pd.Timestamp(setting)


# ---------------------------------------------------------------- processing
def calibration_table(instruments, as_of, cfg):
    t = instruments.copy()
    t["cal_due_date"] = t["last_calibration_date"] + pd.to_timedelta(t["calibration_interval_days"], unit="D")
    days = (t["cal_due_date"] - as_of).dt.total_seconds() / 86400
    t["days_to_cal_due"] = days
    t["cal_status"] = np.where(t["cal_due_date"].isna(), "UNKNOWN",
                      np.where(days < 0, "OVERDUE", np.where(days <= cfg.cal_due_soon_days, "DUE_SOON", "OK")))
    return t


def _flags_to_text(flag_masks, n):
    out = pd.Series([""] * n, dtype=object)
    for name, m in flag_masks.items():
        out = out + np.where(m, name + ";", "")
    return out.str.rstrip(";")


def process(parsed, instruments, locations, criteria, cfg, as_of):
    df = parsed.copy()
    df["ts"] = pd.to_datetime(df["timestamp"])
    inst = instruments.set_index("instrument_id")
    rej = []

    def reject(mask, reason):
        nonlocal df
        if mask.any():
            r = df[mask].copy(); r["reason"] = reason; rej.append(r)
            df = df[~mask].copy()

    reject(~df["instrument_id"].isin(inst.index), "instrument not in register")
    declared = inst["parameters"].str.split(";").map(lambda L: {p.strip() for p in L})
    reject(~df.apply(lambda r: r["parameter"] in declared.get(r["instrument_id"], set()), axis=1) if len(df) else pd.Series(False, index=df.index),
           "parameter not declared for this instrument")
    reject(df["ts"] > as_of + pd.Timedelta(minutes=cfg.future_tolerance_min), "timestamp after the as-of time")
    df["location_id"] = np.where(df["location_id"] != "", df["location_id"], df["instrument_id"].map(inst["location_id"]).fillna(""))
    reject(~df["location_id"].isin(locations["location_id"]), "no valid location (portable instruments need location_id on each reading)")
    reject(df["instrument_id"].map(inst["status"]) == "removed", "instrument is marked removed")

    # units -> standard unit; never guess
    df["unit"] = df["parameter"].map(STD_UNITS)
    df["value"] = np.nan
    for (p, u), idx in df.groupby(["parameter", "raw_unit"]).groups.items():
        cu = canonical_unit(u, p); std = STD_UNITS[p]
        if cu is None and str(u).strip() == "" and cfg.assume_standard_unit_when_blank:
            cu = std
        if cu is None:
            continue                                   # blank or unrecognised unit: value stays NaN (not evaluated)
        if cu == std:
            df.loc[idx, "value"] = df.loc[idx, "raw_value"]
        elif (cu, std) in CONVERSIONS:
            fct, off = CONVERSIONS[(cu, std)]
            df.loc[idx, "value"] = df.loc[idx, "raw_value"] * fct + off
        # else: no exact conversion exists -> value stays NaN

    # exact duplicates dropped; conflicting duplicates kept and flagged
    key = ["location_id", "instrument_id", "parameter", "ts"]
    before = len(df)
    df = df.drop_duplicates(key + ["raw_value", "raw_unit"])
    n_dups = before - len(df)
    df = df.sort_values(CHANNEL_COLS + ["ts"]).reset_index(drop=True)

    f_missing = df["value"].isna() & (df["raw_unit"].str.strip() == "")
    f_mismatch = df["value"].isna() & ~f_missing
    f_dup = df.duplicated(key, keep=False)
    lo = df["parameter"].map(lambda p: cfg.plausible.get(p, (-np.inf, np.inf))[0])
    hi = df["parameter"].map(lambda p: cfg.plausible.get(p, (-np.inf, np.inf))[1])
    f_implaus = df["value"].notna() & ((df["value"] < lo) | (df["value"] > hi))

    # possible flatline (advisory, continuous quantities only; zero excluded)
    g = df.groupby(CHANNEL_COLS, sort=False)["value"]
    run = (df["value"] != g.shift()).groupby([df[c] for c in CHANNEL_COLS]).cumsum()
    run_len = df.groupby(CHANNEL_COLS + [run], sort=False)["value"].transform("size")
    f_flat = (run_len >= cfg.flatline_min_readings) & (df["value"] != 0) & df["parameter"].isin(cfg.flatline_params) & (df["source"] == "sensor")

    cal = calibration_table(instruments, as_of, cfg).set_index("instrument_id")
    due = df["instrument_id"].map(cal["cal_due_date"])
    f_cal = due.notna() & (df["ts"] > due)

    sup = df["quality_supplied"].str.lower().map(QUALITY_MAP).fillna("")
    flags = {"UNIT_MISSING": f_missing, "UNIT_UNRECOGNISED_OR_MISMATCH": f_mismatch, "IMPLAUSIBLE_VALUE": f_implaus,
             "SUPPLIED_BAD": sup == "BAD", "SUPPLIED_SUSPECT": sup == "SUSPECT", "DUPLICATE_CONFLICT": f_dup,
             "POSSIBLE_FLATLINE": f_flat, "CALIBRATION_OVERDUE": f_cal}
    df["flags"] = _flags_to_text(flags, len(df))
    bad = f_missing | f_mismatch | f_implaus | (sup == "BAD")
    sus = f_flat | f_cal | f_dup | (sup == "SUSPECT")
    df["quality_state"] = np.where(bad, "BAD", np.where(sus, "SUSPECT", "OK"))

    # review criteria (from the approved file only)
    ltype = df["location_id"].map(locations.set_index("location_id")["type"])
    met = pd.Series([""] * len(df), dtype=object)
    hits = {}
    for c in criteria.itertuples():
        m = (df["parameter"] == c.parameter) & df["value"].notna()
        if c.location_id:
            m &= df["location_id"] == c.location_id
        if c.location_type:
            m &= ltype == c.location_type
        if pd.notna(c.effective_from):
            m &= df["ts"] >= c.effective_from
        if pd.notna(c.effective_to):
            m &= df["ts"] <= c.effective_to
        v = df["value"]
        h = {">": v > c.threshold_std, ">=": v >= c.threshold_std, "<": v < c.threshold_std, "<=": v <= c.threshold_std}[c.comparator]
        hits[c.criterion_id] = (m, m & h)
        met = met + np.where(m & h, c.criterion_id + ";", "")
    df["criteria_met"] = met.str.rstrip(";")
    rejected = pd.concat(rej, ignore_index=True) if rej else pd.DataFrame(columns=list(parsed.columns) + ["reason"])
    return df, rejected, hits, n_dups


def detect_events(df, criteria, hits):
    rows = []
    for c in criteria.itertuples():
        app, hit = hits[c.criterion_id]
        sub = df[app].copy()
        if sub.empty:
            continue
        sub["hit"] = hit[app]
        grp = [sub[k] for k in CHANNEL_COLS]
        sub["run"] = (sub["hit"] != sub.groupby(CHANNEL_COLS)["hit"].shift()).groupby(grp).cumsum()
        for (loc, ins, par, run), g in sub.groupby(CHANNEL_COLS + ["run"], sort=False):
            if not g["hit"].iloc[0]:
                continue
            chan = sub[(sub["location_id"] == loc) & (sub["instrument_id"] == ins) & (sub["parameter"] == par)]
            after = chan[chan["ts"] > g["ts"].iloc[-1]]
            rec = after["ts"].iloc[0] if len(after) else pd.NaT
            peak = g["value"].max() if c.comparator in (">", ">=") else g["value"].min()
            rows.append(dict(criterion_id=c.criterion_id, criterion_name=c.name, location_id=loc, instrument_id=ins, parameter=par,
                             comparator=c.comparator, threshold=c.threshold_std, unit=STD_UNITS[par], start_ts=g["ts"].iloc[0], end_ts=g["ts"].iloc[-1],
                             n_readings=len(g), peak_value=peak, recovered_ts=rec, active=pd.isna(rec),
                             n_quality_flagged=int((g["quality_state"] != "OK").sum()),
                             duration_min=(g["ts"].iloc[-1] - g["ts"].iloc[0]).total_seconds() / 60))
    ev = pd.DataFrame(rows)
    if len(ev):
        ev = ev.sort_values(["active", "start_ts"], ascending=[False, False]).reset_index(drop=True)
        ev.insert(0, "event_no", range(1, len(ev) + 1))
    return ev


def build_channels(df, instruments, locations, criteria, events, cal, as_of, cfg):
    last = df.sort_values("ts").groupby(CHANNEL_COLS, sort=False).tail(1).set_index(CHANNEL_COLS)
    rows = []
    for ins in instruments[instruments["status"] != "removed"].itertuples():
        for p in [x.strip() for x in ins.parameters.split(";") if x.strip()]:
            locs = [ins.location_id] if ins.location_id else sorted(df[(df.instrument_id == ins.instrument_id) & (df.parameter == p)]["location_id"].unique()) or [""]
            for loc in locs:
                stale = ins.stale_after_min if pd.notna(ins.stale_after_min) else cfg.stale_factor * ins.expected_interval_min
                r = dict(location_id=loc, instrument_id=ins.instrument_id, parameter=p, unit=STD_UNITS[p], stale_after_min=stale,
                         expected_interval_min=ins.expected_interval_min, instrument_status=ins.status,
                         cal_status=cal.loc[ins.instrument_id, "cal_status"], last_ts=pd.NaT, last_value=np.nan, age_min=np.nan,
                         last_flags="", last_criteria_met="", last_quality="", state="", state_reason="")
                key = (loc, ins.instrument_id, p)
                if key in last.index:
                    L = last.loc[key]
                    r.update(last_ts=L["ts"], last_value=L["value"], age_min=(as_of - L["ts"]).total_seconds() / 60,
                             last_flags=L["flags"], last_criteria_met=L["criteria_met"], last_quality=L["quality_state"])
                app = criteria[(criteria.parameter == p) & (criteria.location_id.isin(["", loc])) &
                               ((criteria.location_type == "") | (criteria.location_type == (locations.set_index("location_id")["type"].get(loc, ""))))]
                if pd.notna(r["last_ts"]):
                    app = app[(app.effective_from.isna() | (app.effective_from <= r["last_ts"])) & (app.effective_to.isna() | (app.effective_to >= r["last_ts"]))]
                if ins.status == "out_of_service":
                    r["state"], r["state_reason"] = "OUT_OF_SERVICE", "instrument marked out of service: no readings expected, and no information about conditions here"
                elif pd.isna(r["last_ts"]):
                    r["state"], r["state_reason"] = "NO_DATA", "no readings received for this channel"
                elif r["age_min"] > stale:
                    r["state"] = "STALE"
                    r["state_reason"] = f"last reading {r['age_min'] / 60:.1f} h before the as-of time (stale after {stale / 60:.1f} h); current conditions unknown"
                elif r["last_criteria_met"]:
                    r["state"], r["state_reason"] = "CRITERION_MET", f"latest reading meets {r['last_criteria_met']}" + (f" (quality: {r['last_quality']}, {r['last_flags']})" if r["last_quality"] != "OK" else "")
                elif r["last_quality"] != "OK":
                    r["state"], r["state_reason"] = "QUALITY_CONCERN", f"latest reading flagged: {r['last_flags'] or r['last_quality']}"
                elif app.empty:
                    r["state"], r["state_reason"] = "NO_CRITERIA_CONFIGURED", "no approved review criterion configured for this parameter at this location"
                elif r["cal_status"] == "OVERDUE":
                    r["state"], r["state_reason"] = "QUALITY_CONCERN", "instrument calibration overdue"
                else:
                    r["state"], r["state_reason"] = "NO_CRITERION_MET", "latest reading meets none of the configured review criteria"
                r["n_active_events"] = int(((events.location_id == loc) & (events.instrument_id == ins.instrument_id) & (events.parameter == p) & events.active).sum()) if len(events) else 0
                r["stale_but_last_met_criterion"] = bool(r["state"] == "STALE" and r["last_criteria_met"])
                rows.append(r)
    ch = pd.DataFrame(rows)
    ch["rank"] = ch["state"].map(STATE_RANK)
    return ch.sort_values(["rank", "location_id", "parameter"]).reset_index(drop=True)


def find_gaps(df, channels, as_of, cfg):
    rows = []
    for ch in channels.itertuples():
        e = ch.expected_interval_min
        if pd.isna(e) or ch.instrument_status != "in_service":
            continue
        g = df[(df.location_id == ch.location_id) & (df.instrument_id == ch.instrument_id) & (df.parameter == ch.parameter)]["ts"].sort_values().drop_duplicates()
        if g.empty:
            continue
        d = g.diff().dt.total_seconds() / 60
        for i in np.where(d > cfg.gap_factor * e)[0]:
            rows.append(dict(location_id=ch.location_id, instrument_id=ch.instrument_id, parameter=ch.parameter, gap_start=g.iloc[i - 1], gap_end=g.iloc[i],
                             minutes=d.iloc[i], expected_interval_min=e, open=False))
        tail = (as_of - g.iloc[-1]).total_seconds() / 60
        if tail > cfg.gap_factor * e:
            rows.append(dict(location_id=ch.location_id, instrument_id=ch.instrument_id, parameter=ch.parameter, gap_start=g.iloc[-1], gap_end=as_of,
                             minutes=tail, expected_interval_min=e, open=True))
    out = pd.DataFrame(rows)
    return out.sort_values(["open", "minutes"], ascending=False).reset_index(drop=True) if len(out) else out


def availability(df, channels, as_of, cfg):
    start = (as_of - pd.Timedelta(days=cfg.avail_days)).floor(f"{cfg.avail_bin_hours}h")
    bins = pd.date_range(start, as_of.ceil(f"{cfg.avail_bin_hours}h"), freq=f"{cfg.avail_bin_hours}h", inclusive="left")
    rows = []
    for ch in channels.itertuples():
        if pd.isna(ch.expected_interval_min) or ch.instrument_status == "removed":
            continue
        exp = cfg.avail_bin_hours * 60 / ch.expected_interval_min
        g = df[(df.location_id == ch.location_id) & (df.instrument_id == ch.instrument_id) & (df.parameter == ch.parameter) & (df.ts >= start)]
        cnt = g.groupby(g["ts"].dt.floor(f"{cfg.avail_bin_hours}h")).size().reindex(bins, fill_value=0)
        for b, n in cnt.items():
            rows.append(dict(location_id=ch.location_id, instrument_id=ch.instrument_id, parameter=ch.parameter, bin_start=b, n_readings=int(n),
                             coverage=float(min(1.0, n / exp)), future=b > as_of))
    return pd.DataFrame(rows)


def location_status(channels, locations):
    rows = []
    for loc in locations.itertuples():
        c = channels[channels.location_id == loc.location_id]
        if c.empty:
            rows.append(dict(location_id=loc.location_id, state="NO_DATA", n_channels=0, summary="no instruments or channels configured for this location"))
            continue
        worst = c.sort_values("rank").iloc[0]
        # blue "no criterion met" only if EVERY channel is in that state
        state = worst["state"]
        rows.append(dict(location_id=loc.location_id, state=state, n_channels=len(c),
                         n_criterion_met=int((c.state == "CRITERION_MET").sum()), n_stale_or_no_data=int(c.state.isin(["STALE", "NO_DATA"]).sum()),
                         n_quality=int((c.state == "QUALITY_CONCERN").sum()), summary=worst["state_reason"]))
    ls = pd.DataFrame(rows)
    return locations.merge(ls, on="location_id", how="left")


def analyse(parsed, rejected_parse, instruments, locations, criteria, cfg, as_of):
    df, rej, hits, n_dups = process(parsed, instruments, locations, criteria, cfg, as_of)
    events = detect_events(df, criteria, hits)
    cal = calibration_table(instruments, as_of, cfg)
    channels = build_channels(df, instruments, locations, criteria, events, cal.set_index("instrument_id", drop=False), as_of, cfg)
    gaps = find_gaps(df, channels, as_of, cfg)
    avail = availability(df, channels, as_of, cfg)
    locs = location_status(channels, locations)
    rejected = pd.concat([rejected_parse, rej], ignore_index=True)
    notes = dict(n_readings=len(df), n_rejected=len(rejected), n_exact_duplicates_dropped=n_dups,
                 demo_criteria=bool(criteria["is_demo"].any()) if len(criteria) else False, n_criteria=len(criteria))
    return Analysis(as_of, df, rejected, channels, events, gaps, avail, cal, locs, criteria, notes)
