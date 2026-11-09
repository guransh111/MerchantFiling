"""Shared dashboard state: which dataset is loaded, current settings, analyst reviews,
merchant explanations, and the (cached) analysis results."""
from __future__ import annotations

import dataclasses
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config as C  # noqa: E402
from src import engine  # noqa: E402

LEVEL_COLOR = {0: "#8a8984", 1: "#2a78d6", 2: "#c98500", 3: "#d95926", 4: "#9b1c1c"}
LABEL_NAME = {"legit": "Honest shop", "genuine_drifter": "Honest shop, business changed",
              "betting_front": "Betting front", "rented": "Rented account"}
REVIEW_COLS = ["merchant_id", "outcome", "note", "source"]
DECL_COLS = ["merchant_id", "week_start", "declared_change"]


@st.cache_resource(show_spinner="Loading the demo dataset...")
def demo_prepared() -> engine.Prepared:
    return engine.load_prepared()


def init():
    ss = st.session_state
    ss.setdefault("tl_settings", C.Settings())
    ss.setdefault("reviews", pd.DataFrame(columns=REVIEW_COLS))
    ss.setdefault("extra_decl", pd.DataFrame(columns=DECL_COLS))
    ss.setdefault("prepared", None)       # None = demo
    ss.setdefault("transactions", None)   # raw payments, when available (uploaded / generated)
    ss.setdefault("calendar", None)
    ss.setdefault("reveal", False)


def prepared() -> engine.Prepared:
    p = st.session_state.prepared
    return p if p is not None else demo_prepared()


def is_demo() -> bool:
    return st.session_state.prepared is None


def has_truth() -> bool:
    m = prepared().merchants
    return "label" in m and m.label.notna().any()


def set_dataset(p: engine.Prepared, transactions=None, calendar=None):
    ss = st.session_state
    ss.prepared, ss.transactions, ss.calendar = p, transactions, calendar
    ss.reviews = pd.DataFrame(columns=REVIEW_COLS)
    ss.extra_decl = pd.DataFrame(columns=DECL_COLS)
    ss.pop("_res_key", None)


def use_demo():
    set_dataset(None)


def _sig(*parts) -> str:
    h = hashlib.md5()
    for x in parts:
        h.update((x if isinstance(x, str) else json.dumps(x, sort_keys=True, default=str)).encode())
    return h.hexdigest()


def results() -> engine.Results:
    """Analysis for the current dataset + settings + reviews + explanations (recomputed only when they change)."""
    ss = st.session_state
    p = prepared()
    key = _sig(p.name, id(p), dataclasses.asdict(ss.tl_settings), ss.reviews.to_dict("records"),
               ss.extra_decl.to_dict("records"))
    if ss.get("_res_key") != key:
        pp = p
        if len(ss.extra_decl):
            pp = dataclasses.replace(p, declarations=pd.concat([p.declarations, ss.extra_decl], ignore_index=True))
        box = st.empty()
        with box.status("Running the analysis...", expanded=False) as status:
            res = engine.analyse(pp, ss.tl_settings, ss.reviews if len(ss.reviews) else None,
                                 progress=lambda m: status.update(label=m))
        box.empty()
        ss._res, ss._res_key = res, key
    return ss._res


def add_review(mid: str, outcome: str, note: str, source="analyst (dashboard)"):
    ss = st.session_state
    r = ss.reviews[ss.reviews.merchant_id != mid]
    if outcome != "undo":
        r = pd.concat([r, pd.DataFrame([{"merchant_id": mid, "outcome": outcome, "note": note, "source": source}])],
                      ignore_index=True)
    ss.reviews = r


def add_declaration(mid: str, text: str, week_start=None):
    ss = st.session_state
    row = pd.DataFrame([{"merchant_id": mid, "week_start": week_start, "declared_change": text}])
    ss.extra_decl = pd.concat([ss.extra_decl, row], ignore_index=True)


def level_badge(level: int) -> str:
    return (f"<span style='display:inline-block;padding:2px 10px;border-radius:12px;background:{LEVEL_COLOR[level]};"
            f"color:white;font-size:13px;font-weight:600'>{C.LEVEL_SHORT[level]}</span>")


def merchant_label(d: pd.DataFrame, mid: str) -> str:
    r = d.set_index("merchant_id").loc[mid]
    return f"{mid} · {str(r.category).replace('_', ' ')} · {C.LEVEL_SHORT[int(r.level)]} · risk {r.risk_score:.0f}"
