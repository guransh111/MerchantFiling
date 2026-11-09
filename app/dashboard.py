"""TrustLoop dashboard. Run:   streamlit run app/dashboard.py

What a payment provider's risk analyst would see, plus mock-ups of what the
merchant and the paying customer would see.
"""
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import config as C  # noqa: E402

st.set_page_config(page_title="TrustLoop", layout="wide")

LEVEL_NAME = {0: "Monitor", 1: "Ask", 2: "Friction", 3: "Review"}
LEVEL_COLOR = {0: "#8a8984", 1: "#2a78d6", 2: "#c98500", 3: "#d95926"}
KIND = {"kirana": "a kirana store", "restaurant": "a restaurant", "sweet_shop": "a sweet shop",
        "pharmacy": "a pharmacy", "electronics": "an electronics shop"}
LABEL_NAME = {"legit": "Honest shop", "genuine_drifter": "Honest shop, business changed",
              "betting_front": "Betting front", "rented": "Rented account"}


@st.cache_data
def load():
    need = ["decisions.csv", "dashboard_weekly.csv.gz", "network_edges.csv", "declarations.csv"]
    if not all((C.DATA / n).exists() for n in need):
        return None
    d = pd.read_csv(C.DATA / "decisions.csv")
    w = pd.read_csv(C.DATA / "dashboard_weekly.csv.gz", parse_dates=["week_start"])
    e = pd.read_csv(C.DATA / "network_edges.csv")
    decl = pd.read_csv(C.DATA / "declarations.csv")
    for c in ["reason_1", "reason_2", "reason_3", "notes", "linked_to", "drift_type"]:
        d[c] = d[c].fillna("")
    return d, w, e, decl


data = load()
if data is None:
    st.error("No results yet. In a terminal, run:  python run_all.py --small   then refresh this page.")
    st.stop()
d, w, edges, decl = data

# ------------------------------------------------------------------ sidebar
st.sidebar.title("TrustLoop")
st.sidebar.caption("Declared vs observed: catching merchants whose UPI activity doesn't match their business")
reveal = st.sidebar.toggle("Show hidden truth (demo only)", value=False,
                           help="The synthetic data knows which merchants are really betting fronts. "
                                "A real provider would never have this column.")
cats = st.sidebar.multiselect("Declared category", sorted(d.category.unique()), default=sorted(d.category.unique()))
levels = st.sidebar.multiselect("Action", list(LEVEL_NAME.values()), default=list(LEVEL_NAME.values()))
view = d[d.category.isin(cats) & d.level.map(LEVEL_NAME).isin(levels)]

tab_queue, tab_merchant, tab_appeal, tab_payer, tab_results = st.tabs(
    ["Risk queue", "Merchant drill-down", "Merchant's view", "Customer's payment screen", "How well it works"])

# ------------------------------------------------------------------ 1. queue
with tab_queue:
    st.subheader("Risk queue: who needs attention this week")
    cols = st.columns(5)
    cols[0].metric("Merchants", f"{len(d):,}")
    for i, lvl in enumerate(range(4)):
        cols[i + 1].metric(LEVEL_NAME[lvl], int((d.level == lvl).sum()))
    st.caption("Most merchants are never touched. Only merchants with several independent warning signs "
               "AND a link to known betting activity reach Review.")
    show = view[["merchant_id", "category", "city", "risk_score", "drift_score", "network_score", "level", "reason_1", "notes"]].copy()
    show["action"] = show.level.map(LEVEL_NAME)
    show = show.drop(columns="level")
    if reveal:
        show["hidden truth"] = view.label.map(LABEL_NAME)
    st.dataframe(
        show, hide_index=True, width="stretch", height=520,
        column_config={
            "risk_score": st.column_config.ProgressColumn("Risk", min_value=0, max_value=100, format="%.0f"),
            "drift_score": st.column_config.NumberColumn("Drift", format="%.0f"),
            "network_score": st.column_config.NumberColumn("Network", format="%.0f"),
            "reason_1": "Main reason", "notes": "Notes",
        })

