"""Step 4: the network layer. Who is connected to a known betting account?

Betting operators run many front merchants at once. These fronts give themselves
away through what they SHARE:
  * the same phone / device used to run several 'different' shops
  * the same bank (settlement) account receiving their money
  * the same customers (gamblers deposit with whichever front is live today)
  * the same payout accounts (winners and the operator's collection account)

We draw a graph: each merchant is a dot, each shared thing a line between dots.
Then we start from merchants we already KNOW are bad (their UPI IDs were found on
public betting websites / Telegram channels, or an analyst confirmed them) and run
'personalized PageRank', which spreads suspicion along the lines. Merchants
strongly tied to known-bad ones light up, even if their own behaviour looks clean.

We also look for COMMUNITIES (clusters of merchants densely tied to each other).
A cluster of 6 'unrelated' kirana stores sharing gamblers is itself a red flag,
even before any of them is on a known-bad list.

Output: data/network.csv  (network_score 0-100 + a plain-English reason)
        data/network_edges.csv  (one row per link type between two merchants)
"""
from __future__ import annotations

from itertools import combinations

import networkx as nx
import numpy as np
import pandas as pd
from scipy import sparse

from . import config as C

KIND_LABEL = {"device": "same device", "account": "same settlement bank account",
              "payers": "shared customers", "payouts": "shared payout accounts"}


def _shared_key_edges(df: pd.DataFrame, key: str, kind: str, base: float):
    df = df.dropna(subset=[key])
    for val, grp in df.groupby(key).merchant_id:
        ids = sorted(set(grp))
        if 1 < len(ids) <= 50:
            for a, b in combinations(ids, 2):
                yield a, b, kind, base, f"{KIND_LABEL[kind]} ({val})"


def _overlap_edges(pairs: pd.DataFrame, kind: str, min_common: int, min_jaccard: float):
    """Edges between merchants that share many counterparties (customers or payout accounts)."""
    pairs = pairs.dropna().drop_duplicates()
    if pairs.empty:
        return
    mids, mi = np.unique(pairs.merchant_id.astype(str), return_inverse=True)
    _, ci = np.unique(pairs.counterparty_id.astype(str), return_inverse=True)
    X = sparse.csr_matrix((np.ones(len(pairs)), (mi, ci)))
    common = sparse.triu(X @ X.T, k=1).tocoo()
    size = np.asarray(X.sum(1)).ravel()
    for a, b, c in zip(common.row, common.col, common.data):
        if c >= min_common:
            jac = c / (size[a] + size[b] - c)
            if jac >= min_jaccard:
                yield mids[a], mids[b], kind, min(5.0, jac * 10), f"{KIND_LABEL[kind]}: {int(c)} in common ({jac:.0%} overlap)"


def build_edges(m: pd.DataFrame, tx: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """All links between merchants, one row per (pair, kind). Base weight before settings."""
    devices = tx[["merchant_id", "device_id"]].drop_duplicates()
    accounts = pd.concat([
        m[["merchant_id", "settlement_account"]],
        events.loc[events.event == "settlement_account_change", ["merchant_id", "new_value"]]
              .rename(columns={"new_value": "settlement_account"}),
    ])
    payers = tx.loc[tx.direction == "in", ["merchant_id", "counterparty_id"]]
    payouts = tx.loc[tx.direction == "out", ["merchant_id", "counterparty_id"]]
    rows = [
        *_shared_key_edges(devices, "device_id", "device", 3.0),
        *_shared_key_edges(accounts, "settlement_account", "account", 3.0),
        *_overlap_edges(payers, "payers", 10, 0.05),
        *_overlap_edges(payouts, "payouts", 3, 0.05),
    ]
    e = pd.DataFrame(rows, columns=["a", "b", "kind", "base_weight", "why"])
    return e.drop_duplicates(["a", "b", "kind"]).reset_index(drop=True)


def graph_from_edges(merchant_ids, edges: pd.DataFrame, s: C.Settings | None = None) -> nx.Graph:
    s = s or C.Settings()
    G = nx.Graph()
    G.add_nodes_from(merchant_ids)
    for r in edges.itertuples(index=False):
        w = r.base_weight * s.edge_weights.get(r.kind, 1.0)  # multiplier set in Settings
        if w <= 0:
            continue
        if G.has_edge(r.a, r.b):
            G[r.a][r.b]["weight"] += w
            G[r.a][r.b]["why"].append(r.why)
        else:
            G.add_edge(r.a, r.b, weight=w, why=[r.why])
    return G


def communities(G: nx.Graph) -> pd.DataFrame:
    """Clusters of merchants densely linked to each other (Louvain method)."""
    H = G.subgraph([n for n in G if G.degree(n) > 0])
    rows = []
    if H.number_of_edges():
        for k, comm in enumerate(nx.community.louvain_communities(H, weight="weight", seed=C.SEED)):
            if len(comm) >= 3:
                for n in comm:
                    rows.append({"merchant_id": n, "cluster": f"C{k:03d}", "cluster_size": len(comm)})
    return pd.DataFrame(rows, columns=["merchant_id", "cluster", "cluster_size"])


def network_scores(G: nx.Graph, seeds: list[str]) -> pd.DataFrame:
    seeds = [s for s in seeds if s in G]
    if seeds and G.number_of_edges():
        pers = {n: (1.0 if n in seeds else 0.0) for n in G}
        pr = nx.pagerank(G, alpha=0.85, personalization=pers, weight="weight")
        ref = np.mean([pr[s] for s in seeds]) * 0.1
    else:
        pr, ref = {n: 0.0 for n in G}, 1.0
    rows = []
    for n in G:
        known = n in seeds
        score = 100.0 if known else float(min(100.0, 100 * pr[n] / ref)) if ref > 0 else 0.0
        best, why = "", ""
        nbrs = sorted(G[n], key=lambda x: pr[x] * G[n][x]["weight"], reverse=True)
        if nbrs and (score > 1 or not seeds):
            best = nbrs[0]
            why = "; ".join(sorted(set(G[n][best]["why"])))
        rows.append({"merchant_id": n, "network_score": round(score, 1), "known_bad": known,
                     "linked_to": best, "link_reason": why, "n_links": G.degree(n)})
    out = pd.DataFrame(rows)
    return out.merge(communities(G), on="merchant_id", how="left")


def run(m, tx, events, known_bad_ids, s: C.Settings | None = None, edges: pd.DataFrame | None = None):
    edges = build_edges(m, tx, events) if edges is None else edges
    G = graph_from_edges(m.merchant_id, edges, s)
    return network_scores(G, list(known_bad_ids)), edges, G


def main():
    m = pd.read_csv(C.DATA / "merchants.csv")
    tx = pd.read_csv(C.DATA / "transactions.csv", usecols=["merchant_id", "direction", "counterparty_id", "device_id"])
    ev = pd.read_csv(C.DATA / "account_events.csv")
    kb = pd.read_csv(C.DATA / "known_bad.csv")
    ns, edges, G = run(m, tx, ev, kb.merchant_id)
    ns.to_csv(C.DATA / "network.csv", index=False)
    edges.to_csv(C.DATA / "network_edges.csv", index=False)
    print(f"graph: {G.number_of_nodes()} merchants, {G.number_of_edges()} linked pairs, "
          f"{ns.cluster.nunique()} clusters of 3+")
    if "label" in m:
        print(ns.merge(m[["merchant_id", "label"]]).groupby("label").network_score.describe()[["mean", "50%", "max"]].round(1).to_string())
    return ns


if __name__ == "__main__":
    main()
