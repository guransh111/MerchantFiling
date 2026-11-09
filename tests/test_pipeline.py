"""Tests use the hidden labels as ground truth. Run:  pytest -q

They build a small world (150 merchants) once and check that every step does what
it promises, including bring-your-own-data, settings, change points, the learning
loop and analyst reviews.
"""
import dataclasses
import inspect

import numpy as np
import pandas as pd
import pytest

from src import changepoint, config as C, engine, features, generate, learn, network, schema, score, tuning

BAD = ["betting_front", "rented"]


@pytest.fixture(scope="module")
def world():
    m, tx, cal, kb, ev, decl = generate.simulate(C.N_MERCHANTS_SMALL)
    tables = {"merchants": m, "transactions": tx, "calendar": cal, "known_bad": kb,
              "declarations": decl, "account_events": ev}
    p, r = engine.run(tables, start=C.START_DATE)
    own = score.merchant_summary(score.score(p.features, m, "own"))
    return dict(m=m, tx=tx, cal=cal, kb=kb, p=p, r=r, own=own)


def med(df, col, w):
    return df.merge(w["m"][["merchant_id", "label"]]).groupby("label")[col].median()


# ---- synthetic data
def test_label_mix(world):
    counts = world["m"].label.value_counts()
    assert set(counts.index) == {"legit", "betting_front", "rented", "genuine_drifter"}
    assert counts["legit"] / len(world["m"]) > 0.85


def test_fronts_peak_on_match_days(world):
    tx, cal, m = world["tx"], world["cal"], world["m"]
    t = tx[tx.merchant_id.isin(m.merchant_id[m.label == "betting_front"]) & (tx.direction == "in")]
    match_dates = set(cal.date[cal.is_match_day].dt.date)
    on = t.ts.dt.date.isin(match_dates)
    assert on.sum() / len(match_dates) > 2 * (~on).sum() / (len(cal) - len(match_dates))


def test_reproducible():
    pd.testing.assert_frame_equal(generate.simulate(30)[0], generate.simulate(30)[0])


def test_custom_world_parameters():
    m, tx, *_ = generate.simulate(80, n_weeks=12, label_mix={"betting_front": 0.1, "rented": 0, "genuine_drifter": 0},
                                  evasion=0.9)
    assert (m.label == "betting_front").sum() == 8 and (m.label == "rented").sum() == 0
    assert tx.ts.max() < pd.Timestamp(C.START_DATE) + pd.Timedelta(weeks=12)


# ---- features & score
def test_features_separate_fronts(world):
    f = world["p"].features.merge(world["m"][["merchant_id", "label"]]).groupby("label").median(numeric_only=True)
    for col in ["match_hours_share", "round_share", "out_of_state_share"]:
        assert f.loc["betting_front", col] > f.loc["legit", col]


def test_drifters_score_below_fronts(world):
    s = med(world["r"].scores, "drift_score", world)
    assert s["genuine_drifter"] < s["betting_front"] and s["legit"] < 60


def test_peer_beats_own_history_on_fronts(world):
    assert med(world["r"].scores, "drift_score", world)["betting_front"] > med(world["own"], "drift_score", world)["betting_front"] + 20


def test_score_profile_typical_vs_front(world):
    b = world["r"].baselines
    g = score.resolve_peer_group(b, "kirana", 1)
    typical = score.score_profile({}, g, b)["score"]
    front = score.score_profile({"match_hours_share": 0.7, "round_share": 0.95, "night_share": 0.4, "out_of_state_share": 0.9,
                                 "ticket_variety": 2.5, "pass_through": 0.8}, g, b)["score"]
    assert typical < 20 and front > 75


# ---- network, change points, learning
def test_fronts_cluster(world):
    n = med(world["r"].network, "network_score", world)
    assert n["betting_front"] > 50 and n["legit"] < 5


def test_changepoint_finds_rented_handover(world):
    cp = world["r"].changepoints.merge(world["m"][["merchant_id", "label", "drift_week"]])
    rented = cp[cp.label == "rented"]
    true_week = pd.Timestamp(C.START_DATE) + pd.to_timedelta(rented.drift_week * 7, unit="D")
    assert (rented.shift_week.values == true_week.values).all()
    assert set(cp[cp.near_account_change].label) == {"rented"}


def test_learning_loop_trains_out_of_fold(world):
    r = world["r"]
    hist = learn.simulate_review_history(r.decisions, world["m"].set_index("merchant_id").label, audit_share=0.2)
    L = learn.learn(r.profile, hist)
    assert L["trained"] and L["cv_auc"] > 0.8
    assert L["probability"].notna().all()
    assert set(L["weights"].kind) >= {"worst weeks", "network"}


