"""Trace dashboard. Run:   streamlit run app/dashboard.py

Pages
-----
Home                       what Trace does, the funnel from watched to human review, how Trace decides (with live drawings), and the Load data window
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
import re
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
    st.markdown(f"<p style='font-size:19px;line-height:1.5;color:{ui.INK_2};max-width:38rem;margin:-4px 0 24px'>"
                "Finds UPI merchants whose money doesn't match the business they declared, "
                "without punishing honest shops.</p>", unsafe_allow_html=True)
    row = st.container(horizontal=True, vertical_alignment="center", gap="medium")
    if row.button("Load data", type="primary", icon=":material/upload_file:"):
        load_data_window()
    row.page_link(PAGE_LINKS["queue"], label="Open the risk queue", icon=":material/arrow_forward:")
    # the dataset name may already carry the merchant count; say it once
    count = "" if "merchants" in p.name else f" · {len(d):,} merchants"
    st.caption(f"{p.name}{count} · as of {state.clock():%d %b %Y}")

    # the main figure: how the watched merchants narrow down the ladder
    lc = ui.LEVEL_COLOR
    n, flagged, restricted, human = len(d), int((d.level >= 1).sum()), int((d.level >= 2).sum()), int((d.level >= 3).sum())
    share = (lambda k: k / n) if n else (lambda k: 0.0)
    st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)
    st.markdown(f"##### From {n:,} merchants to {human:,} human reviews")
    st.markdown(ui.funnel([
        (n, "Watched", "Every merchant, every week, against similar shops", ui.NEUTRAL_BAR, 1.0),
        (flagged, "Flagged", f"{share(flagged):.1%} of merchants, from a neutral question upward", lc[1], share(flagged)),
        (restricted, "Restricted", "Lower limits, slower settlement or a reserve", lc[2], share(restricted)),
        (human, "With a human", "Money is held only with a second source of evidence", lc[3], share(human)),
    ]), unsafe_allow_html=True)
    st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)

    # one real flagged merchant against its peers, e.g. "57% vs 10% for similar kirana stores"
    peer_visual, peer_line = ui.peer_bars(57, 10), "Example: share of takings in match hours"
    for r_ in d[d.level >= 1].sort_values("risk_score", ascending=False).itertuples():
        m = re.search(r"^(.*?):\s*([\d.]+)%\s*vs\s*([\d.]+)%", str(r_.reason_1 or ""))
        if m:
            shop = str(r_.category).replace("_", " ")
            peer_visual = ui.peer_bars(float(m.group(2)), float(m.group(3)), f"{r_.merchant_id}, {shop}", "Similar shops")
            peer_line = m.group(1)
            break
    linked = d[d.network_link.fillna(False).astype(bool)] if "network_link" in d else d.iloc[:0]
    clusters = linked.cluster.nunique() if "cluster" in linked else 0
    calm = int((d.level == 0).sum())

    st.markdown("##### How Trace decides")
    st.markdown(ui.principles([
        ("Compare with peers", "Each merchant against similar shops in the same week, so festival rushes stay normal",
         peer_visual, peer_line),
        ("Follow the links", "Shared phones, bank accounts and gamblers tie fronts to known betting accounts",
         ui.link_graph(), f"{len(linked):,} merchants linked, in {clusters:,} clusters"),
        ("Ask before you punish", "Every action has a reason; money is held only with a second source of evidence",
         ui.ladder_steps(d.level.value_counts().to_dict()), f"{calm:,} of {n:,} merchants see no action at all"),
    ]), unsafe_allow_html=True)


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
PAGE_LINKS.update(queue=pages["Results"][1], merchant=pages["Results"][2])
nav = st.navigation(pages, position="hidden")  # the sidebar below draws the menu itself
ui.style(current="" if nav.url_path in ("", "home") else nav.url_path)  # Home links to "" as the default page
ALL_PAGES = [pg for group in pages.values() for pg in group]


def _search_submitted():
    """Remember what was typed and clear the box; the jump happens below, outside the callback."""
    st.session_state._search_go = st.session_state.nav_search.strip()
    st.session_state.nav_search = ""


def _run_search(q: str):
    """A page name opens that page; a merchant ID opens its case file in Merchant drill-down."""
    ql = q.lower()
    for pg in ALL_PAGES:
        if ql in pg.title.lower():
            st.switch_page(pg)
    ids = state.results().decisions.merchant_id
    hit = ids[ids.str.lower() == ql]
    if hit.empty:
        hit = ids[ids.str.lower().str.contains(ql, regex=False)]
    if len(hit):
        st.session_state.focus_merchant = hit.iloc[0]
        st.switch_page(PAGE_LINKS["merchant"])
    st.toast(f"Nothing matches \"{q}\"", icon=":material/search_off:")


with st.sidebar:
    st.markdown(ui.wordmark(), unsafe_allow_html=True)
    st.text_input("Search", key="nav_search", placeholder="Search", icon=":material/search:",
                  label_visibility="collapsed", on_change=_search_submitted,
                  help="A page name, or a merchant ID such as M0002")
    for section, group in pages.items():
        if section:
            st.markdown(f"<div class='nav-label'>{section}</div>", unsafe_allow_html=True)
        for pg in group:
            st.page_link(pg, label=pg.title, icon=pg.icon, width="stretch")

    st.markdown("<div class='nav-rule'></div>", unsafe_allow_html=True)
    p = state.prepared()
    st.caption(f"Data: {p.name}")
    if state.has_truth():
        st.toggle("Show hidden truth", key="reveal",
                  help="Synthetic data knows which merchants are really fronts. A real provider never has this; "
                       "it's here so you can check the system.")
    n_rev, n_dec = len(st.session_state.reviews), len(st.session_state.extra_decl)
    if n_rev or n_dec:
        st.caption(f"This session: {n_rev} analyst decisions, {n_dec} merchant explanations")
    if st.session_state.tl_settings != state.C.Settings():
        st.caption("Custom settings active")

if q := st.session_state.pop("_search_go", ""):
    _run_search(q)

nav.run()
