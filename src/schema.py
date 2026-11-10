"""Bring-your-own-data support: what columns we need, and turning messy files into clean tables.

A user can upload their own merchants and transactions (CSV or Excel). Column names
don't have to match exactly: we guess the mapping from common synonyms (e.g. "amt",
"Amount (Rs)", "txn_amount" all map to `amount`) and the dashboard lets the user fix it.

Only a few columns are truly REQUIRED. Missing optional columns simply switch off
the signals that depend on them (e.g. no payer state -> no out-of-state signal).
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import config as C

# table -> column -> (required?, explanation, synonyms)
SCHEMA: dict[str, dict[str, tuple[bool, str, list[str]]]] = {
    "merchants": {
        "merchant_id": (True, "Unique ID of the merchant", ["mid", "merchant", "merchant_code", "merchantid"]),
        "upi_id": (False, "Merchant's UPI ID / VPA, e.g. shop@okaxis (lets the betting-page scanner match it)", ["vpa", "upi", "upi_handle", "merchant_vpa"]),
        "category": (True, "Declared business type (kirana, restaurant, ...)", ["mcc", "business_type", "declared_category", "type", "segment"]),
        "city": (False, "City", ["town", "location"]),
        "state": (False, "State code or name (enables the out-of-state signal)", ["merchant_state", "region"]),
        "tier": (False, "City tier 1/2/3 (improves peer groups)", ["city_tier"]),
        "declared_monthly_turnover": (False, "Expected monthly turnover from sign-up form, in Rs (enables size signal)",
                                      ["expected_turnover", "monthly_turnover", "declared_turnover", "expected_monthly_volume", "turnover"]),
        "declared_size": (False, "small / medium / large", ["size"]),
        "gst_annual_turnover": (False, "Annual turnover in GST returns, Rs (enables the GST cross-check; blank = not registered)",
                                ["gst_turnover", "gstr_turnover", "annual_gst_turnover", "gst_annual"]),
        "settlement_account": (False, "Bank account the money is paid into (enables network links)", ["bank_account", "account_number", "settlement_acc", "payout_account"]),
        "label": (False, "OPTIONAL known truth for evaluation only (legit / betting_front / rented / genuine_drifter)", ["truth", "is_fraud", "fraud_label"]),
    },
    "transactions": {
        "merchant_id": (True, "Merchant receiving or sending the payment", ["mid", "merchant", "merchant_code", "payee", "vpa"]),
        "ts": (True, "Date and time of the payment", ["timestamp", "time", "datetime", "date_time", "txn_time", "created_at", "date"]),
        "amount": (True, "Amount in Rs", ["amt", "value", "txn_amount", "amount_rs", "amount_inr"]),
        "direction": (False, "'in' (customer paid merchant) or 'out' (merchant paid someone). Default: all in",
                      ["type", "txn_type", "flow", "dr_cr", "credit_debit"]),
        "counterparty_id": (False, "Payer (for 'in') or receiver (for 'out') ID; enables repeat-payer and network signals",
                            ["payer_id", "payer", "customer_id", "payer_vpa", "counterparty", "from"]),
        "counterparty_state": (False, "State of the payer/receiver; enables the out-of-state signal", ["payer_state", "customer_state"]),
        "device_id": (False, "Device the merchant used; enables shared-device links", ["device", "terminal_id", "device_fingerprint"]),
    },
    "known_bad": {
        "merchant_id": (True, "Merchant whose UPI ID was found on a betting page", ["mid", "merchant"]),
        "source": (False, "Where it was found", ["where"]),
    },
    "declarations": {
        "merchant_id": (True, "Merchant that declared a change", ["mid", "merchant"]),
        "week_start": (False, "When the change started", ["date", "from"]),
        "declared_change": (True, "What they said changed", ["change", "note", "description", "reason"]),
    },
    "account_events": {
        "merchant_id": (True, "Merchant", ["mid", "merchant"]),
        "date": (True, "Date of the change", ["ts", "timestamp"]),
        "event": (True, "device_change or settlement_account_change", ["type", "event_type"]),
        "new_value": (False, "New device / account", ["value"]),
    },
    "calendar": {
        "date": (True, "Day", ["day"]),
        "match_start": (False, "Hour the cricket match starts, e.g. 19.5 for 7:30pm (blank = no match)", ["start"]),
        "match_end": (False, "Hour the match ends, e.g. 23.5", ["end"]),
    },
}
REQUIRED_TABLES = ["merchants", "transactions"]


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def guess_mapping(table: str, columns: list[str]) -> dict[str, str | None]:
    """For each expected column, pick the uploaded column that matches it or a synonym."""
    normed = {_norm(c): c for c in columns}
    out = {}
    for col, (_, _, syn) in SCHEMA[table].items():
        hit = None
        for cand in [col, *syn]:
            if _norm(cand) in normed:
                hit = normed[_norm(cand)]
                break
        out[col] = hit
    return out


def read_any(file, name: str | None = None) -> pd.DataFrame:
    """Read CSV / Excel from a path or an uploaded file object."""
    name = (name or getattr(file, "name", "") or str(file)).lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(file)
    if name.endswith(".gz"):
        return pd.read_csv(file, compression="gzip")
    if isinstance(file, (bytes, bytearray)):
        file = io.BytesIO(file)
    return pd.read_csv(file)


def apply_mapping(df: pd.DataFrame, table: str, mapping: dict[str, str | None]) -> pd.DataFrame:
    cols = {src: dst for dst, src in mapping.items() if src}
    return df[list(cols)].rename(columns=cols)


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


_DIRECTION = {"in": "in", "credit": "in", "cr": "in", "c": "in", "received": "in", "collect": "in", "p2m": "in",
              "out": "out", "debit": "out", "dr": "out", "d": "out", "paid": "out", "payout": "out", "refund": "out"}


def cricket_calendar(start, end) -> pd.DataFrame:
    """Built-in schedule when the user doesn't upload one: IPL evening matches each year
    (28 Mar - 31 May, 7:30-11:30pm, weekend double-headers from 3:30pm) plus the 2026 September series."""
    days = pd.date_range(pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize(), freq="D")
    cal = pd.DataFrame({"date": days})
    doy = days.strftime("%m-%d")
    ipl = (doy >= "03-28") & (doy <= "05-31")
    sept = (days >= C.SEPT_SERIES[0]) & (days <= C.SEPT_SERIES[1]) & ((days.day % 2) == 1)
    weekend = days.dayofweek >= 5
    match = ipl | sept
    cal["is_match_day"] = match
    cal["match_start"] = np.where(match, np.where(ipl & weekend, 15.5, 19.5), np.nan)
    cal["match_end"] = np.where(match, 23.5, np.nan)
    diwali = pd.to_datetime(pd.Series(days.year.map(lambda y: C.DIWALI_DAYS.get(y, f"{y}-11-01"))).values)
    d = (days - diwali).days
    cal["is_diwali_week"] = (d >= -6) & (d <= 1)
    return cal


def clean(tables: dict[str, pd.DataFrame]) -> tuple[dict[str, pd.DataFrame], Report]:
    """Validate and normalise already-mapped tables. Returns cleaned tables and a report."""
    rep = Report()
    out: dict[str, pd.DataFrame] = {}
    for t in REQUIRED_TABLES:
        if t not in tables or tables[t] is None or tables[t].empty:
            rep.errors.append(f"The **{t}** table is required but missing or empty.")
    if rep.errors:
        return out, rep

    for t, df in tables.items():
        if df is None:
            continue
        missing = [c for c, (req, _, _) in SCHEMA[t].items() if req and c not in df.columns]
        if missing:
            rep.errors.append(f"**{t}** is missing required column(s): {', '.join(missing)}.")
    if rep.errors:
        return out, rep

    # ---------------- merchants
    m = tables["merchants"].copy()
    m["merchant_id"] = m.merchant_id.astype(str).str.strip()
    dup = m.merchant_id.duplicated().sum()
    if dup:
        rep.warnings.append(f"{dup} duplicate merchant IDs found; kept the first row of each.")
        m = m.drop_duplicates("merchant_id")
    m["category"] = m.category.astype(str).str.strip().str.lower().str.replace(r"\s+", "_", regex=True)
    for col, default in [("city", "unknown"), ("state", None), ("declared_size", "unknown")]:
        if col not in m:
            m[col] = default
    if "tier" not in m:
        m["tier"] = 0
        rep.info.append("No city tier given: peers are grouped by category only.")
    m["tier"] = pd.to_numeric(m.tier, errors="coerce").fillna(0).astype(int)
    if "declared_monthly_turnover" not in m:
        m["declared_monthly_turnover"] = np.nan
        rep.info.append("No declared turnover: the 'size vs declared' signal is switched off.")
    m["declared_monthly_turnover"] = pd.to_numeric(m.declared_monthly_turnover, errors="coerce")
    if "settlement_account" not in m:
        m["settlement_account"] = None
    if "upi_id" not in m:
        m["upi_id"] = None
    m["upi_id"] = m.upi_id.astype("string").str.strip().str.lower()
    m["gst_annual_turnover"] = pd.to_numeric(m.get("gst_annual_turnover"), errors="coerce") if "gst_annual_turnover" in m else np.nan
    if m.state.isna().all():
        rep.info.append("No merchant state: the 'out-of-state payers' signal is switched off.")
    small = m.category.value_counts()
    tiny = small[small < C.MIN_PEER_GROUP]
    if len(tiny):
        rep.warnings.append(f"{len(tiny)} categor{'y has' if len(tiny) == 1 else 'ies have'} fewer than "
                            f"{C.MIN_PEER_GROUP} merchants ({', '.join(tiny.index[:5])}{'...' if len(tiny) > 5 else ''}). "
                            "Peer comparison is unreliable for them; consider merging similar categories.")
    if "label" in m:
        m["label"] = m.label.astype(str).str.strip().str.lower()
        rep.info.append("A `label` column was found. It is used ONLY to grade the results, never to score.")
    out["merchants"] = m

    # ---------------- transactions
    tx = tables["transactions"].copy()
    tx["merchant_id"] = tx.merchant_id.astype(str).str.strip()
    tx["ts"] = pd.to_datetime(tx.ts, errors="coerce", dayfirst=False)
    bad_ts = tx.ts.isna().sum()
    if bad_ts:
        rep.warnings.append(f"{bad_ts:,} rows had an unreadable date/time and were dropped.")
    tx["amount"] = pd.to_numeric(tx.amount.astype(str).str.replace(r"[^0-9.\-]", "", regex=True), errors="coerce")
    bad_amt = tx.amount.isna().sum()
    if bad_amt:
        rep.warnings.append(f"{bad_amt:,} rows had an unreadable amount and were dropped.")
    tx = tx.dropna(subset=["ts", "amount"])
    if "direction" not in tx:
        tx["direction"] = "in"
        rep.info.append("No direction column: all payments treated as money IN. Pass-through and payout signals are off.")
    else:
        d = tx.direction.astype(str).str.strip().str.lower().map(_DIRECTION)
        if d.isna().any():
            rep.warnings.append(f"{d.isna().sum():,} rows had an unknown direction (expected in/out, credit/debit); treated as 'in'.")
        tx["direction"] = d.fillna("in")
    neg = tx.amount < 0
    if neg.any():  # negative amount = money out
        tx.loc[neg, "direction"] = "out"
        tx.loc[neg, "amount"] = -tx.loc[neg, "amount"]
    if "counterparty_id" not in tx:
        tx["counterparty_id"] = np.nan
        rep.info.append("No payer IDs: the repeat-payment signal and shared-customer links are off.")
    if "counterparty_state" not in tx:
        tx["counterparty_state"] = np.nan
    if "device_id" not in tx:
        tx["device_id"] = np.nan
    unknown = ~tx.merchant_id.isin(m.merchant_id)
    if unknown.any():
        rep.warnings.append(f"{unknown.sum():,} transactions belong to merchants not in the merchants table; dropped.")
        tx = tx[~unknown]
    no_tx = (~m.merchant_id.isin(tx.merchant_id)).sum()
    if no_tx:
        rep.info.append(f"{no_tx} merchants have no transactions; they will score 0.")
    if tx.empty:
        rep.errors.append("No usable transactions after cleaning.")
        return out, rep
    span = (tx.ts.max() - tx.ts.min()).days
    if span < 28:
        rep.warnings.append(f"Only {span} days of data. Several weeks are needed for growth and drift signals; 8+ weeks recommended.")
    tx = tx.sort_values("ts").reset_index(drop=True)
    if "txn_id" not in tx:
        tx.insert(0, "txn_id", np.arange(len(tx)))
    out["transactions"] = tx

    # ---------------- optional tables
    kb = tables.get("known_bad")
    out["known_bad"] = (kb.assign(merchant_id=kb.merchant_id.astype(str).str.strip())
                        if kb is not None else pd.DataFrame(columns=["merchant_id", "source"]))
    if "source" not in out["known_bad"]:
        out["known_bad"]["source"] = "uploaded list"
    de = tables.get("declarations")
    if de is not None:
        de = de.assign(merchant_id=de.merchant_id.astype(str).str.strip())
        if "week_start" not in de:
            de["week_start"] = None
    out["declarations"] = de if de is not None else pd.DataFrame(columns=["merchant_id", "week_start", "declared_change"])
    ev = tables.get("account_events")
    if ev is not None:
        ev = ev.assign(merchant_id=ev.merchant_id.astype(str).str.strip(),
                       event=ev.event.astype(str).str.lower().str.strip())
        if "new_value" not in ev:
            ev["new_value"] = None
    out["account_events"] = ev if ev is not None else pd.DataFrame(columns=["merchant_id", "date", "event", "new_value"])
    cal = tables.get("calendar")
    if cal is None:
        out["calendar"] = cricket_calendar(tx.ts.min(), tx.ts.max())
        rep.info.append("No match calendar uploaded: using the built-in IPL schedule (28 Mar - 31 May each year).")
    else:
        cal = cal.copy()
        cal["date"] = pd.to_datetime(cal.date).dt.normalize()
        for c in ["match_start", "match_end"]:
            cal[c] = pd.to_numeric(cal.get(c), errors="coerce")
        cal["is_match_day"] = cal.match_start.notna()
        base = cricket_calendar(tx.ts.min(), tx.ts.max())[["date", "is_diwali_week"]]
        out["calendar"] = base.merge(cal, on="date", how="left").fillna({"is_match_day": False})
    rep.info.insert(0, f"{len(m):,} merchants, {len(tx):,} transactions from {tx.ts.min():%d %b %Y} to {tx.ts.max():%d %b %Y}.")
    return out, rep


def template_tables(n_merchants: int = 12) -> dict[str, pd.DataFrame]:
    """Small example tables users can download, fill in, and upload."""
    from .generate import simulate
    m, tx, cal, kb, ev, decl = simulate(n_merchants, seed=7, n_weeks=10)
    m = m[["merchant_id", "upi_id", "category", "city", "state", "tier", "declared_size", "declared_monthly_turnover",
           "gst_annual_turnover", "settlement_account"]]
    tx = tx.drop(columns="txn_id")
    return {"merchants": m, "transactions": tx, "known_bad": kb, "declarations": decl, "account_events": ev,
            "calendar": cal[["date", "match_start", "match_end"]]}
