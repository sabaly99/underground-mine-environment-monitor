"""Shared interface components (HTML strings + CSS). The same markup and stylesheet drive the single-file offline
dashboard, the Dash app and the Streamlit app, so all three look and behave consistently.

Accessibility rules baked in: status is never colour-only (each state has a glyph shape and a text label),
focus rings are always visible, text/background pairs come from themes.py, and the demo-criteria banner is
red in every theme.
"""
import html

import numpy as np
import pandas as pd

from . import viz
from .config import PARAM_LABEL

ICONS = {
    "logo": "M3 17c3-1 4-5 7-5s3 4 6 4 3-3 5-4M3 12c3-1 4-5 7-5s3 4 6 4 3-3 5-4",
    "grid": "M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z",
    "map": "M9 4 3 6v14l6-2 6 2 6-2V4l-6 2-6-2zM9 4v14M15 6v14",
    "activity": "M3 12h4l3-8 4 16 3-8h4",
    "calendar": "M4 6h16v14H4zM4 10h16M8 3v4M16 3v4M8 14h2M12 14h2M16 14h2",
    "bell": "M6 9a6 6 0 1 1 12 0c0 6 2 7 2 7H4s2-1 2-7zM10 20a2 2 0 0 0 4 0",
    "cpu": "M7 7h10v10H7zM10 3v4M14 3v4M10 17v4M14 17v4M3 10h4M3 14h4M17 10h4M17 14h4",
    "shield": "M12 3 5 6v6c0 4.5 3 7.5 7 9 4-1.5 7-4.5 7-9V6l-7-3zM9 12l2 2 4-4",
    "list": "M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01",
    "search": "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM20 20l-4-4",
    "sidebar": "M4 5h16v14H4zM9 5v14",
    "palette": "M12 3a9 9 0 1 0 0 18c1.5 0 2-1 1.5-2-.5-1.2.3-2.5 1.7-2.5H17a4 4 0 0 0 4-4C21 6.5 17 3 12 3zM7.5 11h.01M10 7.5h.01M14.5 7.5h.01",
    "wind": "M3 8h11a3 3 0 1 0-3-3M3 12h15a3 3 0 1 1-3 3M3 16h7",
    "droplet": "M12 3c3.5 4.2 6 7.1 6 10a6 6 0 0 1-12 0c0-2.9 2.5-5.8 6-10z",
    "thermo": "M14 14.8V5a2 2 0 0 0-4 0v9.8a4 4 0 1 0 4 0z",
    "gas": "M9 3h6M10 3v6l-5 9a2 2 0 0 0 1.8 3h10.4A2 2 0 0 0 19 18l-5-9V3M8 15h8",
    "clock": "M12 7v5l3 2M21 12a9 9 0 1 1-4-7.5",
    "wrench": "M14.7 6.3a4 4 0 0 0-5 5L3 18l3 3 6.7-6.7a4 4 0 0 0 5-5l-2.4 2.4-2.6-.6-.6-2.6z",
    "diamond": "M12 3 21 12 12 21 3 12z",
    "radio": "M12 11a1 1 0 1 0 0 2 1 1 0 0 0 0-2zM8.5 8.5a5 5 0 0 0 0 7M15.5 8.5a5 5 0 0 1 0 7M5.6 5.6a9 9 0 0 0 0 12.8M18.4 5.6a9 9 0 0 1 0 12.8",
    "tool": "M4 20h16M6 20V10l6-6 6 6v10M10 20v-5h4v5",
}
PARAM_ICON = {"air_velocity": "wind", "airflow": "wind", "temperature": "thermo", "humidity": "droplet"}

NAV = [("Overview", [("overview", "Dashboard", "grid"), ("avail", "Data availability", "calendar")]),
       ("Monitoring", [("channels", "Channels", "radio"), ("history", "Histories", "activity"), ("events", "Review events & gaps", "bell")]),
       ("Assets & governance", [("instr", "Instruments & calibration", "cpu"), ("crit", "Review criteria", "shield")])]
PAGES = {p: (label, icon) for _, items in NAV for p, label, icon in items}

