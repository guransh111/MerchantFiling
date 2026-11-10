"""Regulatory reporting and privacy-preserving sharing.

1. STR draft (FIU-IND)
   Under PMLA, a payment system operator must file a Suspicious Transaction Report within 7 days of
   forming a suspicion. We draft one per confirmed case with everything an officer needs: the subject,
   the grounds (the system's plain-English reasons), a transaction summary, linked entities and the
   case history. It is a DRAFT for the Principal Officer to check and file through FIU-IND's FINnet
   portal; it is not FIU-IND's official electronic format.

2. I4C Suspect Registry file
   Identifiers (UPI ID, settlement account, devices) of confirmed merchants, for sharing with the
   Indian Cyber Crime Coordination Centre's registry.

3. Consortium tokens (privacy-preserving sharing between payment providers)
   Each identifier is turned into a keyed hash (HMAC-SHA256) using a secret key shared by the
   members. Providers can then check "has anyone offboarded this bank account / phone before?"
   without ever seeing each other's raw data. The same input always gives the same token; the token
   can't be reversed without the key.
"""
from __future__ import annotations

import hashlib
import hmac

import numpy as np
import pandas as pd

from . import config as C

DEMO_CONSORTIUM_KEY = "trustloop-demo-consortium-key"  # in real life: generated and held by IDPIC / NPCI


def mask(value, keep: int = 4) -> str:
    v = str(value)
    return v if len(v) <= keep else "•" * (len(v) - keep) + v[-keep:]


def token(value: str, key: str = DEMO_CONSORTIUM_KEY) -> str:
    """Keyed hash of a normalised identifier (lower-case, no spaces)."""
    norm = "".join(str(value).lower().split())
    return hmac.new(key.encode(), norm.encode(), hashlib.sha256).hexdigest()[:24]


def _merchant_ids(p, mid: str) -> pd.DataFrame:
    ids = getattr(p, "identifiers", pd.DataFrame())
    return ids[ids.merchant_id == mid] if len(ids) else pd.DataFrame(columns=["merchant_id", "kind", "value"])


def str_draft(mid: str, results, prepared, case_id: str = "", events: pd.DataFrame | None = None,
              entity: str = "[Payment Aggregator name]", entity_id: str = "[FIU-IND Reporting Entity ID]") -> str:
    d = results.decisions.set_index("merchant_id").loc[mid]
    w = results.weekly[results.weekly.merchant_id == mid].sort_values("week_start")
    first, last = (pd.Timestamp(w.week_start.min()), pd.Timestamp(w.week_start.max()) + pd.Timedelta(days=6)) if len(w) else (None, None)
    total_in = w.inflow.sum() if len(w) else 0
    n_pay = int(w.n_txns.sum()) if len(w) else 0
    peak = w.loc[w.inflow.idxmax()] if len(w) else None
    ids = _merchant_ids(prepared, mid)
    links = results.edges[(results.edges.a == mid) | (results.edges.b == mid)]
    lines = [
        f"# DRAFT Suspicious Transaction Report: {mid}",
        "",
        "> Draft prepared by TrustLoop for the Principal Officer. Verify every field, then file through FIU-IND's "
        "FINnet portal in the official format. PMLA requires filing within 7 days of forming the suspicion.",
        "",
        "## 1. Reporting entity",
        f"- Name: {entity}",
        f"- Reporting entity ID: {entity_id}",
        f"- Internal case reference: {case_id or '(none)'}",
        "",
        "## 2. Subject of the report",
        f"- Merchant ID: {mid}",
        f"- UPI ID: {d.get('upi_id', '') or '(not on file)'}",
        f"- Declared business: {str(d.category).replace('_', ' ')}, {d.city} ({d.state}), city tier {d.tier}",
        f"- Declared size / expected monthly turnover: {d.declared_size} / Rs {d.declared_monthly_turnover:,.0f}"
        if pd.notna(d.declared_monthly_turnover) else f"- Declared size: {d.declared_size}",
        f"- GST-declared annual turnover: " + (f"Rs {d.gst_annual_turnover:,.0f}" if pd.notna(d.get('gst_annual_turnover', np.nan)) else "not GST-registered"),
    ]
    for kind, label in [("settlement_account", "Settlement account(s)"), ("device_id", "Device(s) used")]:
        vals = ids[ids.kind == kind].value.tolist()
        if vals:
            lines.append(f"- {label}: {', '.join(mask(v) for v in vals[:6])}{' …' if len(vals) > 6 else ''}")
    lines += [
        "",
        "## 3. Grounds for suspicion",
        f"Risk score {d.risk_score:.0f}/100 (behaviour vs peers {d.drift_score:.0f}, network {d.network_score:.0f}). "
        "Activity is inconsistent with the declared business:",
        "",
        *[f"- {x}" for x in [d.reason_1, d.reason_2, d.reason_3] if isinstance(x, str) and x],
        *[f"- {n}" for n in str(d.notes).split(" | ") if isinstance(d.notes, str) and n],
        "",
        "## 4. Transaction summary",
        f"- Period reviewed: {first:%d %b %Y} to {last:%d %b %Y}" if first is not None else "- Period reviewed: n/a",
        f"- Incoming payments: {n_pay:,} totalling Rs {total_in:,.0f}",
    ]
    if peak is not None:
        lines.append(f"- Peak week: {pd.Timestamp(peak.week_start):%d %b %Y}, Rs {peak.inflow:,.0f} in {int(peak.n_txns):,} payments")
    if pd.notna(d.get("upi_annual_takings", np.nan)):
        lines.append(f"- Annualised UPI takings: Rs {d.upi_annual_takings:,.0f}")
    if len(links):
        lines += ["", "## 5. Linked merchants (shared identifiers)"]
        for r in links.head(10).itertuples(index=False):
            other = r.b if r.a == mid else r.a
            lines.append(f"- {other}: {r.why}")
    if events is not None and len(events):
        lines += ["", "## 6. Case history (audit log)"]
        for r in events.sort_values("ts").itertuples(index=False):
            lines.append(f"- {pd.Timestamp(r.ts):%d %b %Y %H:%M} · {r.actor} · {r.action}" + (f": {r.note}" if r.note else ""))
    lines += ["", "## 7. Action taken", f"- {d.action}", "- Proposed: offboard; add identifiers to the I4C Suspect Registry; "
              "notify the settlement bank.", "", f"_Generated {pd.Timestamp.now():%d %b %Y %H:%M}._"]
    return "\n".join(lines)


