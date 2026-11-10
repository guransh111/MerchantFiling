"""Tests for the operational layer: replay, case management, scanner, reporting, consortium, GST."""
import pandas as pd
import pytest

from src import cases as K
from src import config as C
from src import engine, replay, reporting, scanner
from src.generate import simulate


@pytest.fixture(scope="module")
def small():
    m, tx, cal, kb, ev, decl = simulate(120, n_weeks=16)
    tables = {"merchants": m, "transactions": tx, "calendar": cal, "known_bad": kb, "declarations": decl,
              "account_events": ev}
    p, r = engine.run(tables, start=C.START_DATE)
    return dict(m=m, tables=tables, p=p, r=r)


# ---- replay
def test_replay_never_looks_ahead_and_catches_fronts(small):
    st = replay.replay(small["tables"], start=C.START_DATE, every=2)
    assert st.as_of.nunique() == 8
    summ = replay.detection_summary(st, small["m"])
    fronts = summ[summ.label == "betting_front"]
    assert fronts.first_penalised.notna().mean() >= 0.8
    assert (fronts.days_to_penalty.dropna() >= 7).all()  # acts at the end of a week at the earliest


# ---- cases
def test_case_lifecycle_and_metrics(small):
    d = small["r"].decisions
    now = pd.Timestamp("2026-07-01")
    c, e = K.open_cases(d, *K.empty(), now)
    assert len(c) == (d.level.between(1, 3)).sum()
    cid = c.case_id.iloc[0]
    if c.status.iloc[0] == "Awaiting merchant":
        c, e = K.act(c, e, cid, "merchant_responded", now + pd.Timedelta(hours=5), "merchant", "invoices")
    c, e = K.act(c, e, cid, "confirm", now + pd.Timedelta(hours=30), "Analyst A")
    c, e = K.act(c, e, cid, "appeal", now + pd.Timedelta(hours=50), "merchant")
    c, e = K.act(c, e, cid, "overturn", now + pd.Timedelta(days=4), "Senior analyst")
    row = c.set_index("case_id").loc[cid]
    assert row.status == "Appeal overturned" and row.outcome == "cleared"
    mt = K.metrics(c, e, now + pd.Timedelta(days=5))
    assert mt["overturn_rate"] == 1.0 and mt["decided"] == 1
    assert K.final_outcomes(c).set_index("merchant_id").outcome.loc[row.merchant_id] == "cleared"
    with pytest.raises(ValueError):
        K.act(c, e, cid, "confirm", now, "x")  # closed cases can't be re-decided


def test_simulated_case_history_is_plausible(small):
    d = small["r"].decisions
    c, e = K.simulate_history(d, small["m"].set_index("merchant_id").label, pd.Timestamp("2026-07-06"))
    assert len(c) and set(e.action) >= {"opened"}
    assert (pd.to_datetime(e.ts) <= pd.Timestamp("2026-07-06")).all()


# ---- scanner
def test_scanner_finds_disguised_ids_and_ignores_emails():
    text = ("Pay to shop01@okaxis or shop02 [at] ybl. QR: upi://pay?pa=shop03@paytm&pn=X&am=500 "
            "Mail us: help.desk@gmail.com Telegram @Bookie")
    f = scanner.extract(text)
    assert set(f.upi_id) == {"shop01@okaxis", "shop02@ybl", "shop03@paytm"}
    m = pd.DataFrame({"merchant_id": ["A", "B"], "upi_id": ["shop01@okaxis", "other@ybl"]})
    assert scanner.match(f, m).set_index("upi_id").merchant_id.get("shop01@okaxis") == "A"


def test_demo_page_matches_unlisted_fronts(small):
    m, p = small["m"], small["p"]
    f = scanner.match(scanner.extract(scanner.demo_page(m, p.known_bad.merchant_id)), m)
    hits = f.dropna(subset=["merchant_id"])
    assert len(hits) >= 1
    assert set(m.set_index("merchant_id").label.reindex(hits.merchant_id)) == {"betting_front"}


# ---- reporting & consortium
def test_tokens_are_stable_and_keyed():
    assert reporting.token("SA-001") == reporting.token(" sa-001 ")
    assert reporting.token("SA-001", "k1") != reporting.token("SA-001", "k2")


def test_str_draft_and_i4c_file(small):
    r, p = small["r"], small["p"]
    mid = r.decisions[r.decisions.level >= 3].merchant_id.iloc[0]
    md = reporting.str_draft(mid, r, p)
    for section in ["Reporting entity", "Grounds for suspicion", "Transaction summary"]:
        assert section in md
    i4c = reporting.i4c_submission([mid], p, r.decisions)
    assert set(i4c.identifier_type) >= {"upi_id", "settlement_account"}


def test_consortium_catches_reused_identifiers(small):
    p, d = small["p"], small["r"].decisions
    off = d[d.level >= 3].merchant_id.tolist()
    shared = reporting.consortium_tokens(off, p)
    apps = reporting.simulate_applicants(p, off, n=100, n_reattempts=6)
    res = reporting.check_applicants(apps, shared)
    assert res[res.truth != "new applicant"].flag.all()
    assert not res[res.truth == "new applicant"].flag.any()


# ---- GST cross-check
def test_gst_mismatch_never_hits_honest_merchants(small):
    d = small["r"].decisions
    assert not d[d.label.isin(["legit", "genuine_drifter"])].gst_mismatch.any()
    assert (d.corroborated >= d.network_link).all()
