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

Only deviations in the risky direction count, each one is capped at `z_cap`, and
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
FEATS = list(C.FEATURES)


def peer_groups(m: pd.DataFrame, min_size: int = C.MIN_PEER_GROUP) -> pd.Series:
    """category x tier, falling back to category alone when the group is too small or tier unknown."""
    tier = m.tier.fillna(0).astype(int)
    key = m.category + "|tier" + tier.astype(str)
    small = (key.map(key.value_counts()) < min_size) | (tier == 0)
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


def points(values, centre, spread, s: C.Settings) -> tuple[dict, dict]:
    """z-scores and capped, weighted risk points per feature (works on Series or scalars)."""
    zs, pts = {}, {}
    for feat in FEATS:
        direction = C.FEATURES[feat][0]
        z = direction * (values[feat] - centre[feat]) / np.maximum(spread[feat], FLOOR[feat])
        zs[feat] = z
        p = s.weights.get(feat, 0.0) * np.clip(z, 0, s.z_cap)
        pts[feat] = p.fillna(0) if hasattr(p, "fillna") else (0.0 if pd.isna(p) else float(p))
    return zs, pts


def squash(raw, s: C.Settings):
    return 100 * (1 - np.exp(-np.asarray(raw, dtype=float) / s.squash_k))


def score(f: pd.DataFrame, m: pd.DataFrame, mode: str = "peer", settings: C.Settings | None = None) -> pd.DataFrame:
    s = settings or C.Settings()
    f = f.copy()
    f["peer_group"] = f.merchant_id.map(peer_groups(m, s.min_peer_group))
    centre, spread = reference_stats(f, mode)
    zs, pts = points(f, centre, spread, s)
    out = f[["merchant_id", "week", "week_start", "peer_group", "n_txns", "inflow"]].copy()
    raw = np.zeros(len(f))
    for feat in FEATS:
        out[feat] = f[feat]
        out[f"{feat}__peer"] = centre[feat]
        out[f"{feat}__spread"] = spread[feat]
        out[f"{feat}__z"] = zs[feat]
        out[f"{feat}__pts"] = pts[feat]
        raw += pts[feat].to_numpy()
    out["raw"] = raw
    out["drift_score"] = squash(raw, s)
    return out


def peer_baselines(w: pd.DataFrame) -> pd.DataFrame:
    """Peer median & spread per peer group and week (used to score a single new merchant)."""
    cols = {f"{f}__peer": "median" for f in FEATS} | {f"{f}__spread": "median" for f in FEATS}
    b = w.groupby(["peer_group", "week_start"]).agg(cols).reset_index()
    b["n_merchants"] = w.groupby(["peer_group", "week_start"]).merchant_id.nunique().to_numpy()
    return b


def resolve_peer_group(baselines: pd.DataFrame, category: str, tier: int) -> str:
    """Best available peer group for a new merchant: category x tier, else category, else everyone."""
    groups = set(baselines.peer_group)
    for g in (f"{category}|tier{int(tier)}", f"{category}|all tiers"):
        if g in groups:
            return g
    same_cat = sorted(g for g in groups if g.startswith(category + "|"))
    return same_cat[0] if same_cat else "ALL"


def pooled_baseline(baselines: pd.DataFrame, peer_group: str) -> pd.Series:
    """Typical peer median/spread across all weeks (used when the weeks don't line up)."""
    b = baselines if peer_group == "ALL" else baselines[baselines.peer_group == peer_group]
    return b.drop(columns=["peer_group", "week_start", "n_merchants"], errors="ignore").median(numeric_only=True)


def score_profile(values: dict, peer_group: str, baselines: pd.DataFrame, s: C.Settings | None = None) -> dict:
    """Score one merchant described by signal values (e.g. typed in by a user)."""
    s = s or C.Settings()
    base = pooled_baseline(baselines, peer_group)
    centre = {f: base.get(f"{f}__peer", np.nan) for f in FEATS}
    spread = {f: base.get(f"{f}__spread", np.nan) for f in FEATS}
    vals = {f: values.get(f, np.nan) for f in FEATS}
    zs, pts = points(vals, centre, spread, s)
    raw = sum(pts.values())
    return {"score": float(squash(raw, s)), "raw": raw, "points": pts, "z": zs, "peer": centre, "spread": spread,
            "peer_group": peer_group}


def score_one(f_one: pd.DataFrame, peer_group: str, baselines: pd.DataFrame, s: C.Settings | None = None) -> pd.DataFrame:
    """Score one merchant's weekly features against the dataset's peers (same week if available)."""
    s = s or C.Settings()
    pooled = pooled_baseline(baselines, peer_group)
    b = baselines[baselines.peer_group == peer_group].set_index("week_start") if peer_group != "ALL" else pd.DataFrame()
    rows = []
    for _, r in f_one.iterrows():
        wk = pd.Timestamp(r.week_start)
        base = b.loc[wk] if len(b) and wk in b.index else pooled
        centre = {f: base.get(f"{f}__peer", np.nan) for f in FEATS}
        spread = {f: base.get(f"{f}__spread", np.nan) for f in FEATS}
        zs, pts = points({f: r[f] for f in FEATS}, centre, spread, s)
        row = {"merchant_id": r.merchant_id, "week": r.week, "week_start": wk, "peer_group": peer_group,
               "n_txns": r.n_txns, "inflow": r.inflow}
        for f in FEATS:
            row.update({f: r[f], f"{f}__peer": centre[f], f"{f}__spread": spread[f], f"{f}__z": zs[f], f"{f}__pts": pts[f]})
        row["raw"] = sum(pts.values())
        row["drift_score"] = float(squash(row["raw"], s))
        rows.append(row)
    return pd.DataFrame(rows)


def merchant_summary(w: pd.DataFrame, worst_weeks: int = 3) -> pd.DataFrame:
    """One row per merchant: average of its N worst weeks (sustained, not a one-off blip)."""
    top = w.sort_values("drift_score", ascending=False).groupby("merchant_id").head(worst_weeks)
    s = top.groupby("merchant_id").drift_score.mean().rename("drift_score")
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
    if "label" in m:
        print(f"[{mode}] merchant drift score by hidden label:")
        print(s.merge(m[["merchant_id", "label"]]).groupby("label").drift_score.describe()[["mean", "min", "50%", "max"]].round(1).to_string())
    return w, s


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-peer", action="store_true")
    a = ap.parse_args()
    main("own" if a.no_peer else "peer")
