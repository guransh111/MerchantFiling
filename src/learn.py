"""Two 'second opinions' that sit next to the transparent drift score.

1. ANOMALY DETECTOR (Isolation Forest), no labels needed
   ------------------------------------------------------
   Looks at each merchant's whole profile of 10 peer-relative signals and asks
   "how easy is it to isolate this merchant from everyone else?". Merchants that are
   odd in an unusual COMBINATION get a high anomaly percentile even if no single
   signal crosses a line. Used to choose which unflagged merchants to audit first,
   which is how you discover new fraud patterns the rules don't know about yet.

2. LEARNING LOOP (logistic regression), learns from human reviewers
   -----------------------------------------------------------------
   Every time an analyst confirms a case ("yes, betting") or clears it ("genuine
   business"), that's a label. Once there are enough, we fit a logistic regression:
   which signals actually separated confirmed fronts from cleared merchants?
     * Output 1: a probability for every merchant ("looks like past confirmed cases").
     * Output 2: LEARNED WEIGHTS, which can be compared with the hand-set ones and
       used to retune them. This is how the system improves without becoming a black box.
   Predictions are 'out-of-fold' for reviewed merchants (a merchant is never scored
   by a model that saw its own label), so results aren't flattered.

   Bias warning built in: analysts mostly review what the system flagged, so the
   model can only learn what the system already sees. That's why we also include
   RANDOM AUDITS of ~2% of unflagged merchants in the training set.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from . import config as C

FEATS = list(C.FEATURES)
BAD_LABELS = {"betting_front", "rented", "bad", "fraud", "1", "true", "yes", "confirmed"}
MIN_PER_CLASS = 5


def merchant_profile(weekly: pd.DataFrame, net: pd.DataFrame | None = None, worst_weeks: int = 3) -> pd.DataFrame:
    """One row per merchant: average risk points per signal over its worst weeks, plus network score."""
    top = weekly.sort_values("drift_score", ascending=False).groupby("merchant_id").head(worst_weeks)
    prof = top.groupby("merchant_id")[[f"{f}__pts" for f in FEATS]].mean()
    prof.columns = FEATS
    z = weekly.groupby("merchant_id")[[f"{f}__z" for f in FEATS]].median().clip(-5, 10).fillna(0)
    z.columns = [f"{f}_typical" for f in FEATS]
    prof = prof.join(z)
    if net is not None:
        prof = prof.join(net.set_index("merchant_id")[["network_score"]]).fillna({"network_score": 0})
    return prof.fillna(0)


def anomaly_scores(profile: pd.DataFrame) -> pd.Series:
    """Percentile 0-100: how isolated each merchant's behaviour profile is (100 = most unusual)."""
    cols = [c for c in profile if c != "network_score"]
    if len(profile) < 20:
        return pd.Series(0.0, index=profile.index, name="anomaly_pct")
    iso = IsolationForest(n_estimators=200, random_state=C.SEED, contamination="auto")
    iso.fit(profile[cols])
    raw = -iso.score_samples(profile[cols])
    return pd.Series(pd.Series(raw).rank(pct=True).to_numpy() * 100, index=profile.index, name="anomaly_pct")


def simulate_review_history(decisions: pd.DataFrame, truth: pd.Series, audit_share: float = 0.02,
                            seed: int = C.SEED) -> pd.DataFrame:
    """DEMO ONLY: pretend analysts already reviewed last quarter's cases.

    Reviewed = everything the system escalated (Ask or above, the merchant answered and
    an analyst decided) + a random audit of `audit_share` of the rest. The analyst's
    finding is the hidden truth, which is exactly what a real investigation would reveal.
    """
    rng = np.random.default_rng(seed)
    d = decisions.set_index("merchant_id")
    flagged = d.index[d.level >= 1]
    rest = d.index[d.level < 1]
    audit = rng.choice(rest, max(1, int(round(audit_share * len(rest)))), replace=False) if len(rest) else []
    rows = []
    for mid in flagged:
        rows.append((mid, "flagged case", truth.get(mid)))
    for mid in audit:
        rows.append((mid, "random audit", truth.get(mid)))
    r = pd.DataFrame(rows, columns=["merchant_id", "source", "truth"])
    r["outcome"] = np.where(r.truth.astype(str).str.lower().isin(BAD_LABELS), "confirmed", "cleared")
    r["note"] = "simulated past review"
    return r.drop(columns="truth")


