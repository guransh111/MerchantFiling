"""Tests use the hidden labels as ground truth. Run:  pytest -q

They build a small world (150 merchants) once, in a temporary folder, and check
that every step does what it promises.
"""
import numpy as np
import pandas as pd
import pytest

from src import config as C
from src import actions, features, generate, network, score


@pytest.fixture(scope="module")
def world(tmp_path_factory, monkeypatch_module):
    tmp = tmp_path_factory.mktemp("data")
    monkeypatch_module.setattr(C, "DATA", tmp)
    m, tx, cal, kb, ev, decl = generate.simulate(C.N_MERCHANTS_SMALL)
    f = features.build_features(m, tx, cal)
    w = score.score(f, m, "peer")
    s = score.merchant_summary(w)
    w_own = score.score(f, m, "own")
    s_own = score.merchant_summary(w_own)
    G = network.build_graph(m, tx, ev)
    ns = network.network_scores(G, kb.merchant_id.tolist())
    d = actions.decide(m, w, s, ns, decl, ev)
    return dict(m=m, tx=tx, cal=cal, kb=kb, f=f, w=w, s=s, s_own=s_own, ns=ns, d=d)


@pytest.fixture(scope="module")
def monkeypatch_module():
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


def by_label(df, col, world):
    return df.merge(world["m"][["merchant_id", "label"]]).groupby("label")[col].median()


# ---- step 1: synthetic data
def test_label_mix(world):
    counts = world["m"].label.value_counts()
    assert set(counts.index) == {"legit", "betting_front", "rented", "genuine_drifter"}
    assert counts["legit"] / len(world["m"]) > 0.85


def test_fronts_peak_on_match_days(world):
    tx, cal, m = world["tx"], world["cal"], world["m"]
    fronts = m.merchant_id[m.label == "betting_front"]
    t = tx[tx.merchant_id.isin(fronts) & (tx.direction == "in")]
    match_dates = set(cal.date[cal.is_match_day].dt.date)
    on_match = t.ts.dt.date.isin(match_dates)
    per_day_match = on_match.sum() / len(match_dates)
    per_day_other = (~on_match).sum() / (len(cal) - len(match_dates))
    assert per_day_match > 2 * per_day_other


def test_reproducible():
    a = generate.simulate(30)[0]
    b = generate.simulate(30)[0]
    pd.testing.assert_frame_equal(a, b)


# ---- step 2: features
def test_features_separate_fronts(world):
    med = world["f"].merge(world["m"][["merchant_id", "label"]]).groupby("label").median(numeric_only=True)
    assert med.loc["betting_front", "match_hours_share"] > med.loc["legit", "match_hours_share"]
    assert med.loc["betting_front", "round_share"] > med.loc["legit", "round_share"]
    assert med.loc["betting_front", "out_of_state_share"] > med.loc["legit", "out_of_state_share"]


# ---- step 3: drift score
def test_drifters_score_below_fronts(world):
    med = by_label(world["s"], "drift_score", world)
    assert med["genuine_drifter"] < med["betting_front"]
    assert med["legit"] < 60


def test_peer_beats_own_history_on_fronts(world):
    peer = by_label(world["s"], "drift_score", world)["betting_front"]
    own = by_label(world["s_own"], "drift_score", world)["betting_front"]
    assert peer > own + 20


# ---- step 4: network
def test_fronts_cluster(world):
    med = by_label(world["ns"], "network_score", world)
    assert med["betting_front"] > 50
    assert med["legit"] < 5


# ---- step 5: actions
def test_every_flag_has_reasons(world):
    flagged = world["d"][world["d"].level >= 1]
    assert len(flagged) > 0
    assert (flagged.reason_1.str.len() > 0).all()


def test_no_reserve_without_corroboration(world):
    d = world["d"]
    assert not ((d.level == 3) & ~d.network_link).any()


def test_honest_shops_left_alone(world):
    d = world["d"]
    legit = d[d.label == "legit"]
    assert (legit.level >= 2).mean() < 0.02


def test_labels_not_used_as_features():
    import inspect
    for mod in (features, score, network):
        src = inspect.getsource(mod)
        assert ".label" not in src and '"label"' not in src.split("def main")[0]
