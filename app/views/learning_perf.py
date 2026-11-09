"""Learning loop, audit queue, and performance / cost-based threshold tuning."""
from __future__ import annotations

import dataclasses

import altair as alt
import pandas as pd
import streamlit as st

import state
from src import config as C
from src.learn import suggested_weights
from src.tuning import Costs, best_threshold, sweep, truth_series


def learning():
    st.title("Learning loop")
    r = state.results()
    L = r.learning
    p = state.prepared()
    st.markdown("Every time an analyst **confirms** or **clears** a case, that becomes a label. The system fits a "
                "logistic regression to learn which signals actually separated confirmed fronts from cleared merchants, "
                "and suggests new weights. It is a learned second opinion that you can inspect, not a black box.")
    c = st.columns(4)
    c[0].metric("Past reviews (history)", len(p.review_history))
    c[1].metric("Your decisions this session", len(st.session_state.reviews))
    c[2].metric("Confirmed / cleared used", f"{L['n_confirmed']} / {L['n_cleared']}")
    c[3].metric("Cross-validated AUC", f"{L['cv_auc']:.2f}" if L["trained"] else "n/a",
                help="1.0 = perfectly separates confirmed from cleared on cases it didn't train on; 0.5 = coin flip")
    st.info(L["message"])
    if L["trained"]:
        w = L["weights"]
        ww = w[w.kind == "worst weeks"].copy()
        ww["signal_name"] = ww.signal.map(C.SHORT_NAME)
        st.markdown("**What it learned** (positive = pushes towards 'confirmed'; standardised units)")
        st.altair_chart(alt.Chart(ww).mark_bar(cornerRadiusEnd=4).encode(
            y=alt.Y("signal_name:N", sort="-x", title=None), x=alt.X("learned_weight:Q", title="Learned weight"),
            color=alt.condition("datum.learned_weight > 0", alt.value("#d95926"), alt.value("#8a8984")),
            tooltip=["signal_name", alt.Tooltip("learned_weight:Q", format=".2f")]).properties(height=280), width="stretch")
        sug = suggested_weights(w, st.session_state.tl_settings.weights)
        sug["signal"] = sug.signal.map(C.SHORT_NAME)
        st.markdown("**Suggested drift-score weights** (rescaled to the same total)")
        st.dataframe(sug, hide_index=True, width="stretch")
        if st.button("Apply suggested weights", type="primary"):
            new = dict(zip(C.FEATURES, sug.suggested_weight))
            st.session_state.settings_before = r.decisions
            st.session_state.tl_settings = dataclasses.replace(st.session_state.tl_settings, weights=new)
            st.rerun()
        st.caption("Bias warning: analysts mostly review what the system already flags, so the model can only learn "
                   "what the system already sees. That's why random audits (below) matter.")

    st.markdown("### Audit queue: unusual merchants the rules don't flag")
    st.markdown("The anomaly detector (Isolation Forest) needs no labels. It ranks merchants whose overall behaviour "
                "profile is unusual. Auditing the top of this list, plus a random ~2% sample, is how you find **new** "
                "fraud patterns before the rules know about them.")
    d = r.decisions
    aq = d[(d.level == 0)].sort_values("anomaly_pct", ascending=False).head(25)
    show = aq[["merchant_id", "category", "city", "anomaly_pct", "drift_score", "learned_prob", "reason_1"]]
    if st.session_state.reveal and "label" in d:
        show = show.assign(**{"hidden truth": aq.label.map(lambda x: state.LABEL_NAME.get(x, x))})
    st.dataframe(show, hide_index=True, width="stretch", column_config={
        "anomaly_pct": st.column_config.ProgressColumn("Anomaly", min_value=0, max_value=100, format="%.0f"),
        "learned_prob": st.column_config.NumberColumn("Learned", format="percent")})

    with st.expander("Review history used for training"):
        hist = pd.concat([p.review_history, st.session_state.reviews], ignore_index=True)
        st.dataframe(hist, hide_index=True, width="stretch")
        st.download_button("Download your decisions (CSV)", st.session_state.reviews.to_csv(index=False), "analyst_reviews.csv")
    up = st.file_uploader("Load previously saved decisions (CSV with merchant_id, outcome = confirmed/cleared)", type=["csv"])
    if up is not None and st.button("Load decisions"):
        rv = pd.read_csv(up)
        rv = rv[rv.outcome.isin(["confirmed", "cleared"])].assign(source=rv.get("source", "uploaded"), note=rv.get("note", ""))
        st.session_state.reviews = pd.concat([st.session_state.reviews, rv[state.REVIEW_COLS]], ignore_index=True)
        st.rerun()


