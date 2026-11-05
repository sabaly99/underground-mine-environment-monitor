import re
import sqlite3

import pytest

from mineenv import database as db, viz
from mineenv.report import build_report
from mineenv.offline_html import build_offline_html
from mineenv.manual_entry import build_form
from mineenv.dash_app import create_app
from mineenv.config import EnvConfig


@pytest.fixture(scope="module")
def stored(demo_run, tmp_path_factory):
    p = tmp_path_factory.mktemp("db") / "t.sqlite"
    con = db.connect(p)
    A = demo_run["A"]
    n1 = db.upsert_raw(con, demo_run["parsed"])
    n2 = db.upsert_raw(con, demo_run["parsed"])
    db.store_analysis(con, A, demo_run["cfg"])
    con.close()
    return dict(path=p, n1=n1, n2=n2)


def test_demo_scenarios_present(demo_run):
    A = demo_run["A"]
    def st(i, p="co"):
        return set(A.channels[(A.channels.instrument_id == i) & (A.channels.parameter == p)].state)
    assert st("GM-05") == {"CRITERION_MET"}
    assert st("GM-04") == {"STALE"}
    assert st("GM-06") == {"OUT_OF_SERVICE"}
    assert len(A.events) == 3 and int(A.events.active.sum()) == 1
    assert A.locations.set_index("location_id").loc["REF1", "state"] == "NO_DATA"
    assert (A.gaps.minutes >= 9 * 60).any()                       # 9 h outage on GM-03


def test_db_idempotent(stored):
    assert stored["n1"] > 1000 and stored["n2"] == 0


def test_db_roundtrip_tables(stored, demo_run):
    con = db.connect(stored["path"])
    ch = db.read(con, "channels")
    assert len(ch) == len(demo_run["A"].channels)
    assert db.run_info(con)["demo_criteria"] == "True"
    con.close()


def test_report_contains_safety_and_demo_banners(demo_run):
    A = demo_run["A"]
    h = build_report(A, lambda l, i, p: A.readings[(A.readings.location_id == l) & (A.readings.instrument_id == i) & (A.readings.parameter == p)], "Test")
    low = h.lower()
    assert "not an alarm" in low or "not a replacement" in low
    assert "demonstration" in low
    assert "unknown" in low


def test_offline_html_is_self_contained(demo_run):
    h = build_offline_html(demo_run["A"])
    markup = re.sub(r"<script>.*?</script>", "", h, flags=re.S)       # plotly.js text mentions URLs in comments; check the real markup
    assert not re.search(r'(src|href)\s*=\s*["\']?https?://', markup)
    assert "<script src" not in h
    assert "<link" not in h
    assert "not an alarm" in h.lower() and "unknown, not safe" in h.lower()


def test_manual_form_has_instruments_and_no_external_urls(demo_run):
    h = build_form(demo_run["I"], demo_run["L"], "T")
    for iid in ("AN-01", "GM-01", "HH-01"):
        assert iid in h
    assert not re.search(r'(src|href)\s*=\s*["\']https?://', h)
    assert "<script src" not in h


def test_dash_app_serves_locally_and_callbacks(stored):
    app = create_app(stored["path"], EnvConfig())
    assert app.config.serve_locally
    c = app.server.test_client()
    assert c.get("/").status_code == 200
    layout = c.get("/_dash-layout").get_json()
    assert "Mine Environment" in str(layout) and "Mine environment monitor" in c.get("/").get_data(as_text=True)
    assert c.get("/_dash-component-suites/plotly/package_data/plotly.min.js").status_code == 200

    def call(outputs, inputs, out_id):
        body = {"output": outputs, "outputs": out_id, "inputs": inputs, "changedPropIds": []}
        r = c.post("/_dash-update-component", json=body)
        assert r.status_code == 200, r.get_data(as_text=True)[:300]
        return r.get_json()

    th = lambda v: {"id": "theme", "property": "value", "value": v}
    for page in ("overview", "channels", "history", "avail", "events", "instr", "crit"):
        for theme in ("midnight", "daylight"):
            j = call("tab-body.children", [{"id": "page", "property": "data", "value": page}, th(theme), {"id": "reload", "property": "n_clicks", "value": 0}],
                     {"id": "tab-body", "property": "children"})
            assert j["response"]["tab-body"]["children"]
    j = call("hist-out.children", [{"id": "channel", "property": "value", "value": "B102|GM-05|co"}, th("ocean")], {"id": "hist-out", "property": "children"})
    assert "g-hist" in str(j) and "Criterion met" in str(j)
    j = call("map-out.children", [{"id": "level", "property": "value", "value": "1200L"}, th("forest")], {"id": "map-out", "property": "children"})
    assert "g-map" in str(j)
    j = call("..chan-grid.children...shown.children..", [{"id": "q", "property": "value", "value": "gm-04"}, {"id": "chan-filter", "property": "value", "value": "all"},
                                                         {"id": "reload", "property": "n_clicks", "value": 0}],
             [{"id": "chan-grid", "property": "children"}, {"id": "shown", "property": "children"}])
    assert "Showing 2 of 33" in str(j)
    j = call("..chan-grid.children...shown.children..", [{"id": "q", "property": "value", "value": ""}, {"id": "chan-filter", "property": "value", "value": "missing"},
                                                         {"id": "reload", "property": "n_clicks", "value": 0}],
             [{"id": "chan-grid", "property": "children"}, {"id": "shown", "property": "children"}])
    assert "Showing 5 of 33" in str(j)


def test_map_marks_missing_differently_from_ok(stored):
    con = db.connect(stored["path"])
    fig = viz.fig_map(db.read(con, "locations"), db.read(con, "channels"), "1200L")
    con.close()
    syms = {t.name: t.marker.symbol for t in fig.data if t.marker and t.name}
    ok = [s for n, s in syms.items() if "no configured criterion" in n.lower() and "latest" in n.lower()]
    assert ok and all(s == "circle" for s in ok)
    for n, s in syms.items():
        if "stale" in n.lower() or n.lower().startswith("no data"):
            assert s != "circle"


def test_root_scripts_have_config_and_no_cli_args():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    for f in ("run_pipeline.py", "make_demo_data.py", "make_manual_entry_form.py", "dashboard_dash.py", "dashboard_streamlit.py"):
        t = (root / f).read_text()
        assert "CONFIG" in t and "argparse" not in t and "sys.argv" not in t, f
