"""Overview, risk queue and merchant drill-down (with analyst review)."""
from __future__ import annotations

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

import state
from src import config as C
from src.actions import peer_phrase


def _with_truth(df: pd.DataFrame, d: pd.DataFrame) -> pd.DataFrame:
    if st.session_state.reveal and "label" in d:
        df = df.copy()
        df["hidden truth"] = df.merchant_id.map(d.set_index("merchant_id").label.map(lambda x: state.LABEL_NAME.get(x, x)))
    return df


# ---------------------------------------------------------------- overview
def overview():
    r = state.results()
    d = r.decisions
    p = state.prepared()
    st.title("Overview")
    st.caption(f"Dataset: **{p.name}**")
    cols = st.columns(6)
    cols[0].metric("Merchants", f"{len(d):,}")
    for i in range(5):
        cols[i + 1].metric(C.LEVEL_SHORT[i], int((d.level == i).sum()))

    vol = r.weekly.groupby("merchant_id").inflow.sum()
    under = vol[vol.index.isin(d.merchant_id[d.level >= 2])].sum() / vol.sum() if vol.sum() else 0
    asked = (d.level == 1).sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("Payment volume under friction or worse", f"{under:.1%}",
              help="Business cost of the current settings: share of all money received by merchants at Friction or above")
    c2.metric("Merchants asked a question", int(asked), help="Level 1: a neutral prompt, no restriction")
    c3.metric("Analyst decisions this session", len(st.session_state.reviews))

    left, right = st.columns([3, 2])
    with left:
        st.markdown("**What the system recommends**")
        lv = d.level.value_counts().reindex(range(5), fill_value=0).rename_axis("level").reset_index(name="merchants")
        lv["action"] = lv.level.map(C.LEVEL_SHORT)
        lv["color"] = lv.level.map(state.LEVEL_COLOR)
        ch = alt.Chart(lv).mark_bar(cornerRadiusEnd=4).encode(
            y=alt.Y("action:N", sort=list(C.LEVEL_SHORT.values()), title=None),
            x=alt.X("merchants:Q", title="Merchants", scale=alt.Scale(type="symlog")),
            color=alt.Color("color:N", scale=None), tooltip=["action", "merchants"])
        txt = ch.mark_text(align="left", dx=4).encode(text="merchants:Q", color=alt.value("#52514e"))
        st.altair_chart((ch + txt).properties(height=200), width="stretch")
        st.caption("Log scale: most merchants are never touched.")
    with right:
        st.markdown("**Most common main reason (flagged merchants)**")
        flagged = d[d.level >= 1]
        if len(flagged):
            reasons = flagged.reason_1.str.split(":").str[0].replace("", "No behaviour reason (network / account change)")
            rc = reasons.value_counts().rename_axis("reason").reset_index(name="merchants")[["merchants", "reason"]]
            st.dataframe(rc, hide_index=True, width="stretch")
        else:
            st.info("No merchant is flagged under the current settings.")

    st.markdown("**Which signals this dataset supports**")
    f = state.prepared().features
    cov = pd.DataFrame({"signal": [C.SHORT_NAME[x] for x in C.FEATURES],
                        "weeks with data": [f[x].notna().mean() for x in C.FEATURES]})
    st.dataframe(cov, hide_index=True, width="stretch",
                 column_config={"weeks with data": st.column_config.ProgressColumn(min_value=0, max_value=1, format="percent")})
    if state.has_truth():
        bad = d.label.isin(["betting_front", "rented"])
        st.info(f"This dataset has a hidden truth. Bad merchants at Friction or above: **{(d[bad].level >= 2).mean():.0%}**. "
                f"Honest merchants at Friction or above: **{int((~bad & (d.level >= 2)).sum())}**. See **Performance** for detail.")