def performance():
    st.title("Performance & thresholds")
    r = state.results()
    d = r.decisions
    truth = truth_series(d, st.session_state.reviews)
    if truth.empty:
        st.warning("Performance needs ground truth: either a `label` column in your merchants file, or analyst "
                   "decisions (confirm / clear cases on the Merchant drill-down page).")
        return
    src = "hidden labels" if "label" in d and d.label.notna().any() else f"{len(truth)} analyst decisions"
    st.caption(f"Ground truth from: {src}.")
    dd = d.set_index("merchant_id").join(truth.rename("bad"), how="inner")
    rows = []
    for name, lvl in [("Ask or above", 1), ("Friction or above", 2), ("Review or above", 3)]:
        hit = dd.level >= lvl
        tp = (hit & dd.bad).sum()
        rows.append({"counts as flagged": name, "flagged": int(hit.sum()),
                     "precision": tp / hit.sum() if hit.sum() else float("nan"),
                     "recall": tp / dd.bad.sum() if dd.bad.sum() else float("nan"),
                     "honest merchants hit": int((hit & ~dd.bad).sum())})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", column_config={
        "precision": st.column_config.NumberColumn(format="percent"), "recall": st.column_config.NumberColumn(format="percent")})
    if "label" in d:
        st.markdown("**What happens to each kind of merchant**")
        ct = pd.crosstab(d.label.map(lambda x: state.LABEL_NAME.get(x, x)).rename("Hidden truth"), d.level.map(C.LEVEL_SHORT))
        st.dataframe(ct[[c for c in C.LEVEL_SHORT.values() if c in ct]], width="stretch")

    st.markdown("### Set the threshold with money")
    st.markdown("Estimate what each mistake costs. The chart shows the expected total cost at every possible "
                "Friction threshold; the cheapest one is marked.")
    c = st.columns(3)
    miss = c[0].number_input("Cost of a missed betting front (₹)", 0, 100_000_000, 500_000, 50_000,
                             help="Regulatory penalty, reputational damage, funds not reported")
    fp = c[1].number_input("Cost of wrongly penalising an honest merchant (₹)", 0, 10_000_000, 20_000, 5_000,
                           help="Lost fees, churn, complaints")
    rv = c[2].number_input("Analyst review cost per flagged case (₹)", 0, 100_000, 1_500, 500)
    sw = sweep(d, truth, Costs(miss, fp, rv))
    best = best_threshold(sw)
    cur = st.session_state.tl_settings.friction
    base = alt.Chart(sw).encode(x=alt.X("threshold:Q", title="Penalise (Friction) from risk score"))
    line = base.mark_line(strokeWidth=2, color="#2a78d6").encode(
        y=alt.Y("total_cost:Q", title="Expected cost (₹)", axis=alt.Axis(format="~s")),
        tooltip=["threshold", alt.Tooltip("total_cost:Q", format=",.0f"), "caught", "missed", "honest_flagged"])
    rules = alt.Chart(pd.DataFrame({"x": [best.threshold, cur], "what": ["cheapest", "current"]})).mark_rule(strokeDash=[4, 4]).encode(
        x="x:Q", color=alt.Color("what:N", scale=alt.Scale(range=["#d95926", "#8a8984"]), legend=alt.Legend(orient="top", title=None)))
    st.altair_chart((line + rules).properties(height=280), width="stretch")
    cur_row = sw.iloc[(sw.threshold - cur).abs().argmin()]
    a, b = st.columns(2)
    a.metric("Cheapest threshold", f"{best.threshold:.0f}")
    a.caption(f"Expected cost ₹{best.total_cost:,.0f}: catches {int(best.caught)}, misses {int(best.missed)}, "
              f"wrongly penalises {int(best.honest_flagged)}")
    b.metric("Current threshold", f"{cur:.0f}")
    b.caption(f"Expected cost ₹{cur_row.total_cost:,.0f}: catches {int(cur_row.caught)}, misses {int(cur_row.missed)}, "
              f"wrongly penalises {int(cur_row.honest_flagged)}")
    if best.threshold != cur and st.button(f"Use {best.threshold:.0f} as the Friction threshold"):
        s = st.session_state.tl_settings
        st.session_state.settings_before = d
        st.session_state.tl_settings = dataclasses.replace(
            s, friction=float(best.threshold), ask=min(s.ask, float(best.threshold)), review=max(s.review, float(best.threshold)))
        st.rerun()

    st.markdown("### Catching fraud vs bothering honest merchants, at every threshold")
    long = sw.melt("threshold", ["caught", "honest_flagged"], var_name="what", value_name="merchants")
    long["what"] = long.what.map({"caught": "Bad merchants caught", "honest_flagged": "Honest merchants penalised"})
    st.altair_chart(alt.Chart(long).mark_line(strokeWidth=2).encode(
        x=alt.X("threshold:Q", title="Penalise (Friction) from risk score"),
        y=alt.Y("merchants:Q", title="Merchants", scale=alt.Scale(type="symlog")),
        color=alt.Color("what:N", scale=alt.Scale(range=["#2a78d6", "#d95926"]), legend=alt.Legend(orient="top", title=None)),
        tooltip=["threshold", "what", "merchants"]).properties(height=260), width="stretch")
    st.caption("Log scale. Move right: fewer honest merchants penalised, but eventually bad ones slip through.")

    stress = C.REPORTS / "stress_test.csv"
    if state.is_demo() and stress.exists():
        st.markdown("### Stress test (from `python run_all.py`)")
        st.dataframe(pd.read_csv(stress), hide_index=True, width="stretch")
        st.image(str(C.REPORTS / "7_stress_test.png"))
