"""Streamlit dashboard (alongside the offline Dash one). Edit CONFIG, then run:  streamlit run dashboard_streamlit.py
Reporting and visualisation only: not an alarm, gas monitor or ventilation control."""
# ============================== CONFIG ==============================
CONFIG = {
    "DB_PATH": "outputs/environment.sqlite",
    "DEFAULT_THEME": "midnight",   # midnight, daylight, ocean, forest, sand, contrast (changeable in the sidebar)
    "ENV": {},                     # keep equal to run_pipeline.py if you changed gap_factor etc.
}
# ====================================================================
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from mineenv import database as db, themes, ui, viz          # noqa: E402
from mineenv.config import EnvConfig                          # noqa: E402
from mineenv.offline_html import table_html, CAL_KIND         # noqa: E402

st.set_page_config(page_title="Mine environment monitor", layout="wide")
cfg = EnvConfig.from_dict(CONFIG["ENV"])
dbp = ROOT / CONFIG["DB_PATH"]
if not dbp.exists():
    st.error(f"{dbp} not found. Run make_demo_data.py then run_pipeline.py first.")
    st.stop()


@st.cache_data(show_spinner=False)
def load(path, mtime):
    con = db.connect(path)
    d = {n: db.read(con, n) for n in ("channels", "locations", "events", "gaps", "availability", "instruments", "criteria")}
    d["info"] = db.run_info(con)
    con.close()
    d["rows"] = d["channels"].sort_values(["rank", "location_id", "parameter"]).to_dict("records")
    return d


d = load(str(dbp), dbp.stat().st_mtime)
ch = d["channels"]

# ---- sidebar: brand, navigation, theme ----
names = dict(themes.options())
with st.sidebar:
    st.markdown(f'<div class="brand"><span class="mark">{ui.icon("logo", 22)}</span><div>Mine Environment<small>Monitor</small></div></div>', unsafe_allow_html=True)
    page = st.radio("Navigate", list(ui.PAGES), format_func=lambda p: ui.PAGES[p][0], label_visibility="collapsed")
    theme = st.selectbox("Theme", list(names), index=list(names).index(themes.resolve(CONFIG["DEFAULT_THEME"])), format_func=names.get, key="theme")
    st.caption("Reporting and visualisation only. Not an alarm or control system.")

