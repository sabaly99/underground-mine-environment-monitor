"""Colour themes shared by every front end (charts, single-file HTML, Dash, Streamlit).

A theme only changes the look of the interface. The status colours and marker shapes that carry safety meaning
(viz.STATE_STYLE) are identical in every theme, so switching theme can never change what a state means.
"""

ORDER = ["midnight", "daylight", "ocean", "forest", "sand", "contrast"]
ALIASES = {"dark": "midnight", "light": "daylight"}

_LIGHT_SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
_DARK_SERIES = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#2fa35a", "#9085e9", "#e66767"]
_BLUES_LIGHT = ["#cde2fb", "#6da7ec", "#256abf", "#0d366b"]
_BLUES_DARK = ["#184f95", "#2a78d6", "#6da7ec", "#cde2fb"]

THEMES = {
    "midnight": dict(label="Midnight", dark=True, page="#262833", side="#0f1014", panel="#1a1b21", surface="#23242c", raised="#2c2d37",
                     ink="#f2f2f5", ink2="#c4c5d0", muted="#9496a5", grid="#30313c", axis="#434454", accent="#8b7cf6", accent_ink="#12101f", accent_soft="#33305c"),
    "daylight": dict(label="Daylight", dark=False, page="#e6e8f0", side="#ffffff", panel="#f4f5f9", surface="#ffffff", raised="#eceef5",
                     ink="#14151a", ink2="#464856", muted="#666877", grid="#e4e6ee", axis="#c5c8d4", accent="#5646d0", accent_ink="#ffffff", accent_soft="#e8e5fb"),
    "ocean": dict(label="Ocean", dark=True, page="#0a1420", side="#060d15", panel="#0c1a28", surface="#112437", raised="#183249",
                  ink="#eaf3fb", ink2="#b6cadb", muted="#86a0b6", grid="#1d3349", axis="#2d4a66", accent="#38bdf8", accent_ink="#04202e", accent_soft="#0f3a54"),
    "forest": dict(label="Forest", dark=True, page="#0e1510", side="#080d09", panel="#0f1812", surface="#17231b", raised="#20302a",
                   ink="#eef5ef", ink2="#bccdbf", muted="#8aa08d", grid="#27382d", axis="#375040", accent="#5fd48a", accent_ink="#06200f", accent_soft="#1c3d28"),
    "sand": dict(label="Sand", dark=False, page="#ebe4d6", side="#fbf8f2", panel="#f6f1e7", surface="#fffdf9", raised="#f0eadc",
                 ink="#201c16", ink2="#4f4a40", muted="#6f685a", grid="#e8e1d3", axis="#cdc3ae", accent="#a8480a", accent_ink="#ffffff", accent_soft="#fbe6d0"),
    "contrast": dict(label="High contrast", dark=True, page="#000000", side="#000000", panel="#000000", surface="#0b0b0b", raised="#1c1c1c",
                     ink="#ffffff", ink2="#f0f0f0", muted="#d0d0d0", grid="#5c5c5c", axis="#a0a0a0", accent="#ffd60a", accent_ink="#000000", accent_soft="#3d3400"),
}
for _t in THEMES.values():
    _t["series"] = [_t["accent"]] + (_DARK_SERIES if _t["dark"] else _LIGHT_SERIES)[1:]
    _t["heat"] = _BLUES_DARK if _t["dark"] else _BLUES_LIGHT
    _t["nodata"] = "#5a5b66" if _t["dark"] else "#c3c2b7"

_VARS = ["page", "side", "panel", "surface", "raised", "ink", "ink2", "muted", "grid", "axis", "accent", "accent_ink", "accent_soft"]


def resolve(name):
    name = ALIASES.get(name, name)
    return name if name in THEMES else "midnight"


def get(name):
    return THEMES[resolve(name)]


def options():
    return [(k, THEMES[k]["label"]) for k in ORDER]


def _decl(t):
    return "".join(f"--{k.replace('_', '-')}:{t[k]};" for k in _VARS) + f"color-scheme:{'dark' if t['dark'] else 'light'};--bw:{'2px' if t is THEMES['contrast'] else '1px'};--demo:{'#ff6b6f' if t['dark'] else '#b42318'};"


def root_css(name):
    """CSS for one theme applied to :root (used by Streamlit, which cannot set attributes on its page)."""
    return ":root{" + _decl(get(name)) + "}"


def all_themes_css():
    """CSS for every theme, selectable with data-theme="name" or class "theme-name" on any ancestor."""
    out = []
    for k in ORDER:
        sel = f'[data-theme="{k}"],.theme-{k}' + (',:root:not([data-theme])' if k == "midnight" else "")
        out.append(sel + "{" + _decl(THEMES[k]) + "}")
    return "\n".join(out)


def js_tokens():
    keys = ["label", "dark", "surface", "ink", "ink2", "muted", "grid", "axis", "accent", "series"]
    return {k: {x: THEMES[k][x] for x in keys} for k in ORDER}
