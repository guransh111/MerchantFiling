"""Step 5: decide what to DO about each merchant, and say WHY in plain English.

Inputs
------
drift score        behaviour vs peers (score.py)
network score      links to known-bad merchants (network.py)
declarations       "we started late-night delivery" (merchant told us in advance)
account events     phone changed + bank account changed = possible account rental
change points      the week behaviour flipped, and whether it was right after an account change
learned model      probability the merchant resembles past CONFIRMED cases (learn.py)
analyst reviews    a human confirmed ("betting") or cleared ("genuine") the case

Proportionate response ladder (thresholds in Settings):
  0 Monitor   -> nothing visible to the merchant
  1 Ask       -> neutral prompt: "Your sales pattern changed. Tell us what's new."
  2 Friction  -> lower limits, slower (T+2) settlement. Money still flows.
  3 Review    -> 20% rolling reserve + a human investigator. Only with corroboration
                 (a network link or a known-bad match). No machine freezes anyone alone.
  4 Offboard  -> only after an ANALYST confirms; report to FIU-IND and the I4C registry.

Output: data/decisions.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import changepoint as CP
from . import config as C

PLURAL = {"kirana": "kirana stores", "restaurant": "restaurants", "sweet_shop": "sweet shops",
          "pharmacy": "pharmacies", "electronics": "electronics shops"}


def plural(cat: str) -> str:
    return PLURAL.get(cat, f"{cat.replace('_', ' ')} merchants")


def _fmt(feat: str, v: float) -> str:
    if pd.isna(v):
        return "n/a"
    if feat.endswith("_share") or feat == "pass_through":
        return f"{v:.0%}"
    if feat == "volume_growth":
        return f"{np.exp(v) - 1:+.0%}"
    if feat == "size_mismatch":
        return f"{np.exp(v):.1f}x declared"
    if feat == "payout_fanout":
        return f"{v:.0f} accounts"
    if feat == "payments_per_payer":
        return f"{v:.1f} per customer"
    if feat == "ticket_variety":
        return f"{v:.1f}/5"
    return f"{v:.2f}"


def peer_phrase(peer_group: str) -> str:
    cat, grp = peer_group.split("|")
    where = "in all city tiers" if grp == "all tiers" else f"in tier-{grp[-1]} cities"
    return f"{plural(cat)} {where}"


def reasons_for(weekly: pd.DataFrame, top_n: int = 3, worst_weeks: int = 3) -> list[str]:
    """Top signals across the merchant's worst weeks, written as a sentence each."""
    worst = weekly.nlargest(worst_weeks, "drift_score")
    pts = {f: worst[f"{f}__pts"].mean() for f in C.FEATURES}
    peak = worst.iloc[0]
    peers = peer_phrase(peak.peer_group)
    out = []
    for f, p in sorted(pts.items(), key=lambda kv: -kv[1])[:top_n]:
        if p < 0.5:
            break
        desc = C.FEATURES[f][2]
        out.append(f"{desc[0].upper() + desc[1:]}: {_fmt(f, peak[f])} vs {_fmt(f, peak[f + '__peer'])} for similar {peers}")
    return out


def takeover_flags(events: pd.DataFrame) -> pd.Series:
    """Device AND settlement account changed within 14 days -> possible rental / takeover."""
    if events is None or events.empty:
        return pd.Series(dtype=bool)
    ev = events.assign(date=pd.to_datetime(events.date, errors="coerce")).dropna(subset=["date"])
    flags = {}
    for mid, g in ev.groupby("merchant_id"):
        d = g[g.event == "device_change"].date
        s = g[g.event == "settlement_account_change"].date
        flags[mid] = any(abs((a - b).days) <= 14 for a in d for b in s)
    return pd.Series(flags, dtype=bool)


def level_for(score: float, s: C.Settings) -> int:
    return max(lvl for thr, lvl in s.thresholds() if score >= thr)