def i4c_submission(mids, prepared, decisions: pd.DataFrame) -> pd.DataFrame:
    """Identifiers of confirmed merchants for the I4C Suspect Registry (confidential: identifiers in clear)."""
    d = decisions.set_index("merchant_id")
    ids = getattr(prepared, "identifiers", pd.DataFrame())
    rows = []
    for mid in mids:
        mine = ids[ids.merchant_id == mid] if len(ids) else pd.DataFrame()
        for r in mine.itertuples(index=False):
            rows.append({"merchant_id": mid, "identifier_type": r.kind, "identifier": r.value,
                         "declared_business": d.category.get(mid, ""), "state": d.state.get(mid, ""),
                         "reason": d.reason_1.get(mid, ""), "risk_score": round(float(d.risk_score.get(mid, np.nan)), 1)})
    return pd.DataFrame(rows, columns=["merchant_id", "identifier_type", "identifier", "declared_business", "state",
                                       "reason", "risk_score"])


def consortium_tokens(mids, prepared, key: str = DEMO_CONSORTIUM_KEY, provider: str = "Provider A") -> pd.DataFrame:
    """What a provider shares with the consortium for offboarded merchants: tokens only, no raw identifiers."""
    ids = getattr(prepared, "identifiers", pd.DataFrame())
    if not len(ids):
        return pd.DataFrame(columns=["provider", "identifier_type", "token"])
    mine = ids[ids.merchant_id.isin(set(mids))]
    out = pd.DataFrame({"provider": provider, "identifier_type": mine.kind.values,
                        "token": [token(v, key) for v in mine.value]})
    return out.drop_duplicates().reset_index(drop=True)


def simulate_applicants(prepared, offboarded, n: int = 200, n_reattempts: int = 8, seed: int = C.SEED) -> pd.DataFrame:
    """DEMO: Provider B's new merchant applications. Most are new people; a few are operators of fronts
    that Provider A already offboarded, re-applying with a new name but reusing a bank account or phone."""
    rng = np.random.default_rng(seed + 202)
    cats = ["kirana", "restaurant", "sweet_shop", "pharmacy", "electronics"]
    rows = [{"application_id": f"B-APP-{i:04d}", "business_name": f"New Shop {i:04d}",
             "category": rng.choice(cats), "settlement_account": f"BB{rng.integers(10**9, 10**10)}",
             "device_id": f"BDEV{rng.integers(10**7, 10**8)}", "truth": "new applicant"} for i in range(n)]
    ids = getattr(prepared, "identifiers", pd.DataFrame())
    pool = ids[ids.merchant_id.isin(set(offboarded))] if len(ids) else pd.DataFrame()
    acc = pool[pool.kind == "settlement_account"].value.unique()
    dev = pool[pool.kind == "device_id"].value.unique()
    for j in range(min(n_reattempts, len(acc) + len(dev))):
        r = rows[int(rng.integers(0, n))]
        if j % 2 == 0 and len(acc):
            r["settlement_account"] = str(rng.choice(acc))
            r["truth"] = "re-application: reused bank account"
        elif len(dev):
            r["device_id"] = str(rng.choice(dev))
            r["truth"] = "re-application: reused phone"
    return pd.DataFrame(rows)


def check_applicants(applicants: pd.DataFrame, shared: pd.DataFrame, key: str = DEMO_CONSORTIUM_KEY) -> pd.DataFrame:
    """Provider B tokenises its own applicants with the same key and looks for matches in the shared list."""
    known = set(shared.token)
    out = applicants.copy()
    out["account_token"] = out.settlement_account.map(lambda v: token(v, key))
    out["device_token"] = out.device_id.map(lambda v: token(v, key))
    out["match_account"] = out.account_token.isin(known)
    out["match_device"] = out.device_token.isin(known)
    out["flag"] = out.match_account | out.match_device
    return out
