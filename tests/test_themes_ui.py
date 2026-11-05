import re

import pytest

from mineenv import themes, ui, viz
from mineenv.offline_html import build_offline_html
from mineenv.config import EnvConfig


def lum(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def ratio(a, b):
    hi, lo = sorted([lum(a), lum(b)], reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_six_themes_and_legacy_aliases():
    assert len(themes.ORDER) == 6 and set(themes.ORDER) == set(themes.THEMES)
    assert themes.resolve("dark") == "midnight" and themes.resolve("light") == "daylight" and themes.resolve("nonsense") == "midnight"


@pytest.mark.parametrize("name", themes.ORDER)
def test_theme_text_contrast_meets_wcag_aa(name):
    t = themes.THEMES[name]
    for fg, bg in [("ink", "surface"), ("ink2", "surface"), ("muted", "surface"), ("muted", "panel"), ("ink2", "side"), ("muted", "side"),
                   ("ink", "accent_soft"), ("muted", "raised"), ("ink", "raised")]:
        assert ratio(t[fg], t[bg]) >= 4.5, (name, fg, bg)
    assert ratio(t["accent"], t["surface"]) >= 3.0              # accent is used for non-text indicators


@pytest.mark.parametrize("name", themes.ORDER)
def test_all_figures_build_in_every_theme(name, demo_run):
    A = demo_run["A"]
    viz.fig_map(A.locations, A.channels, "1200L", name)
    viz.fig_availability(A.availability, name)
    r = A.channels.iloc[0].to_dict()
    viz.fig_history(A.readings[A.readings.instrument_id == r["instrument_id"]].head(50), r, None, None, A.as_of, name)


def test_status_meaning_never_depends_on_theme():
    # status colours/shapes live only in viz.STATE_STYLE, which has no theme argument; each state has a distinct label
    labels = [v[2] for v in viz.STATE_STYLE.values()]
    assert len(set(labels)) == len(labels)
    assert viz.STATE_STYLE["NO_CRITERION_MET"][1] == "circle" and "open" in viz.STATE_STYLE["STALE"][1]


def test_pills_are_never_colour_only():
    for st in viz.STATE_STYLE:
        h = ui.pill(st)
        assert "<svg" in h and re.search(r">[A-Za-z][^<]+</span>$", h)       # shape glyph + text label


def test_none_met_pill_is_not_the_word_safe():
    assert "safe" not in ui.pill("NO_CRITERION_MET").lower()


def test_offline_html_has_theme_selector_and_cards(demo_run):
    h = build_offline_html(demo_run["A"])
    for n in themes.ORDER:
        assert f'value="{n}"' in h and f'data-t="{n}"' in h
    assert h.count('class="ch clk"') == len(demo_run["A"].channels)
    assert "data-idx=" in h and "Search channels" in h
    assert "aria-label='Theme'" in h


def test_stale_channel_card_shows_unknown_not_safe(demo_run):
    A = demo_run["A"]
    r = A.channels[A.channels.state == "STALE"].iloc[0].to_dict()
    h = ui.channel_card(r)
    assert "Stale" in h and "unknown" in h.lower()


def test_streamlit_app_runs_on_every_page_and_theme():
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    root = Path(__file__).resolve().parents[1]
    if not (root / "outputs" / "environment.sqlite").exists():
        pytest.skip("run run_pipeline.py first")
    at = AppTest.from_file(str(root / "dashboard_streamlit.py"), default_timeout=90).run()
    assert not at.exception
    for page in list(ui.PAGES):
        at.sidebar.radio[0].set_value(page).run()
        assert not at.exception, page
    for th in themes.ORDER:
        at.sidebar.selectbox[0].set_value(th).run()
        assert not at.exception, th
