"""Plotly figures shared by the Dash app, the Streamlit app and the single-file offline dashboard.

State styling rule: a colour is never the only cue (each state has its own marker shape and a text label), and
'missing' states (no data, stale, out of service, no criterion configured) are grey/orange and OPEN or crossed,
so they can never be mistaken for the filled blue 'no configured criterion met'.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from . import themes
from .config import PARAM_LABEL, UNIT_LABEL

THEMES = themes.THEMES
T = themes.get          # T("midnight") or legacy "dark"/"light"

STATE_STYLE = {
    "CRITERION_MET": ("#d03b3b", "diamond", "Review criterion met"),
    "STALE": ("#ec835a", "square-open", "Stale: no recent reading"),
    "NO_DATA": ("#898781", "x", "No data"),
    "OUT_OF_SERVICE": ("#898781", "pentagon-open", "Instrument out of service"),
    "QUALITY_CONCERN": ("#fab219", "triangle-up", "Data-quality concern"),
    "NO_CRITERIA_CONFIGURED": ("#898781", "circle-open", "No criterion configured"),
    "NO_CRITERION_MET": ("#2a78d6", "circle", "Latest readings meet no configured criterion"),
}
STATE_ORDER = list(STATE_STYLE)


def plabel(p):
    return PARAM_LABEL.get(p, p)


def ulabel(u):
    return UNIT_LABEL.get(u, u)


def _base(fig, theme, title=None, height=420, xtitle=None, ytitle=None, legend=True):
    t = T(theme)
    fig.update_layout(
        title=dict(text=title, x=0.01, font=dict(size=15, color=t["ink"])) if title else None, paper_bgcolor=t["surface"], plot_bgcolor=t["surface"],
        height=height, font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", size=12, color=t["ink2"]),
        margin=dict(l=56, r=20, t=56 if title else 20, b=50), showlegend=legend, legend=dict(orientation="h", y=-0.2, x=0, font=dict(color=t["ink2"])),
        hoverlabel=dict(bgcolor=t["surface"], font=dict(color=t["ink"]), bordercolor=t["axis"]))
    fig.update_xaxes(title=xtitle, gridcolor=t["grid"], linecolor=t["axis"], zeroline=False, tickfont=dict(color=t["muted"]))
    fig.update_yaxes(title=ytitle, gridcolor=t["grid"], linecolor=t["axis"], zeroline=False, tickfont=dict(color=t["muted"]))
    return fig


def empty_figure(msg, theme="midnight", height=320):
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, xref="paper", yref="paper", x=0.5, y=0.5, font=dict(size=14, color=T(theme)["ink2"]))
    fig.update_xaxes(visible=False); fig.update_yaxes(visible=False)
    return _base(fig, theme, height=height, legend=False)


def channel_label(r):
    return f"{r['location_id'] or '(portable)'} · {r['instrument_id']} · {plabel(r['parameter'])}"


def hover_for_location(loc_id, channels):
    c = channels[channels["location_id"] == loc_id]
    if c.empty:
        return "No instruments configured for this location.<br>This is NOT an indication of conditions."
    lines = []
    for r in c.sort_values("rank").itertuples():
        val = "no reading" if pd.isna(r.last_ts) else f"{r.last_value:g} {ulabel(r.unit)}, {r.age_min / 60:.1f} h ago"
        lines.append(f"{plabel(r.parameter)} ({r.instrument_id}): {val} [{STATE_STYLE[r.state][2]}]")
    return "<br>".join(lines)


def fig_map(locs, channels, level, theme="midnight", selected=None):
    t = T(theme)
    L = locs[locs["level"] == level]
    fig = go.Figure()
    for r in L.itertuples():
        if all(pd.notna(v) for v in (r.x1, r.y1, r.x2, r.y2)) and (r.x1, r.y1) != (r.x2, r.y2):
            fig.add_trace(go.Scatter(x=[r.x1, r.x2], y=[r.y1, r.y2], mode="lines", line=dict(color=t["axis"], width=6), hoverinfo="skip", showlegend=False))
    for state in STATE_ORDER:
        g = L[L["state"] == state]
        if g.empty:
            continue
        col, sym, lab = STATE_STYLE[state]
        fig.add_trace(go.Scatter(
            x=g["x"], y=g["y"], mode="markers+text", name=lab, text=g["location_id"], textposition="top center", textfont=dict(size=11, color=t["ink2"]),
            marker=dict(color=col, symbol=sym, size=17, line=dict(width=2, color=col if "open" in sym or sym == "x" else t["surface"])),
            customdata=[[n, ty, hover_for_location(i, channels)] for i, n, ty in zip(g["location_id"], g["name"], g["type"])],
            hovertemplate="<b>%{customdata[0]}</b> (%{customdata[1]})<br>%{customdata[2]}<extra>" + lab + "</extra>"))
    if selected is not None and (L["location_id"] == selected).any():
        s = L[L["location_id"] == selected].iloc[0]
        fig.add_trace(go.Scatter(x=[s["x"]], y=[s["y"]], mode="markers", name="Selected", marker=dict(symbol="circle-open", size=28, color=t["ink"], line=dict(width=2.5))))
    _base(fig, theme, title=f"State of the latest readings, level {level}", height=470, xtitle="Schematic east (m)", ytitle="Schematic north (m)")
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig


def _gap_break(df, expected_min, gap_factor):
    """Insert NaN where the series has a gap so the line is broken (never interpolated across missing data)."""
    if df.empty or not expected_min or np.isnan(expected_min):
        return df
    d = df["ts"].diff().dt.total_seconds() / 60
    idx = np.where(d > gap_factor * expected_min)[0]
    if not len(idx):
        return df
    parts, prev = [], 0
    for i in idx:
        parts.append(df.iloc[prev:i]); parts.append(pd.DataFrame({"ts": [df["ts"].iloc[i - 1] + (df["ts"].iloc[i] - df["ts"].iloc[i - 1]) / 2], "value": [np.nan]})); prev = i
    parts.append(df.iloc[prev:])
    return pd.concat(parts, ignore_index=True)


def fig_history(rd, ch, crit, gaps, as_of, theme="midnight", gap_factor=2.5):
    """History of one channel with gaps, flagged readings and the approved review criteria."""
    t = T(theme)
    if rd is None or rd.empty:
        return empty_figure("No readings for this channel. This is NOT an indication of conditions.", theme)
    exp = ch.get("expected_interval_min", np.nan)
    line = _gap_break(rd[["ts", "value"]], exp, gap_factor)
    fig = go.Figure()
    for g in (gaps.itertuples() if gaps is not None and len(gaps) else []):
        fig.add_vrect(x0=g.gap_start, x1=g.gap_end, fillcolor=t["muted"], opacity=0.16, line_width=0, layer="below")
    fig.add_trace(go.Scatter(x=line["ts"], y=line["value"], mode="lines", name="Readings", line=dict(color=t["series"][0], width=1.6), connectgaps=False,
                             hovertemplate="%{x}<br>%{y:g} " + ulabel(ch["unit"]) + "<extra></extra>"))
    hit = rd[rd["criteria_met"] != ""]
    if len(hit):
        fig.add_trace(go.Scatter(x=hit["ts"], y=hit["value"], mode="markers", name="Meets a review criterion", marker=dict(symbol="diamond", size=9, color="#d03b3b", line=dict(width=1, color=t["surface"])),
                                 customdata=np.c_[hit["criteria_met"], hit["quality_state"]], hovertemplate="%{x}<br>%{y:g}<br>%{customdata[0]} (quality: %{customdata[1]})<extra></extra>"))
    q = rd[rd["quality_state"] != "OK"]
    if len(q):
        fig.add_trace(go.Scatter(x=q["ts"], y=q["value"], mode="markers", name="Quality flag", marker=dict(symbol="triangle-up-open", size=8, color="#fab219", line=dict(width=1.6)),
                                 customdata=np.c_[q["flags"]], hovertemplate="%{x}<br>%{y:g}<br>%{customdata[0]}<extra></extra>"))
    for c in (crit.itertuples() if crit is not None else []):
        fig.add_hline(y=c.threshold_std, line=dict(color=t["ink2"], dash="dash", width=1.4),
                      annotation_text=f"{c.criterion_id} {c.comparator} {c.threshold_std:g} ({c.approved_by})", annotation_position="top left", annotation_font=dict(size=10, color=t["ink2"]))
    last = rd["ts"].max()
    if as_of > last + pd.Timedelta(minutes=(exp or 10) * gap_factor if pd.notna(exp) else 30):
        fig.add_vrect(x0=last, x1=as_of, fillcolor=t["muted"], opacity=0.16, line_width=0, layer="below")
        fig.add_annotation(x=last + (as_of - last) / 2, y=1, yref="paper", text="no readings since", showarrow=False, font=dict(size=11, color=t["ink2"]))
    fig.add_vline(x=as_of, line=dict(color=t["ink"], width=1, dash="dot"))
    _base(fig, theme, title=channel_label(ch) + " · grey bands = missing data", height=400, ytitle=f"{plabel(ch['parameter'])} ({ulabel(ch['unit'])})")
    return fig


def fig_availability(av, theme="midnight"):
    t = T(theme)
    if av is None or av.empty:
        return empty_figure("No availability data", theme)
    av = av.copy()
    av["label"] = av["location_id"] + " · " + av["instrument_id"] + " · " + av["parameter"]
    pv = av.pivot_table(index="label", columns="bin_start", values="coverage", aggfunc="first")
    fut = av.pivot_table(index="label", columns="bin_start", values="future", aggfunc="first").reindex_like(pv).fillna(False).astype(bool)
    z = pv.where(~fut)
    blues = t["heat"]
    fig = go.Figure(go.Heatmap(z=z.values, x=list(z.columns), y=list(z.index), zmin=0, zmax=1, xgap=1, ygap=1,
                               colorscale=[[0, t["nodata"]], [1e-6, blues[0]], [0.5, blues[1]], [0.8, blues[2]], [1, blues[3]]],
                               colorbar=dict(title="Share of expected<br>readings received", tickformat=".0%", tickfont=dict(color=t["muted"])),
                               hovertemplate="%{y}<br>%{x}<br>%{z:.0%} of expected readings received<extra></extra>"))
    _base(fig, theme, title="Data availability: grey = NO readings received in that period (not 'fine')", height=max(320, 24 * len(z) + 140), legend=False)
    fig.update_yaxes(autorange="reversed")
    return fig


def kpis(channels, events, instruments):
    c = channels
    return dict(channels=len(c), criterion_met=int((c.state == "CRITERION_MET").sum()), missing=int(c.state.isin(["STALE", "NO_DATA"]).sum()),
                quality=int((c.state == "QUALITY_CONCERN").sum()), out_of_service=int((c.state == "OUT_OF_SERVICE").sum()),
                active_events=int(events["active"].sum()) if len(events) else 0,
                cal_overdue=int((instruments.cal_status == "OVERDUE").sum()), cal_due_soon=int((instruments.cal_status == "DUE_SOON").sum()))


def criteria_for(criteria, location_id, parameter):
    """Approved criteria that apply to one channel (blank location_id = applies at every location)."""
    if criteria is None or criteria.empty:
        return criteria
    loc = criteria["location_id"].fillna("").astype(str)
    return criteria[(criteria["parameter"] == parameter) & loc.isin(["", location_id])]
