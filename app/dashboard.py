"""Trace dashboard. Run:   streamlit run app/dashboard.py

Pages
-----
Home                       what Trace does, the ladder at a glance, and the Load data window
                           (upload your own CSV/Excel, generate a simulated world, templates)
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

st.set_page_config(page_title="Trace", layout="wide", page_icon=":material/sync_alt:")
state.init()
ui.style()


PAGE_LINKS: dict = {}  # filled once the pages exist, used by Home's link to the risk queue


@st.dialog("Load data", width="large")
def load_data_window():
    """A window over Home: upload your own files, generate a simulated world, or get templates."""
    data_page.body()


def home():
    p = state.prepared()
    d = state.results().decisions
    if msg := st.session_state.pop("_toast", None):
        st.toast(msg, icon=":material/check_circle:")

    st.title("Trace")
    st.markdown(f"<p style='font-size:19px;line-height:1.5;color:{ui.INK_2};max-width:38rem;margin:-4px 0 20px'>"
                "Finds UPI merchants whose money doesn't match the business they declared, "
                "without punishing honest shops.</p>", unsafe_allow_html=True)
    a, b, _ = st.columns([1, 1.3, 3])
    if a.button("Load data", type="primary", icon=":material/upload_file:", width="stretch"):
        load_data_window()
    b.page_link(PAGE_LINKS["queue"], label="Open the risk queue", icon=":material/arrow_forward:")
    st.caption(f"{p.name} · {len(d):,} merchants · as of {state.clock():%d %b %Y}")

    st.write("")
    st.markdown(ui.ladder_strip(d.level.value_counts().to_dict()), unsafe_allow_html=True)
    st.write("")

    cols = st.columns(3, gap="large")
    for col, (title, text) in zip(cols, [
        ("Compare with peers", "Each merchant against similar shops in the same week, so festival rushes stay normal"),
        ("Follow the links", "Shared phones, bank accounts and gamblers tie fronts to known betting accounts"),
        ("Ask before you punish", "Every action has a reason; money is held only with a second source of evidence"),
    ]):
        col.markdown(f"##### {title}")
        col.caption(text)


pages = {
    "": [st.Page(home, title="Home", icon=":material/home:", url_path="home", default=True)],
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
PAGE_LINKS.update(queue=pages["Results"][1])
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
    st.caption("Light or dark: menu ⋮ → Settings → Theme")
    if st.session_state.tl_settings != state.C.Settings():
        st.caption("Custom settings active")

nav.run()
