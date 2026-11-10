"""Shared look: palettes for light and dark, chart theme, ladder colours and the 'ladder pips' signature.

Design pass after unslop by Damir Sokolovsky (@heydamir, CC BY 4.0):
quiet graphite chrome, sections on soft raised panels, one cobalt accent, colour only where it means
something.

The app is dark for everyone; the light palette is kept for a future light theme.
Colours are looked up per session when something is drawn, so two viewers on different themes
never affect each other: `ui.ACCENT`, `ui.INK` etc. always return the current viewer's palette.
"""
from __future__ import annotations

import html

import altair as alt
import streamlit as st

MONO = "IBM Plex Mono, ui-monospace, monospace"
SANS = "IBM Plex Sans, system-ui, sans-serif"
LEVEL_NAME = {0: "Monitor", 1: "Ask", 2: "Friction", 3: "Review", 4: "Offboard"}

# graphite ramp, dark (the default) and light. PANEL is the raised surface a section sits on, one step
# lighter than the page; HAIRLINE is its edge. The ladder colours step from quiet to serious.
PALETTES = {
    "dark": {
        "INK": "#ededef", "INK_2": "#a1a1a8", "MUTED": "#85858d",
        "BG": "#111113", "PANEL": "#1a1a1d", "RAISED": "#222226", "HAIRLINE": "#2a2a2f",
        "TRACK": "#2c2c31", "BAND": "#222226", "ACTIVE": "#232327",
        "ACCENT": "#5b93d9", "NEUTRAL_BAR": "#4a4a51", "EDGE": "#3a3a40", "GOOD": "#4cc38a",
        "LEVEL_COLOR": {0: "#76767e", 1: "#5b93d9", 2: "#d08a3a", 3: "#e0703f", 4: "#d05a5a"},
    },
    "light": {
        "INK": "#1c1c1f", "INK_2": "#56565e", "MUTED": "#6e6e76",
        "BG": "#f5f5f7", "PANEL": "#ffffff", "RAISED": "#ececef", "HAIRLINE": "#e2e2e6",
        "TRACK": "#e8e8ec", "BAND": "#efeff2", "ACTIVE": "#dedee3",
        "ACCENT": "#1f5fae", "NEUTRAL_BAR": "#bdbdc4", "EDGE": "#cbcbd1", "GOOD": "#16a34a",
        "LEVEL_COLOR": {0: "#9a9aa2", 1: "#1f5fae", 2: "#b45309", 3: "#c2410c", 4: "#7f1d1d"},
    },
}


def mode() -> str:
    """The palette to draw with. The app is dark for everyone (.streamlit/config.toml), and Streamlit reports
    the browser's own light/dark setting rather than the app's, so this stays dark. The light palette is kept
    for printing or a future light theme."""
    return "dark"


def pal() -> dict:
    return PALETTES[mode()]


def __getattr__(name: str):
    """ui.ACCENT, ui.INK, ui.LEVEL_COLOR ... resolve to the current viewer's palette."""
    p = PALETTES[mode()]
    if name in p:
        return p[name]
    raise AttributeError(name)


# Chart structure only: fonts, sizes, no frame. Colours of text and grid come from Streamlit's own
# chart theme, which already follows light/dark; mark colours are set per chart from pal().
@alt.theme.register("trace", enable=True)
def _chart_theme() -> alt.theme.ThemeConfig:
    return {
        "config": {
            "font": SANS,
            "background": "transparent",
            "view": {"stroke": None},
            "axis": {"labelFont": MONO, "labelFontSize": 11, "labelLimit": 260, "titleFont": SANS,
                     "titleFontSize": 12, "titleFontWeight": 400, "domain": False, "ticks": False, "labelPadding": 6},
            "legend": {"labelFont": SANS, "labelFontSize": 12, "titleFontWeight": 400, "symbolType": "circle",
                       "symbolSize": 60},
            "line": {"strokeWidth": 2},
            "text": {"font": MONO, "fontSize": 11},
        }
    }


def pips(level: int, label: bool = True) -> str:
    """The signature: five small steps showing where a merchant sits on the ladder."""
    p = pal()
    level = int(level)
    color = p["LEVEL_COLOR"][level]
    cells = "".join(
        f"<span style='display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:3px;"
        f"background:{color if i <= level else p['TRACK']}'></span>"
        for i in range(5))
    text = (f"<span style='margin-left:6px;font-size:14px;font-weight:500;color:{color if level else p['INK_2']}'>"
            f"{LEVEL_NAME[level]}</span>") if label else ""
    return f"<span style='display:inline-flex;align-items:center;vertical-align:middle' title='{LEVEL_NAME[level]}'>{cells}{text}</span>"