# ---- theme + design system ----
st.markdown("<style>" + themes.root_css(theme) + ui.BASE_CSS + """
.stApp{background:var(--panel);color:var(--ink)}[data-testid=stSidebar]{background:var(--side)}[data-testid=stHeader]{background:transparent}
.block-container{padding-top:2rem;max-width:1500px}.stApp,.stApp p,.stApp label,.stApp li,.stApp span,.stApp div[data-testid=stCaptionContainer]{color:inherit}
[data-testid=stSidebar] label,[data-testid=stSidebar] p{color:var(--ink2)}
[data-baseweb=select]>div,[data-baseweb=input]>div,.stTextInput input{background:var(--surface)!important;color:var(--ink)!important;border-color:var(--axis)!important;border-radius:12px!important}
[data-baseweb=popover] ul,[data-baseweb=menu]{background:var(--surface)!important;color:var(--ink)!important}[data-baseweb=popover] li:hover{background:var(--raised)!important}
div[data-testid=stVerticalBlockBorderWrapper]{background:var(--surface);border-radius:20px;border:var(--bw) solid var(--grid)}
[data-testid=stSidebar] [role=radiogroup] label{padding:8px 10px;border-radius:12px;width:100%}[data-testid=stSidebar] [role=radiogroup] label:has(input:checked){background:var(--raised)}
[data-testid=stSidebar] [role=radiogroup] label:has(input:checked) p{color:var(--ink);font-weight:600}
[data-testid=stPills] button,[data-testid=stBaseButton-pills],[data-testid=stBaseButton-pillsActive]{background:var(--raised)!important;color:var(--ink)!important;border:1px solid var(--axis)!important}
[data-testid=stBaseButton-pillsActive]{background:var(--accent-soft)!important;border-color:var(--accent)!important}

.stMarkdown .brand{color:var(--ink);margin-bottom:6px}
.stMarkdown .ch .why{font-size:12.5px!important;line-height:1.4;margin:0!important;color:var(--ink2)}.stMarkdown .ch-t span,.stMarkdown .att-i small{font-size:12.5px}
.stMarkdown h1.pt{font-size:30px;padding:0;margin:0 0 4px}.stMarkdown p.ps{margin:0 0 18px;color:var(--ink2)}
div[data-baseweb=select] div,div[data-baseweb=select] input{background-color:var(--surface)!important;color:var(--ink)!important}div[data-baseweb=select] svg{fill:var(--ink2)!important}
[data-testid^=stBaseButton-pills]{background:var(--raised)!important;color:var(--ink)!important;border:1px solid var(--axis)!important}[data-testid^=stBaseButton-pills] *{color:var(--ink)!important}
[data-testid=stBaseButton-pillsActive]{background:var(--accent-soft)!important;border-color:var(--accent)!important}
input::placeholder{color:var(--muted)!important;opacity:1}.stTextInput input{border-radius:12px!important}[data-testid=stToolbar]{visibility:hidden}
[data-testid=stSidebar] .stRadio label p,[data-testid=stSidebar] label p{color:var(--ink2)!important}[data-testid=stSidebar] [role=radiogroup] label:has(input:checked) p{color:var(--ink)!important}
[data-testid=stSelectbox] [role=group],[data-testid=stSelectbox] .react-aria-ComboBox,[data-testid=stSelectbox] input{background:var(--surface)!important;color:var(--ink)!important;border-color:var(--axis)!important}
[data-testid=stSelectbox] svg{color:var(--ink2)!important;fill:var(--ink2)!important}[data-testid=stButtonGroup] button{background:var(--raised)!important;color:var(--ink)!important;border:1px solid var(--axis)!important}
[data-testid=stButtonGroup] button *{color:var(--ink)!important}[data-testid=stButtonGroup] button[aria-checked=true],[data-testid=stButtonGroup] button[aria-pressed=true],[data-testid=stButtonGroup] button[kind=pillsActive]{background:var(--accent-soft)!important;border-color:var(--accent)!important}
[role=listbox],[role=listbox] [role=option]{background:var(--surface)!important;color:var(--ink)!important}
</style>""", unsafe_allow_html=True)

st.markdown(ui.banners(d["info"].get("demo_criteria") == "True"), unsafe_allow_html=True)
st.markdown(f'<h1 class="pt">{ui.PAGES[page][0]}</h1><p class="ps">As-of {d["info"].get("as_of", "?")[:16]} (site time)</p>', unsafe_allow_html=True)
plot = lambda f: st.plotly_chart(f, width="stretch", theme=None)

if page == "overview":
    st.markdown(ui.kpi_tiles(viz.kpis(ch, d["events"], d["instruments"])), unsafe_allow_html=True)
    left, right = st.columns([1.7, 1])
    with left, st.container(border=True):
        lv = st.selectbox("Level", sorted(d["locations"]["level"].unique()))
        plot(viz.fig_map(d["locations"], ch, lv, theme))
        st.markdown(ui.STATUS_KEY, unsafe_allow_html=True)
    with right, st.container(border=True):
        st.markdown("**Needs attention**")
        att = [r for r in d["rows"] if r["state"] != "NO_CRITERION_MET"][:14]
        st.markdown('<div class="att">' + "".join(f'<div class="att-i"><div><b>{viz.channel_label(r)}</b><small>{r["state_reason"]}</small></div>{ui.pill(r["state"])}</div>' for r in att) + "</div>", unsafe_allow_html=True)
