"""When did the behaviour change? (change-point detection)

For every merchant we look at its weekly drift score as a time series and find the
single week that best splits it into a 'before' and an 'after' period: the split
that makes the two halves as internally consistent as possible (least squared error,
the same idea as fitting a step function).

Why it matters
--------------
* A RENTED account looks honest for months, then flips. Knowing the flip happened
  in the week of 1 June, two days after the phone and bank account changed, is far
  stronger evidence than either fact alone.
* It tells an investigator WHERE to look ("pull transactions from June onwards").
* A genuine business change also shows a step, but usually without an account change
  and with a merchant declaration around the same time.

Output columns: shift_week, score_before, score_after, jump, near_account_change, days_from_change
"""
from __future__ import annotations

import numpy as np
import pandas as pd

MIN_SEGMENT = 3     # weeks on each side of the split
MIN_JUMP = 20       # points; smaller steps are treated as noise
NEAR_DAYS = 21      # an account change within 3 weeks of the shift counts as 'near'


def best_split(y: np.ndarray) -> tuple[int, float, float]:
    """Index k maximising the drop in squared error when y is split into y[:k], y[k:]."""
    n = len(y)
    if n < 2 * MIN_SEGMENT:
        return -1, np.nan, np.nan
    c1 = np.cumsum(y)
    c2 = np.cumsum(y * y)
    best, best_k = -np.inf, -1
    total_sse = c2[-1] - c1[-1] ** 2 / n
    for k in range(MIN_SEGMENT, n - MIN_SEGMENT + 1):
        s1, q1 = c1[k - 1], c2[k - 1]
        s2, q2 = c1[-1] - s1, c2[-1] - q1
        sse = (q1 - s1 ** 2 / k) + (q2 - s2 ** 2 / (n - k))
        gain = total_sse - sse
        if gain > best:
            best, best_k = gain, k
    return best_k, float(y[:best_k].mean()), float(y[best_k:].mean())


def detect(weekly: pd.DataFrame, events: pd.DataFrame | None = None) -> pd.DataFrame:
    ev = None
    if events is not None and len(events):
        ev = events.assign(date=pd.to_datetime(events.date, errors="coerce")).dropna(subset=["date"])
    rows = []
    for mid, g in weekly.sort_values("week_start").groupby("merchant_id"):
        y = g.drift_score.to_numpy(dtype=float)
        weeks = pd.to_datetime(g.week_start).to_numpy()
        k, before, after = best_split(y)
        if k < 0:
            continue
        jump = after - before
        shift = pd.Timestamp(weeks[k])
        near, days = False, np.nan
        if ev is not None:
            mine = ev[ev.merchant_id == mid]
            if len(mine):
                diffs = (mine.date - shift).dt.days
                i = diffs.abs().idxmin()
                days = int(diffs[i])
                near = abs(days) <= NEAR_DAYS
        rows.append({"merchant_id": mid, "shift_week": shift, "score_before": round(before, 1),
                     "score_after": round(after, 1), "jump": round(jump, 1),
                     "near_account_change": bool(near and jump >= MIN_JUMP), "days_from_change": days})
    return pd.DataFrame(rows, columns=["merchant_id", "shift_week", "score_before", "score_after", "jump",
                                       "near_account_change", "days_from_change"])


def describe(row) -> str:
    if row is None or pd.isna(row.get("jump")) or row["jump"] < MIN_JUMP:
        return ""
    txt = (f"Behaviour shifted in the week of {pd.Timestamp(row['shift_week']):%d %b %Y} "
           f"(average score {row['score_before']:.0f} before, {row['score_after']:.0f} after)")
    if row.get("near_account_change"):
        d = int(row["days_from_change"])
        when = "the same day as" if d == 0 else f"{abs(d)} days {'after' if d < 0 else 'before'}"
        txt += f", {when} a phone/bank-account change"
    return txt
