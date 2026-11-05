"""Self-contained HTML report for the authorised ventilation / environmental team (print to PDF from a browser)."""
import base64
import html
import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import __version__
from .config import PARAM_LABEL, UNIT_LABEL
from .viz import STATE_STYLE, channel_label, _gap_break

INK, INK2, MUTED, GRID, BLUE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#2a78d6"
MPL = {"CRITERION_MET": ("D", True), "STALE": ("s", False), "NO_DATA": ("x", False), "OUT_OF_SERVICE": ("p", False),
       "QUALITY_CONCERN": ("^", True), "NO_CRITERIA_CONFIGURED": ("o", False), "NO_CRITERION_MET": ("o", True)}
CSS = """
body{font:14px/1.5 system-ui,-apple-system,'Segoe UI',sans-serif;color:#0b0b0b;max-width:1000px;margin:24px auto;padding:0 20px}
h1{font-size:24px;margin:0 0 4px}h2{font-size:18px;border-bottom:1px solid #c3c2b7;padding-bottom:4px;margin-top:30px}h3{font-size:15px;margin:18px 0 6px}
table{border-collapse:collapse;width:100%;margin:8px 0 14px;font-size:12.2px}th,td{border-bottom:1px solid #e1e0d9;padding:4px 7px;text-align:right}
th{background:#f4f3ef}th:first-child,td:first-child{text-align:left}.meta{color:#52514e}
.safety{border:2px solid #0b0b0b;border-radius:6px;padding:10px 14px;margin:12px 0;background:#fafaf7}
.demo{border:2px solid #d03b3b;border-radius:6px;padding:10px 14px;margin:12px 0;color:#7a1f1f;background:#fff3f1}
.note{background:#f4f3ef;padding:8px 12px;border-radius:6px;font-size:13px}img{max-width:100%}.sign td{height:34px;text-align:left}
@media print{h2{page-break-after:avoid}}
"""


def _png(fig):
    b = io.BytesIO(); fig.savefig(b, format="png", dpi=125, bbox_inches="tight", facecolor="white"); plt.close(fig)
    return base64.b64encode(b.getvalue()).decode()


def _style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=8); ax.grid(color=GRID, lw=0.6); ax.set_axisbelow(True)


def map_png(locs, level):
    L = locs[locs.level == level]
    fig, ax = plt.subplots(figsize=(7.2, 4.2)); _style(ax)
    for r in L.itertuples():
        if all(pd.notna(v) for v in (r.x1, r.y1, r.x2, r.y2)):
            ax.plot([r.x1, r.x2], [r.y1, r.y2], color="#c3c2b7", lw=6, solid_capstyle="round", zorder=1)
    for st, (mk, filled) in MPL.items():
        g = L[L.state == st]
        if g.empty:
            continue
        col = STATE_STYLE[st][0]
        ax.scatter(g.x, g.y, s=110, marker=mk, c=col if filled or mk == "x" else "none", linewidths=1.8, **({} if mk == "x" else {"edgecolors": col}), label=STATE_STYLE[st][2], zorder=3)
    for r in L.itertuples():
        ax.annotate(r.location_id, (r.x, r.y), textcoords="offset points", xytext=(0, 9), ha="center", fontsize=8, color=INK2)
    ax.set_aspect("equal", adjustable="datalim"); ax.set_title(f"Level {level} schematic (not to scale)", fontsize=9, color=INK)
    ax.legend(fontsize=7, frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1))
    return _png(fig)


def history_png(rd, ch, crit, gaps, as_of, gap_factor=2.5):
    fig, ax = plt.subplots(figsize=(7.2, 2.7)); _style(ax)
    for g in (gaps.itertuples() if len(gaps) else []):
        ax.axvspan(g.gap_start, g.gap_end, color=MUTED, alpha=0.18, lw=0)
    s = _gap_break(rd[["ts", "value"]], ch["expected_interval_min"], gap_factor)   # NaN breaks the line: never interpolate across missing data
    ax.plot(s["ts"], s["value"], color=BLUE, lw=1.2)
    hit = rd[rd["criteria_met"] != ""]
    if len(hit):
        ax.scatter(hit["ts"], hit["value"], marker="D", s=14, c="#d03b3b", zorder=3, label="Meets a review criterion")
    q = rd[rd["quality_state"] != "OK"]
    if len(q):
        ax.scatter(q["ts"], q["value"], marker="^", s=12, facecolors="none", edgecolors="#fab219", zorder=3, label="Quality flag")
    for c in crit.itertuples():
        ax.axhline(c.threshold_std, color=INK2, ls="--", lw=1)
        ax.text(1.005, c.threshold_std, f"{c.criterion_id}\n{c.comparator} {c.threshold_std:g}", transform=ax.get_yaxis_transform(), fontsize=6.5, color=INK2, va="center")
    last = rd["ts"].max()
    if as_of > last + pd.Timedelta(minutes=30):
        ax.axvspan(last, as_of, color=MUTED, alpha=0.18, lw=0)
    ax.axvline(as_of, color=INK, ls=":", lw=1)
    ax.set_title(f"{channel_label(ch)}  (grey = missing data; dotted line = as-of time)", fontsize=8.5, color=INK)
    ax.set_ylabel(f"{PARAM_LABEL.get(ch['parameter'])} ({UNIT_LABEL.get(ch['unit'], ch['unit'])})", fontsize=8, color=INK2)
    ax.legend(fontsize=7, frameon=False, loc="upper left"); fig.autofmt_xdate()
    return _png(fig)


