"""Learning loop, audit queue, and performance / cost-based threshold tuning."""
from __future__ import annotations

import dataclasses

import altair as alt
import pandas as pd
import streamlit as st

import state
import ui
from src import config as C
from src.learn import suggested_weights
from src.tuning import Costs, best_threshold, sweep, truth_series


def learning():
    st.title("Learning loop")
    r = state.results()
    L = r.learning
    p = state.prepared()
    st.markdown("Every analyst decision to **confirm** or **clear** a case becomes a label. Trace fits a logistic "
                "regression to those labels to learn which signals really separate confirmed fronts from cleared "
                "merchants, and suggests new weights: a second opinion you can inspect, not a black box.")

    n_hist, n_sess = len(p.review_history), len(st.session_state.reviews)
    n_conf, n_clear = int(L["n_confirmed"]), int(L["n_cleared"])
    used = (n_conf + n_clear) or 1
    lc = ui.LEVEL_COLOR
    auc = L["cv_auc"] if L["trained"] else None
    st.markdown(f"##### From {n_conf + n_clear:,} analyst decisions to new weights")
    st.markdown(ui.funnel([
        (n_conf + n_clear, "Decisions used", f"{n_hist:,} from past reviews, {n_sess:,} from this session", ui.NEUTRAL_BAR,
         [(n_conf / used, lc[4]), (n_clear / used, ui.GOOD)]),
        (n_conf, "Confirmed", "Fronts or rented accounts an analyst confirmed", lc[4], n_conf / used),
        (n_clear, "Cleared", "Merchants an analyst found genuine", ui.GOOD, n_clear / used),
        (f"{auc:.2f}" if auc is not None else "n/a", "Cross-validated AUC",
         "On cases it didn't train on: 0.5 is a coin flip, 1.0 separates them perfectly", ui.ACCENT,
         max(0.0, (auc - 0.5) / 0.5) if auc is not None else None),
    ]), unsafe_allow_html=True)
    if not L["trained"]:
        st.info(L["message"])
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    if L["trained"]:
        w = L["weights"]
        ww = w[w.kind == "worst weeks"].copy()
        ww["signal_name"] = ww.signal.map(C.SHORT_NAME)
        sug = suggested_weights(w, st.session_state.tl_settings.weights)
        sug["signal"] = sug.signal.map(C.SHORT_NAME)
        left, right = st.columns(2, gap="medium")
        with left, ui.panel("learn_weights"):
            st.markdown("##### What it learned")
            st.altair_chart(alt.Chart(ww).mark_bar(cornerRadiusEnd=3, height=14).encode(
                y=alt.Y("signal_name:N", sort="-x", title=None,
                        axis=alt.Axis(labelFont=ui.SANS, labelFontSize=13, labelColor=ui.INK)),
                x=alt.X("learned_weight:Q", title=None),
                color=alt.condition("datum.learned_weight > 0", alt.value(ui.ACCENT), alt.value(ui.NEUTRAL_BAR)),
                tooltip=[alt.Tooltip("signal_name", title="Signal"), alt.Tooltip("learned_weight:Q", format=".2f", title="Weight")]
            ).properties(height=34 * len(ww)), width="stretch")
            st.caption("Longer bar = the signal pushes harder towards 'confirmed' (standardised units). Grey: no push or "
                       "the other way")
        with right, ui.panel("learn_suggest"):
            st.markdown("##### Weights now and suggested")
            long = sug.melt("signal", ["current_weight", "suggested_weight"], var_name="which", value_name="weight")
            long["which"] = long.which.map({"current_weight": "Now", "suggested_weight": "Suggested"})
            order = list(sug.sort_values("suggested_weight", ascending=False).signal)
            y = alt.Y("signal:N", sort=order, title=None, axis=alt.Axis(labelFont=ui.SANS, labelFontSize=13, labelColor=ui.INK))
            rule = alt.Chart(sug).mark_rule(color=ui.EDGE, strokeWidth=2).encode(y=y, x="current_weight:Q", x2="suggested_weight:Q")
            dots = alt.Chart(long).mark_circle(size=90, opacity=1).encode(
                y=y, x=alt.X("weight:Q", title=None),
                color=alt.Color("which:N", scale=alt.Scale(domain=["Now", "Suggested"], range=[ui.NEUTRAL_BAR, ui.ACCENT]),
                                legend=alt.Legend(orient="top", title=None)),
                tooltip=["signal", "which", alt.Tooltip("weight:Q", format=".2f")])
            st.altair_chart(alt.layer(rule, dots).properties(height=34 * len(sug)), width="stretch")
            st.caption("Rescaled to the same total, so only the balance between signals changes")
            if st.button("Apply suggested weights", type="primary"):
                new = dict(zip(C.FEATURES, sug.suggested_weight))
                st.session_state.settings_before = r.decisions
                state.set_settings(dataclasses.replace(st.session_state.tl_settings, weights=new),
                                   "Applied weights suggested by the learning loop")
                st.rerun()
            with st.expander("Exact weights"):
                st.dataframe(sug, hide_index=True, width="stretch", column_config={
                    "signal": "Signal", "current_weight": st.column_config.NumberColumn("Now", format="%.2f"),
                    "suggested_weight": st.column_config.NumberColumn("Suggested", format="%.2f")})
        st.caption("Bias warning: analysts mostly review what the system already flags, so the model can only learn "
                   "what the system already sees. That's why the random audits below matter.")

    d = r.decisions
    with ui.panel("learn_audit"):
        st.markdown("##### Audit queue: unusual merchants the rules don't flag")
        st.caption("An anomaly detector (Isolation Forest) needs no labels: it ranks merchants whose overall profile is "
                   "unusual. Auditing the top of this list, plus a random 2% sample, finds new fraud patterns before "
                   "the rules know about them")
        aq = d[(d.level == 0)].sort_values("anomaly_pct", ascending=False).head(25)
        show = aq[["merchant_id", "category", "city", "anomaly_pct", "drift_score", "learned_prob", "reason_1"]]
        if st.session_state.reveal and "label" in d:
            show = show.assign(**{"hidden truth": aq.label.map(lambda x: state.LABEL_NAME.get(x, x))})
        st.dataframe(show, hide_index=True, width="stretch", column_config={
            "merchant_id": "Merchant", "category": "Declared as", "city": "City",
            "anomaly_pct": st.column_config.ProgressColumn("Anomaly", min_value=0, max_value=100, format="%.0f"),
            "drift_score": st.column_config.NumberColumn("Drift", format="%.0f"),
            "learned_prob": st.column_config.NumberColumn("Learned", format="percent"), "reason_1": "Main reason"})

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
    st.caption(f"Ground truth from: {src}")
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
        st.markdown("##### What happens to each kind of merchant")
        ct = pd.crosstab(d.label.map(lambda x: state.LABEL_NAME.get(x, x)).rename("Hidden truth"), d.level.map(C.LEVEL_SHORT))
        st.dataframe(ct[[c for c in C.LEVEL_SHORT.values() if c in ct]], width="stretch")

    with ui.panel("perf_cost"):
        st.markdown("##### Set the threshold with money")
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
        line = base.mark_line(strokeWidth=2, color=ui.ACCENT).encode(
            y=alt.Y("total_cost:Q", title="Expected cost (₹)", axis=alt.Axis(format="~s")),
            tooltip=["threshold", alt.Tooltip("total_cost:Q", format=",.0f"), "caught", "missed", "honest_flagged"])
        rules = alt.Chart(pd.DataFrame({"x": [best.threshold, cur], "what": ["cheapest", "current"]})).mark_rule(strokeDash=[4, 4]).encode(
            x="x:Q", color=alt.Color("what:N", scale=alt.Scale(range=[ui.ACCENT, ui.MUTED]), legend=alt.Legend(orient="top", title=None)))
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
            state.set_settings(dataclasses.replace(
                s, friction=float(best.threshold), ask=min(s.ask, float(best.threshold)), review=max(s.review, float(best.threshold))),
                f"Cost-based threshold (miss Rs {miss:,}, false penalty Rs {fp:,}, review Rs {rv:,})")
            st.rerun()

    with ui.panel("perf_tradeoff"):
        st.markdown("##### Catching fraud vs bothering honest merchants, at every threshold")
        long = sw.melt("threshold", ["caught", "honest_flagged"], var_name="what", value_name="merchants")
        long["what"] = long.what.map({"caught": "Bad merchants caught", "honest_flagged": "Honest merchants penalised"})
        st.altair_chart(alt.Chart(long).mark_line(strokeWidth=2).encode(
            x=alt.X("threshold:Q", title="Penalise (Friction) from risk score"),
            y=alt.Y("merchants:Q", title="Merchants", scale=alt.Scale(type="symlog")),
            color=alt.Color("what:N", scale=alt.Scale(range=[ui.ACCENT, ui.LEVEL_COLOR[3]]), legend=alt.Legend(orient="top", title=None)),
            tooltip=["threshold", "what", "merchants"]).properties(height=260), width="stretch")
        st.caption("Log scale. Move right: fewer honest merchants penalised, but eventually bad ones slip through.")

    stress = C.REPORTS / "stress_test.csv"
    if state.is_demo() and stress.exists():
        st.markdown("##### Stress test")
        st.dataframe(pd.read_csv(stress), hide_index=True, width="stretch")
        st.image(str(C.REPORTS / "7_stress_test.png"))
