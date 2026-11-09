"""Choosing thresholds with money, not gut feel.

Every threshold trades two kinds of mistake:
  * MISS   a betting front keeps operating      -> regulatory penalty, reputational damage,
                                                    funds that should have been reported
  * FALSE  an honest merchant gets friction       -> lost fees, churn, complaints, review time
Plus a fixed cost for every case a human has to look at.

Given an estimate of each cost in rupees, we sweep the threshold from 0 to 100 and
pick the one with the lowest expected total cost. That's the same logic as setting a
credit-score cut-off from the cost of a default vs the profit of a good loan.

Needs ground truth: either a `label` column (synthetic/test data) or analyst reviews.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

BAD = {"betting_front", "rented", "bad", "fraud", "1", "true", "yes", "confirmed"}


@dataclass
class Costs:
    miss: float = 500_000.0       # Rs per bad merchant left untouched
    false_penalty: float = 20_000.0  # Rs per honest merchant put under friction or worse
    review: float = 1_500.0       # Rs of analyst time per flagged case


def truth_series(decisions: pd.DataFrame, reviews: pd.DataFrame | None = None) -> pd.Series:
    """True = bad. From `label` if present, else from analyst reviews (only reviewed merchants)."""
    if "label" in decisions and decisions.label.notna().any():
        return decisions.set_index("merchant_id").label.astype(str).str.lower().isin(BAD)
    if reviews is not None and len(reviews):
        r = reviews.drop_duplicates("merchant_id", keep="last").set_index("merchant_id")
        return (r.outcome == "confirmed")
    return pd.Series(dtype=bool)


def sweep(decisions: pd.DataFrame, truth: pd.Series, costs: Costs, score_col: str = "risk_score") -> pd.DataFrame:
    d = decisions.set_index("merchant_id")[[score_col]].join(truth.rename("bad"), how="inner")
    rows = []
    n_bad = int(d.bad.sum())
    for t in np.arange(0, 100.5, 1.0):
        flag = d[score_col] >= t
        tp = int((flag & d.bad).sum())
        fp = int((flag & ~d.bad).sum())
        fn = n_bad - tp
        rows.append({
            "threshold": t, "flagged": int(flag.sum()), "caught": tp, "missed": fn, "honest_flagged": fp,
            "precision": tp / flag.sum() if flag.sum() else np.nan,
            "recall": tp / n_bad if n_bad else np.nan,
            "cost_missed": fn * costs.miss, "cost_false": fp * costs.false_penalty,
            "cost_review": int(flag.sum()) * costs.review,
        })
    out = pd.DataFrame(rows)
    out["total_cost"] = out.cost_missed + out.cost_false + out.cost_review
    return out


def best_threshold(sw: pd.DataFrame) -> pd.Series:
    """Lowest cost; ties go to the HIGHER threshold (fewer merchants bothered)."""
    m = sw.total_cost.min()
    return sw[sw.total_cost == m].iloc[-1]
