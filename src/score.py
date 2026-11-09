"""Step 3: the 'declared vs observed' drift score (0-100) for every merchant-week.

Core idea
---------
Compare each merchant with its PEERS in the same week: shops of the same declared
category in the same city tier. Because every sweet shop gets busier at Diwali,
the peer group's 'normal' moves too, so a Diwali rush does not look odd.

For each signal we compute a robust z-score:

    z = (merchant value - peer median) / peer spread

(spread = MAD, the median absolute deviation, a version of standard deviation
that a few extreme merchants cannot distort). z = 3 means "three typical spreads
further from normal than its peers".

Only deviations in the risky direction count, each one is capped at Z_CAP, and
they are added up. Capping means one odd signal can never produce a high score on
its own: you need several independent signals to agree. The sum is squashed onto 0-100.

The `--no-peer` baseline compares each merchant only with its own past. We keep it
to show *why* peers matter (it punishes Diwali sweet shops and misses fronts that
were betting from day one).
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from . import config as C

# Smallest spread we allow, so tiny peer spreads don't create huge z-scores
FLOOR = {
    "volume_growth": 0.15, "size_mismatch": 0.25, "round_share": 0.05,
    "match_hours_share": 0.05, "night_share": 0.03, "out_of_state_share": 0.03,
    "payments_per_payer": 0.15, "ticket_variety": 0.2, "pass_through": 0.05, "payout_fanout": 1.0,
}
K = 15.0  # squash constant: a raw total of ~14 -> score 60, ~21 -> 75, ~35 -> 90
FEATS = list(C.FEATURES)


def peer_groups(m: pd.DataFrame) -> pd.Series:
    """category x tier, falling back to category alone when the group is too small."""
    key = m.category + "|tier" + m.tier.astype(str)
    small = key.map(key.value_counts()) < C.MIN_PEER_GROUP
    key[small] = m.category[small] + "|all tiers"
    return pd.Series(key.values, index=m.merchant_id)


def reference_stats(f: pd.DataFrame, mode: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (centre, spread) for every row and feature, either from peers or own history."""
    if mode == "peer":
        g = f.groupby(["peer_group", "week"])[FEATS]
        centre = g.transform("median")
        spread = (f[FEATS] - centre).abs().groupby([f.peer_group, f.week]).transform("median") * 1.4826
    else:  # own history: everything this merchant did in earlier weeks
        f = f.sort_values(["merchant_id", "week"])
        g = f.groupby("merchant_id")[FEATS]
        centre = g.transform(lambda s: s.shift(1).expanding(4).median())
        dev = (f[FEATS] - centre).abs()
        spread = dev.groupby(f.merchant_id).transform(lambda s: s.shift(1).expanding(4).median()) * 1.4826
        centre, spread = centre.reindex(f.index), spread.reindex(f.index)
    return centre, spread


def score(f: pd.DataFrame, m: pd.DataFrame, mode: str = "peer") -> pd.DataFrame:
    f = f.copy()
    f["peer_group"] = f.merchant_id.map(peer_groups(m))
    centre, spread = reference_stats(f, mode)
    out = f[["merchant_id", "week", "week_start", "peer_group", "n_txns", "inflow"]].copy()
    raw = np.zeros(len(f))
    for feat in FEATS:
        direction, weight, _ = C.FEATURES[feat]
        z = (f[feat] - centre[feat]) / np.maximum(spread[feat], FLOOR[feat])
        contrib = (weight * np.clip(direction * z, 0, C.Z_CAP)).fillna(0)
        out[f"{feat}"] = f[feat]
        out[f"{feat}__peer"] = centre[feat]
        out[f"{feat}__z"] = direction * z
        out[f"{feat}__pts"] = contrib
        raw += contrib.to_numpy()
    out["raw"] = raw
    out["drift_score"] = 100 * (1 - np.exp(-raw / K))
    return out


def merchant_summary(w: pd.DataFrame) -> pd.DataFrame:
    """One row per merchant: average of its 3 worst weeks (sustained, not a one-off blip)."""
    top3 = w.sort_values("drift_score", ascending=False).groupby("merchant_id").head(3)
    s = top3.groupby("merchant_id").drift_score.mean().rename("drift_score")
    peak = w.loc[w.groupby("merchant_id").drift_score.idxmax(), ["merchant_id", "week_start"]]
    return s.to_frame().join(peak.set_index("merchant_id").rename(columns={"week_start": "peak_week"})).reset_index()


def main(mode: str = "peer"):
    m = pd.read_csv(C.DATA / "merchants.csv")
    f = pd.read_csv(C.DATA / "features.csv", parse_dates=["week_start"])
    w = score(f, m, mode)
    suffix = "" if mode == "peer" else "_nopeer"
    w.to_csv(C.DATA / f"scores_weekly{suffix}.csv", index=False)
    s = merchant_summary(w)
    s.to_csv(C.DATA / f"scores{suffix}.csv", index=False)
    print(f"[{mode}] merchant drift score by hidden label:")
    print(s.merge(m[["merchant_id", "label"]]).groupby("label").drift_score.describe()[["mean", "min", "50%", "max"]].round(1).to_string())
    return w, s


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-peer", action="store_true")
    a = ap.parse_args()
    main("own" if a.no_peer else "peer")