# ------------------------------------------------------------------ 2. drill-down
with tab_merchant:
    ids = view.merchant_id.tolist() or d.merchant_id.tolist()
    mid = st.selectbox("Choose a merchant (sorted by risk)", ids,
                       format_func=lambda x: f"{x} · {d.set_index('merchant_id').loc[x, 'category']} · "
                                             f"{LEVEL_NAME[d.set_index('merchant_id').loc[x, 'level']]}")
    r = d.set_index("merchant_id").loc[mid]
    mw = w[w.merchant_id == mid]

    c1, c2 = st.columns([2, 3])
    with c1:
        st.markdown(f"### {mid}")
        st.markdown(f"**Declared:** {r.category.replace('_', ' ')} · {r.city} (tier {r.tier}) · {r.declared_size} · "
                    f"expects ₹{r.declared_monthly_turnover:,.0f}/month")
        a, b, c = st.columns(3)
        a.metric("Risk", f"{r.risk_score:.0f}")
        b.metric("Drift", f"{r.drift_score:.0f}")
        c.metric("Network", f"{r.network_score:.0f}")
        st.markdown(f"<div style='padding:10px 14px;border-radius:8px;border-left:6px solid {LEVEL_COLOR[r.level]};"
                    f"background:rgba(127,127,127,.08)'><b>Recommended action:</b> {r.action}</div>",
                    unsafe_allow_html=True)
        st.markdown("**Why (top signals vs peers)**")
        for x in [r.reason_1, r.reason_2, r.reason_3]:
            if x:
                st.markdown(f"- {x}")
        if not r.reason_1:
            st.markdown("- Nothing unusual compared with similar shops.")
        if r.notes:
            st.markdown("**Notes**")
            for n in r.notes.split(" | "):
                st.markdown(f"- {n}")
        if reveal:
            st.info(f"Hidden truth: **{LABEL_NAME[r.label]}**" + (f" ({r.drift_type})" if r.drift_type else ""))
    with c2:
        st.markdown("**Weekly drift score** (dashed line = Ask threshold)")
        line = alt.Chart(mw).mark_line(strokeWidth=2, color="#2a78d6").encode(
            x=alt.X("week_start:T", title=None), y=alt.Y("drift_score:Q", title="Drift score", scale=alt.Scale(domain=[0, 100])),
            tooltip=[alt.Tooltip("week_start:T", title="Week"), alt.Tooltip("drift_score:Q", format=".0f", title="Score"),
                     alt.Tooltip("inflow:Q", format=",.0f", title="Money in (₹)")])
        rule = alt.Chart(pd.DataFrame({"y": [60]})).mark_rule(strokeDash=[4, 4], color="#8a8984").encode(y="y:Q")
        st.altair_chart((line + rule).properties(height=230), width="stretch")

        st.markdown("**This merchant vs its peers, in its worst week**")
        peak = mw.loc[mw.drift_score.idxmax()] if len(mw) else None
        if peak is not None:
            rows = []
            for f, (direction, _, desc) in C.FEATURES.items():
                rows.append({"signal": desc, "this merchant": peak[f], "typical peer": peak[f + "__peer"],
                             "risk points": peak[f + "__pts"]})
            t = pd.DataFrame(rows).sort_values("risk points", ascending=False)
            st.dataframe(t, hide_index=True, width="stretch",
                         column_config={"this merchant": st.column_config.NumberColumn(format="%.2f"),
                                        "typical peer": st.column_config.NumberColumn(format="%.2f"),
                                        "risk points": st.column_config.ProgressColumn(min_value=0, max_value=C.Z_CAP * 1.2, format="%.1f")})
            st.caption(f"Peers = {peak.peer_group.replace('|', ', ')}, same week. Each signal adds at most "
                       f"{C.Z_CAP:.0f} points, so no single oddity can condemn a merchant.")

    links = edges[(edges.a == mid) | (edges.b == mid)].copy()
    if len(links):
        links["other merchant"] = links.a.where(links.b == mid, links.b)
        links = links.merge(d[["merchant_id", "risk_score", "known_bad"]], left_on="other merchant", right_on="merchant_id")
        st.markdown("**Network links** (things this merchant shares with other merchants)")
        st.dataframe(links[["other merchant", "why", "risk_score", "known_bad"]].sort_values("risk_score", ascending=False),
                     hide_index=True, width="stretch")