def style(current: str = ""):
    """Finishing touches the theme can't express: panels, soft corners, the sidebar.

    `current` is the open page's address, so its sidebar row gets the highlight."""
    p = pal()
    st.markdown(
        f"""<style>
        [data-testid="stMainBlockContainer"] {{ padding-top: 48px; max-width: 1440px; }}
        h1 {{ letter-spacing: -0.01em; }}
        [data-testid="stCaptionContainer"] {{ color: {p['MUTED']}; }}

        /* sections sit on soft raised panels (ui.panel), one step lighter than the page */
        [class*="st-key-panel_"], [data-testid="stForm"] {{
            background: {p['PANEL']}; border: 1px solid {p['HAIRLINE']} !important;
            border-radius: 14px !important; padding: 20px 24px !important; }}
        [class*="st-key-panel_"] h5 {{ padding-top: 0; }}

        /* figures: each metric is a small card */
        [data-testid="stMetric"] {{ background: {p['PANEL']}; border: 1px solid {p['HAIRLINE']};
            border-radius: 12px; padding: 16px 20px; height: 100%; }}
        [class*="st-key-panel_"] [data-testid="stMetric"] {{ background: {p['RAISED']}; border-color: transparent;
            border-radius: 10px; padding: 12px 16px; }}
        [data-testid="stMetricValue"] {{ font-variant-numeric: tabular-nums; font-family: {MONO}; }}
        [data-testid="stMetricLabel"] p {{ color: {p['INK_2']}; }}
        [data-testid="stMetricLabel"] div, [data-testid="stMetricLabel"] p {{ white-space: normal !important;
            overflow: visible !important; text-overflow: clip !important; }}

        /* tables, expanders, notices: same soft corners */
        [data-testid="stDataFrame"] > div {{ border-radius: 12px; overflow: hidden; }}
        [data-testid="stExpander"] details {{ background: {p['PANEL']}; border-color: {p['HAIRLINE']};
            border-radius: 12px; }}
        [data-testid="stAlert"] > div {{ border-radius: 10px; }}

        /* sidebar: a wordmark, a small search, dense rows with a soft grey highlight */
        /* Streamlit keeps an empty 56px band at the top for its collapse button; float the button in the
           top-right corner instead, so the logo can sit at the top beside it */
        [data-testid="stSidebarHeader"] {{ position: absolute; top: 0; right: 16px; width: auto; height: 56px;
            z-index: 2; }}
        [data-testid="stSidebarUserContent"] {{ padding-top: 14px; }}
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{ gap: 2px; }}
        .st-key-nav_search {{ margin: 24px 0 12px; }}
        .st-key-nav_search [data-testid="stTextInputRootElement"] {{ height: 32px; min-height: 32px;
            background: {p['PANEL']}; border: 1px solid {p['HAIRLINE']}; border-radius: 8px; }}
        .st-key-nav_search input {{ font-size: 13px; background: transparent; }}
        [data-testid="stSidebar"] [data-testid="stElementContainer"]:has([data-testid="stPageLink"]) {{ margin: 0; }}
        [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] {{ height: 32px; min-height: 32px; margin: 0;
            padding: 0 8px; border-radius: 8px; background: transparent; transition: background-color 120ms ease-out; }}
        [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover {{ background: {p['PANEL']}; }}
        [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] p {{ font-size: 14px; font-weight: 400; }}
        [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] span {{ color: {p['INK_2']}; }}
        [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][href="{current}"] {{
            background: {p['ACTIVE']}; box-shadow: inset 0 0 0 1px {p['HAIRLINE']}; }}
        [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][href="{current}"] span,
        [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][href="{current}"] p {{ color: {p['INK']}; }}
        /* each section starts under a thin grey line, so the groups read apart */
        .nav-label {{ font-size: 12px; line-height: 16px; color: {p['MUTED']}; padding: 16px 8px 4px;
            margin-top: 12px; border-top: 1px solid {p['HAIRLINE']}; }}
        .nav-rule {{ height: 1px; background: {p['HAIRLINE']}; margin: 12px 0 16px; }}
        [data-testid="stMarkdownContainer"]:has(> .nav-label),
        [data-testid="stMarkdownContainer"]:has(> .wordmark),
        [data-testid="stMarkdownContainer"]:has(> .nav-rule) {{ margin-bottom: 0; }}
        </style>""",
        unsafe_allow_html=True,
    )


def wordmark() -> str:
    """The logo: a flat mark in one solid colour, then the name. The mark is two linked merchants, a big one
    and a small one tied to it, for what Trace does: follow the links between accounts."""
    p = pal()
    mark = (f"<svg width='22' height='22' viewBox='0 0 18 18' fill='{p['INK']}' aria-hidden='true'>"
            f"<path d='M6 12.5 13.5 5' stroke='{p['INK']}' stroke-width='2.5' stroke-linecap='round'/>"
            "<circle cx='6' cy='12' r='4.5'/><circle cx='14' cy='4.5' r='3'/></svg>")
    return (f"<div class='wordmark' style='display:flex;align-items:center;gap:10px;height:28px;padding:0 8px'>"
            f"{mark}<span style='font-size:20px;line-height:28px;font-weight:500;letter-spacing:-0.01em;"
            f"color:{p['INK']}'>Trace</span></div>")


def panel(key: str):
    """A section on a soft raised panel. Use as `with ui.panel("overview_trend"):` (keys unique per page)."""
    return st.container(key=f"panel_{key}")


