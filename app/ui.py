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
import json
import re
from pathlib import Path

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


def funnel(steps) -> str:
    """A strip of big figures on one panel, the main figure at the top of a page. Each step is
    (figure, label, note, colour, bar): figure is a number or text; bar is a share 0..1 drawn as a thin bar,
    a list of (share, colour) drawn as one stacked bar, or None for no bar."""
    p = pal()
    cells = []
    for i, (figure, label, note, color, bar) in enumerate(steps):
        fig = f"{figure:,}" if isinstance(figure, (int, float)) and not isinstance(figure, bool) else str(figure)
        if bar is None:
            bar_html = f"<div style='height:4px;margin-top:12px'></div>"
        else:
            segs = bar if isinstance(bar, (list, tuple)) else [(bar, color)]
            inner = "".join(f"<div style='width:{max(0.0, min(1.0, sh)) * 100:.2f}%;min-width:{4 if sh > 0 else 0}px;"
                            f"height:4px;background:{c}'></div>" for sh, c in segs)
            bar_html = (f"<div style='display:flex;gap:2px;height:4px;background:{p['TRACK']};border-radius:2px;"
                        f"overflow:hidden;margin-top:12px'>{inner}</div>")
        dot = f"<span style='width:8px;height:8px;border-radius:2px;background:{color}'></span>" if color else ""
        cells.append(
            f"<div style='flex:1 1 200px;padding:20px 24px;border-left:{'none' if i == 0 else '1px solid ' + p['HAIRLINE']}'>"
            f"<div style='display:flex;align-items:center;gap:8px;font-size:14px;color:{p['INK_2']}'>{dot}{label}</div>"
            f"<div style='font-family:{MONO};font-size:32px;line-height:40px;font-weight:500;color:{p['INK']};"
            f"margin-top:8px;font-variant-numeric:tabular-nums;white-space:nowrap'>{fig}</div>"
            f"{bar_html}"
            f"<div style='font-size:13px;line-height:1.5;color:{p['MUTED']};margin-top:12px'>{note}</div></div>")
    return (f"<div style='display:flex;flex-wrap:wrap;background:{p['PANEL']};border:1px solid {p['HAIRLINE']};"
            f"border-radius:14px;overflow:hidden'>" + "".join(cells) + "</div>")


def _num(text: str) -> float | None:
    m = re.search(r"-?[\d,]*\.?\d+", text or "")
    return float(m.group(0).replace(",", "")) if m else None


def reason_compare(reason: str, color: str | None = None) -> str:
    """One reason drawn as a comparison: 'Share of money in match hours: 57% vs 10% for similar kirana stores'
    becomes the signal name, then two bars (this merchant, similar shops) with the figures. Plain text if the
    reason has no 'A vs B for ...' shape."""
    p = pal()
    m = re.match(r"^(.*?):\s*(.+?)\s+vs\s+(.+?)\s+for\s+(.*)$", reason or "")
    a, b = (_num(m.group(2)), _num(m.group(3))) if m else (None, None)
    if not m or a is None or b is None:
        return f"<div style='font-size:14px;line-height:1.5;color:{p['INK']};padding:12px 0'>{html.escape(reason or '')}</div>"
    title, a_txt, b_txt, peers = (html.escape(x) for x in m.groups())
    top = max(abs(a), abs(b)) or 1
    color = color or p["LEVEL_COLOR"][3]
    rows = ""
    for label, txt, v, c in (("This merchant", a_txt, a, color), ("Similar shops", b_txt, b, p["NEUTRAL_BAR"])):
        rows += (f"<div style='display:grid;grid-template-columns:104px 1fr 120px;align-items:center;gap:12px;margin-top:8px'>"
                 f"<span style='font-size:12px;color:{p['INK_2']}'>{label}</span>"
                 f"<div style='height:8px;background:{p['TRACK']};border-radius:4px'>"
                 f"<div style='width:{abs(v) / top * 100:.1f}%;min-width:4px;height:8px;background:{c};border-radius:4px'></div></div>"
                 f"<span style='font-family:{MONO};font-size:12px;color:{p['INK']};text-align:right;white-space:nowrap;"
                 f"font-variant-numeric:tabular-nums'>{txt}</span></div>")
    return (f"<div style='padding:16px 0;border-top:1px solid {p['HAIRLINE']}'>"
            f"<div style='font-size:14px;font-weight:500;color:{p['INK']}'>{title}</div>{rows}"
            f"<div style='font-size:12px;color:{p['MUTED']};margin-top:8px'>Against {peers}</div></div>")


