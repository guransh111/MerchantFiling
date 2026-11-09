"""TrustLoop dashboard. Run:   streamlit run app/dashboard.py

Pages
-----
Start here                 what this is and how to use it
Load data                  upload your own CSV/Excel, generate a simulated world, templates
Overview / Risk queue      what the system recommends
Merchant drill-down        full case file + analyst confirm / clear buttons
Network                    clusters and a picture of linked merchants
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
from views import analysis, check_one, data_page, experience, learning_perf, network_page, settings_page  # noqa: E402

st.set_page_config(page_title="TrustLoop", layout="wide", page_icon="🔁")
state.init()


def home():
    st.title("TrustLoop")
    st.markdown("#### Does this merchant's money match its declared business?")
    st.markdown("""
TrustLoop helps a payment provider find merchants whose UPI activity doesn't match what they declared (for example,
"kirana stores" that are really collecting cricket bets) **without punishing honest shops** whose business is
seasonal or genuinely changing.

**How it decides**
1. **10 weekly signals** per merchant: match-hour share, late-night share, round amounts, out-of-state payers,
   repeat payments, amount variety, same-day pass-through, payout accounts, growth, size vs declared.
2. **Compared with peers in the same week** (same category and city tier), so a Diwali rush is normal.
3. **Corroboration:** each signal is capped, so several must agree.
4. **Network:** shared phones, bank accounts and customers spread suspicion from known betting accounts.
5. **Change points:** finds the week behaviour flipped, and whether a phone/bank change came with it.
6. **Learning loop:** learns from analysts' confirm/clear decisions and suggests better weights.
7. **Proportionate ladder:** Monitor → Ask → Friction → Review (needs corroboration) → Offboard (needs a human).

**How to use this dashboard**
- Start with the **demo** (already loaded), or bring your own data in **Load data**.
- Look at the **Risk queue**, open a case in **Merchant drill-down**, and **confirm or clear** it. Everything updates.
- Try **Check a merchant** to score any profile you can imagine.
- Move the sliders in **Settings & what-if** to see the trade-off between catching fraud and bothering honest merchants.
""")
    p = state.prepared()
    st.info(f"Loaded now: **{p.name}**, {len(p.merchants):,} merchants.")


pages = {
    "": [st.Page(home, title="Start here", icon="🏠", url_path="home", default=True),
         st.Page(data_page.page, title="Load data", icon="📂", url_path="data")],
    "Results": [st.Page(analysis.overview, title="Overview", icon="📊", url_path="overview"),
                st.Page(analysis.queue, title="Risk queue", icon="📋", url_path="queue"),
                st.Page(analysis.merchant, title="Merchant drill-down", icon="🔎", url_path="merchant"),
                st.Page(network_page.page, title="Network", icon="🕸️", url_path="network")],
    "Tools": [st.Page(check_one.page, title="Check a merchant", icon="🧪", url_path="check"),
              st.Page(settings_page.page, title="Settings & what-if", icon="🎛️", url_path="settings"),
              st.Page(learning_perf.learning, title="Learning loop", icon="🧠", url_path="learning"),
              st.Page(learning_perf.performance, title="Performance & thresholds", icon="🎯", url_path="performance")],
    "People": [st.Page(experience.merchant_view, title="Merchant's view", icon="🏪", url_path="merchant-view"),
               st.Page(experience.payer_view, title="Customer's payment screen", icon="📱", url_path="payer")],
}
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
        st.caption("⚙️ Custom settings active")

nav.run()