# state -> small SVG glyph (same shapes as the map markers)
_GLYPH = {
    "diamond": '<path d="M5 .8 9.2 5 5 9.2.8 5z" fill="currentColor"/>', "square-open": '<rect x="1.4" y="1.4" width="7.2" height="7.2" fill="none" stroke="currentColor" stroke-width="1.6"/>',
    "x": '<path d="M1.5 1.5l7 7M8.5 1.5l-7 7" stroke="currentColor" stroke-width="1.8" fill="none"/>', "pentagon-open": '<path d="M5 .9 9 3.8 7.5 8.8h-5L1 3.8z" fill="none" stroke="currentColor" stroke-width="1.5"/>',
    "triangle-up": '<path d="M5 1 9.3 8.8H.7z" fill="currentColor"/>', "circle-open": '<circle cx="5" cy="5" r="3.5" fill="none" stroke="currentColor" stroke-width="1.6"/>',
    "circle": '<circle cx="5" cy="5" r="4" fill="currentColor"/>',
}
PARAM_LABEL_SHORT = PARAM_LABEL


def icon_mask_css():
    """CSS classes .mi-<name>::before that draw an icon with a CSS mask (lets Dash buttons show icons without inline SVG)."""
    from urllib.parse import quote
    out = []
    for n, d in ICONS.items():
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="{d}"/></svg>')
        u = f'url("data:image/svg+xml,{quote(svg)}")'
        out.append(f'.mi-{n}::before{{content:"";display:block;flex:none;width:20px;height:20px;background:currentColor;-webkit-mask:{u} no-repeat center/contain;mask:{u} no-repeat center/contain}}')
    return "\n".join(out)


def icon(name, size=20):
    return f'<svg class="ic" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="{ICONS[name]}"/></svg>'


def glyph(state):
    col, sym, _ = viz.STATE_STYLE[state]
    return f'<svg class="gl" width="10" height="10" viewBox="0 0 10 10" style="color:{col}" aria-hidden="true">{_GLYPH[sym]}</svg>'


def pill(state):
    col, _, label = viz.STATE_STYLE[state]
    short = {"CRITERION_MET": "Criterion met", "STALE": "Stale", "NO_DATA": "No data", "OUT_OF_SERVICE": "Out of service", "QUALITY_CONCERN": "Quality concern",
             "NO_CRITERIA_CONFIGURED": "No criterion set", "NO_CRITERION_MET": "None met"}[state]
    bg, bd = f"color-mix(in srgb,{col} 18%,transparent)", f"color-mix(in srgb,{col} 55%,transparent)"
    return f'<span class="pill" style="background:{bg};border-color:{bd}" title="{html.escape(label)}">{glyph(state)}{short}</span>'


def chip(text, kind="neutral"):
    return f'<span class="chip chip-{kind}">{html.escape(str(text))}</span>'


def age_text(m):
    if m is None or pd.isna(m):
        return "never"
    m = float(m)
    return f"{m:.0f} min ago" if m < 90 else (f"{m / 60:.1f} h ago" if m < 2880 else f"{m / 1440:.1f} d ago")


def dur_text(m):
    m = float(m)
    return f"{m:.0f} min" if m < 120 else (f"{m / 60:.0f} h" if m < 2880 else f"{m / 1440:.0f} d")


def stat_tile(icon_name, label, sub, value):
    return (f'<div class="tile"><span class="bubble">{icon(icon_name, 22)}</span><div class="tile-t"><b>{html.escape(label)}</b><span>{html.escape(sub)}</span></div>'
            f'<div class="tile-n">{html.escape(str(value))}</div></div>')


def kpi_tiles(k):
    return '<div class="tiles">' + "".join([
        stat_tile("radio", "Channels", "Monitored", k["channels"]), stat_tile("diamond", "Criterion met", "Latest reading", k["criterion_met"]),
        stat_tile("clock", "Missing data", "Stale or none: unknown", k["missing"]), stat_tile("wrench", "Quality", "Concerns", k["quality"]),
        stat_tile("bell", "Active events", "Meeting a criterion now", k["active_events"]),
        stat_tile("tool", "Calibration", "Overdue / due soon", f"{k['cal_overdue']} / {k['cal_due_soon']}")]) + "</div>"


