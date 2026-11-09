"""Step 2: turn millions of raw payments into 10 weekly 'signals' per merchant.

A feature (or signal) is one number that summarises one aspect of behaviour,
e.g. "what share of this week's money arrived between 11pm and 4am?".
Detection then works on these numbers, not on individual payments.

Output: data/features.csv with one row per merchant per week.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C

MIN_TXNS_PER_WEEK = 5  # fewer payments than this -> too little data to judge that week


def load():
    m = pd.read_csv(C.DATA / "merchants.csv")
    tx = pd.read_csv(C.DATA / "transactions.csv", parse_dates=["ts"])
    cal = pd.read_csv(C.DATA / "calendar.csv", parse_dates=["date"])
    return m, tx, cal


def _entropy(values: np.ndarray) -> float:
    """How varied are the amounts? Uses ~5% wide price bands (log scale)."""
    bins = np.round(np.log10(np.maximum(values, 1)) * 20)
    _, counts = np.unique(bins, return_counts=True)
    p = counts / counts.sum()
    return float(-(p * np.log2(p)).sum())


def build_features(m: pd.DataFrame, tx: pd.DataFrame, cal: pd.DataFrame) -> pd.DataFrame:
    start = pd.Timestamp(C.START_DATE)
    tx = tx.copy()
    tx["date"] = tx.ts.dt.normalize()
    tx["week"] = (tx.date - start).dt.days // 7
    hour = tx.ts.dt.hour + tx.ts.dt.minute / 60

    cal = cal.set_index("date")
    ms = cal.match_start.reindex(tx.date).to_numpy()
    me = cal.match_end.reindex(tx.date).to_numpy()
    tx["in_match"] = (hour.to_numpy() >= ms) & (hour.to_numpy() <= me)
    tx["night"] = (tx.ts.dt.hour >= 23) | (tx.ts.dt.hour < 4)
    tx["round"] = (tx.amount % 100) == 0
    tx = tx.merge(m[["merchant_id", "state"]], on="merchant_id")
    tx["out_of_state"] = tx.counterparty_state != tx.state

    inn = tx[tx.direction == "in"]
    out = tx[tx.direction == "out"]
    g = inn.groupby(["merchant_id", "week"])

    f = pd.DataFrame({
        "n_txns": g.size(),
        "inflow": g.amount.sum(),
        "round_share": g["round"].mean(),
        "night_share": g.apply(lambda d: d.amount[d.night].sum() / d.amount.sum(), include_groups=False),
        "match_value": g.apply(lambda d: d.amount[d.in_match].sum(), include_groups=False),
        "out_of_state_share": g.out_of_state.mean(),
        "payments_per_payer": g.size() / g.counterparty_id.nunique(),
        "ticket_variety": g.amount.apply(lambda a: _entropy(a.to_numpy())),
    })

    # cricket share only means something in weeks that had matches
    match_weeks = set(((cal.index[cal.is_match_day] - start).days // 7).tolist())
    f["match_hours_share"] = f.match_value / f.inflow
    f.loc[~f.index.get_level_values("week").isin(match_weeks), "match_hours_share"] = np.nan
    f = f.drop(columns="match_value")

    # money in vs money out, day by day
    din = inn.groupby(["merchant_id", "week", "date"]).amount.sum()
    dout = out.groupby(["merchant_id", "week", "date"]).amount.sum().reindex(din.index, fill_value=0)
    f["pass_through"] = np.minimum(din, dout).groupby(level=[0, 1]).sum() / din.groupby(level=[0, 1]).sum()
    f["payout_fanout"] = out.groupby(["merchant_id", "week"]).counterparty_id.nunique()
    f["payout_fanout"] = f.payout_fanout.fillna(0)

    f = f.reset_index()
    # growth vs the merchant's own previous 8 weeks (median, so one odd week doesn't matter)
    f = f.sort_values(["merchant_id", "week"])
    prev = f.groupby("merchant_id").inflow.transform(lambda s: s.shift(1).rolling(8, min_periods=4).median())
    f["volume_growth"] = np.log(f.inflow / prev)

    # takings vs what the merchant declared at sign-up
    decl = f.merchant_id.map(m.set_index("merchant_id").declared_monthly_turnover)
    f["size_mismatch"] = np.log(f.inflow * 30 / 7 / decl)

    thin = f.n_txns < MIN_TXNS_PER_WEEK
    f.loc[thin, list(C.FEATURES)] = np.nan
    f["week_start"] = start + pd.to_timedelta(f.week * 7, unit="D")
    cols = ["merchant_id", "week", "week_start", "n_txns", "inflow"] + list(C.FEATURES)
    return f[cols].reset_index(drop=True)


def main():
    m, tx, cal = load()
    f = build_features(m, tx, cal)
    f.to_csv(C.DATA / "features.csv", index=False)
    print(f"features: {len(f):,} merchant-weeks")
    lab = f.merge(m[["merchant_id", "label"]]).groupby("label")[list(C.FEATURES)].median()
    print(lab.round(3).T.to_string())
    return f


if __name__ == "__main__":
    main()
