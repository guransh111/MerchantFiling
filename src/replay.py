"""Time-to-detection replay: run the system week by week as if it had been live all along.

At the end of every week we analyse ONLY what was known by then:
  * payments up to that week (weekly signals never look ahead; growth uses past weeks only)
  * network links built from payments up to that week
  * known-bad UPI IDs only from the date they were found on a betting page
  * declarations and phone/bank-account changes only once they happened
The learning loop is switched off (no reviewer history is assumed at the start).

This answers the implementation plan's metric "days from first anomaly to action":
how long does a betting front or rented account operate before the system acts, and how
many honest merchants are ever penalised along the way (in ANY week, not just at the end)?
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd

from . import config as C
from . import network as N
from .engine import Prepared, analyse
from .features import build_features


def replay(tables: dict, s: C.Settings | None = None, start=None, progress=None, every: int = 1) -> pd.DataFrame:
    """Return one row per (as-of week, merchant): the level and risk the system would have shown then."""
    s = dataclasses.replace(s or C.Settings(), use_learning=False)
    m, tx = tables["merchants"], tables["transactions"]
    f_all = build_features(m, tx, tables["calendar"], start=start)
    kb = tables.get("known_bad", pd.DataFrame(columns=["merchant_id"]))
    decl = tables.get("declarations", pd.DataFrame(columns=["merchant_id", "week_start", "declared_change"]))
    ev = tables.get("account_events", pd.DataFrame(columns=["merchant_id", "date", "event", "new_value"]))
    weeks = sorted(f_all.week.unique())
    t0 = pd.Timestamp(f_all.week_start.min())
    rows = []
    for w in weeks[::every]:
        week_end = t0 + pd.Timedelta(days=7 * (w + 1))
        known = kb[pd.to_datetime(kb.get("found_date", pd.Series(t0, index=kb.index))) < week_end] if len(kb) else kb
        ev_w = ev[pd.to_datetime(ev.date) < week_end] if len(ev) else ev
        decl_w = decl[pd.to_datetime(decl.week_start, errors="coerce").fillna(t0) < week_end] if len(decl) else decl
        tx_w = tx[tx.ts < week_end]
        edges = N.build_edges(m, tx_w, ev_w)
        p = Prepared(merchants=m, features=f_all[f_all.week <= w], edges=edges, known_bad=known,
                     declarations=decl_w, account_events=ev_w)
        d = analyse(p, s, use_history=False).decisions
        rows.append(d[["merchant_id", "level", "risk_score", "drift_score", "network_score"]].assign(week=w, as_of=week_end))
        if progress:
            progress(f"  replay: week {w + 1}/{len(weeks)} ({week_end:%d %b}) "
                     f"flagged {int((d.level >= 1).sum())}, penalised {int((d.level >= 2).sum())}")
    return pd.concat(rows, ignore_index=True)


def detection_summary(status: pd.DataFrame, m: pd.DataFrame) -> pd.DataFrame:
    """Per merchant: when trouble started (onset), first week asked / penalised / reviewed, days to action."""
    t0 = status.as_of.min() - pd.Timedelta(days=7)
    first = {}
    for lvl, name in [(1, "first_asked"), (2, "first_penalised"), (3, "first_review")]:
        hit = status[status.level >= lvl].groupby("merchant_id").as_of.min()
        first[name] = hit
    out = m[["merchant_id", "category", "label", "drift_week"]].set_index("merchant_id").join(pd.DataFrame(first))
    # onset: fronts bet from day one; rented accounts from the handover week; honest drifters from their change
    onset_week = np.where(out.label == "betting_front", 0, out.drift_week.clip(lower=0))
    out["onset"] = t0 + pd.to_timedelta(onset_week * 7, unit="D")
    out.loc[out.label == "legit", "onset"] = pd.NaT
    out["days_to_penalty"] = (out.first_penalised - out.onset).dt.days
    out["days_to_ask"] = (out.first_asked - out.onset).dt.days
    weeks_pen = status[status.level >= 2].groupby("merchant_id").size()
    out["weeks_penalised"] = weeks_pen.reindex(out.index).fillna(0).astype(int)
    return out.reset_index()


def headline(summary: pd.DataFrame) -> dict:
    bad = summary[summary.label.isin(["betting_front", "rented"])]
    honest = summary[summary.label.isin(["legit", "genuine_drifter"])]
    res = {}
    for lab, g in bad.groupby("label"):
        caught = g.days_to_penalty.notna()
        res[lab] = {"n": len(g), "caught": int(caught.sum()),
                    "median_days": float(g.days_to_penalty.median()) if caught.any() else np.nan,
                    "p90_days": float(g.days_to_penalty.quantile(0.9)) if caught.any() else np.nan,
                    "max_days": float(g.days_to_penalty.max()) if caught.any() else np.nan}
    res["honest_ever_penalised"] = int(honest.first_penalised.notna().sum())
    res["honest_ever_asked"] = int(honest.first_asked.notna().sum())
    res["honest_n"] = len(honest)
    res["honest_penalised_weeks"] = int(honest.weeks_penalised.sum())
    res["honest_penalised_by_label"] = honest[honest.first_penalised.notna()].label.value_counts().to_dict()
    return res
