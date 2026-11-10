"""What the merchant and the paying customer see."""
from __future__ import annotations

import streamlit as st

import state
import ui
from src import config as C

KIND = {"kirana": "a kirana store", "restaurant": "a restaurant", "sweet_shop": "a sweet shop",
        "pharmacy": "a pharmacy", "electronics": "an electronics shop"}
SHOP = {"kirana": "General Store", "restaurant": "Restaurant", "sweet_shop": "Sweets", "pharmacy": "Medicals",
        "electronics": "Electronics"}


def merchant_view():
    st.title("Merchant's view")
    st.markdown("What a flagged merchant sees. **Submitting an explanation here really feeds back into the system**: "
                "it is recorded as a declaration, lowers the merchant one level (unless network-linked), and an "
                "analyst is asked for evidence.")
    r = state.results()
    d = r.decisions
    explained = list(dict.fromkeys(st.session_state.extra_decl.merchant_id)) if len(st.session_state.extra_decl) else []
    flagged = d[d.level.between(1, 3)].merchant_id.tolist() or d.merchant_id.tolist()
    options = list(dict.fromkeys(flagged + explained))  # keep merchants who just explained, even if no longer flagged
    last = st.session_state.get("mv_merchant")
    mid = st.selectbox("Merchant", options, index=options.index(last) if last in options else 0,
                       format_func=lambda x: state.merchant_label(d, x))
    st.session_state.mv_merchant = mid
    row = d.set_index("merchant_id").loc[mid]
    left, right = st.columns([3, 2])
    with left:
        if row.level <= 1:
            st.info("**Your sales pattern has changed recently. Tell us what's new.**\n\n"
                    "This is a routine check. Nothing about your account has changed. If you've started something new "
                    "(delivery, online orders, a second branch), let us know and we'll update your business profile.")
        else:
            st.warning(f"**We've applied a temporary measure to your account:** {row.action.split(': ', 1)[-1]}.\n\n"
                       "Your payments continue to work. Here is why, and how to resolve it within **72 hours**.")
        st.markdown("##### What we noticed")
        for x in [row.reason_1, row.reason_2]:
            if isinstance(x, str) and x:
                st.markdown(f"- {x}")
        with st.form(f"explain_{mid}"):
            reason = st.selectbox("What changed?", ["Started delivery / online orders", "Opened a new branch",
                                                    "Seasonal / festival sales", "Started wholesale supply",
                                                    "Event or match screening", "Other"])
            details = st.text_area("Details", placeholder="e.g. We started late-night delivery on Swiggy from 1 September.")
            st.file_uploader("Evidence (GST return, Swiggy/Zomato partner page, rent agreement, invoices)", accept_multiple_files=True)
            if st.form_submit_button("Submit explanation", type="primary"):
                state.add_declaration(mid, f"{reason}: {details}" if details else reason)
                st.rerun()
        if len(st.session_state.extra_decl) and mid in set(st.session_state.extra_decl.merchant_id):
            st.success("Explanation received. A person will review it within 72 hours. You can appeal to our grievance "
                       f"officer if you disagree. Current action: **{C.LEVEL_SHORT[int(row.level)]}**.")
    with right, ui.panel("mv_tier"):
        st.markdown("##### Your trust tier")
        tier = {0: ("Gold", "same-day settlement"), 1: ("Silver", "next-day settlement"),
                2: ("Bronze", "T+2 settlement"), 3: ("Under review", "20% reserve held"),
                4: ("Closed", "account closed")}[int(row.level)]
        st.metric("Tier", tier[0], tier[1], delta_color="off")
        st.caption("Merchants whose activity matches their profile move up tiers over time: faster settlement, higher "
                   "limits, lower fees. Honest merchants have a reason to keep their profile current.")


def payer_view():
    st.title("Customer's payment screen")
    r = state.results()
    d = r.decisions
    mid = st.selectbox("Merchant", d.merchant_id.tolist(), format_func=lambda x: state.merchant_label(d, x))
    row = d.set_index("merchant_id").loc[mid]
    cat = str(row.category)
    warn = ""
    if row.level >= 2:
        warn = ("<div style='margin-top:12px;padding:10px;border-radius:8px;background:#fff4e5;color:#7a4b00;font-size:14px'>"
                f"{ui.lucide('alert', 16, '#7a4b00')} This merchant is registered as <b>{KIND.get(cat, cat.replace('_', ' '))}</b>. "
                "If you are not buying from a shop, stop and check.</div>")
    st.markdown(f"""
<div style="max-width:340px;margin:auto;border:1px solid #ccc;border-radius:24px;padding:22px;font-family:sans-serif;background:#fff;color:#111">
  <div style="font-size:13px;color:#666">Paying</div>
  <div style="font-size:20px;font-weight:600">Shree {mid[-3:]} {SHOP.get(cat, cat.replace('_', ' ').title())}</div>
  <div style="font-size:14px;color:#1f5fae;margin-top:2px">{ui.lucide('check', 16, '#1f5fae')} Verified: {cat.replace('_', ' ').title()} · {row.city}</div>
  <div style="font-size:34px;font-weight:600;margin:18px 0">₹ 500</div>
  {warn}
  <div style="margin-top:16px;padding:12px;border-radius:12px;background:#1f5fae;color:white;text-align:center">Pay</div>
  <div style="margin-top:10px;font-size:12px;color:#666;text-align:center">Not a shop? <u>Report this merchant</u></div>
</div>""", unsafe_allow_html=True)
    st.caption("Showing the declared business at payment time makes a 'kirana' collecting cricket bets obvious to the "
               "payer, and every 'Report' tap is a free label for the learning loop. Needs NPCI to adopt it across UPI apps.")