def channel_card(r, loc_name="", itype="", idx=None, clickable=False):
    """One channel card (the 'fleet card' of this dashboard): status pill, freshness bar, latest value, calibration."""
    st = r["state"]
    col = viz.STATE_STYLE[st][0]
    stale = r.get("stale_after_min")
    age = r.get("age_min")
    has = pd.notna(age) and pd.notna(r.get("last_ts"))
    if st == "OUT_OF_SERVICE":
        left, frac, right = "Out of service", 0.0, "No readings expected"
    elif not has:
        left, frac, right = "No readings", 0.0, "Conditions unknown"
    else:
        frac = float(min(max(age / stale, 0), 1)) if pd.notna(stale) and stale else 0.0
        left, right = age_text(age), (f"Stale after {dur_text(stale)}" if pd.notna(stale) else "")
    knob = f'<span class="knob" style="left:{frac * 100:.1f}%"></span>' if has and st != "OUT_OF_SERVICE" else ""
    val = r.get("last_value")
    vtxt = "–" if val is None or pd.isna(val) else f"{val:g} {viz.ulabel(r['unit'])}"
    ltxt = "–" if not has else pd.Timestamp(r["last_ts"]).strftime("%Y-%m-%d %H:%M")
    p = r["parameter"]
    search = " ".join(str(x) for x in (r["location_id"], loc_name, r["instrument_id"], viz.plabel(p), viz.STATE_STYLE[st][2], itype)).lower()
    attrs = f' data-idx="{idx}" tabindex="0" role="button"' if clickable else ""
    cal = r.get("cal_status") or "UNKNOWN"
    return (f'<article class="ch{" clk" if clickable else ""}" data-state="{st}" data-search="{html.escape(search)}"{attrs}>'
            f'<header><span class="bubble">{icon(PARAM_ICON.get(p, "gas"))}</span><div class="ch-t"><strong class="ch-h">{html.escape(viz.plabel(p))}</strong>'
            f'<span>{html.escape(str(r["location_id"] or "(portable)"))} · {html.escape(str(r["instrument_id"]))}</span></div>{pill(st)}</header>'
            f'<div class="bar-row"><span>{html.escape(left)}</span><div class="bar"><i style="width:{frac * 100:.1f}%;background:{col}"></i>{knob}</div><span>{html.escape(right)}</span></div>'
            f'<dl class="meta"><div><dt>Latest value</dt><dd>{html.escape(vtxt)}</dd></div><div><dt>Last reading</dt><dd>{ltxt}</dd></div>'
            f'<div><dt>Calibration</dt><dd>{html.escape({"OK": "OK"}.get(str(cal), str(cal).replace("_", " ").capitalize()))}</dd></div></dl>'
            f'<p class="why">{html.escape(str(r.get("state_reason") or ""))}</p></article>')


def channel_grid(channels, locations, instruments, clickable=False, order=None):
    ln = locations.set_index("location_id")["name"].to_dict() if len(locations) else {}
    it = instruments.set_index("instrument_id")["instrument_type"].to_dict() if len(instruments) else {}
    rows = channels.to_dict("records") if order is None else order
    return '<div class="ch-grid">' + "".join(channel_card(r, ln.get(r["location_id"], ""), it.get(r["instrument_id"], ""), i, clickable) for i, r in enumerate(rows)) + "</div>"


FILTERS = [("all", "All channels", None), ("CRITERION_MET", "Criterion met", ["CRITERION_MET"]), ("missing", "Missing data", ["STALE", "NO_DATA"]),
           ("OUT_OF_SERVICE", "Out of service", ["OUT_OF_SERVICE"]), ("QUALITY_CONCERN", "Quality", ["QUALITY_CONCERN"]),
           ("NO_CRITERIA_CONFIGURED", "No criterion set", ["NO_CRITERIA_CONFIGURED"]), ("NO_CRITERION_MET", "None met", ["NO_CRITERION_MET"])]


