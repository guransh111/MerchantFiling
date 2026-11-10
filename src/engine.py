"""The engine: run the whole TrustLoop pipeline on ANY dataset in one call.

    prepared = prepare(tables)                     # slow part: payments -> weekly signals, links
    results  = analyse(prepared, Settings(), ...)  # fast part: scores, network, decisions (seconds)

Splitting it this way lets the dashboard re-run `analyse` instantly whenever the user
moves a slider (weights, thresholds) or confirms/clears a case.

`tables` is a dict of DataFrames: merchants, transactions (required), and optionally
known_bad, declarations, account_events, calendar. Use schema.clean() first on raw uploads.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from . import changepoint as CP
from . import config as C
from . import learn as L
from . import network as N
from . import score as S
from .actions import decide
from .features import build_features


@dataclass
class Prepared:
    merchants: pd.DataFrame
    features: pd.DataFrame
    edges: pd.DataFrame
    known_bad: pd.DataFrame
    declarations: pd.DataFrame
    account_events: pd.DataFrame
    review_history: pd.DataFrame = field(default_factory=pd.DataFrame)  # past analyst decisions (training data)
    name: str = "dataset"
    identifiers: pd.DataFrame = field(default_factory=pd.DataFrame)  # merchant_id, kind, value (devices, accounts, UPI IDs)


@dataclass
class Results:
    settings: C.Settings
    decisions: pd.DataFrame
    weekly: pd.DataFrame
    scores: pd.DataFrame
    network: pd.DataFrame
    changepoints: pd.DataFrame
    profile: pd.DataFrame
    learning: dict
    baselines: pd.DataFrame
    edges: pd.DataFrame


def _say(progress, msg):
    if progress:
        progress(msg)


def identifiers(m: pd.DataFrame, tx: pd.DataFrame, events: pd.DataFrame | None = None) -> pd.DataFrame:
    """Every identifier tied to each merchant: UPI ID, settlement accounts (incl. changes), devices used.
    Used for regulator reports and for privacy-preserving sharing with other payment providers."""
    parts = []
    if "upi_id" in m:
        parts.append(m[["merchant_id", "upi_id"]].rename(columns={"upi_id": "value"}).assign(kind="upi_id"))
    if "settlement_account" in m:
        parts.append(m[["merchant_id", "settlement_account"]].rename(columns={"settlement_account": "value"}).assign(kind="settlement_account"))
    if events is not None and len(events):
        e = events[events.event == "settlement_account_change"][["merchant_id", "new_value"]]
        parts.append(e.rename(columns={"new_value": "value"}).assign(kind="settlement_account"))
        d = events[events.event == "device_change"][["merchant_id", "new_value"]]
        parts.append(d.rename(columns={"new_value": "value"}).assign(kind="device_id"))
    if "device_id" in tx:
        parts.append(tx[["merchant_id", "device_id"]].drop_duplicates().rename(columns={"device_id": "value"}).assign(kind="device_id"))
    if not parts:
        return pd.DataFrame(columns=["merchant_id", "kind", "value"])
    out = pd.concat(parts, ignore_index=True).dropna(subset=["value"])
    out["value"] = out.value.astype(str)
    return out[["merchant_id", "kind", "value"]].drop_duplicates().reset_index(drop=True)


def prepare(tables: dict, start=None, progress=None, name: str = "dataset") -> Prepared:
    m, tx = tables["merchants"], tables["transactions"]
    _say(progress, f"Calculating weekly signals from {len(tx):,} payments...")
    f = build_features(m, tx, tables["calendar"], start=start)
    _say(progress, "Finding shared phones, bank accounts and customers...")
    edges = N.build_edges(m, tx, tables.get("account_events", pd.DataFrame(columns=["merchant_id", "event", "new_value"])))
    ids = identifiers(m, tx, tables.get("account_events"))
    return Prepared(merchants=m, features=f, edges=edges, identifiers=ids,
                    known_bad=tables.get("known_bad", pd.DataFrame(columns=["merchant_id"])),
                    declarations=tables.get("declarations", pd.DataFrame(columns=["merchant_id", "declared_change"])),
                    account_events=tables.get("account_events", pd.DataFrame(columns=["merchant_id", "date", "event"])),
                    name=name)


def analyse(p: Prepared, s: C.Settings | None = None, reviews: pd.DataFrame | None = None,
            use_history: bool = True, progress=None) -> Results:
    """reviews = decisions made by analysts in this session (they override the system and
    also train the learning loop). p.review_history = older decisions, used for training only."""
    s = s or C.Settings()
    m = p.merchants
    _say(progress, "Comparing every merchant with its peers, week by week...")
    weekly = S.score(p.features, m, "peer", s)
    scores = S.merchant_summary(weekly, s.worst_weeks)
    _say(progress, "Spreading suspicion from known-bad merchants through the network...")
    G = N.graph_from_edges(m.merchant_id, p.edges, s)
    seeds = set(p.known_bad.merchant_id.astype(str))
    if reviews is not None and len(reviews):  # analyst-confirmed merchants become new seeds
        seeds |= set(reviews.loc[reviews.outcome == "confirmed", "merchant_id"])
    net = N.network_scores(G, sorted(seeds))
    _say(progress, "Looking for the week behaviour changed...")
    cps = CP.detect(weekly, p.account_events)
    profile = L.merchant_profile(weekly, net, s.worst_weeks)
    anomaly = L.anomaly_scores(profile)
    train = [x for x in [p.review_history if use_history else None, reviews] if x is not None and len(x)]
    train = pd.concat(train, ignore_index=True) if train else pd.DataFrame(columns=["merchant_id", "outcome"])
    _say(progress, "Learning from past reviewer decisions...")
    learned = L.learn(profile, train)
    _say(progress, "Deciding actions and writing reasons...")
    d = decide(m, weekly, scores, net, p.declarations, p.account_events, s, changepoints=cps,
               learned=learned["probability"] if learned["trained"] else None, anomaly=anomaly, reviews=reviews)
    return Results(settings=s, decisions=d, weekly=weekly, scores=scores, network=net, changepoints=cps,
                   profile=profile, learning=learned, baselines=S.peer_baselines(weekly), edges=p.edges)


def demo_review_history(p: Prepared, s: C.Settings | None = None) -> pd.DataFrame:
    """For synthetic data with labels: simulate last quarter's analyst decisions, so the
    learning loop has something to learn from. Uses a first pass WITHOUT learning."""
    if "label" not in p.merchants:
        return pd.DataFrame()
    first = analyse(Prepared(**{**p.__dict__, "review_history": pd.DataFrame()}), s, use_history=False)
    truth = p.merchants.set_index("merchant_id").label
    return L.simulate_review_history(first.decisions, truth)


def run(tables: dict, s: C.Settings | None = None, reviews=None, progress=None, simulate_history: bool = True,
        start=None, name: str = "dataset") -> tuple[Prepared, Results]:
    p = prepare(tables, start=start, progress=progress, name=name)
    if simulate_history and "label" in p.merchants:
        p.review_history = demo_review_history(p, s)
    return p, analyse(p, s, reviews, progress=progress)


# ----------------------------------------------------------------- saving / loading the demo
def save(p: Prepared, r: Results, folder=C.DATA):
    p.merchants.to_csv(folder / "merchants.csv", index=False)
    p.features.round({c: 6 for c in C.FEATURES}).to_csv(folder / "features.csv.gz", index=False)
    p.edges.to_csv(folder / "network_edges.csv", index=False)
    p.known_bad.to_csv(folder / "known_bad.csv", index=False)
    p.declarations.to_csv(folder / "declarations.csv", index=False)
    p.account_events.to_csv(folder / "account_events.csv", index=False)
    p.review_history.to_csv(folder / "review_history.csv", index=False)
    p.identifiers.to_csv(folder / "identifiers.csv", index=False)
    r.decisions.to_csv(folder / "decisions.csv", index=False)
    r.scores.to_csv(folder / "scores.csv", index=False)
    r.network.to_csv(folder / "network.csv", index=False)
    r.changepoints.to_csv(folder / "changepoints.csv", index=False)
    r.baselines.to_csv(folder / "peer_baselines.csv", index=False)
    if r.learning["trained"]:
        r.learning["weights"].to_csv(folder / "learned_weights.csv", index=False)


def load_prepared(folder=C.DATA, name: str = "Demo (simulated 1,000 merchants)") -> Prepared:
    rd = lambda n, **k: pd.read_csv(folder / n, **k) if (folder / n).exists() else pd.DataFrame()
    hist = rd("review_history.csv")
    return Prepared(merchants=rd("merchants.csv"), features=rd("features.csv.gz", parse_dates=["week_start"]),
                    edges=rd("network_edges.csv"), known_bad=rd("known_bad.csv"),
                    declarations=rd("declarations.csv"), account_events=rd("account_events.csv"),
                    review_history=hist, name=name, identifiers=rd("identifiers.csv"))


def main():
    """Run on the synthetic data in data/ (created by generate.py) and save everything."""
    m = pd.read_csv(C.DATA / "merchants.csv")
    tx = pd.read_csv(C.DATA / "transactions.csv", parse_dates=["ts"])
    cal = pd.read_csv(C.DATA / "calendar.csv", parse_dates=["date"])
    tables = {"merchants": m, "transactions": tx, "calendar": cal,
              "known_bad": pd.read_csv(C.DATA / "known_bad.csv"),
              "declarations": pd.read_csv(C.DATA / "declarations.csv"),
              "account_events": pd.read_csv(C.DATA / "account_events.csv")}
    p, r = run(tables, start=C.START_DATE, progress=print, name="Demo (simulated)")
    save(p, r)
    # own-history baseline (for the comparison in evaluate.py)
    own = S.score(p.features, m, "own")
    own.to_csv(C.DATA / "scores_weekly_nopeer.csv", index=False)
    S.merchant_summary(own).to_csv(C.DATA / "scores_nopeer.csv", index=False)
    r.weekly.to_csv(C.DATA / "scores_weekly.csv", index=False)
    lr = r.learning
    print(f"learning loop: {lr['message']} cross-validated AUC={lr['cv_auc']:.2f}" if lr["trained"] else lr["message"])
    if "label" in r.decisions:
        print(pd.crosstab(r.decisions.label, r.decisions.action).to_string())
    return p, r


if __name__ == "__main__":
    main()