def decide(m, weekly, scores, net, decl, events, s: C.Settings | None = None,
           changepoints: pd.DataFrame | None = None, learned: pd.Series | None = None,
           anomaly: pd.Series | None = None, reviews: pd.DataFrame | None = None) -> pd.DataFrame:
    s = s or C.Settings()
    d = m.merge(scores, on="merchant_id", how="left").merge(net, on="merchant_id", how="left")
    d["drift_score"] = d.drift_score.fillna(0)
    d["network_score"] = d.network_score.fillna(0) if s.use_network else 0.0
    d["known_bad"] = d.known_bad.fillna(False).astype(bool)
    d["risk_score"] = np.minimum(100, d.drift_score + s.network_weight * d.network_score)
    d.loc[d.known_bad, "risk_score"] = np.maximum(d.loc[d.known_bad, "risk_score"], 95)
    d["network_link"] = d.known_bad | (s.use_network & (d.network_score >= s.network_link_threshold))
    # GST cross-check: annualised UPI takings vs turnover declared in GST returns
    wk = weekly.groupby("merchant_id").agg(inflow=("inflow", "sum"), weeks=("week_start", "nunique"))
    annual = (wk.inflow / wk.weeks.clip(lower=1) * 52).reindex(d.merchant_id).to_numpy()
    gst = d.get("gst_annual_turnover", pd.Series(np.nan, index=d.index)).astype(float).to_numpy()
    d["upi_annual_takings"] = annual
    d["gst_ratio"] = np.where(gst > 0, annual / np.where(gst > 0, gst, 1), np.nan)
    d["gst_mismatch"] = s.use_gst & (d.gst_ratio >= s.gst_ratio_flag)
    d["gst_unregistered_above_threshold"] = s.use_gst & np.isnan(gst) & (annual >= 4_000_000) & \
        ("gst_annual_turnover" in d)
    d["corroborated"] = d.network_link | d.gst_mismatch
    d["possible_takeover"] = d.merchant_id.map(takeover_flags(events)).fillna(False).astype(bool)
    for c in ["linked_to", "link_reason", "cluster"]:
        d[c] = d.get(c, pd.Series("", index=d.index)).fillna("")
    d["cluster_size"] = d.get("cluster_size", pd.Series(np.nan, index=d.index))

    cp = changepoints.set_index("merchant_id") if changepoints is not None and len(changepoints) else pd.DataFrame()
    d["shift_week"] = d.merchant_id.map(cp.shift_week) if len(cp) else pd.NaT
    d["shift_jump"] = d.merchant_id.map(cp.jump) if len(cp) else np.nan
    d["learned_prob"] = d.merchant_id.map(learned) if learned is not None else np.nan
    d["anomaly_pct"] = d.merchant_id.map(anomaly) if anomaly is not None else np.nan

    rev = {}
    if reviews is not None and len(reviews):
        rev = reviews.drop_duplicates("merchant_id", keep="last").set_index("merchant_id").to_dict("index")
    by_m = {k: g for k, g in weekly.groupby("merchant_id")}
    decl_by_m = decl.groupby("merchant_id").declared_change.agg(lambda x: " / ".join(map(str, x))) if len(decl) else pd.Series(dtype=str)

    rows = []
    for _, r in d.iterrows():
        mid = r.merchant_id
        level = level_for(r.risk_score, s)
        system_level = level
        notes = []
        if level == 3 and s.require_corroboration and not r.corroborated:
            level = 2
            notes.append("Capped at Friction: no independent corroboration (network link or GST mismatch)")
        if s.use_takeover and r.possible_takeover:
            level = max(level, 1)  # always at least ask
            if r.network_link:
                level = min(3, level + 1)
            notes.append("Phone and bank account changed within 14 days: possible account rental")
        cpr = cp.loc[mid].to_dict() if len(cp) and mid in cp.index else None
        cp_text = CP.describe(cpr) if cpr else ""
        if s.use_changepoint and cpr and cpr.get("near_account_change") and cpr["score_after"] >= s.ask:
            level = max(level, 2 if r.network_link or r.possible_takeover else 1)
        if cp_text and (level >= 1 or (cpr and cpr.get("near_account_change"))):
            notes.append(cp_text)
        declared = decl_by_m.get(mid, "") if s.use_declarations else ""
        if declared and level > 0 and not r.network_link:
            level -= 1
            notes.append(f"Merchant declared: '{declared}'; lowered one level, evidence requested")
        elif declared and r.network_link and level > 0:
            notes.append(f"Merchant declared '{declared}' but is linked to a known betting account; not accepted without evidence")
        if s.use_learning and level == 0 and pd.notna(r.learned_prob) and r.learned_prob >= s.learning_escalate_at:
            level = 1
            notes.append(f"Resembles cases analysts confirmed before (learned model: {r.learned_prob:.0%}); asking to explain")
        if r.gst_mismatch:
            notes.append(f"UPI takings (~Rs {r.upi_annual_takings / 1e5:,.1f} lakh/yr) are {r.gst_ratio:.1f}x the turnover "
                         f"in its GST returns (Rs {r.gst_annual_turnover / 1e5:,.1f} lakh)")
        elif r.gst_unregistered_above_threshold and level >= 1:
            notes.append(f"UPI takings ~Rs {r.upi_annual_takings / 1e5:,.0f} lakh/yr, above the GST registration "
                         "threshold, but no GST registration on file")
        if r.known_bad:
            notes.append("UPI ID found on a public betting page / known-bad list")
        elif r.network_link and r.linked_to:
            notes.append(f"Linked to {r.linked_to}: {r.link_reason}")
        if r.cluster and r.cluster_size and r.cluster_size >= 3 and r.network_link:
            notes.append(f"Part of cluster {r.cluster} ({int(r.cluster_size)} merchants densely linked)")
        review = rev.get(mid)
        if review:
            if review.get("outcome") == "confirmed":
                level = 4
                notes.insert(0, f"CONFIRMED by analyst{': ' + str(review.get('note')) if review.get('note') else ''}")
            elif review.get("outcome") == "cleared":
                level = 0
                notes.insert(0, f"Cleared by analyst{': ' + str(review.get('note')) if review.get('note') else ''}; "
                                "monitoring continues")
        reasons = reasons_for(by_m[mid], worst_weeks=s.worst_weeks) if mid in by_m else []
        rows.append({"merchant_id": mid, "system_level": system_level, "level": level, "action": C.LEVELS[level],
                     "reason_1": reasons[0] if len(reasons) > 0 else "",
                     "reason_2": reasons[1] if len(reasons) > 1 else "",
                     "reason_3": reasons[2] if len(reasons) > 2 else "",
                     "notes": " | ".join(notes),
                     "review_outcome": review.get("outcome") if review else ""})
    out = d.merge(pd.DataFrame(rows), on="merchant_id")
    cols = ["merchant_id", "category", "city", "state", "tier", "declared_size", "declared_monthly_turnover",
            "drift_score", "network_score", "risk_score", "level", "action",
            "reason_1", "reason_2", "reason_3", "notes", "known_bad", "network_link", "possible_takeover",
            "upi_id", "gst_annual_turnover", "upi_annual_takings", "gst_ratio", "gst_mismatch", "corroborated",
            "linked_to", "cluster", "cluster_size", "peak_week", "shift_week", "shift_jump",
            "learned_prob", "anomaly_pct", "review_outcome", "label", "drift_type"]
    cols = [c for c in cols if c in out]
    return out[cols].sort_values(["level", "risk_score"], ascending=False).reset_index(drop=True)


def main():
    """Kept for backwards compatibility: the full pipeline now runs through engine.py."""
    from .engine import main as engine_main
    return engine_main()


if __name__ == "__main__":
    main()