def learn(profile: pd.DataFrame, reviews: pd.DataFrame | None) -> dict:
    """Fit the learning-loop model if there are enough reviewed cases of both kinds."""
    out = {"trained": False, "message": "", "probability": pd.Series(np.nan, index=profile.index, name="learned_prob"),
           "weights": pd.DataFrame(), "n_confirmed": 0, "n_cleared": 0, "cv_auc": np.nan}
    if reviews is None or reviews.empty:
        out["message"] = "No reviewed cases yet. Confirm or clear cases in the dashboard to start the learning loop."
        return out
    r = reviews.drop_duplicates("merchant_id", keep="last")
    r = r[r.merchant_id.isin(profile.index) & r.outcome.isin(["confirmed", "cleared"])]
    y = (r.set_index("merchant_id").outcome == "confirmed").astype(int)
    out["n_confirmed"], out["n_cleared"] = int(y.sum()), int((1 - y).sum())
    if y.sum() < MIN_PER_CLASS or (1 - y).sum() < MIN_PER_CLASS:
        out["message"] = (f"Need at least {MIN_PER_CLASS} confirmed and {MIN_PER_CLASS} cleared cases to learn "
                          f"(have {out['n_confirmed']} confirmed, {out['n_cleared']} cleared).")
        return out
    X = profile.loc[y.index]
    model = lambda: make_pipeline(StandardScaler(), LogisticRegression(C=0.5, class_weight="balanced", max_iter=2000))
    prob = pd.Series(np.nan, index=profile.index, name="learned_prob")
    # out-of-fold predictions for the reviewed merchants
    k = int(min(5, y.sum(), (1 - y).sum()))
    oof = pd.Series(np.nan, index=y.index)
    for tr, te in StratifiedKFold(k, shuffle=True, random_state=C.SEED).split(X, y):
        mdl = model().fit(X.iloc[tr], y.iloc[tr])
        oof.iloc[te] = mdl.predict_proba(X.iloc[te])[:, 1]
    final = model().fit(X, y)
    unreviewed = profile.index.difference(y.index)
    if len(unreviewed):
        prob.loc[unreviewed] = final.predict_proba(profile.loc[unreviewed])[:, 1]
    prob.loc[oof.index] = oof
    coef = final[-1].coef_[0]
    w = pd.DataFrame({"input": X.columns, "learned_weight": coef})
    w["signal"] = w.input.str.replace("_typical", "", regex=False)
    w["kind"] = np.where(w.input.str.endswith("_typical"), "typical week", "worst weeks")
    w.loc[w.input == "network_score", "kind"] = "network"
    out.update(trained=True, probability=prob, weights=w,
               cv_auc=float(roc_auc_score(y, oof)) if y.nunique() > 1 else np.nan,
               message=f"Learned from {out['n_confirmed']} confirmed and {out['n_cleared']} cleared cases.")
    return out


def suggested_weights(weights: pd.DataFrame, current: dict) -> pd.DataFrame:
    """Turn learned coefficients (worst-week inputs) into suggested drift-score weights,
    rescaled so they sum to the same total as the current weights."""
    if weights.empty:
        return pd.DataFrame()
    w = weights[weights.kind == "worst weeks"].set_index("signal").learned_weight.clip(lower=0)
    w = w.reindex(FEATS).fillna(0)
    total = sum(current.values())
    sugg = w / w.sum() * total if w.sum() > 0 else w
    return pd.DataFrame({"signal": FEATS, "current_weight": [current[f] for f in FEATS],
                         "suggested_weight": sugg.round(2).to_numpy()})