# ------------------------------------------------------------------ 3. merchant's view
with tab_appeal:
    st.subheader("What the merchant sees")
    asked = d[d.level >= 1].merchant_id.tolist()
    mid2 = st.selectbox("Merchant", asked, key="appeal")
    r2 = d.set_index("merchant_id").loc[mid2]
    left, right = st.columns([3, 2])
    with left:
        if r2.level == 1:
            st.info("**Your sales pattern has changed recently. Tell us what's new.**\n\n"
                    "This is a routine check. Nothing about your account has changed. "
                    "If you've started something new (delivery, online orders, a second branch), let us know and "
                    "we'll update your business profile.")
        else:
            st.warning(f"**We've applied a temporary measure to your account:** {r2.action.split(': ', 1)[-1]}.\n\n"
                       "Your payments continue to work. Here is why, and how to resolve it within **72 hours**.")
        st.markdown("**What we noticed**")
        for x in [r2.reason_1, r2.reason_2]:
            if x:
                st.markdown(f"- {x}")
        st.markdown("**Tell us what changed**")
        st.selectbox("Reason", ["Started delivery / online orders", "Opened a new branch", "Seasonal / festival sales",
                                "Started wholesale supply", "Event or screening", "Other"])
        st.text_area("Details", placeholder="e.g. We started late-night delivery on Swiggy from 1 September.")
        st.file_uploader("Evidence (GST return, Swiggy/Zomato partner page, rent agreement, invoices)", accept_multiple_files=True)
        if st.button("Submit explanation"):
            st.success("Thanks. A person will review this within 72 hours. You can appeal to our grievance officer if you disagree.")
    with right:
        st.markdown("**Your trust tier**")
        tier = {0: "Gold: same-day settlement", 1: "Silver: next-day settlement", 2: "Bronze: T+2 settlement", 3: "Under review"}[r2.level]
        st.metric("Tier", tier.split(":")[0], tier.split(": ")[-1] if ":" in tier else None)
        st.caption("Merchants whose activity matches their profile move up tiers over time: faster settlement, "
                   "higher limits, lower fees. That gives honest merchants a reason to keep their profile up to date.")

# ------------------------------------------------------------------ 4. payer screen
with tab_payer:
    st.subheader("What the customer sees when paying")
    mid3 = st.selectbox("Merchant", d.merchant_id.tolist(), key="payer")
    r3 = d.set_index("merchant_id").loc[mid3]
    shop = {"kirana": "General Store", "restaurant": "Restaurant", "sweet_shop": "Sweets", "pharmacy": "Medicals",
            "electronics": "Electronics"}[r3.category]
    warn = ""
    if r3.level >= 2:
        warn = ("<div style='margin-top:12px;padding:10px;border-radius:8px;background:#fff4e5;color:#7a4b00;font-size:14px'>"
                "⚠️ This merchant is registered as <b>" + KIND[r3.category] +
                "</b>. If you are not buying from a shop, stop and check.</div>")
    st.markdown(f"""
<div style="max-width:340px;margin:auto;border:1px solid #ccc;border-radius:24px;padding:22px;font-family:sans-serif;background:#fff;color:#111">
  <div style="font-size:13px;color:#666">Paying</div>
  <div style="font-size:20px;font-weight:600">Shree {mid3[-3:]} {shop}</div>
  <div style="font-size:14px;color:#2a78d6;margin-top:2px">✔ Verified: {r3.category.replace('_', ' ').title()} · {r3.city}</div>
  <div style="font-size:34px;font-weight:600;margin:18px 0">₹ 500</div>
  {warn}
  <div style="margin-top:16px;padding:12px;border-radius:12px;background:#2a78d6;color:white;text-align:center">Pay</div>
  <div style="margin-top:10px;font-size:12px;color:#666;text-align:center">Not a shop? <u>Report this merchant</u></div>
</div>""", unsafe_allow_html=True)
    st.caption("Showing the declared business at payment time makes a 'kirana' collecting cricket bets obvious to the payer, "
               "and every 'Report' tap gives the model a free label. This would need NPCI to adopt it across UPI apps.")

# ------------------------------------------------------------------ 5. results
with tab_results:
    res = C.REPORTS / "results.md"
    if res.exists():
        txt = res.read_text().split("\n")
        st.markdown("\n".join(l for l in txt if not l.startswith("![")))
        for img in sorted(C.REPORTS.glob("*.png")):
            st.image(str(img))
    else:
        st.info("Run  python run_all.py  to generate results.")
