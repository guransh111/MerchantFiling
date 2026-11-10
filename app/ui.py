"""Shared look: palettes for light and dark, chart theme, ladder colours and the 'ladder pips' signature.

Design pass after unslop by Damir Sokolovsky (@heydamir, CC BY 4.0):
quiet ink-grey chrome, one cobalt accent, colour only where it means something.

Light or dark follows the viewer's choice (menu ⋮ → Settings → Theme, or their system setting).
Colours are looked up per session when something is drawn, so two viewers on different themes
never affect each other: `ui.ACCENT`, `ui.INK` etc. always return the current viewer's palette.
"""
from __future__ import annotations

import altair as alt
import streamlit as st

MONO = "IBM Plex Mono, ui-monospace, monospace"
SANS = "IBM Plex Sans, system-ui, sans-serif"
LEVEL_NAME = {0: "Monitor", 1: "Ask", 2: "Friction", 3: "Review", 4: "Offboard"}

# ink ramp, light and dark (unslop tokens). The ladder colours step from quiet to serious.
PALETTES = {
    "light": {
        "INK": "#111827", "INK_2": "#4b5565", "MUTED": "#6b7487",
        "HAIRLINE": "#e3e7ee", "RAISED": "#f4f6f9", "TRACK": "#eef1f5", "BAND": "#f1f3f7",
        "ACCENT": "#1f5fae", "NEUTRAL_BAR": "#b8bfcc", "EDGE": "#c9ced8", "GOOD": "#16a34a", "BG": "#ffffff",
        "LEVEL_COLOR": {0: "#9aa3b2", 1: "#1f5fae", 2: "#b45309", 3: "#c2410c", 4: "#7f1d1d"},
    },
    "dark": {
        "INK": "#eef0f5", "INK_2": "#a3a9b8", "MUTED": "#8a91a3",
        "HAIRLINE": "#262b36", "RAISED": "#1a1e28", "TRACK": "#1f2430", "BAND": "#161a23",
        "ACCENT": "#5b93d9", "NEUTRAL_BAR": "#4a5263", "EDGE": "#3a4150", "GOOD": "#4cc38a", "BG": "#0b0d14",
        "LEVEL_COLOR": {0: "#6b7385", 1: "#5b93d9", 2: "#d08a3a", 3: "#e0703f", 4: "#d05a5a"},
    },
}


def mode() -> str:
    """'dark' or 'light' for the current viewer (light until the browser has told us)."""
    try:
        t = st.context.theme.type
    except Exception:  # outside a Streamlit run (tests, scripts)
        t = None
    return "dark" if t == "dark" else "light"


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


def style():
    """Small finishing touches the theme can't express."""
    p = pal()
    st.markdown(
        f"""<style>
        [data-testid="stMetricValue"] {{ font-variant-numeric: tabular-nums; }}
        [data-testid="stMetricLabel"] p {{ color: {p['INK_2']}; }}
        [data-testid="stCaptionContainer"] {{ color: {p['MUTED']}; }}
        h1 {{ letter-spacing: -0.01em; }}
        </style>""",
        unsafe_allow_html=True,
    )


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


def ladder_strip(counts: dict) -> str:
    """The ladder at a glance, in one row: pips, step name and how many merchants sit there."""
    p = pal()
    cells = []
    for lvl in range(5):
        color = p["LEVEL_COLOR"][lvl] if lvl else p["INK_2"]
        cells.append(
            f"<div style='flex:1;min-width:120px;padding:16px 20px;"
            f"border-left:{'none' if lvl == 0 else '1px solid ' + p['HAIRLINE']}'>"
            f"<div>{pips(lvl, label=False)}</div>"
            f"<div style='font-family:{MONO};font-size:28px;font-weight:500;color:{p['INK']};margin-top:10px;"
            f"font-variant-numeric:tabular-nums'>{int(counts.get(lvl, 0)):,}</div>"
            f"<div style='font-size:14px;color:{color};font-weight:500'>{LEVEL_NAME[lvl]}</div></div>")
    return (f"<div style='display:flex;flex-wrap:wrap;border:1px solid {p['HAIRLINE']};border-radius:12px;"
            f"overflow:hidden'>" + "".join(cells) + "</div>")
