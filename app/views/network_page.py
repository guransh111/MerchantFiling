"""Network explorer: clusters of linked merchants and a picture of who is tied to whom."""
from __future__ import annotations

import altair as alt
import networkx as nx
import pandas as pd
import streamlit as st

import state
from src import config as C
from src.network import graph_from_edges


def page():
    st.title("Network")
    st.markdown("Each dot is a merchant; a line means they share a phone, a bank account, many customers or payout "
                "accounts. Betting operators run **families** of fronts, so they show up as tight clusters.")
    r = state.results()
    d = r.decisions.set_index("merchant_id")
    if r.edges.empty:
        st.info("No links found. Upload payer IDs, device IDs or settlement accounts to enable the network.")
        return
    G = graph_from_edges(d.index, r.edges, st.session_state.tl_settings)

    net = r.network.dropna(subset=["cluster"])
    if len(net):
        cl = net.groupby("cluster").agg(merchants=("merchant_id", "count"), known_bad=("known_bad", "sum")).reset_index()
        lv = d.level.reindex(net.merchant_id).to_numpy()
        net = net.assign(flagged=lv >= 2, risk=d.risk_score.reindex(net.merchant_id).to_numpy())
        cl = cl.merge(net.groupby("cluster").agg(at_friction_or_above=("flagged", "sum"), avg_risk=("risk", "mean")).reset_index())
        cl = cl.sort_values(["avg_risk", "merchants"], ascending=False)
        st.markdown("**Clusters of 3+ densely linked merchants**")
        st.dataframe(cl, hide_index=True, width="stretch",
                     column_config={"avg_risk": st.column_config.ProgressColumn("Avg risk", min_value=0, max_value=100, format="%.0f")})

    c1, c2 = st.columns([3, 1])
    linked = [n for n in d.index if G.degree(n) > 0]
    start = st.session_state.get("focus_merchant")
    options = sorted(linked, key=lambda x: -d.risk_score[x])
    mid = c1.selectbox("Centre the picture on", options, index=options.index(start) if start in options else 0,
                       format_func=lambda x: state.merchant_label(r.decisions, x))
    hops = c2.radio("Steps out", [1, 2], index=1, horizontal=True)
    nodes = nx.ego_graph(G, mid, radius=hops)
    if nodes.number_of_nodes() > 80:
        keep = sorted(nodes, key=lambda x: -d.risk_score[x])[:80]
        nodes = G.subgraph(set(keep) | {mid})
    pos = nx.spring_layout(nodes, seed=C.SEED, weight="weight")
    nd = pd.DataFrame([{"merchant_id": n, "x": pos[n][0], "y": pos[n][1], "risk": d.risk_score[n],
                        "action": C.LEVEL_SHORT[int(d.level[n])], "level": int(d.level[n]),
                        "category": d.category[n], "known_bad": bool(d.known_bad[n]), "centre": n == mid} for n in nodes])
    if st.session_state.reveal and "label" in d:
        nd["truth"] = nd.merchant_id.map(d.label).map(lambda x: state.LABEL_NAME.get(x, x))
    ed = pd.DataFrame([{"x": pos[a][0], "y": pos[a][1], "x2": pos[b][0], "y2": pos[b][1], "w": dd["weight"],
                        "why": "; ".join(dd["why"])} for a, b, dd in nodes.edges(data=True)])
    lines = alt.Chart(ed).mark_rule(color="#b8b7b0").encode(
        x=alt.X("x:Q", axis=None), y=alt.Y("y:Q", axis=None), x2="x2", y2="y2",
        strokeWidth=alt.StrokeWidth("w:Q", scale=alt.Scale(range=[0.5, 4]), legend=None), tooltip=["why"])
    tips = ["merchant_id", "category", "action", alt.Tooltip("risk:Q", format=".0f"), "known_bad"] + (["truth"] if "truth" in nd else [])
    dots = alt.Chart(nd).mark_circle(stroke="white", strokeWidth=1.5, opacity=1).encode(
        x="x:Q", y="y:Q", size=alt.Size("risk:Q", scale=alt.Scale(range=[60, 600]), legend=None),
        color=alt.Color("action:N", scale=alt.Scale(domain=list(C.LEVEL_SHORT.values()),
                                                    range=[state.LEVEL_COLOR[i] for i in range(5)]),
                        legend=alt.Legend(orient="top", title=None)),
        tooltip=tips)
    ring = alt.Chart(nd[nd.known_bad | nd.centre]).mark_circle(filled=False, color="#111", strokeWidth=2, size=900).encode(x="x:Q", y="y:Q")
    st.altair_chart((lines + dots + ring).properties(height=520).configure_view(strokeWidth=0), width="stretch")
    st.caption("Bigger dot = higher risk. Black ring = the centre merchant or a known-bad merchant. Hover a line to see what is shared.")
