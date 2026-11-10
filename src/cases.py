"""Case management: turning flags into cases with deadlines, decisions, appeals and an audit trail.

Lifecycle of a case
-------------------
  Awaiting merchant  -> the merchant was asked to explain; they have 72 hours (the SLA)
  Under review       -> the merchant replied (or the case is at Review level); an analyst decides
  Closed: confirmed  -> analyst found misuse  -> offboard, report to FIU-IND / I4C
  Closed: cleared    -> genuine business      -> back to Monitor
  Appealed           -> the merchant disputes a 'confirmed' decision; a second analyst decides
  Appeal upheld / Appeal overturned

Every step is written to an audit log (who, what, when, note), which a regulator or an
ombudsman can inspect. Metrics from the implementation plan come straight out of this:
appeal overturn rate (high = over-flagging), time to decision, overdue cases.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C

SLA_HOURS = 72
APPEAL_SLA_DAYS = 7
OPEN = ["Awaiting merchant", "Under review", "Appealed"]
CASE_COLS = ["case_id", "merchant_id", "opened", "level_at_open", "status", "due", "assignee", "outcome",
             "decided", "appeal_outcome"]
EVENT_COLS = ["case_id", "merchant_id", "ts", "actor", "action", "note"]

# which actions are allowed in which status
ACTIONS = {
    "Awaiting merchant": ["merchant_responded", "confirm", "clear", "extend_deadline"],
    "Under review": ["request_info", "confirm", "clear"],
    "Closed: confirmed": ["appeal"],
    "Closed: cleared": [],
    "Appealed": ["uphold", "overturn"],
    "Appeal upheld": [],
    "Appeal overturned": [],
}
ACTION_LABEL = {
    "merchant_responded": "Record merchant's reply", "request_info": "Ask merchant for more evidence",
    "confirm": "Confirm misuse", "clear": "Clear: genuine business", "extend_deadline": "Extend deadline 72h",
    "appeal": "Merchant appeals", "uphold": "Uphold decision", "overturn": "Overturn decision",
}


def empty():
    return pd.DataFrame(columns=CASE_COLS), pd.DataFrame(columns=EVENT_COLS)


def _ts(x) -> pd.Timestamp:
    """Timestamps to whole seconds (pandas 3 refuses to mix precisions in one column)."""
    return pd.Timestamp(x).floor("s").as_unit("ns")


def _log(events, case_id, mid, ts, actor, action, note=""):
    row = pd.DataFrame([{"case_id": case_id, "merchant_id": mid, "ts": _ts(ts), "actor": actor,
                         "action": action, "note": note}])
    return pd.concat([events, row], ignore_index=True) if len(events) else row


def open_cases(decisions: pd.DataFrame, cases: pd.DataFrame, events: pd.DataFrame, now, actor="system"):
    """Open a case for every merchant at Ask or above that has no open case yet."""
    now = _ts(now)
    has_case = set(cases.merchant_id[cases.status.isin(OPEN)]) if len(cases) else set()
    closed = set(cases.merchant_id[~cases.status.isin(OPEN)]) if len(cases) else set()
    new = decisions[(decisions.level.between(1, 3)) & ~decisions.merchant_id.isin(has_case | closed)]
    rows = []
    n0 = len(cases)
    for i, r in enumerate(new.itertuples(index=False)):
        cid = f"CASE-{n0 + i + 1:05d}"
        status = "Under review" if r.level >= 3 else "Awaiting merchant"
        rows.append({"case_id": cid, "merchant_id": r.merchant_id, "opened": now, "level_at_open": int(r.level),
                     "status": status, "due": now + pd.Timedelta(hours=SLA_HOURS), "assignee": "",
                     "outcome": "", "decided": pd.NaT, "appeal_outcome": ""})
        reason = r.reason_1 if isinstance(r.reason_1, str) and r.reason_1 else (r.notes or "")
        events = _log(events, cid, r.merchant_id, now, actor, "opened", f"{C.LEVEL_SHORT[int(r.level)]}: {reason}")
        if status == "Awaiting merchant":
            events = _log(events, cid, r.merchant_id, now, actor, "notified merchant",
                          f"Neutral prompt sent; reply due within {SLA_HOURS}h")
    if rows:
        cases = pd.concat([cases, pd.DataFrame(rows)], ignore_index=True) if len(cases) else pd.DataFrame(rows)
        for col in ["opened", "due", "decided"]:
            cases[col] = pd.to_datetime(cases[col]).astype("datetime64[ns]")
    return cases, events


def act(cases, events, case_id, action, now, actor="analyst", note=""):
    """Apply an action to a case (validated against the allowed transitions)."""
    now = _ts(now)
    i = cases.index[cases.case_id == case_id][0]
    status = cases.at[i, "status"]
    if action not in ACTIONS.get(status, []):
        raise ValueError(f"'{action}' is not allowed when a case is '{status}'")
    mid = cases.at[i, "merchant_id"]
    if action == "merchant_responded":
        cases.at[i, "status"] = "Under review"
    elif action == "request_info":
        cases.at[i, "status"] = "Awaiting merchant"
        cases.at[i, "due"] = now + pd.Timedelta(hours=SLA_HOURS)
    elif action == "extend_deadline":
        cases.at[i, "due"] = _ts(cases.at[i, "due"]) + pd.Timedelta(hours=SLA_HOURS)
    elif action in ("confirm", "clear"):
        cases.at[i, "status"] = "Closed: confirmed" if action == "confirm" else "Closed: cleared"
        cases.at[i, "outcome"] = "confirmed" if action == "confirm" else "cleared"
        cases.at[i, "decided"] = now
        cases.at[i, "assignee"] = cases.at[i, "assignee"] or actor
    elif action == "appeal":
        cases.at[i, "status"] = "Appealed"
        cases.at[i, "due"] = now + pd.Timedelta(days=APPEAL_SLA_DAYS)
    elif action in ("uphold", "overturn"):
        cases.at[i, "status"] = "Appeal upheld" if action == "uphold" else "Appeal overturned"
        cases.at[i, "appeal_outcome"] = "upheld" if action == "uphold" else "overturned"
        if action == "overturn":
            cases.at[i, "outcome"] = "cleared"
    events = _log(events, case_id, mid, now, actor, action, note)
    return cases, events


def final_outcomes(cases: pd.DataFrame) -> pd.DataFrame:
    """Latest analyst outcome per merchant, in the format the engine's `reviews` input expects."""
    if not len(cases):
        return pd.DataFrame(columns=["merchant_id", "outcome", "note", "source"])
    c = cases[cases.outcome.isin(["confirmed", "cleared"])].sort_values("opened")
    out = c.drop_duplicates("merchant_id", keep="last")[["merchant_id", "outcome"]].copy()
    out["note"] = "case " + c.drop_duplicates("merchant_id", keep="last").case_id.values
    out["source"] = "case management"
    return out


