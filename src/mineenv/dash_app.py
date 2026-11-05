"""Offline Dash/Plotly dashboard (serve_locally=True: no internet needed). Reporting and visualisation only.
Same design system as the single-file dashboard and the Streamlit app (themes.py / ui.py)."""
from pathlib import Path

import pandas as pd
from dash import ALL, Dash, Input, Output, ctx, dcc, html, dash_table, no_update

from . import database as db, themes, ui, viz
from .config import EnvConfig


def _load(path):
    con = db.connect(path)
    try:
        d = {n: db.read(con, n) for n in ("channels", "locations", "events", "gaps", "availability", "instruments", "criteria")}
        d["info"] = db.run_info(con)
    finally:
        con.close()
    d["rows"] = d["channels"].sort_values(["rank", "location_id", "parameter"]).to_dict("records")
    return d


def md(s, **kw):
    return dcc.Markdown(s, dangerously_allow_html=True, className="md", **kw)


def _table(df, tid, page=12):
    if df is None or df.empty:
        return html.P("None.", className="empty")
    df = df.copy()
    for c in df.columns:
        if str(df[c].dtype).startswith("datetime"):
            df[c] = df[c].dt.strftime("%Y-%m-%d %H:%M")
    df = df.astype(object).where(df.notna(), "")
    return dash_table.DataTable(
        id=tid, data=df.to_dict("records"), columns=[{"name": c.replace("_", " "), "id": c} for c in df.columns], page_size=page, sort_action="native",
        style_table={"overflowX": "auto", "borderRadius": "12px"},
        style_header={"backgroundColor": "var(--raised)", "color": "var(--ink2)", "fontWeight": "600", "border": "0"},
        style_cell={"backgroundColor": "transparent", "color": "var(--ink)", "border": "0", "borderBottom": "1px solid var(--grid)", "padding": "8px 12px",
                    "fontFamily": "inherit", "fontSize": "13px", "textAlign": "left", "minWidth": "70px"})


def _card(title, *children):
    return html.Section([html.H2(title)] + list(children), className="card")


def _head(page, sub):
    return [html.H1(ui.PAGES[page][0], className="pt"), html.P(sub, className="ps")]