# ---------------------------------------------------------------- queue
def queue():
    r = state.results()
    d = r.decisions
    st.title("Risk queue")
    c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
    levels = c1.multiselect("Action", list(C.LEVEL_SHORT.values()), default=["Ask", "Friction", "Review", "Offboard"])
    cats = c2.multiselect("Declared category", sorted(d.category.unique()))
    min_risk = c3.number_input("Min risk", 0, 100, 0)
    search = c4.text_input("Search ID")
    v = d[d.level.map(C.LEVEL_SHORT).isin(levels) & (d.risk_score >= min_risk)]
    if cats:
        v = v[v.category.isin(cats)]
    if search:
        v = v[v.merchant_id.str.contains(search, case=False)]
    show = v[["merchant_id", "category", "city", "risk_score", "drift_score", "network_score", "learned_prob",
              "anomaly_pct", "level", "reason_1", "notes"]].copy()
    show["action"] = show.level.map(C.LEVEL_SHORT)
    cb, _ = state.cases()
    if len(cb):
        show["case"] = show.merchant_id.map(cb.drop_duplicates("merchant_id", keep="last").set_index("merchant_id").status).fillna("")
    show = _with_truth(show.drop(columns="level"), d)
    st.caption(f"{len(v):,} merchants. Click a column to sort. Open **Merchant drill-down** for the full case file.")
    st.dataframe(show, hide_index=True, width="stretch", height=560, column_config={
        "risk_score": st.column_config.ProgressColumn("Risk", min_value=0, max_value=100, format="%.0f"),
        "drift_score": st.column_config.NumberColumn("Drift", format="%.0f"),
        "network_score": st.column_config.NumberColumn("Network", format="%.0f"),
        "learned_prob": st.column_config.NumberColumn("Learned", format="percent", help="Learning-loop probability"),
        "anomaly_pct": st.column_config.NumberColumn("Anomaly", format="%.0f", help="Percentile; 100 = most unusual"),
        "reason_1": "Main reason", "notes": "Notes"})
    st.download_button("Download all decisions (CSV)", d.to_csv(index=False), "trustloop_decisions.csv")


# ---------------------------------------------------------------- merchant drill-down
def _hour_profile(mid: str, peer_ids) -> pd.DataFrame | None:
    tx = st.session_state.transactions
    if tx is None:
        return None
    t = tx[(tx.direction == "in") & tx.merchant_id.isin(set(peer_ids) | {mid})]
    t = t.assign(hour=t.ts.dt.hour, who=np.where(t.merchant_id == mid, "This merchant", "Peers (median shop)"))
    mine = t[t.who == "This merchant"].groupby("hour").amount.sum()
    mine = (mine / mine.sum()).rename("This merchant")
    per = t[t.who != "This merchant"].groupby(["merchant_id", "hour"]).amount.sum()
    per = per / per.groupby(level=0).transform("sum")
    peers = per.groupby(level=1).median()
    peers = (peers / peers.sum()).rename("Typical peer")
    out = pd.concat([mine, peers], axis=1).reindex(range(24), fill_value=0).fillna(0).reset_index(names="hour")
    return out.melt("hour", var_name="who", value_name="share")