def _tbl(df, fmt=None, cols=None):
    fmt, cols = fmt or {}, cols or list(df.columns)
    if df.empty:
        return "<p class='meta'>None.</p>"
    head = "".join(f"<th>{html.escape(str(c))}</th>" for c in cols)
    body = ""
    for _, r in df.iterrows():
        cells = ""
        for c in cols:
            v = r[c]
            if v is None or (isinstance(v, float) and np.isnan(v)) or v is pd.NaT:
                s = "&ndash;"
            elif isinstance(v, pd.Timestamp):
                s = v.strftime("%Y-%m-%d %H:%M")
            elif c in fmt and not isinstance(v, str):
                s = fmt[c].format(v)
            else:
                s = html.escape(str(v))
            cells += f"<td>{s}</td>"
        body += f"<tr>{cells}</tr>"
    return f"<table><tr>{head}</tr>{body}</table>"


def build_report(A, db_readings_fn, project="Underground operation (set PROJECT_NAME)", prepared_by=""):
    ch, ev, gp, ins, loc, cr = A.channels, A.events, A.gaps, A.instruments, A.locations, A.criteria
    o = [f"<html><head><meta charset='utf-8'><title>Environmental monitoring report</title><style>{CSS}</style></head><body>"]
    o.append(f"<h1>Environmental monitoring report</h1><div class='meta'>{html.escape(project)} &middot; as-of {A.as_of:%Y-%m-%d %H:%M} (site time) &middot; software v{__version__} &middot; DRAFT FOR AUTHORISED REVIEW</div>")
    o.append("<div class='safety'><b>Reporting and visualisation only.</b> This report is not an alarm, gas-monitoring system, ventilation control or emergency-response tool, "
             "and it does not set or interpret safety limits. &ldquo;Review criteria&rdquo; below are supplied by qualified personnel; this software only checks readings against them. "
             "<b>Missing, stale or unevaluated data are not safe readings:</b> they mean current conditions are unknown. Follow site procedures for any reading of concern.</div>")
    if A.notes.get("demo_criteria"):
        o.append("<div class='demo'><b>DEMONSTRATION CRITERIA IN USE.</b> At least one criterion is a synthetic placeholder, not an approved limit. This output must not be used for any operational purpose.</div>")
    n = ch.state.value_counts()
    o.append("<h2>1. Status summary</h2>")
    o.append("<table><tr><th>State of latest readings</th><th>Channels</th></tr>" + "".join(
        f"<tr><td>{html.escape(STATE_STYLE[s][2])}</td><td>{int(n.get(s, 0))}</td></tr>" for s in STATE_STYLE) + f"<tr><td><b>All channels</b></td><td><b>{len(ch)}</b></td></tr></table>")
    o.append(f"<p class='meta'>{A.notes['n_readings']:,} readings analysed; {A.notes['n_rejected']} rows rejected; {A.notes['n_exact_duplicates_dropped']} exact duplicates removed. "
             "A channel is one parameter measured by one instrument at one location.</p>")
    o.append("<h2>2. Review criteria in force (supplied by qualified personnel)</h2>")
    o.append(_tbl(cr, cols=["criterion_id", "parameter", "comparator", "threshold", "unit", "name", "source_reference", "approved_by", "approval_date", "effective_from", "effective_to"]))
    o.append("<h2>3. Channels needing attention</h2>")
    att = ch[ch.state != "NO_CRITERION_MET"].copy()
    att["state_label"] = att["state"].map(lambda s: STATE_STYLE[s][2])
    att["last_value"] = att.apply(lambda r: "" if pd.isna(r.last_ts) else f"{r.last_value:g} {UNIT_LABEL.get(r.unit, r.unit)}", axis=1)
    att["age_h"] = (att["age_min"] / 60).round(1)
    o.append(_tbl(att, cols=["state_label", "location_id", "instrument_id", "parameter", "last_ts", "last_value", "age_h", "state_reason"]))
    o.append("<h2>4. Review events (readings meeting a configured criterion)</h2>")
    if ev.empty:
        o.append("<p>No readings met a configured criterion in the data analysed.</p>")
    else:
        e = ev.copy(); e["status"] = np.where(e.active, "ACTIVE (no later reading below criterion)", "ended")
        o.append(_tbl(e, {"peak_value": "{:g}", "duration_min": "{:.0f}", "threshold": "{:g}"}, ["event_no", "status", "criterion_id", "location_id", "instrument_id", "parameter", "start_ts", "end_ts", "duration_min", "n_readings", "peak_value", "threshold", "n_quality_flagged"]))
    o.append("<h2>5. Missing data</h2>")
    o.append("<p>Gaps are intervals longer than the configured multiple of the instrument's expected reporting interval. An open gap has no reading up to the as-of time.</p>")
    o.append(_tbl(gp.head(40), {"minutes": "{:.0f}"}, ["location_id", "instrument_id", "parameter", "gap_start", "gap_end", "minutes", "open"]) if len(gp) else "<p>No gaps detected.</p>")
    o.append("<h2>6. Data-quality summary</h2>")
    fl = A.readings["flags"].str.split(";").explode().replace("", np.nan).dropna().value_counts().rename_axis("flag").reset_index(name="readings")
    o.append(_tbl(fl)); 
    o.append(_tbl(A.rejected["reason"].value_counts().rename_axis("rejection reason").reset_index(name="rows")) if len(A.rejected) else "<p class='meta'>No rows rejected.</p>")
    o.append("<h2>7. Instruments and calibration</h2>")
    o.append(_tbl(ins, {"days_to_cal_due": "{:.0f}"}, ["instrument_id", "instrument_type", "model", "serial_no", "location_id", "status", "last_calibration_date", "calibration_interval_days", "cal_due_date", "days_to_cal_due", "cal_status", "calibration_ref"]))
    o.append("<p class='meta'>UNKNOWN = calibration metadata not supplied. Readings taken after a calibration due date are flagged CALIBRATION_OVERDUE.</p>")
    o.append("<h2>8. Schematics and histories</h2>")
    for lv in sorted(loc.level.unique()):
        o.append(f"<img alt='map {lv}' src='data:image/png;base64,{map_png(loc, lv)}'>")
    pick = ch[ch.state.isin(["CRITERION_MET"]) | (ch.n_active_events > 0)]
    evc = ev[["location_id", "instrument_id", "parameter"]].drop_duplicates() if len(ev) else pd.DataFrame(columns=["location_id", "instrument_id", "parameter"])
    sel = pd.concat([pick[["location_id", "instrument_id", "parameter"]], evc]).drop_duplicates().head(8)
    o.append("<h3>Histories of channels with review events</h3>" if len(sel) else "")
    for r in sel.itertuples():
        c = ch[(ch.location_id == r.location_id) & (ch.instrument_id == r.instrument_id) & (ch.parameter == r.parameter)].iloc[0].to_dict()
        rd = db_readings_fn(r.location_id, r.instrument_id, r.parameter)
        app = cr[(cr.parameter == r.parameter) & cr.location_id.isin(["", r.location_id])]
        gg = gp[(gp.location_id == r.location_id) & (gp.instrument_id == r.instrument_id) & (gp.parameter == r.parameter)] if len(gp) else gp
        o.append(f"<img alt='history' src='data:image/png;base64,{history_png(rd, c, app, gg, A.as_of)}'>")
    o.append("<h2>9. Method, assumptions and limitations</h2><ul>"
             "<li><b>Criteria.</b> Every review criterion must name its source and approver; the tool refuses criteria without them and never supplies defaults. It checks readings against criteria, nothing more.</li>"
             "<li><b>Units.</b> Readings are converted to standard units only by exact conversions (for example ppm &harr; % vol). Anything else is left unevaluated and flagged.</li>"
             "<li><b>Missing data.</b> A channel is STALE when its latest reading is older than the instrument's stale threshold, NO_DATA when it has never reported, OUT_OF_SERVICE when marked so. None of these is treated as a normal reading.</li>"
             "<li><b>Quality flags</b> (implausible value, unit problem, duplicate conflict, possible flatline, calibration overdue, supplied quality) are advisory. They never hide a reading that meets a criterion; both are shown together. The flatline check is applied only to continuously varying quantities and ignores zero.</li>"
             "<li><b>Plausibility ranges</b> are physical sanity bounds to catch corrupt data (for example humidity above 100 %), not safety limits.</li>"
             "<li><b>Time.</b> Timestamps without a time zone are read as site local time. The as-of time controls staleness; readings after it are excluded.</li>"
             "<li><b>Locations.</b> Positions are schematic. A fixed instrument is assigned to one location; portable instruments need a location on every reading.</li></ul>")
    o.append("<h2>10. Review</h2><table class='sign'><tr><th>Role</th><th>Name</th><th>Signature</th><th>Date</th></tr>"
             f"<tr><td>Prepared by</td><td>{html.escape(prepared_by)}</td><td></td><td></td></tr><tr><td>Reviewed by (ventilation / environmental)</td><td></td><td></td><td></td></tr></table></body></html>")
    return "\n".join(o)