def metrics(cases: pd.DataFrame, events: pd.DataFrame, now) -> dict:
    now = pd.Timestamp(now)
    if not len(cases):
        return {"open": 0, "overdue": 0, "decided": 0, "median_hours_to_decision": np.nan,
                "appeals": 0, "overturn_rate": np.nan, "cleared_share": np.nan, "within_sla": np.nan}
    open_ = cases[cases.status.isin(OPEN)]
    decided = cases[cases.decided.notna()]
    hours = (pd.to_datetime(decided.decided) - pd.to_datetime(decided.opened)).dt.total_seconds() / 3600
    appeals = cases[cases.appeal_outcome.isin(["upheld", "overturned"])]
    replied = events[events.action == "merchant_responded"].groupby("case_id").ts.min()
    opened = cases.set_index("case_id").opened
    resp_h = (pd.to_datetime(replied) - pd.to_datetime(opened.reindex(replied.index))).dt.total_seconds() / 3600
    return {
        "open": len(open_),
        "overdue": int((pd.to_datetime(open_.due) < now).sum()),
        "decided": len(decided),
        "median_hours_to_decision": float(hours.median()) if len(hours) else np.nan,
        "appeals": len(appeals),
        "overturn_rate": float((appeals.appeal_outcome == "overturned").mean()) if len(appeals) else np.nan,
        "cleared_share": float((decided.outcome == "cleared").mean()) if len(decided) else np.nan,
        "within_sla": float((resp_h <= SLA_HOURS).mean()) if len(resp_h) else np.nan,
    }


def simulate_history(decisions: pd.DataFrame, truth: pd.Series, now, seed: int = C.SEED,
                     analyst_error: float = 0.03):
    """DEMO ONLY: a plausible quarter of case handling, so the metrics have something to show.

    Honest merchants usually reply within the 72h window; fronts often stall or send scripted replies.
    Analysts decide using the truth, but make occasional mistakes (analyst_error), and wrongly confirmed
    honest merchants usually appeal and get overturned. Some recent cases are still open.
    """
    rng = np.random.default_rng(seed)
    now = pd.Timestamp(now)
    cases, events = empty()
    flagged = decisions[decisions.level.between(1, 3)].sort_values("risk_score", ascending=False)
    bad_set = {"betting_front", "rented"}
    for r in flagged.itertuples(index=False):
        opened = now - pd.Timedelta(hours=float(rng.uniform(6, 24 * 45)))
        cases, events = open_cases(pd.DataFrame([r._asdict()]), cases, events, opened)
        cid = cases.case_id.iloc[-1]
        bad = str(truth.get(r.merchant_id)) in bad_set
        age = (now - opened).total_seconds() / 3600
        if age < 48 and rng.random() < 0.6:
            continue  # recent, still open
        reply_h = float(rng.uniform(2, 60) if not bad else rng.uniform(20, 140))
        replies = (not bad and rng.random() < 0.9) or (bad and rng.random() < 0.45)
        t = opened
        if cases.status.iloc[-1] == "Awaiting merchant" and replies and reply_h < age:
            t = opened + pd.Timedelta(hours=reply_h)
            note = ("Scripted reply: 'bulk order from a client', no invoices" if bad
                    else rng.choice(["Started delivery via Swiggy; partner page attached",
                                     "Screening IPL matches, set-menu bills attached",
                                     "Opened second branch; rent agreement attached",
                                     "Festival season; GST return attached"]))
            cases, events = act(cases, events, cid, "merchant_responded", t, "merchant", note)
        decide_h = float(rng.uniform(4, 96))
        t_dec = t + pd.Timedelta(hours=decide_h)
        if t_dec > now:
            continue
        wrong = rng.random() < analyst_error
        verdict = "confirm" if (bad != wrong) else "clear"
        analyst = rng.choice(["Analyst A", "Analyst B", "Analyst C"])
        cases, events = act(cases, events, cid, verdict, t_dec, analyst,
                            "Pattern consistent with betting collections" if verdict == "confirm" else "Evidence verified")
        if verdict == "confirm" and rng.random() < (0.9 if not bad else 0.3):
            t_ap = t_dec + pd.Timedelta(hours=float(rng.uniform(12, 120)))
            if t_ap < now:
                cases, events = act(cases, events, cid, "appeal", t_ap, "merchant", "Merchant disputes the decision")
                t_res = t_ap + pd.Timedelta(days=float(rng.uniform(1, 6)))
                if t_res < now:
                    cases, events = act(cases, events, cid, "overturn" if not bad else "uphold", t_res, "Senior analyst",
                                        "Appeal reviewed by a second analyst")
    return cases, events
