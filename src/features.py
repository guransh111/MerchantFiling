"""Step 2: turn millions of raw payments into 10 weekly 'signals' per merchant.

A feature (or signal) is one number that summarises one aspect of behaviour,
e.g. "what share of this week's money arrived between 11pm and 4am?".
Detection then works on these numbers, not on individual payments.

Works on any dataset (synthetic or uploaded). If an optional column is missing
(e.g. no payer state), the signals that need it are simply left blank, and blank
signals never add risk.

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


def week_zero(ts: pd.Series) -> pd.Timestamp:
    """Monday of the first week in the data."""
    first = ts.min().normalize()
    return first - pd.Timedelta(days=first.dayofweek)


def build_features(m: pd.DataFrame, tx: pd.DataFrame, cal: pd.DataFrame,
                   start: pd.Timestamp | None = None) -> pd.DataFrame:
    start = week_zero(tx.ts) if start is None else pd.Timestamp(start)
    tx = tx[["merchant_id", "ts", "amount", "direction", "counterparty_id", "counterparty_state"]].copy()
    tx["date"] = tx.ts.dt.normalize()
    tx["week"] = (tx.date - start).dt.days // 7
    hour = (tx.ts.dt.hour + tx.ts.dt.minute / 60).to_numpy()

    c = cal.assign(date=pd.to_datetime(cal.date).dt.normalize()).drop_duplicates("date").set_index("date")
    ms = c.match_start.reindex(tx.date).to_numpy(dtype=float)
    me = c.match_end.reindex(tx.date).to_numpy(dtype=float)
    in_match = (hour >= ms) & (hour <= me)
    night = (tx.ts.dt.hour >= 23) | (tx.ts.dt.hour < 4)
    state = tx.merchant_id.map(m.set_index("merchant_id").state)
    has_state = state.notna() & tx.counterparty_state.notna()

    tx["v_match"] = tx.amount * in_match
    tx["v_night"] = tx.amount * night
    tx["is_round"] = (tx.amount % 100) == 0
    tx["oos"] = np.where(has_state, (tx.counterparty_state.astype(str) != state.astype(str)).astype(float), np.nan)
    # price band on a log scale (~5% wide), for the variety signal
    tx["band"] = np.round(np.log10(np.maximum(tx.amount, 1)) * 20).astype(int)

    inn = tx[tx.direction == "in"]
    out = tx[tx.direction == "out"]
    keys = ["merchant_id", "week"]
    g = inn.groupby(keys)
    f = pd.DataFrame({
        "n_txns": g.size(),
        "inflow": g.amount.sum(),
        "round_share": g.is_round.mean(),
        "night_share": g.v_night.sum() / g.amount.sum(),
        "match_value": g.v_match.sum(),
        "out_of_state_share": g.oos.mean(),
        "payments_per_payer": g.size() / g.counterparty_id.nunique().replace(0, np.nan),
        # investigator metric from the implementation plan (not scored): how many states pay this merchant
        "payer_states": g.counterparty_state.nunique(),
    })
    # variety = Shannon entropy of price bands (bits)
    bc = inn.groupby(keys + ["band"]).size()
    p = bc / bc.groupby(level=[0, 1]).transform("sum")
    f["ticket_variety"] = (-(p * np.log2(p))).groupby(level=[0, 1]).sum()

    # cricket share only means something in weeks that had matches
    match_days = c.index[c.match_start.notna()]
    match_weeks = set(((match_days - start).days // 7).tolist())
    f["match_hours_share"] = f.match_value / f.inflow
    f.loc[~f.index.get_level_values("week").isin(match_weeks), "match_hours_share"] = np.nan
    f = f.drop(columns="match_value")

    # money in vs money out, day by day
    din = inn.groupby(keys + ["date"]).amount.sum()
    dout = out.groupby(keys + ["date"]).amount.sum().reindex(din.index, fill_value=0)
    f["pass_through"] = np.minimum(din, dout).groupby(level=[0, 1]).sum() / din.groupby(level=[0, 1]).sum()
    f["payout_fanout"] = out.groupby(keys).counterparty_id.nunique()
    f["payout_fanout"] = f.payout_fanout.fillna(0)
    if out.empty:  # dataset has no outflows at all -> these signals carry no information
        f["pass_through"] = np.nan
        f["payout_fanout"] = np.nan
    if tx.counterparty_id.isna().all():
        f["payments_per_payer"] = np.nan

    f = f.reset_index().sort_values(keys)
    # growth vs the merchant's own previous 8 weeks (median, so one odd week doesn't matter)
    prev = f.groupby("merchant_id").inflow.transform(lambda s: s.shift(1).rolling(8, min_periods=4).median())
    f["volume_growth"] = np.log(f.inflow / prev)

    # takings vs what the merchant declared at sign-up
    decl = f.merchant_id.map(m.set_index("merchant_id").declared_monthly_turnover).astype(float)
    f["size_mismatch"] = np.log(f.inflow * 30 / 7 / decl.where(decl > 0))

    feats = list(C.FEATURES)
    thin = f.n_txns < MIN_TXNS_PER_WEEK
    f.loc[thin, feats] = np.nan
    f["week_start"] = start + pd.to_timedelta(f.week * 7, unit="D")
    cols = ["merchant_id", "week", "week_start", "n_txns", "inflow", "payer_states"] + feats
    return f[cols].reset_index(drop=True)


def available_signals(f: pd.DataFrame) -> list[str]:
    """Signals that have at least some data in this dataset."""
    return [c for c in C.FEATURES if c in f and f[c].notna().any()]


def main():
    m, tx, cal = load()
    f = build_features(m, tx, cal, start=C.START_DATE)
    f.to_csv(C.DATA / "features.csv", index=False)
    print(f"features: {len(f):,} merchant-weeks")
    if "label" in m:
        lab = f.merge(m[["merchant_id", "label"]]).groupby("label")[list(C.FEATURES)].median()
        print(lab.round(3).T.to_string())
    return f


if __name__ == "__main__":
    main()
