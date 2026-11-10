"""TrustLoop dashboard. Run:   streamlit run app/dashboard.py

Pages
-----
Start here                 what this is and how to use it
Load data                  upload your own CSV/Excel, generate a simulated world, templates
Overview / Risk queue      what the system recommends
Merchant drill-down        full case file + analyst confirm / clear buttons
Network                    clusters and a picture of linked merchants
Case management            cases with 72h deadlines, decisions, appeals, audit log
Scan a betting page        find UPI IDs on public betting pages, match to merchants
Consortium check           privacy-preserving sharing of offboarded identifiers between providers
Regulator reports          draft STRs for FIU-IND, I4C Suspect Registry file
Check a merchant           score a new merchant from sliders or its payments file
Settings & what-if         change any weight / threshold and see the impact
Learning loop              what it learned from reviewer decisions; audit queue
Performance & thresholds   precision / recall, cost-based threshold
Merchant's view / Customer's payment screen   the human side
"""
import sys
from pathlib import Path

import streamlit as st

APP = Path(__file__).resolve().parent
for p in (APP, APP.parent):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import state  # noqa: E402
import ui  # noqa: E402
from views import (analysis, cases_page, check_one, data_page, experience, intel, learning_perf,  # noqa: E402
                   network_page, settings_page)

st.set_page_config(page_title="TrustLoop", layout="wide", page_icon=":material/sync_alt:")
state.init()
ui.style()


PAGE_LINKS: dict = {}  # filled once the pages exist, used by the start page's links


def home():
    p = state.prepared()
    d = state.results().decisions
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.caption("TrustLoop · merchant risk console")
        st.title("Does this merchant's money match the business it declared?")
        st.markdown(
            "TrustLoop reads every merchant's UPI payments, compares them with similar shops in the same week, "
            "and finds the ones that look like betting collections rather than the kirana or restaurant they "
            "registered as. Honest shops whose sales change, grow or spike at Diwali are left alone, and every "
            "action comes with a reason the merchant can answer.")
        a, b = st.columns(2)
        a.page_link(PAGE_LINKS["queue"], label="Open the risk queue", icon=":material/list_alt:")
        b.page_link(PAGE_LINKS["data"], label="Use your own data", icon=":material/upload_file:")
        st.caption(f"Loaded: {p.name} · {len(p.merchants):,} merchants")
    with right:
        st.markdown("##### Where every merchant sits on the ladder")
        st.markdown(ui.ladder_list(d.level.value_counts().to_dict()), unsafe_allow_html=True)
        st.caption("Review needs a second source of evidence: a network link or a GST mismatch")

    st.divider()
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("##### How it decides")
        st.markdown("""
1. Ten weekly signals per merchant: match hours, late night, round amounts, out-of-state payers and six more
2. Each merchant compared with its peers in the same week, so festival rushes stay normal
3. Every signal capped, so several have to agree before the score is high
4. Shared phones, bank accounts and gamblers link fronts to known betting accounts
5. The week behaviour changed is found, and checked against phone and bank changes
6. Analysts' decisions teach it which signals matter
""")
    with c2:
        st.markdown("##### What you can do here")
        st.markdown("""
- Work the **Risk queue**, open a merchant and confirm or clear it
- Score any merchant you can describe in **Check a merchant**
- Move thresholds in **Settings & what-if** and see who changes treatment
- Run cases, scan betting pages and draft regulator reports under **Operations**
""")


pages = {
    "": [st.Page(home, title="Start here", icon=":material/home:", url_path="home", default=True),
         st.Page(data_page.page, title="Load data", icon=":material/upload_file:", url_path="data")],
    "Results": [st.Page(analysis.overview, title="Overview", icon=":material/monitoring:", url_path="overview"),
                st.Page(analysis.queue, title="Risk queue", icon=":material/list_alt:", url_path="queue"),
                st.Page(analysis.merchant, title="Merchant drill-down", icon=":material/person_search:", url_path="merchant"),
                st.Page(network_page.page, title="Network", icon=":material/hub:", url_path="network")],
    "Operations": [st.Page(cases_page.page, title="Case management", icon=":material/folder_open:", url_path="cases"),
                   st.Page(intel.scanner_page, title="Scan a betting page", icon=":material/travel_explore:", url_path="scanner"),
                   st.Page(intel.consortium_page, title="Consortium check", icon=":material/handshake:", url_path="consortium"),
                   st.Page(intel.reports_page, title="Regulator reports", icon=":material/description:", url_path="reports")],
    "Tools": [st.Page(check_one.page, title="Check a merchant", icon=":material/fact_check:", url_path="check"),
              st.Page(settings_page.page, title="Settings & what-if", icon=":material/tune:", url_path="settings"),
              st.Page(learning_perf.learning, title="Learning loop", icon=":material/model_training:", url_path="learning"),
              st.Page(learning_perf.performance, title="Performance & thresholds", icon=":material/target:", url_path="performance")],
    "People": [st.Page(experience.merchant_view, title="Merchant's view", icon=":material/storefront:", url_path="merchant-view"),
               st.Page(experience.payer_view, title="Customer's payment screen", icon=":material/smartphone:", url_path="payer")],
}
PAGE_LINKS.update(queue=pages["Results"][1], data=pages[""][1])
nav = st.navigation(pages)

with st.sidebar:
    p = state.prepared()
    st.caption(f"**Data:** {p.name}")
    if state.has_truth():
        st.toggle("Show hidden truth", key="reveal",
                  help="Synthetic data knows which merchants are really fronts. A real provider never has this; "
                       "it's here so you can check the system.")
    n_rev, n_dec = len(st.session_state.reviews), len(st.session_state.extra_decl)
    if n_rev or n_dec:
        st.caption(f"This session: {n_rev} analyst decisions, {n_dec} merchant explanations")
    if st.session_state.tl_settings != state.C.Settings():
        st.caption("Custom settings active")

nav.run()
