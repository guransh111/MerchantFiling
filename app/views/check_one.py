"""Check one merchant: describe it (sliders) or upload its payments, and score it against the loaded peers."""
from __future__ import annotations

import io

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

import state
from src import config as C
from src import schema
from src import score as S
from src.actions import _fmt, level_for, peer_phrase
from src.features import build_features

# slider set-up per signal: (min, max, step, how to show, to-model, from-model)
PCT = (lambda v: v * 100, lambda v: v / 100)
SLIDERS = {
    "match_hours_share": (0.0, 100.0, 1.0, "%", *PCT),
    "night_share": (0.0, 100.0, 1.0, "%", *PCT),
    "round_share": (0.0, 100.0, 1.0, "%", *PCT),
    "out_of_state_share": (0.0, 100.0, 1.0, "%", *PCT),
    "pass_through": (0.0, 100.0, 1.0, "%", *PCT),
    "payments_per_payer": (1.0, 6.0, 0.1, "x", lambda v: v, lambda v: v),
    "ticket_variety": (0.0, 6.0, 0.1, "/6", lambda v: v, lambda v: v),
    "payout_fanout": (0.0, 60.0, 1.0, "accounts", lambda v: v, lambda v: v),
    "volume_growth": (-50.0, 500.0, 5.0, "% growth", lambda v: (np.exp(v) - 1) * 100, lambda v: np.log1p(v / 100)),
    "size_mismatch": (0.1, 50.0, 0.1, "x declared", lambda v: np.exp(v), lambda v: np.log(v)),
}
PRESETS = {
    "Typical peer": {},
    "Betting front (classic)": {"match_hours_share": 0.65, "night_share": 0.4, "round_share": 0.95, "out_of_state_share": 0.9,
                                "payments_per_payer": 2.4, "ticket_variety": 2.6, "pass_through": 0.8, "payout_fanout": 28,
                                "size_mismatch": np.log(12)},
    "Careful betting front": {"match_hours_share": 0.35, "night_share": 0.12, "round_share": 0.55, "out_of_state_share": 0.45,
                              "payments_per_payer": 1.9, "ticket_variety": 3.5, "size_mismatch": np.log(3)},
    "Restaurant screening IPL": {"match_hours_share": 0.65, "night_share": 0.14, "round_share": 0.3, "volume_growth": np.log(1.8)},
    "Kirana turned wholesaler": {"size_mismatch": np.log(8), "round_share": 0.27, "pass_through": 0.6, "payout_fanout": 8,
                                 "volume_growth": np.log(3)},
    "Sweet shop in Diwali week": {"volume_growth": np.log(2.8)},
}


def _ladder_for(score, network, known_bad, takeover, declared, s: C.Settings):
    risk = min(100.0, score + (s.network_weight * (100 if network else 0) if s.use_network else 0))
    if known_bad:
        risk = max(risk, 95)
    link = known_bad or (network and s.use_network)
    level = level_for(risk, s)
    notes = []
    if level == 3 and s.require_corroboration and not link:
        level = 2
        notes.append("Capped at Friction: no network corroboration")
    if s.use_takeover and takeover:
        level = max(level, 1)
        if link:
            level = min(3, level + 1)
        notes.append("Phone and bank account changed together: possible rental")
    if declared and s.use_declarations and level > 0:
        if link:
            notes.append("Declaration not accepted: linked to a known betting account")
        else:
            level -= 1
            notes.append("Pre-declared change: lowered one level, evidence requested")
    return risk, level, notes


def _points_chart(res: dict):
    df = pd.DataFrame({"signal": [C.SHORT_NAME[f] for f in C.FEATURES],
                       "points": [float(res["points"][f]) for f in C.FEATURES]}).sort_values("points", ascending=False)
    ch = alt.Chart(df).mark_bar(cornerRadiusEnd=4, color="#d95926").encode(
        y=alt.Y("signal:N", sort="-x", title=None),
        x=alt.X("points:Q", title="Risk points (max per signal = cap x weight)",
                scale=alt.Scale(domain=[0, max(4.0, df.points.max())])),
        tooltip=["signal", alt.Tooltip("points:Q", format=".1f")])
    st.altair_chart(ch.properties(height=280), width="stretch")


