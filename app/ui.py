"""Shared look: chart theme, ladder colours and the 'ladder pips' signature.

Design pass after unslop by Damir Sokolovsky (@heydamir, CC BY 4.0):
quiet ink-grey chrome, one cobalt accent, colour only where it means something.
"""
from __future__ import annotations

import altair as alt
import streamlit as st

# ink ramp (light)
INK = "#111827"        # primary text
INK_2 = "#4b5565"      # secondary text
MUTED = "#6b7487"      # muted text, axis labels
HAIRLINE = "#e3e7ee"   # borders, grid
RAISED = "#f4f6f9"     # sidebar, inputs
ACCENT = "#1f5fae"     # cobalt: the one accent
NEUTRAL_BAR = "#b8bfcc"  # neutral series in charts
MONO = "IBM Plex Mono, ui-monospace, monospace"
SANS = "IBM Plex Sans, system-ui, sans-serif"

# the ladder is an ordered scale of severity, so its colours step from quiet to serious
LEVEL_COLOR = {0: "#9aa3b2", 1: ACCENT, 2: "#b45309", 3: "#c2410c", 4: "#7f1d1d"}
LEVEL_NAME = {0: "Monitor", 1: "Ask", 2: "Friction", 3: "Review", 4: "Offboard"}


@alt.theme.register("trustloop", enable=True)
def _chart_theme() -> alt.theme.ThemeConfig:
    return {
        "config": {
            "font": SANS,
            "background": "transparent",
            "view": {"stroke": None},
            "axis": {"labelFont": MONO, "labelFontSize": 11, "labelColor": MUTED, "labelLimit": 260, "titleFont": SANS,
                     "titleFontSize": 12, "titleFontWeight": 400, "titleColor": MUTED, "gridColor": "#eef1f5",
                     "domain": False, "tickColor": HAIRLINE, "ticks": False, "labelPadding": 6},
            "legend": {"labelFont": SANS, "labelFontSize": 12, "labelColor": INK_2, "titleFontWeight": 400,
                       "titleColor": MUTED, "symbolType": "circle", "symbolSize": 60},
            "range": {"category": [ACCENT, NEUTRAL_BAR, "#b45309", "#c2410c", "#5b6b85", "#7f1d1d"]},
            "line": {"color": ACCENT, "strokeWidth": 2},
            "bar": {"color": ACCENT},
            "point": {"color": ACCENT, "filled": True},
            "rule": {"color": MUTED},
            "text": {"font": MONO, "fontSize": 11, "color": INK_2},
        }
    }


def pips(level: int, label: bool = True) -> str:
    """The signature: five small steps showing where a merchant sits on the ladder."""
    level = int(level)
    color = LEVEL_COLOR[level]
    cells = "".join(
        f"<span style='display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:3px;"
        f"background:{color if i <= level else '#e3e7ee'}'></span>"
        for i in range(5))
    text = (f"<span style='margin-left:6px;font-size:14px;font-weight:500;color:{color if level else INK_2}'>"
            f"{LEVEL_NAME[level]}</span>") if label else ""
    return f"<span style='display:inline-flex;align-items:center;vertical-align:middle' title='{LEVEL_NAME[level]}'>{cells}{text}</span>"


def style():
    """Small finishing touches the theme can't express."""
    st.markdown(
        """<style>
        [data-testid="stMetricValue"] { font-variant-numeric: tabular-nums; }
        [data-testid="stMetricLabel"] p { color: #4b5565; }
        [data-testid="stCaptionContainer"] { color: #6b7487; }
        h1 { letter-spacing: -0.01em; }
        </style>""",
        unsafe_allow_html=True,
    )


# lucide line icons (stroke 1.5) for the few places that render raw HTML
def lucide(name: str, size: int = 16, color: str = INK_2) -> str:
    paths = {
        "check": "<path d='M20 6 9 17l-5-5'/>",
        "alert": "<path d='m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3'/>"
                 "<path d='M12 9v4'/><path d='M12 17h.01'/>",
    }[name]
    return (f"<svg width='{size}' height='{size}' viewBox='0 0 24 24' fill='none' stroke='{color}' stroke-width='1.5' "
            f"stroke-linecap='round' stroke-linejoin='round' style='vertical-align:-3px'>{paths}</svg>")


def bar_list(rows, fmt="{:,}", accent_first: bool = True, max_value=None) -> str:
    """A ranked list with thin bars: label, figure, and a hairline-thin bar (one accent, the rest neutral)."""
    rows = list(rows)
    top = max_value or max((v for _, v in rows), default=1) or 1
    out = []
    for i, (label, v) in enumerate(rows):
        color = ACCENT if (accent_first and i == 0) else NEUTRAL_BAR
        w = max(0.0, min(1.0, v / top)) * 100
        out.append(
            "<div style='padding:8px 0'>"
            "<div style='display:flex;justify-content:space-between;gap:16px;font-size:14px'>"
            f"<span style='color:{INK}'>{label}</span>"
            f"<span style='font-family:{MONO};color:{INK_2};font-variant-numeric:tabular-nums'>{fmt.format(v)}</span></div>"
            f"<div style='height:4px;background:#eef1f5;border-radius:2px;margin-top:6px'>"
            f"<div style='width:{w:.1f}%;height:4px;background:{color};border-radius:2px'></div></div></div>")
    return "".join(out)


def ladder_list(counts: dict, describe: bool = True) -> str:
    """Counts per ladder step, with the pips signature."""
    what = {0: "nothing visible", 1: "a neutral question", 2: "lower limits, T+2 settlement",
            3: "20% reserve and an investigator", 4: "closed after a human confirms"}
    rows = []
    for lvl in range(5):
        rows.append(f"<div style='display:flex;align-items:center;justify-content:space-between;gap:16px;"
                    f"padding:10px 0;border-bottom:1px solid #e9ecf1'>"
                    f"<div style='display:flex;align-items:center;gap:12px'>{pips(lvl)}"
                    + (f"<span style='color:{MUTED};font-size:14px'>{what[lvl]}</span>" if describe else "") + "</div>"
                    f"<span style='font-family:{MONO};font-size:15px;color:{INK}'>{int(counts.get(lvl, 0)):,}</span></div>")
    return "".join(rows)