def merchant():
    r = state.results()
    d = r.decisions
    st.title("Merchant drill-down")
    ids = d.merchant_id.tolist()
    default = st.session_state.get("focus_merchant")
    mid = st.selectbox("Merchant (sorted by action, then risk)", ids, index=ids.index(default) if default in ids else 0,
                       format_func=lambda x: state.merchant_label(d, x))
    st.session_state.focus_merchant = mid
    row = d.set_index("merchant_id").loc[mid]
    mw = r.weekly[r.weekly.merchant_id == mid].sort_values("week_start")

    head, act = st.columns([3, 2])
    with head:
        turnover = f" · expects ₹{row.declared_monthly_turnover:,.0f}/month" if pd.notna(row.declared_monthly_turnover) else ""
        st.markdown(f"### {mid} {state.level_badge(int(row.level))}", unsafe_allow_html=True)
        st.markdown(f"**Declared:** {str(row.category).replace('_', ' ')} · {row.city} (tier {row.tier}){turnover}")
        st.markdown(f"**Recommended action:** {row.action}")
        if st.session_state.reveal and "label" in d:
            st.info(f"Hidden truth: **{state.LABEL_NAME.get(row.label, row.label)}**"
                    + (f" ({row.drift_type})" if isinstance(row.get("drift_type"), str) and row.drift_type else ""))
    with act:
        m = st.columns(3)
        m[0].metric("Risk", f"{row.risk_score:.0f}")
        m[1].metric("Drift", f"{row.drift_score:.0f}")
        m[2].metric("Network", f"{row.network_score:.0f}")
        m = st.columns(2)
        m[0].metric("Learned model", f"{row.learned_prob:.0%}" if pd.notna(row.learned_prob) else "n/a",
                    help="Probability it resembles cases analysts confirmed before")
        m[1].metric("Anomaly percentile", f"{row.anomaly_pct:.0f}" if pd.notna(row.anomaly_pct) else "n/a",
                    help="How unusual its overall profile is (no labels used)")

    c1, c2 = st.columns([2, 3])
    with c1:
        st.markdown("**Why**")
        any_reason = False
        for x in [row.reason_1, row.reason_2, row.reason_3]:
            if isinstance(x, str) and x:
                st.markdown(f"- {x}")
                any_reason = True
        if not any_reason:
            st.markdown("- Behaviour is in line with similar merchants.")
        if isinstance(row.notes, str) and row.notes:
            st.markdown("**Notes**")
            for n in row.notes.split(" | "):
                st.markdown(f"- {n}")
    with c2:
        st.markdown("**Weekly drift score** (dashed = Ask threshold; red rule = detected behaviour shift)")
        layers = [alt.Chart(mw).mark_line(strokeWidth=2, color="#2a78d6").encode(
            x=alt.X("week_start:T", title=None),
            y=alt.Y("drift_score:Q", title="Drift score", scale=alt.Scale(domain=[0, 100])),
            tooltip=[alt.Tooltip("week_start:T", title="Week"), alt.Tooltip("drift_score:Q", format=".0f", title="Score"),
                     alt.Tooltip("inflow:Q", format=",.0f", title="Money in (₹)"), alt.Tooltip("n_txns:Q", title="Payments")]),
            alt.Chart(pd.DataFrame({"y": [st.session_state.tl_settings.ask]})).mark_rule(strokeDash=[4, 4], color="#8a8984").encode(y="y:Q")]
        if pd.notna(row.shift_week) and pd.notna(row.shift_jump) and row.shift_jump >= 20:
            layers.append(alt.Chart(pd.DataFrame({"x": [pd.Timestamp(row.shift_week)]})).mark_rule(color="#d95926", strokeWidth=2).encode(x="x:T"))
        st.altair_chart(alt.layer(*layers).properties(height=230), width="stretch")

    st.markdown("**This merchant vs its peers, in its worst week**")
    if len(mw):
        peak = mw.loc[mw.drift_score.idxmax()]
        t = pd.DataFrame([{"signal": C.SHORT_NAME[f], "this merchant": peak[f], "typical peer": peak[f + "__peer"],
                           "z (spreads from normal)": peak[f + "__z"], "risk points": peak[f + "__pts"]} for f in C.FEATURES])
        st.dataframe(t.sort_values("risk points", ascending=False), hide_index=True, width="stretch", column_config={
            "this merchant": st.column_config.NumberColumn(format="%.2f"),
            "typical peer": st.column_config.NumberColumn(format="%.2f"),
            "z (spreads from normal)": st.column_config.NumberColumn(format="%.1f"),
            "risk points": st.column_config.ProgressColumn(min_value=0, max_value=st.session_state.tl_settings.z_cap * 1.2, format="%.1f")})
        st.caption(f"Peers: {peer_phrase(peak.peer_group)}, week of {pd.Timestamp(peak.week_start):%d %b %Y}.")
        if "payer_states" in peak and pd.notna(peak.payer_states):
            same = r.weekly[(r.weekly.peer_group == peak.peer_group) & (r.weekly.week_start == peak.week_start)]
            st.caption(f"Distinct payer states that week: **{int(peak.payer_states)}** "
                       f"(typical peer: {same.payer_states.median():.0f}).")
    if pd.notna(row.get("gst_annual_turnover", float("nan"))) or pd.notna(row.get("upi_annual_takings", float("nan"))):
        g1, g2, g3 = st.columns(3)
        g1.metric("UPI takings (annualised)", f"₹{row.upi_annual_takings / 1e5:,.1f} lakh" if pd.notna(row.upi_annual_takings) else "n/a")
        g2.metric("GST-declared turnover", f"₹{row.gst_annual_turnover / 1e5:,.1f} lakh" if pd.notna(row.gst_annual_turnover) else "not registered")
        g3.metric("UPI ÷ GST", f"{row.gst_ratio:.1f}x" if pd.notna(row.gst_ratio) else "n/a",
                  help=f"Flagged at {st.session_state.tl_settings.gst_ratio_flag:.1f}x or more")

        peers = r.weekly[(r.weekly.peer_group == peak.peer_group) & (r.weekly.week_start == peak.week_start)].merchant_id
        hp = _hour_profile(mid, peers)
        if hp is not None and len(hp):
            st.markdown("**When the money arrives (share of value by hour of day)**")
            st.altair_chart(alt.Chart(hp).mark_line(point=True, strokeWidth=2).encode(
                x=alt.X("hour:O", title="Hour of day"), y=alt.Y("share:Q", axis=alt.Axis(format="%"), title=None),
                color=alt.Color("who:N", scale=alt.Scale(range=["#2a78d6", "#8a8984"]), legend=alt.Legend(orient="top", title=None)),
                tooltip=["who", "hour", alt.Tooltip("share:Q", format=".1%")]).properties(height=220), width="stretch")

    links = r.edges[(r.edges.a == mid) | (r.edges.b == mid)].copy()
    if len(links):
        links["other merchant"] = links.a.where(links.b == mid, links.b)
        links = links.merge(d[["merchant_id", "risk_score", "level", "known_bad"]], left_on="other merchant", right_on="merchant_id")
        links["their action"] = links.level.map(C.LEVEL_SHORT)
        st.markdown("**Network links** (what this merchant shares with others)")
        st.dataframe(links[["other merchant", "why", "risk_score", "their action", "known_bad"]].sort_values("risk_score", ascending=False),
                     hide_index=True, width="stretch")

    tx = st.session_state.transactions
    if tx is not None:
        with st.expander("Latest payments"):
            st.dataframe(tx[tx.merchant_id == mid].tail(100).iloc[::-1], hide_index=True, width="stretch")

    st.divider()
    st.markdown("### Analyst decision")
    st.caption("Your decision overrides the system for this merchant, adds a label for the learning loop, and (if "
               "confirmed) makes this merchant a new starting point for the network search.")
    current = st.session_state.reviews.set_index("merchant_id").outcome.get(mid) if len(st.session_state.reviews) else None
    if current:
        st.markdown(f"Current decision: **{current}**")
    note = st.text_input("Note (evidence, reasoning)", key=f"note_{mid}")
    b1, b2, b3 = st.columns(3)
    if b1.button("Confirm: betting / misuse", type="primary"):
        state.add_review(mid, "confirmed", note)
        st.rerun()
    if b2.button("Clear: genuine business"):
        state.add_review(mid, "cleared", note)
        st.rerun()
    if current and b3.button("Undo decision"):
        state.add_review(mid, "undo", "")
        st.rerun()
    if row.level >= 3:
        from src import reporting as RPT
        st.download_button("Download draft STR for FIU-IND (Markdown)", RPT.str_draft(mid, r, state.prepared()),
                           f"STR_draft_{mid}.md")