def risk_scale(score: float, ask: float, friction: float, review: float, level: int) -> str:
    """Where a merchant's risk score sits on 0-100, over the ladder's bands (Monitor, Ask, Friction, Review)."""
    p = pal()
    lc = p["LEVEL_COLOR"]
    s = max(0.0, min(100.0, float(score)))
    bands = [(0, ask, lc[0]), (ask, friction, lc[1]), (friction, review, lc[2]), (review, 100, lc[3])]
    segs = "".join(f"<div style='position:absolute;left:{lo}%;width:{hi - lo}%;top:0;bottom:0;background:{c};"
                   f"opacity:{0.9 if lo <= s < hi or (hi == 100 and s >= lo) else 0.25}'></div>" for lo, hi, c in bands)
    ticks = "".join(f"<span style='position:absolute;left:{t}%;transform:translateX(-50%);font-family:{MONO};"
                    f"font-size:11px;color:{p['MUTED']}'>{t:.0f}</span>" for t in (ask, friction, review))
    names = "".join(f"<span style='position:absolute;left:{(lo + hi) / 2}%;transform:translateX(-50%);font-size:11px;"
                    f"color:{p['INK_2'] if lo <= s < hi or (hi == 100 and s >= lo) else p['MUTED']};white-space:nowrap'>"
                    f"{LEVEL_NAME[i]}</span>" for i, (lo, hi, _) in enumerate(bands))
    marker = (f"<div style='position:absolute;left:{s}%;top:-6px;width:2px;height:20px;background:{p['INK']};"
              f"transform:translateX(-1px);border-radius:1px'></div>")
    return (f"<div style='position:relative;height:16px;margin-top:4px'>{names}</div>"
            f"<div style='position:relative;height:8px;border-radius:4px;overflow:visible;margin-top:8px'>"
            f"<div style='position:absolute;inset:0;border-radius:4px;overflow:hidden'>{segs}</div>{marker}</div>"
            f"<div style='position:relative;height:16px;margin-top:8px'>{ticks}</div>")


def clock_rows(rows) -> str:
    """Open cases against their deadline: label, meta, and a bar for the share of the allowed time used.
    Each row is (label, meta, used 0..1+, text on the right); past the deadline the bar turns red."""
    p = pal()
    out = []
    for label, meta, used, right in rows:
        over = used >= 1
        color = p["LEVEL_COLOR"][4] if over else p["LEVEL_COLOR"][2] if used >= 2 / 3 else p["ACCENT"]
        out.append(
            "<div style='padding:12px 0;border-top:1px solid " + p["HAIRLINE"] + "'>"
            "<div style='display:flex;justify-content:space-between;gap:16px;font-size:14px'>"
            f"<span style='color:{p['INK']}'>{label} <span style='color:{p['MUTED']}'>{meta}</span></span>"
            f"<span style='font-family:{MONO};font-size:13px;color:{color if over else p['INK_2']};"
            f"font-variant-numeric:tabular-nums'>{right}</span></div>"
            f"<div style='height:4px;background:{p['TRACK']};border-radius:2px;margin-top:8px'>"
            f"<div style='width:{min(1.0, max(0.0, used)) * 100:.1f}%;min-width:4px;height:4px;background:{color};"
            f"border-radius:2px'></div></div></div>")
    return "".join(out)


ASSETS = Path(__file__).resolve().parent / "assets"


def how_trace_decides(d) -> str:
    """Home's animated 'How Trace decides' panel (app/assets/how_trace_decides.html), filled with live numbers:
    the top flagged merchant against similar shops, how many merchants are linked and in how many clusters, and
    how many merchants sit on each step of the ladder. Plays once on load; click it to replay."""
    shop, peers, label, cap = 57.0, 10.0, "Example shop", "Share of takings in cricket match hours"
    for r in d[d.level >= 1].sort_values("risk_score", ascending=False).itertuples():
        m = re.search(r"^(.*?):\s*([\d.]+)%\s*vs\s*([\d.]+)%", str(r.reason_1 or ""))
        if m:
            shop, peers, cap = float(m.group(2)), float(m.group(3)), m.group(1)
            label = f"{r.merchant_id}, {str(r.category).replace('_', ' ')}"
            break
    linked = d[d.network_link.fillna(False).astype(bool)] if "network_link" in d else d.iloc[:0]
    clusters = linked.cluster.nunique() if "cluster" in linked else 0
    counts = d.level.value_counts()
    n, calm = len(d), int(counts.get(0, 0))
    esc = lambda x: json.dumps(html.escape(str(x)))  # noqa: E731  safe inside the page's JavaScript
    page = (ASSETS / "how_trace_decides.html").read_text()
    values = {"__PEER_CAP__": esc(cap), "__LINK_CAP__": esc(f"{len(linked):,} merchants linked, in {clusters:,} clusters"),
              "__LADDER_CAP__": esc(f"{calm:,} of {n:,} merchants see no action at all"),
              "__SHOP_LABEL__": esc(label), "__SHOP_VAL__": f"{shop:g}", "__PEERS_VAL__": f"{peers:g}"}
    values.update({f"__N{i}__": str(int(counts.get(i, 0))) for i in range(5)})
    for k, v in values.items():
        page = page.replace(k, v)
    return page


def intro():
    """The opening animation (app/assets/trace_intro.html): the Trace mark draws in, the name slides out beside it,
    then the dark overlay fades away after about 3.6 seconds. Shown once per visit (a reload counts as a new visit),
    so moving between pages doesn't replay it. It also covers the first few seconds while the data loads."""
    if st.session_state.get("_intro_shown"):
        return
    st.session_state._intro_shown = True
    # st.html would strip the SVG mark, so use markdown; without blank lines or indentation it reads the whole
    # thing as one block of HTML instead of mistaking indented CSS for code
    page = "\n".join(line.strip() for line in (ASSETS / "trace_intro.html").read_text().splitlines() if line.strip())
    st.markdown(page, unsafe_allow_html=True)