def filter_counts(channels):
    return {k: (len(channels) if s is None else int(channels["state"].isin(s).sum())) for k, _, s in FILTERS}


def banners(demo):
    s = ('<div class="banner safety"><b>Reporting and visualisation only.</b> Not an alarm, gas monitor, ventilation control or emergency-response system, '
         'and it sets no safety limits: review criteria come from the approved criteria file. <b>Missing, stale or out-of-service data mean conditions are UNKNOWN, not safe.</b></div>')
    d = '<div class="banner demo">DEMONSTRATION CRITERIA IN USE: placeholder values, not approved limits. Not for operational use.</div>' if demo else ""
    return s + d


STATUS_KEY = ('<p class="note">Status shapes: <span class="k">' + glyph("NO_CRITERION_MET") + 'filled circle = latest readings meet no configured criterion</span> '
              '<span class="k">' + glyph("CRITERION_MET") + 'diamond = criterion met</span> <span class="k">' + glyph("STALE") + 'open square = stale</span> '
              '<span class="k">' + glyph("NO_DATA") + 'cross = no data</span> <span class="k">' + glyph("NO_CRITERIA_CONFIGURED") + 'open circle = no criterion configured</span> '
              '<span class="k">' + glyph("OUT_OF_SERVICE") + 'open pentagon = out of service</span> <span class="k">' + glyph("QUALITY_CONCERN") + 'triangle = quality concern</span>. '
              'The filled circle is never shown where data are missing or stale.</p>')

