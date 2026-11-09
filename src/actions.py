"""Step 5: decide what to DO about each merchant, and say WHY in plain English.

Inputs: drift score (behaviour vs peers), network score (links to known-bad),
merchant declarations ("we started late-night delivery"), account events
(phone changed + bank account changed = possible account rental).

Proportionate response ladder (see config.LADDER):
  0 Monitor   -> nothing visible to the merchant
  1 Ask       -> neutral prompt: "Your sales pattern changed. Tell us what's new."
  2 Friction  -> lower limits, slower (T+2) settlement. Money still flows.
  3 Review    -> 20% rolling reserve + a human investigator. Only with corroboration
                 (a network link or a known-bad match). No machine freezes anyone alone.

Output: data/decisions.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C

NETWORK_WEIGHT = 0.25  # how many risk points a full network link adds
PLURAL = {"kirana": "kirana stores", "restaurant": "restaurants", "sweet_shop": "sweet shops",
          "pharmacy": "pharmacies", "electronics": "electronics shops"}


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


def reasons_for(weekly: pd.DataFrame, merchant_row: pd.Series, top_n: int = 3) -> list[str]:
    """Top signals across the merchant's 3 worst weeks, written as a sentence each."""
    worst = weekly.nlargest(3, "drift_score")
    pts = {f: worst[f"{f}__pts"].mean() for f in C.FEATURES}
    peak = worst.iloc[0]
    cat, grp = peak.peer_group.split("|")
    where = "in all city tiers" if grp == "all tiers" else f"in tier-{grp[-1]} cities"
    peer_name = f"{PLURAL[cat]} {where}"
    out = []
    for f, p in sorted(pts.items(), key=lambda kv: -kv[1])[:top_n]:
        if p < 0.5:
            break
        desc = C.FEATURES[f][2]
        out.append(f"{desc[0].upper() + desc[1:]}: {_fmt(f, peak[f])} vs {_fmt(f, peak[f + '__peer'])} for similar {peer_name}")
    return out


def takeover_flags(events: pd.DataFrame) -> pd.Series:
    """Device AND settlement account changed within 14 days -> possible rental / takeover."""
    if events.empty:
        return pd.Series(dtype=bool)
    ev = events.assign(date=pd.to_datetime(events.date))
    flags = {}
    for mid, g in ev.groupby("merchant_id"):
        d = g[g.event == "device_change"].date
        s = g[g.event == "settlement_account_change"].date
        flags[mid] = any(abs((a - b).days) <= 14 for a in d for b in s)
    return pd.Series(flags)


def decide(m, weekly, scores, net, decl, events) -> pd.DataFrame:
    d = m.merge(scores, on="merchant_id", how="left").merge(net, on="merchant_id", how="left")
    d["drift_score"] = d.drift_score.fillna(0)
    d["risk_score"] = np.minimum(100, d.drift_score + NETWORK_WEIGHT * d.network_score)
    d.loc[d.known_bad, "risk_score"] = np.maximum(d.loc[d.known_bad, "risk_score"], 95)
    d["network_link"] = d.known_bad | (d.network_score >= C.NETWORK_LINK_THRESHOLD)
    d["possible_takeover"] = d.merchant_id.map(takeover_flags(events)).fillna(False).astype(bool)

    by_m = {k: g for k, g in weekly.groupby("merchant_id")}
    decl_by_m = decl.groupby("merchant_id").declared_change.agg(" / ".join)
    rows = []
    for _, r in d.iterrows():
        level = max(lvl for thr, lvl, _ in C.LADDER if r.risk_score >= thr)
        notes = []
        if level == 3 and not r.network_link:
            level = 2
            notes.append("Capped at Friction: no network corroboration")
        if r.possible_takeover:
            level = max(level, 1)  # always at least ask
            if r.network_link:
                level = min(3, level + 1)
            notes.append("Phone and bank account changed within 14 days: possible account rental")
        declared = decl_by_m.get(r.merchant_id, "")
        if declared and level > 0 and not r.network_link:
            level -= 1
            notes.append(f"Merchant pre-declared: '{declared}'; lowered one level, evidence requested")
        elif declared and r.network_link and level > 0:
            notes.append(f"Merchant declared '{declared}' but is linked to a known betting account; not accepted without evidence")
        if r.known_bad:
            notes.append("UPI ID found on a public betting page")
        elif r.network_link:
            notes.append(f"Linked to {r.linked_to}: {r.link_reason}")
        reasons = reasons_for(by_m[r.merchant_id], r) if r.merchant_id in by_m else []
        rows.append({"merchant_id": r.merchant_id, "level": level,
                     "action": dict((lvl, a) for _, lvl, a in C.LADDER)[level],
                     "reason_1": reasons[0] if len(reasons) > 0 else "",
                     "reason_2": reasons[1] if len(reasons) > 1 else "",
                     "reason_3": reasons[2] if len(reasons) > 2 else "",
                     "notes": " | ".join(notes)})
    out = d.merge(pd.DataFrame(rows), on="merchant_id")
    cols = ["merchant_id", "category", "city", "state", "tier", "declared_size", "declared_monthly_turnover",
            "drift_score", "network_score", "risk_score", "level", "action",
            "reason_1", "reason_2", "reason_3", "notes", "known_bad", "network_link", "possible_takeover",
            "linked_to", "peak_week", "label", "drift_type"]
    return out[cols].sort_values("risk_score", ascending=False).reset_index(drop=True)


def main():
    m = pd.read_csv(C.DATA / "merchants.csv")
    weekly = pd.read_csv(C.DATA / "scores_weekly.csv")
    scores = pd.read_csv(C.DATA / "scores.csv")
    net = pd.read_csv(C.DATA / "network.csv")
    decl = pd.read_csv(C.DATA / "declarations.csv")
    ev = pd.read_csv(C.DATA / "account_events.csv")
    out = decide(m, weekly, scores, net, decl, ev)
    out.to_csv(C.DATA / "decisions.csv", index=False)
    # slim copy for the dashboard (small enough to keep in git)
    keep = ["merchant_id", "week_start", "peer_group", "n_txns", "inflow", "drift_score"]
    keep += [c for f in C.FEATURES for c in (f, f + "__peer", f + "__pts")]
    weekly[keep].round(3).to_csv(C.DATA / "dashboard_weekly.csv.gz", index=False)
    print(pd.crosstab(out.label, out.action).to_string())
    return out


if __name__ == "__main__":
    main()