elif page == "channels":
    counts = ui.filter_counts(ch)
    labels = {k: f"{lab} ({counts[k]})" for k, lab, _ in ui.FILTERS}
    with st.container(border=True):
        fil = st.pills("Filter", list(labels), default="all", format_func=labels.get, label_visibility="collapsed") or "all"
        q = st.text_input("Search channels", placeholder="Search channels, instruments or locations", label_visibility="collapsed").strip().lower()
        sel = dict((k, s) for k, _, s in ui.FILTERS)[fil]
        ln, it = d["locations"].set_index("location_id")["name"].to_dict(), d["instruments"].set_index("instrument_id")["instrument_type"].to_dict()
        rows = [r for r in d["rows"] if (sel is None or r["state"] in sel) and (not q or q in " ".join(map(str, (r["location_id"], ln.get(r["location_id"], ""), r["instrument_id"], viz.plabel(r["parameter"]), viz.STATE_STYLE[r["state"]][2], it.get(r["instrument_id"], "")))).lower())]
        st.caption(f"Showing {len(rows)} of {len(d['rows'])} channels")
        st.markdown(ui.channel_grid(ch, d["locations"], d["instruments"], False, rows) if rows else '<p class="empty">No channels match. Clear the search box or choose another filter.</p>', unsafe_allow_html=True)
elif page == "history":
    with st.container(border=True):
        r = st.selectbox("Channel", d["rows"], format_func=lambda r: f"{viz.channel_label(r)} [{viz.STATE_STYLE[r['state']][2]}]")
        con = db.connect(dbp)
        rd = db.readings_for(con, r["location_id"], r["instrument_id"], r["parameter"])
        con.close()
        g = d["gaps"]
        g = g[(g.location_id == r["location_id"]) & (g.instrument_id == r["instrument_id"]) & (g.parameter == r["parameter"])] if len(g) else g
        plot(viz.fig_history(rd, r, viz.criteria_for(d["criteria"], r["location_id"], r["parameter"]), g, pd.Timestamp(d["info"]["as_of"]), theme, cfg.gap_factor))
        st.markdown(ui.pill(r["state"]) + f'<p class="note">{r["state_reason"]}</p>', unsafe_allow_html=True)
elif page == "avail":
    with st.container(border=True):
        st.caption("Grey cells mean no readings were received in that period. They are not a sign that conditions were fine.")
        plot(viz.fig_availability(d["availability"], theme))
elif page == "events":
    with st.container(border=True):
        st.markdown("**Review events**")
        st.markdown(table_html(d["events"], ["event_no", "criterion_id", "location_id", "instrument_id", "parameter", "start_ts", "end_ts", "duration_min", "n_readings", "peak_value", "active"], {"duration_min": "{:.0f}", "peak_value": "{:g}"},
                               {"active": lambda v: ui.chip("ACTIVE", "bad") if bool(v) else ui.chip("closed")}), unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("**Missing-data gaps**")
        st.markdown(table_html(d["gaps"].head(80), ["location_id", "instrument_id", "parameter", "gap_start", "gap_end", "minutes", "open"], {"minutes": "{:.0f}"},
                               {"open": lambda v: ui.chip("OPEN: still no data", "warn") if bool(v) else ui.chip("closed")}) if len(d["gaps"]) else "<p class='empty'>None.</p>", unsafe_allow_html=True)
elif page == "instr":
    with st.container(border=True):
        st.markdown(table_html(d["instruments"], ["instrument_id", "instrument_type", "serial_no", "location_id", "status", "last_calibration_date", "cal_due_date", "days_to_cal_due", "cal_status", "calibration_ref"],
                               {"days_to_cal_due": "{:.0f}"}, {"cal_status": lambda v: ui.chip(str(v).replace("_", " "), CAL_KIND.get(str(v), "neutral"))}), unsafe_allow_html=True)
else:
    with st.container(border=True):
        st.markdown(table_html(d["criteria"], ["criterion_id", "parameter", "comparator", "threshold", "unit", "name", "source_reference", "approved_by", "approval_date"]), unsafe_allow_html=True)
