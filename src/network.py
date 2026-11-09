"""Step 4: the network layer. Who is connected to a known betting account?

Betting operators run many front merchants at once. These fronts give themselves
away through what they SHARE:
  * the same phone / device used to run several 'different' shops
  * the same bank (settlement) account receiving their money
  * the same customers (gamblers deposit with whichever front is live today)
  * the same payout accounts (winners and the operator's collection account)

We draw a graph: each merchant is a dot, each shared thing a line between dots.
Then we start from merchants we already KNOW are bad (their UPI IDs were found on
public betting websites / Telegram channels: data/known_bad.csv) and run
'personalized PageRank', which spreads suspicion along the lines. Merchants
strongly tied to known-bad ones light up, even if their own behaviour looks clean.

Output: data/network.csv  (network_score 0-100 + a plain-English reason)
"""
from __future__ import annotations

from itertools import combinations

import networkx as nx
import numpy as np
import pandas as pd
from scipy import sparse

from . import config as C


def _shared_key_edges(df: pd.DataFrame, key: str, kind: str, weight: float, label: str):
    for val, grp in df.groupby(key).merchant_id:
        ids = sorted(set(grp))
        if 1 < len(ids) <= 50:
            for a, b in combinations(ids, 2):
                yield a, b, weight, f"{label} ({val})", kind


def _overlap_edges(pairs: pd.DataFrame, kind: str, min_common: int, min_jaccard: float, scale: float, label: str):
    """Edges between merchants that share many counterparties (customers or payout accounts)."""
    pairs = pairs.drop_duplicates()
    mids, mi = np.unique(pairs.merchant_id, return_inverse=True)
    _, ci = np.unique(pairs.counterparty_id, return_inverse=True)
    X = sparse.csr_matrix((np.ones(len(pairs)), (mi, ci)))
    common = (X @ X.T).tocoo()
    size = np.asarray(X.sum(1)).ravel()
    for a, b, c in zip(common.row, common.col, common.data):
        if a < b and c >= min_common:
            jac = c / (size[a] + size[b] - c)
            if jac >= min_jaccard:
                yield mids[a], mids[b], min(5.0, jac * scale), f"{label}: {int(c)} in common ({jac:.0%} overlap)", kind


def build_graph(m: pd.DataFrame, tx: pd.DataFrame, events: pd.DataFrame) -> nx.Graph:
    G = nx.Graph()
    G.add_nodes_from(m.merchant_id)
    devices = tx[["merchant_id", "device_id"]].drop_duplicates()
    accounts = pd.concat([
        m[["merchant_id", "settlement_account"]],
        events.loc[events.event == "settlement_account_change", ["merchant_id", "new_value"]]
              .rename(columns={"new_value": "settlement_account"}),
    ])
    payers = tx.loc[tx.direction == "in", ["merchant_id", "counterparty_id"]]
    payouts = tx.loc[tx.direction == "out", ["merchant_id", "counterparty_id"]]
    edges = [
        *_shared_key_edges(devices, "device_id", "device", 3.0, "same device"),
        *_shared_key_edges(accounts, "settlement_account", "account", 3.0, "same settlement bank account"),
        *_overlap_edges(payers, "payers", 10, 0.05, 10, "shared customers"),
        *_overlap_edges(payouts, "payouts", 3, 0.05, 10, "shared payout accounts"),
    ]
    for a, b, w, why, kind in edges:
        if G.has_edge(a, b):
            G[a][b]["weight"] += w
            G[a][b]["why"].append(why)
        else:
            G.add_edge(a, b, weight=w, why=[why])
    return G


def network_scores(G: nx.Graph, seeds: list[str]) -> pd.DataFrame:
    seeds = [s for s in seeds if s in G]
    pers = {n: (1.0 if n in seeds else 0.0) for n in G}
    pr = nx.pagerank(G, alpha=0.85, personalization=pers, weight="weight") if seeds else {n: 0 for n in G}
    ref = np.mean([pr[s] for s in seeds]) * 0.1 if seeds else 1
    rows = []
    for n in G:
        known = n in seeds
        score = 100.0 if known else float(min(100.0, 100 * pr[n] / ref))
        # explain: the neighbour that passes on the most suspicion
        best, why = None, ""
        nbrs = sorted(G[n], key=lambda x: pr[x] * G[n][x]["weight"], reverse=True)
        if nbrs and score > 1:
            best = nbrs[0]
            why = "; ".join(sorted(set(G[n][best]["why"])))
        rows.append({
            "merchant_id": n, "network_score": round(score, 1), "known_bad": known,
            "linked_to": best or "", "link_reason": why, "n_links": G.degree(n),
        })
    return pd.DataFrame(rows)


def main():
    m = pd.read_csv(C.DATA / "merchants.csv")
    tx = pd.read_csv(C.DATA / "transactions.csv", usecols=["merchant_id", "direction", "counterparty_id", "device_id"])
    ev = pd.read_csv(C.DATA / "account_events.csv")
    kb = pd.read_csv(C.DATA / "known_bad.csv")
    G = build_graph(m, tx, ev)
    ns = network_scores(G, kb.merchant_id.tolist())
    ns.to_csv(C.DATA / "network.csv", index=False)
    edges = pd.DataFrame([(a, b, d["weight"], "; ".join(d["why"])) for a, b, d in G.edges(data=True)],
                         columns=["a", "b", "weight", "why"])
    edges.to_csv(C.DATA / "network_edges.csv", index=False)
    print(f"graph: {G.number_of_nodes()} merchants, {G.number_of_edges()} links")
    print(ns.merge(m[["merchant_id", "label"]]).groupby("label").network_score.describe()[["mean", "50%", "max"]].round(1).to_string())
    return ns


if __name__ == "__main__":
    main()