def page():
    st.title("Check a merchant")
    st.markdown("Score a **new** merchant against the peers in the loaded dataset. Describe its behaviour with the "
                "sliders, or upload its payments. Useful for onboarding reviews and for 'what if' questions.")
    r = state.results()
    s = st.session_state.tl_settings
    base = r.baselines
    cats = sorted(state.prepared().merchants.category.unique())
    c1, c2, c3 = st.columns(3)
    cat = c1.selectbox("Declared category", cats, index=cats.index("kirana") if "kirana" in cats else 0)
    tier = c2.selectbox("City tier", [1, 2, 3, 0], format_func=lambda t: "unknown" if t == 0 else f"Tier {t}")
    group = S.resolve_peer_group(base, cat, tier)
    c3.markdown(f"**Compared with:** {peer_phrase(group) if group != 'ALL' else 'all merchants'}")
    pooled = S.pooled_baseline(base, group)

    mode = st.radio("How do you want to describe the merchant?", ["Sliders", "Upload its payments"], horizontal=True)
    if mode == "Sliders":
        preset = st.selectbox("Start from an example", list(PRESETS))
        vals = {}
        cols = st.columns(2)
        for i, (f, (lo, hi, step, unit, to_ui, from_ui)) in enumerate(SLIDERS.items()):
            peer = pooled.get(f"{f}__peer", np.nan)
            default = PRESETS[preset].get(f, peer)
            if pd.isna(default):
                default = from_ui(lo)
            ui = float(np.clip(to_ui(default), lo, hi))
            peer_ui = to_ui(peer) if pd.notna(peer) else None
            v = cols[i % 2].slider(f"{C.SHORT_NAME[f]} ({unit})", lo, hi, round(ui / step) * step, step,
                                   key=f"sl_{f}_{preset}",
                                   help=f"{C.FEATURES[f][2]}. Typical peer: {peer_ui:.1f}" if peer_ui is not None else C.FEATURES[f][2])
            vals[f] = from_ui(v)
        st.markdown("**Other evidence**")
        e = st.columns(4)
        network = e[0].checkbox("Shares phone/bank/customers with a known betting merchant")
        known_bad = e[1].checkbox("UPI ID found on a betting page")
        takeover = e[2].checkbox("Phone and bank account just changed")
        declared = e[3].checkbox("Merchant pre-declared this change")
        res = S.score_profile(vals, group, base, s)
        risk, level, notes = _ladder_for(res["score"], network, known_bad, takeover, declared, s)
        st.divider()
        a, b = st.columns([1, 2])
        with a:
            st.metric("Drift score", f"{res['score']:.0f}")
            st.metric("Risk score", f"{risk:.0f}")
            st.markdown(f"**Action:** {state.level_badge(level)}", unsafe_allow_html=True)
            st.caption(C.LEVELS[level])
            for n in notes:
                st.markdown(f"- {n}")
        with b:
            _points_chart(res)
        top = sorted(C.FEATURES, key=lambda f: -float(res["points"][f]))[:3]
        for f in top:
            if float(res["points"][f]) >= 0.5:
                st.markdown(f"- **{C.SHORT_NAME[f]}**: {_fmt(f, vals[f])} vs {_fmt(f, res['peer'][f])} for the typical peer "
                            f"({float(res['z'][f]):.1f} spreads away → {float(res['points'][f]):.1f} points)")
    else:
        st.markdown("Upload a CSV/Excel of this merchant's payments with at least a date-time and an amount column. "
                    "Optional: direction (in/out), payer ID, payer state.")
        up = st.file_uploader("Payments file", type=["csv", "xlsx", "xls"])
        c1, c2 = st.columns(2)
        state_code = c1.text_input("Merchant's state (e.g. UP)", "")
        turnover = c2.number_input("Declared monthly turnover (₹, 0 = unknown)", 0, 100_000_000, 0, 10_000)
        if up is None:
            return
        raw = schema.read_any(io.BytesIO(up.getvalue()), up.name)
        mp = schema.guess_mapping("transactions", list(raw.columns))
        mp["merchant_id"] = None
        tx = schema.apply_mapping(raw, "transactions", mp)
        tx["merchant_id"] = "NEW"
        m = pd.DataFrame([{"merchant_id": "NEW", "category": cat, "tier": tier, "state": state_code or None,
                           "declared_monthly_turnover": turnover or np.nan}])
        clean, rep = schema.clean({"merchants": m, "transactions": tx})
        for x in rep.errors:
            st.error(x)
        if not rep.ok:
            st.caption(f"Columns detected: {', '.join(k for k, v in mp.items() if v)}")
            return
        f = build_features(clean["merchants"], clean["transactions"], clean["calendar"])
        w = S.score_one(f, group, base, s)
        if w.empty:
            st.warning("Not enough payments to compute weekly signals (need 5+ per week).")
            return
        summary = w.nlargest(s.worst_weeks, "drift_score").drift_score.mean()
        lvl = level_for(summary, s)
        a, b = st.columns([1, 3])
        a.metric("Drift score (worst weeks)", f"{summary:.0f}")
        a.markdown(f"**Action:** {state.level_badge(lvl)}", unsafe_allow_html=True)
        b.altair_chart(alt.Chart(w).mark_line(point=True, color="#2a78d6").encode(
            x=alt.X("week_start:T", title=None), y=alt.Y("drift_score:Q", scale=alt.Scale(domain=[0, 100]), title="Weekly drift"),
            tooltip=["week_start:T", alt.Tooltip("drift_score:Q", format=".0f"), "n_txns"]).properties(height=220), width="stretch")
        from src.actions import reasons_for
        for x in reasons_for(w, worst_weeks=s.worst_weeks):
            st.markdown(f"- {x}")
        st.caption(f"{len(clean['transactions']):,} payments, {len(w)} weeks scored. "
                   "Weeks that overlap the loaded dataset are compared with peers in the same week; others with typical peer values.")