BASE_CSS = """
*{box-sizing:border-box}html,body{margin:0}
body{background:var(--page);color:var(--ink);font:14px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;-webkit-font-smoothing:antialiased}
.ic{flex:none}.shell{color:var(--ink);display:grid;grid-template-columns:264px minmax(0,1fr);background:var(--side);border-radius:24px;margin:14px;min-height:calc(100vh - 28px);overflow:hidden}
.shell.collapsed{grid-template-columns:0 minmax(0,1fr)}.shell.collapsed .side{display:none}
.side{padding:20px 14px;display:flex;flex-direction:column;gap:4px;min-width:0}
.brand{display:flex;align-items:center;gap:12px;padding:0 8px 14px;font-size:18px;font-weight:600}
.brand .mark{width:36px;height:36px;border-radius:10px;background:var(--ink);color:var(--side);display:grid;place-items:center}
.brand small{display:block;font-size:11px;font-weight:400;color:var(--muted);margin-top:-2px}
.ng{font-size:12px;color:var(--muted);padding:14px 10px 4px;letter-spacing:.02em}
.nav{display:flex;align-items:center;gap:12px;width:100%;text-align:left;background:none;border:0;border-radius:12px;color:var(--ink2);padding:9px 10px;font:inherit;font-size:14.5px;cursor:pointer;min-height:40px}
.nav:hover{background:var(--surface);color:var(--ink)}.nav.on{background:var(--raised);color:var(--ink);font-weight:600}.nav.on .ic{color:var(--accent)}
.side-foot{margin-top:auto;padding:14px 8px 0;border-top:var(--bw) solid var(--grid)}.side-foot .l{font-size:12px;color:var(--muted);margin-bottom:8px}
.sw{display:flex;gap:8px;flex-wrap:wrap}.sw button{width:26px;height:26px;border-radius:50%;border:2px solid var(--axis);padding:0;cursor:pointer;background:linear-gradient(135deg,var(--a) 50%,var(--b) 50%)}
.sw button[aria-pressed=true]{border-color:var(--accent);box-shadow:0 0 0 2px var(--side),0 0 0 4px var(--accent)}
.main{background:var(--panel);margin:10px 10px 10px 0;border-radius:18px;padding:16px 26px 40px;min-width:0;border:var(--bw) solid transparent}
.topbar{display:flex;align-items:center;gap:12px;margin-bottom:22px}
.iconbtn{display:grid;place-items:center;width:40px;height:40px;border-radius:12px;border:0;background:none;color:var(--ink2);cursor:pointer}.iconbtn:hover{background:var(--surface);color:var(--ink)}
.search{flex:1;display:flex;align-items:center;gap:10px;background:var(--surface);border-radius:999px;padding:0 14px;height:44px;max-width:620px;color:var(--muted);border:var(--bw) solid var(--grid)}
.search input{flex:1;min-width:0;background:none;border:0;outline:0;color:var(--ink);font:inherit;font-size:14.5px;height:100%}.search input::placeholder{color:var(--muted)}
.search:focus-within{border-color:var(--accent)}kbd{font:12px ui-monospace,monospace;background:var(--raised);color:var(--muted);border-radius:6px;padding:2px 8px}
.top-r{margin-left:auto;display:flex;align-items:center;gap:10px}
.sel{display:flex;align-items:center;gap:8px;background:var(--surface);border:var(--bw) solid var(--grid);border-radius:999px;padding:0 12px;height:40px;color:var(--ink2)}
.sel select,select.plain{background:transparent;color:var(--ink);border:0;font:inherit;font-size:14px;outline:0;cursor:pointer;max-width:100%}.sel select option,select.plain option{background:var(--surface);color:var(--ink)}
select.box{background:var(--surface);color:var(--ink);border:var(--bw) solid var(--axis);border-radius:12px;padding:9px 12px;font:inherit;max-width:100%;cursor:pointer}
.asof{background:var(--accent-soft);color:var(--ink);border-radius:999px;padding:8px 14px;font-size:13px;white-space:nowrap}
h1.pt{font-size:30px;font-weight:600;margin:0 0 4px;letter-spacing:-.01em}.ps{color:var(--ink2);margin:0 0 18px;max-width:80ch}
.banner{border-radius:14px;padding:10px 14px;font-size:13px;margin:0 0 12px;background:var(--surface);border:2px solid var(--ink2)}
.banner.demo{border-color:#e5484d;color:var(--demo);font-weight:600}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(255px,1fr));gap:14px;margin:6px 0 18px}
.tile{display:flex;align-items:center;gap:14px;background:var(--surface);border-radius:20px;padding:16px 18px;border:var(--bw) solid var(--grid)}
.bubble{width:44px;height:44px;border-radius:14px;background:var(--raised);color:var(--accent);display:grid;place-items:center;flex:none}
.tile-t{min-width:0}.tile-t b{display:block;font-weight:600;font-size:15px}.tile-t span{display:block;color:var(--ink2);font-size:13px}.tile-n{margin-left:auto;font-size:34px;font-weight:600;line-height:1}
.card{background:var(--surface);border-radius:20px;padding:18px 20px;margin-bottom:16px;border:var(--bw) solid var(--grid);min-width:0}
.card h2{font-size:16px;margin:0 0 12px;font-weight:600}.card .plot{border-radius:12px;overflow:hidden}
.two{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(300px,1fr);gap:16px;align-items:start}
.pilltabs{display:flex;gap:6px;flex-wrap:wrap;border-bottom:var(--bw) solid var(--grid);margin-bottom:14px}
.pt-b{background:none;border:0;color:var(--ink2);font:inherit;font-size:14px;padding:10px 10px;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px;display:flex;gap:8px;align-items:center;border-radius:8px 8px 0 0}
.pt-b:hover{color:var(--ink)}.pt-b[aria-selected=true]{color:var(--ink);font-weight:600;border-bottom-color:var(--accent)}
.pt-b .n{background:var(--raised);color:var(--muted);border-radius:999px;font-size:12px;padding:1px 9px}.pt-b[aria-selected=true] .n{background:var(--accent-soft);color:var(--ink)}
.sbar{display:flex;align-items:center;gap:10px;background:var(--raised);border-radius:999px;padding:0 16px;height:44px;margin-bottom:14px;color:var(--muted)}
.sbar input{flex:1;background:none;border:0;outline:0;color:var(--ink);font:inherit;height:100%}.sbar:focus-within{outline:2px solid var(--accent)}
.ch-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:14px}
.ch{background:var(--panel);border-radius:18px;padding:16px;border:var(--bw) solid var(--grid);display:flex;flex-direction:column;gap:12px;min-width:0}
.ch.clk{cursor:pointer}.ch.clk:hover{border-color:var(--accent)}
.ch header{display:flex;align-items:center;gap:12px}.ch-t{min-width:0;flex:1}.ch-h{display:block;font-size:16px;font-weight:600;line-height:1.3;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.ch-t span{color:var(--ink2);font-size:13px}
.pill{display:inline-flex;align-items:center;gap:7px;border-radius:999px;padding:4px 12px;font-size:12.5px;white-space:nowrap;color:var(--ink);border:1px solid}
.chip{display:inline-block;border-radius:999px;padding:2px 10px;font-size:12px;background:var(--raised);color:var(--ink);border:1px solid var(--axis)}
.chip-bad{border-color:#e5484d;background:color-mix(in srgb,#e5484d 18%,transparent)}.chip-warn{border-color:#ec835a;background:color-mix(in srgb,#ec835a 18%,transparent)}.chip-ok{border-color:var(--accent)}
.bar-row{display:grid;grid-template-columns:auto minmax(40px,1fr) auto;gap:12px;align-items:center;font-size:13.5px;color:var(--ink2)}.bar-row span:first-child{color:var(--ink)}
.bar{position:relative;height:6px;border-radius:99px;background:var(--grid);margin:0 9px}.bar i{position:absolute;left:0;top:0;bottom:0;border-radius:99px}
.knob{position:absolute;top:50%;width:18px;height:18px;border-radius:50%;background:var(--panel);border:2px solid var(--accent);transform:translate(-50%,-50%)}
.meta{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:0}.meta dt{color:var(--muted);font-size:12.5px}.meta dd{margin:0;font-size:14.5px;font-weight:500}
.why{margin:0;color:var(--ink2);font-size:12.5px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.att{display:flex;flex-direction:column;gap:8px}.att-i{display:flex;align-items:center;gap:12px;background:var(--panel);border-radius:14px;padding:10px 12px;cursor:pointer;border:var(--bw) solid var(--grid)}
.att-i:hover{border-color:var(--accent)}.att-i div{min-width:0;flex:1}.att-i b{display:block;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.att-i small{color:var(--ink2);font-size:12.5px}
.empty{color:var(--ink2);padding:24px;text-align:center}
.tw{overflow-x:auto;border-radius:12px}table.t{border-collapse:collapse;width:100%;font-size:13px}
table.t th{background:var(--raised);color:var(--ink2);font-weight:600;text-align:left;padding:9px 12px;white-space:nowrap}table.t td{padding:8px 12px;border-bottom:var(--bw) solid var(--grid);white-space:nowrap}
table.t tr:hover td{background:color-mix(in srgb,var(--raised) 55%,transparent)}
.note{color:var(--ink2);font-size:12.5px;margin:10px 2px 0}.k{display:inline-flex;align-items:center;gap:5px;margin-right:12px;white-space:nowrap}
.ctl{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:12px}.ctl label{color:var(--ink2);font-size:13px}
button:focus-visible,select:focus-visible,input:focus-visible,[tabindex]:focus-visible,a:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.panel{display:none}.panel.on{display:block}
@media (max-width:1100px){.two{grid-template-columns:1fr}}
@media (max-width:900px){.shell{grid-template-columns:1fr;margin:0;border-radius:0}.side{position:fixed;z-index:20;left:0;top:0;bottom:0;width:272px;background:var(--side);display:none;overflow:auto}
 .shell.open .side{display:flex}.main{margin:0;border-radius:0;padding:14px}.asof{display:none}h1.pt{font-size:24px}.meta{grid-template-columns:1fr 1fr}.topbar{gap:6px}.search{min-width:0;padding:0 10px}.search kbd{display:none}.top-r{margin-left:0}.sel{padding:0 8px}.sel select{max-width:84px}}
@media print{.side,.topbar,.sw{display:none!important}.shell{display:block;margin:0}.main{margin:0}.panel{display:block!important}}
"""

BASE_CSS += "#banners{margin-bottom:6px}\n"
