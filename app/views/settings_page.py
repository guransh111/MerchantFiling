"""Settings & what-if: change any weight or threshold and see the impact."""
from __future__ import annotations

import dataclasses
import json

import pandas as pd
import streamlit as st

import state
from src import config as C


def _impact(before: pd.DataFrame, after: pd.DataFrame) -> pd.DataFrame:
    b = before.set_index("merchant_id").level
    a = after.set_index("merchant_id").level.reindex(b.index)
    t = pd.crosstab(b.map(C.LEVEL_SHORT).rename("Before"), a.map(C.LEVEL_SHORT).rename("After"))
    order = [x for x in C.LEVEL_SHORT.values() if x in t.index or x in t.columns]
    return t.reindex(index=[o for o in order if o in t.index], columns=[o for o in order if o in t.columns], fill_value=0)


def page():
    st.title("Settings & what-if")
    st.markdown("Every number the system uses is here. Change them, press **Apply**, and every page updates. "
                "Use this to show judges the trade-off between catching fraud and bothering honest merchants.")
    cur: C.Settings = st.session_state.tl_settings
    before = state.results().decisions

    with st.form("settings_form"):
        st.markdown("##### 1. How much each signal counts (weights)")
        cols = st.columns(5)
        weights = {}
        for i, (f, (_, default, desc)) in enumerate(C.FEATURES.items()):
            weights[f] = cols[i % 5].number_input(C.SHORT_NAME[f], 0.0, 3.0, float(cur.weights.get(f, default)), 0.1,
                                                  help=f"{desc}. Default {default}. 0 switches the signal off.")
        st.markdown("##### 2. Scoring")
        c = st.columns(4)
        z_cap = c[0].slider("Cap per signal (spreads)", 1.0, 10.0, float(cur.z_cap), 0.5,
                            help="Lower = more signals must agree before the score gets high")
        k = c[1].slider("Scale strictness", 5.0, 30.0, float(cur.squash_k), 0.5,
                        help="Raw points needed for a high score. Higher = more lenient")
        worst = c[2].slider("Worst weeks averaged", 1, 8, int(cur.worst_weeks),
                            help="Merchant score = average of its N worst weeks. Higher = ignores short blips")
        mpg = c[3].slider("Minimum peer group size", 3, 50, int(cur.min_peer_group))
        st.markdown("##### 3. Action ladder")
        c = st.columns(4)
        ask = c[0].slider("Ask from risk", 0.0, 100.0, float(cur.ask), 1.0)
        fric = c[1].slider("Friction from risk", 0.0, 100.0, float(cur.friction), 1.0)
        rev = c[2].slider("Review from risk", 0.0, 100.0, float(cur.review), 1.0)
        corr = c[3].checkbox("Review needs network corroboration", cur.require_corroboration)
        st.markdown("##### 4. Network")
        c = st.columns(6)
        use_net = c[0].checkbox("Use network", cur.use_network)
        nw = c[1].slider("Risk points per network point", 0.0, 1.0, float(cur.network_weight), 0.05)
        thr = c[2].slider("Network score that counts as a link", 0.0, 100.0, float(cur.network_link_threshold), 5.0)
        ew = {}
        for j, kind in enumerate(["device", "account", "payers", "payouts"]):
            ew[kind] = (c[3] if j < 2 else c[4] if j < 3 else c[5]).slider(
                f"Link type: {kind}", 0.0, 3.0, float(cur.edge_weights.get(kind, 1.0)), 0.25, help="Importance multiplier; 0 = ignore")
        st.markdown("##### 5. Other evidence")
        c = st.columns(5)
        use_decl = c[0].checkbox("Declarations lower the level", cur.use_declarations)
        use_take = c[1].checkbox("Phone + bank change = possible rental", cur.use_takeover)
        use_cp = c[2].checkbox("Escalate behaviour shift after account change", cur.use_changepoint)
        use_learn = c[3].checkbox("Learning loop can escalate Monitor → Ask", cur.use_learning)
        learn_at = c[4].slider("Learning loop probability needed", 0.5, 0.99, float(cur.learning_escalate_at), 0.01)
        c = st.columns(3)
        use_gst = c[0].checkbox("GST cross-check counts as corroboration", cur.use_gst)
        gst_ratio = c[1].slider("Flag when UPI takings ≥ this × GST turnover", 1.5, 10.0, float(cur.gst_ratio_flag), 0.5)
        why = c[2].text_input("Reason for this change (goes in the change log)")
        a, b = st.columns(2)
        apply = a.form_submit_button("Apply", type="primary")
        reset = b.form_submit_button("Reset to defaults")

    if reset:
        state.set_settings(C.Settings(), "Reset to defaults")
        st.rerun()
    if apply:
        if not (ask <= fric <= rev):
            st.error("Thresholds must be in order: Ask ≤ Friction ≤ Review.")
            return
        state.set_settings(C.Settings(
            weights=weights, z_cap=z_cap, squash_k=k, min_peer_group=mpg, worst_weeks=worst,
            ask=ask, friction=fric, review=rev, require_corroboration=corr,
            use_network=use_net, network_weight=nw, network_link_threshold=thr, edge_weights=ew,
            use_declarations=use_decl, use_takeover=use_take, use_changepoint=use_cp,
            use_learning=use_learn, learning_escalate_at=learn_at, use_gst=use_gst, gst_ratio_flag=gst_ratio),
            why or "Changed on the Settings page")
        st.session_state.settings_before = before
        st.rerun()

    prev = st.session_state.get("settings_before")
    if prev is not None:
        after = state.results().decisions
        st.markdown("##### Impact of your last change")
        st.markdown("Rows = action before the change, columns = action after. Off-diagonal cells are merchants whose "
                    "treatment changed.")
        st.dataframe(_impact(prev, after), width="stretch")
        if state.has_truth():
            bad = lambda d: d.label.isin(["betting_front", "rented"])
            rows = []
            for name, d in [("Before", prev), ("After", after)]:
                bd = bad(d)
                rows.append({"": name,
                             "bad merchants penalised (Friction+)": f"{(d[bd].level >= 2).mean():.0%}",
                             "honest merchants penalised": int((~bd & (d.level >= 2)).sum()),
                             "honest merchants asked": int((~bd & (d.level == 1)).sum())})
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    diff = {k: v for k, v in dataclasses.asdict(cur).items() if v != dataclasses.asdict(C.Settings())[k]}
    if diff:
        st.caption("Changed from defaults: " + ", ".join(diff))

    st.divider()
    st.markdown("##### Policy file and change log")
    st.markdown("Thresholds are policy, not code. Save the current settings as a file to version them, share them "
                "with the risk committee, or load an approved policy.")
    a, b = st.columns(2)
    a.download_button("Download current policy (JSON)", json.dumps(dataclasses.asdict(cur), indent=2),
                      "trustloop_policy.json", mime="application/json")
    up = b.file_uploader("Load a policy file (JSON)", type=["json"])
    if up is not None and b.button("Apply loaded policy"):
        try:
            data = json.loads(up.getvalue())
            valid = {f.name for f in dataclasses.fields(C.Settings)}
            state.set_settings(C.Settings(**{k: v for k, v in data.items() if k in valid}), f"Loaded policy file {up.name}")
            st.rerun()
        except (ValueError, TypeError) as err:
            st.error(f"Could not read that policy file: {err}")
    log = st.session_state.settings_log
    if log:
        st.dataframe(pd.DataFrame(log[::-1]), hide_index=True, width="stretch")
    else:
        st.caption("No policy changes in this session yet")