# lucide line icons (stroke 1.5) for the few places that render raw HTML
def lucide(name: str, size: int = 16, color: str | None = None) -> str:
    color = color or pal()["INK_2"]
    paths = {
        "check": "<path d='M20 6 9 17l-5-5'/>",
        "alert": "<path d='m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3'/>"
                 "<path d='M12 9v4'/><path d='M12 17h.01'/>",
    }[name]
    return (f"<svg width='{size}' height='{size}' viewBox='0 0 24 24' fill='none' stroke='{color}' stroke-width='1.5' "
            f"stroke-linecap='round' stroke-linejoin='round' style='vertical-align:-3px'>{paths}</svg>")


def bar_list(rows, fmt="{:,}", accent_first: bool = True, max_value=None) -> str:
    """A ranked list with thin bars: label, figure, and a thin bar (one accent, the rest neutral)."""
    p = pal()
    rows = list(rows)
    top = max_value or max((v for _, v in rows), default=1) or 1
    out = []
    for i, (label, v) in enumerate(rows):
        color = p["ACCENT"] if (accent_first and i == 0) else p["NEUTRAL_BAR"]
        w = max(0.0, min(1.0, v / top)) * 100
        out.append(
            "<div style='padding:8px 0'>"
            "<div style='display:flex;justify-content:space-between;gap:16px;font-size:14px'>"
            f"<span style='color:{p['INK']}'>{label}</span>"
            f"<span style='font-family:{MONO};color:{p['INK_2']};font-variant-numeric:tabular-nums'>{fmt.format(v)}</span></div>"
            f"<div style='height:4px;background:{p['TRACK']};border-radius:2px;margin-top:6px'>"
            f"<div style='width:{w:.1f}%;height:4px;background:{color};border-radius:2px'></div></div></div>")
    return "".join(out)


def ladder_list(counts: dict, describe: bool = True) -> str:
    """Counts per ladder step, with the pips signature."""
    p = pal()
    what = {0: "nothing visible", 1: "a neutral question", 2: "lower limits, T+2 settlement",
            3: "20% reserve and an investigator", 4: "closed after a human confirms"}
    rows = []
    for lvl in range(5):
        rows.append(f"<div style='display:flex;align-items:center;justify-content:space-between;gap:16px;"
                    f"padding:10px 0;border-bottom:1px solid {p['HAIRLINE']}'>"
                    f"<div style='display:flex;align-items:center;gap:12px'>{pips(lvl)}"
                    + (f"<span style='color:{p['MUTED']};font-size:14px'>{what[lvl]}</span>" if describe else "") + "</div>"
                    f"<span style='font-family:{MONO};font-size:15px;color:{p['INK']}'>{int(counts.get(lvl, 0)):,}</span></div>")
    return "".join(rows)


def queue_preview(rows) -> str:
    """A few merchants from the top of the queue: ID and declared shop, the main reason, and the pips."""
    p = pal()
    out = []
    for i, r in enumerate(rows.itertuples()):
        shop = f"{str(r.category).replace('_', ' ').capitalize()} · {r.city}"
        reason = html.escape(str(r.reason_1 or "")) or "Network or account change only"
        border = "none" if i == 0 else f"1px solid {p['HAIRLINE']}"
        out.append(
            f"<div style='display:flex;flex-wrap:wrap;align-items:center;gap:8px 24px;padding:16px 20px;border-top:{border}'>"
            f"<div style='width:160px'><div style='font-family:{MONO};font-size:14px;color:{p['INK']}'>{r.merchant_id}</div>"
            f"<div style='font-size:13px;color:{p['MUTED']};margin-top:2px'>{shop}</div></div>"
            f"<div style='flex:1;min-width:240px;font-size:14px;line-height:1.5;color:{p['INK_2']}'>{reason}</div>"
            f"<div style='width:132px'>{pips(int(r.level))}</div></div>")
    return (f"<div style='background:{p['PANEL']};border:1px solid {p['HAIRLINE']};border-radius:14px;overflow:hidden'>"
            + "".join(out) + "</div>")


def principles(items) -> str:
    """Home's three ideas: one panel, three equal columns split by hairlines, a title and a line each."""
    p = pal()
    cells = []
    for i, (title, text) in enumerate(items):
        cells.append(
            f"<div style='flex:1 1 220px;padding:20px 24px;border-left:{'none' if i == 0 else '1px solid ' + p['HAIRLINE']}'>"
            f"<div style='font-family:{MONO};font-size:12px;color:{p['MUTED']}'>{i + 1:02d}</div>"
            f"<div style='font-size:15px;font-weight:500;color:{p['INK']};margin-top:8px'>{title}</div>"
            f"<div style='font-size:14px;line-height:1.55;color:{p['INK_2']};margin-top:4px'>{text}</div></div>")
    return (f"<div style='display:flex;flex-wrap:wrap;background:{p['PANEL']};border:1px solid {p['HAIRLINE']};"
            f"border-radius:14px;overflow:hidden'>" + "".join(cells) + "</div>")