def create_app(db_path, cfg=None, default_theme="midnight"):
    cfg = cfg or EnvConfig()
    data = {"d": _load(db_path)}
    default_theme = themes.resolve(default_theme)
    app = Dash(__name__, assets_folder=str(Path(__file__).resolve().parents[2] / "assets"), serve_locally=True,
               title="Mine environment monitor", suppress_callback_exceptions=True)
    css = themes.all_themes_css() + ui.BASE_CSS + ui.icon_mask_css()
    app.index_string = ("<!DOCTYPE html><html lang='en'><head>{%metas%}<title>{%title%}</title>{%favicon%}<style>" + css.replace("{%", "{ %") + "</style>{%css%}</head>"
                        "<body>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer></body></html>")

    nav = []
    for g, items in ui.NAV:
        nav.append(html.Div(g, className="ng"))
        nav += [html.Button([html.Span(className=f"mi mi-{ic}"), html.Span(lab)], id={"type": "nav", "page": p}, n_clicks=0, className="nav" + (" on" if p == "overview" else ""))
                for p, lab, ic in items]

    app.layout = html.Div(id="root", className=f"shell theme-{default_theme}", children=[
        dcc.Store(id="page", data="overview"),
        html.Aside(className="side", children=[
            html.Div(className="brand", children=[md(f'<span class="mark">{ui.icon("logo", 22)}</span>'), html.Div(["Mine Environment", html.Small("Monitor")])]), *nav,
            html.Div(className="side-foot", children=[html.Div("Reporting and visualisation only. Not an alarm or control system.", className="l")])]),
        html.Main(className="main", children=[
            html.Div(className="topbar", children=[
                html.Button(html.Span(className="mi mi-sidebar"), id="menu", n_clicks=0, className="iconbtn", title="Toggle sidebar", **{"aria-label": "Toggle sidebar"}),
                html.Label(className="search", children=[html.Span(className="mi mi-search"), dcc.Input(id="q", type="search", placeholder="Search channels, instruments or locations", debounce=False, value="")]),
                html.Div(className="top-r", children=[html.Span(id="asof", className="asof"),
                                                      html.Label(className="sel", children=[html.Span(className="mi mi-palette"), dcc.Dropdown(
                                                          id="theme", options=[{"label": l, "value": k} for k, l in themes.options()], value=default_theme, clearable=False,
                                                          searchable=False, persistence=True, persistence_type="local", className="theme-dd")]),
                                                      html.Button("Reload data", id="reload", n_clicks=0, className="chip")])]),
            html.Div(id="banners"), html.Div(id="tab-body")])])

    @app.callback(Output("root", "className"), Input("theme", "value"), Input("menu", "n_clicks"))
    def root_class(theme, n):
        return f"shell theme-{themes.resolve(theme)}" + (" collapsed" if (n or 0) % 2 else "")

    @app.callback(Output("page", "data"), Input({"type": "nav", "page": ALL}, "n_clicks"), prevent_initial_call=True)
    def nav_click(_n):
        t = ctx.triggered_id
        return t["page"] if isinstance(t, dict) else no_update

    @app.callback(Output("page", "data", allow_duplicate=True), Input("q", "value"), prevent_initial_call=True)
    def search_goes_to_channels(q):
        return "channels" if q else no_update

    @app.callback(Output({"type": "nav", "page": ALL}, "className"), Input("page", "data"))
    def nav_class(page):
        return ["nav" + (" on" if p == page else "") for g, items in ui.NAV for p, _, _ in items]

    @app.callback(Output("banners", "children"), Output("asof", "children"), Input("reload", "n_clicks"))
    def top(_n):
        if ctx.triggered_id == "reload":
            data["d"] = _load(db_path)
        d = data["d"]
        return md(ui.banners(d["info"].get("demo_criteria") == "True")), f"As-of {d['info'].get('as_of', '?')[:16]} · site time"

    @app.callback(Output("tab-body", "children"), Input("page", "data"), Input("theme", "value"), Input("reload", "n_clicks"))
    def body(page, theme, _n):
        d = data["d"]
        ch = d["channels"]
        if ch.empty:
            return html.Div("No channels in the database. Run run_pipeline.py first.", className="card")
        theme = themes.resolve(theme)
        g = lambda i, f: dcc.Graph(id=i, figure=f, config={"displaylogo": False, "displayModeBar": "hover"}, className="plot")
        if page == "overview":
            levels = sorted(d["locations"]["level"].unique())
            att = [r for r in d["rows"] if r["state"] != "NO_CRITERION_MET"][:14]
            att_html = "".join(f'<div class="att-i"><div><b>{viz.channel_label(r)}</b><small>{r["state_reason"]}</small></div>{ui.pill(r["state"])}</div>' for r in att)
            k = viz.kpis(ch, d["events"], d["instruments"])
            return [*_head("overview", "State of the latest readings by location and level. Runs fully offline."), md(ui.kpi_tiles(k)),
                    html.Div(className="two", children=[
                        html.Section(className="card", children=[html.Div(className="ctl", children=[html.H2("Level map", style={"margin": 0}), dcc.Dropdown(id="level", options=levels, value=levels[0], clearable=False, searchable=False, className="box-dd")]),
                                                                 html.Div(id="map-out"), md(ui.STATUS_KEY)]),
                        html.Section(className="card", children=[html.H2("Needs attention"), md(f'<div class="att">{att_html}</div>' if att else '<p class="empty">Every channel shows "none met". This is not a statement that conditions are safe.</p>')])])]
        if page == "channels":
            counts = ui.filter_counts(ch)
            opts = [{"label": html.Span([lab, html.Span(counts[k], className="n")]), "value": k} for k, lab, _ in ui.FILTERS]
            return [*_head("channels", "Every monitored parameter at every location. Use the search box in the top bar to filter."),
                    html.Section(className="card", children=[dcc.RadioItems(id="chan-filter", options=opts, value="all", inline=True, className="pilltabs"), html.P(id="shown", className="note", style={"margin": "0 0 12px"}), html.Div(id="chan-grid")])]
        if page == "history":
            o = [{"label": f"{viz.channel_label(r)} [{viz.STATE_STYLE[r['state']][2]}]", "value": f"{r['location_id']}|{r['instrument_id']}|{r['parameter']}"} for r in d["rows"]]
            return [*_head("history", "Readings with missing periods shaded, flagged readings marked and the approved review criteria drawn."),
                    html.Section(className="card", children=[html.Div(className="ctl", children=[html.Label("Channel", htmlFor="channel"), dcc.Dropdown(id="channel", options=o, value=o[0]["value"], clearable=False, className="box-dd", style={"minWidth": "min(560px,100%)"})]), html.Div(id="hist-out")])]
        if page == "avail":
            return [*_head("avail", "Grey cells mean no readings were received in that period. They are not a sign that conditions were fine."), html.Section(g("g-avail", viz.fig_availability(d["availability"], theme)), className="card")]
        if page == "events":
            return [*_head("events", "Runs of readings that met a configured review criterion, and periods with no data."), _card("Review events", _table(d["events"], "ev-table")), _card("Missing-data gaps", _table(d["gaps"], "gap-table"))]
        if page == "instr":
            return [*_head("instr", "Instrument register and calibration metadata. UNKNOWN means the metadata was not supplied."), _card("Instruments", _table(d["instruments"], "ins-table"))]
        return [*_head("crit", "Supplied by qualified personnel. This tool never sets or infers limits."), _card("Review criteria", _table(d["criteria"], "crit-table"))]

    @app.callback(Output("chan-grid", "children"), Output("shown", "children"), Input("q", "value"), Input("chan-filter", "value"), Input("reload", "n_clicks"))
    def grid(q, fil, _n):
        d = data["d"]
        sel = dict((k, s) for k, _, s in ui.FILTERS).get(fil)
        rows = [r for r in d["rows"] if sel is None or r["state"] in sel]
        if q and q.strip():
            ln, it = d["locations"].set_index("location_id")["name"].to_dict(), d["instruments"].set_index("instrument_id")["instrument_type"].to_dict()
            ql = q.strip().lower()
            rows = [r for r in rows if ql in " ".join(map(str, (r["location_id"], ln.get(r["location_id"], ""), r["instrument_id"], viz.plabel(r["parameter"]), viz.STATE_STYLE[r["state"]][2], it.get(r["instrument_id"], "")))).lower()]
        if not rows:
            return md('<p class="empty">No channels match. Clear the search box or choose another filter.</p>'), "Showing 0 channels"
        return md(ui.channel_grid(d["channels"], d["locations"], d["instruments"], False, rows)), f"Showing {len(rows)} of {len(d['rows'])} channels"

    @app.callback(Output("map-out", "children"), Input("level", "value"), Input("theme", "value"))
    def map_out(level, theme):
        d = data["d"]
        return dcc.Graph(id="g-map", figure=viz.fig_map(d["locations"], d["channels"], level, themes.resolve(theme)), config={"displaylogo": False, "displayModeBar": "hover"}, className="plot")

    @app.callback(Output("hist-out", "children"), Input("channel", "value"), Input("theme", "value"))
    def hist_out(val, theme):
        d = data["d"]
        loc, ins, par = val.split("|")
        row = d["channels"][(d["channels"].location_id == loc) & (d["channels"].instrument_id == ins) & (d["channels"].parameter == par)].iloc[0].to_dict()
        con = db.connect(db_path)
        try:
            rd = db.readings_for(con, loc, ins, par)
        finally:
            con.close()
        g = d["gaps"]
        g = g[(g.location_id == loc) & (g.instrument_id == ins) & (g.parameter == par)] if len(g) else g
        fig = viz.fig_history(rd, row, viz.criteria_for(d["criteria"], loc, par), g, pd.Timestamp(d["info"]["as_of"]), themes.resolve(theme), cfg.gap_factor)
        return [dcc.Graph(id="g-hist", figure=fig, config={"displaylogo": False, "displayModeBar": "hover"}, className="plot"), md(ui.pill(row["state"])), html.P(row["state_reason"], className="note")]

    return app