def test_learning_needs_enough_reviews(world):
    out = learn.learn(world["r"].profile, pd.DataFrame({"merchant_id": ["M0001"], "outcome": ["confirmed"]}))
    assert not out["trained"] and "Need at least" in out["message"]


# ---- actions
def test_every_flag_has_reasons(world):
    d = world["r"].decisions
    flagged = d[(d.level >= 1) & ~d.notes.str.contains("Phone and bank")]
    assert len(flagged) and (flagged.reason_1.str.len() > 0).all()


def test_no_reserve_without_corroboration(world):
    d = world["r"].decisions
    assert not ((d.level == 3) & ~d.network_link).any()


def test_honest_shops_left_alone(world):
    d = world["r"].decisions
    assert (d[d.label == "legit"].level >= 2).mean() < 0.02


def test_analyst_review_overrides_and_seeds_network(world):
    d = world["r"].decisions
    honest = d[d.label == "legit"].merchant_id.iloc[0]
    flagged = d[d.level >= 2].merchant_id.iloc[0]
    rv = pd.DataFrame({"merchant_id": [honest, flagged], "outcome": ["confirmed", "cleared"], "note": "", "source": "test"})
    d2 = engine.analyse(world["p"], reviews=rv).decisions.set_index("merchant_id")
    assert d2.loc[honest, "level"] == 4 and d2.loc[flagged, "level"] == 0
    assert d2.loc[honest, "network_score"] == 100  # confirmed merchants become seeds


def test_settings_change_results(world):
    strict = dataclasses.replace(C.Settings(), ask=30, friction=40, review=50, require_corroboration=False)
    a = world["r"].decisions
    b = engine.analyse(world["p"], strict).decisions
    assert (b.level >= 1).sum() > (a.level >= 1).sum()
    off = dataclasses.replace(C.Settings(), weights={f: 0.0 for f in C.FEATURES}, use_network=False)
    c = engine.analyse(world["p"], off).decisions
    assert c.drift_score.max() == 0


def test_cost_sweep_prefers_cheapest(world):
    d = world["r"].decisions
    sw = tuning.sweep(d, tuning.truth_series(d), tuning.Costs())
    best = tuning.best_threshold(sw)
    assert best.total_cost == sw.total_cost.min() and 0 <= best.threshold <= 100


# ---- bring your own data
def test_messy_upload_is_mapped_and_cleaned():
    t = schema.template_tables(10)
    tx = t["transactions"].rename(columns={"merchant_id": "Merchant Code", "ts": "Txn Time", "amount": "Amount (Rs)",
                                           "direction": "Dr/Cr", "counterparty_id": "Payer VPA"})
    tx["Dr/Cr"] = tx["Dr/Cr"].map({"in": "CR", "out": "DR"})
    tm = schema.guess_mapping("transactions", list(tx.columns))
    assert tm["ts"] == "Txn Time" and tm["amount"] == "Amount (Rs)" and tm["direction"] == "Dr/Cr"
    m = t["merchants"].rename(columns={"merchant_id": "MID", "category": "Business Type"})
    clean, rep = schema.clean({"merchants": schema.apply_mapping(m, "merchants", schema.guess_mapping("merchants", list(m.columns))),
                               "transactions": schema.apply_mapping(tx, "transactions", tm)})
    assert rep.ok and set(clean["transactions"].direction) == {"in", "out"}
    r = engine.analyse(engine.prepare(clean))
    assert len(r.decisions) == len(m)


def test_minimal_upload_three_columns():
    t = schema.template_tables(10)
    clean, rep = schema.clean({"merchants": t["merchants"][["merchant_id", "category"]],
                               "transactions": t["transactions"][["merchant_id", "ts", "amount"]]})
    assert rep.ok and any("switched off" in i for i in rep.info)
    f = features.build_features(clean["merchants"], clean["transactions"], clean["calendar"])
    assert f.out_of_state_share.isna().all() and f.round_share.notna().any()
    engine.analyse(engine.prepare(clean))


def test_missing_required_column_is_reported():
    _, rep = schema.clean({"merchants": pd.DataFrame({"merchant_id": ["A"]}),
                           "transactions": pd.DataFrame({"merchant_id": ["A"], "amount": [1]})})
    assert not rep.ok and any("category" in e for e in rep.errors)


def test_labels_not_used_as_features():
    for mod in (features, score, network, changepoint):
        src = inspect.getsource(mod).split("def main")[0]
        assert ".label" not in src and '"label"' not in src
