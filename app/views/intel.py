"""Intelligence & reporting pages: betting-page scanner, consortium check, regulator reports."""
from __future__ import annotations

import io
import zipfile

import pandas as pd
import streamlit as st

import state
from src import config as C
from src import reporting as RPT
from src import scanner as SC


def scanner_page():
    st.title("Scan a betting page")
    st.markdown("Betting websites and Telegram channels publish the UPI IDs gamblers should pay into. Paste the text "
                "of a **public** page (or the text decoded from its QR code). The scanner finds every UPI ID, including "
                "disguised ones like `name [at] okaxis` and `upi://pay?pa=…` payment links, and matches them to your "
                "merchants. Matches can be added to the known-bad list, which re-runs the network search.")
    p = state.prepared()
    d = state.results().decisions
    if "sample_page" not in st.session_state:
        st.session_state.sample_page = ""
    c1, c2 = st.columns([1, 3])
    if c1.button("Load an example post"):
        st.session_state.sample_page = SC.demo_page(p.merchants, set(p.known_bad.merchant_id) | set(st.session_state.extra_kb.merchant_id))
    c2.caption("The example is a synthetic Telegram-style post built from the demo data.")
    text = st.text_area("Page text", value=st.session_state.sample_page, height=200,
                        placeholder="Paste the text of a public betting page or Telegram post here")
    source = st.text_input("Where is this from? (recorded as provenance)", "public Telegram channel")
    if not text.strip():
        return
    found = SC.match(SC.extract(text, source), p.merchants)
    if found.empty:
        st.info("No UPI IDs found.")
        return
    lvl = d.set_index("merchant_id").level
    found["our action now"] = found.merchant_id.map(lvl).map(lambda x: C.LEVEL_SHORT.get(x, "") if pd.notna(x) else "")
    found["already known-bad"] = found.merchant_id.isin(set(p.known_bad.merchant_id) | set(st.session_state.extra_kb.merchant_id))
    cols = [c for c in ["upi_id", "how_found", "known_handle", "merchant_id", "our action now", "already known-bad", "context"] if c in found]
    st.dataframe(found[cols], hide_index=True, width="stretch")
    ours = found.dropna(subset=["merchant_id"])
    new = ours[~ours["already known-bad"]]
    st.markdown(f"**{len(found)}** UPI IDs found, **{len(ours)}** belong to our merchants, **{len(new)}** are new to the known-bad list.")
    if len(new) and st.button(f"Add {len(new)} merchant(s) to the known-bad list and re-run", type="primary"):
        state.add_known_bad(new.merchant_id, source)
        st.rerun()
    if len(st.session_state.extra_kb):
        st.caption("Added this session: " + ", ".join(st.session_state.extra_kb.merchant_id))


def consortium_page():
    st.title("Consortium check")
    st.markdown("""
A merchant offboarded by one payment provider often just signs up with another. Providers can't simply swap
customer data (privacy law, competition). The fix is **keyed hashing**:

1. Every member turns each identifier (bank account, phone/device, UPI ID) into a **token** using a secret key
   held by the consortium (e.g. IDPIC or NPCI). The same input always gives the same token; without the key the
   token can't be reversed.
2. Provider A shares the tokens of merchants it **confirmed and offboarded**, never the raw details.
3. Provider B tokenises its **new applicants** with the same key and checks for matches at onboarding.
""")
    p = state.prepared()
    r = state.results()
    d = r.decisions
    if not len(getattr(p, "identifiers", pd.DataFrame())):
        st.warning("This dataset has no identifiers (bank accounts / devices / UPI IDs), so there's nothing to share.")
        return
    key = st.text_input("Consortium key (shared secret)", RPT.DEMO_CONSORTIUM_KEY, type="password")
    basis = st.radio("Provider A shares tokens for", ["Merchants at Review or Offboard", "Analyst-confirmed merchants only"],
                     horizontal=True)
    if basis.startswith("Analyst"):
        rv = st.session_state.reviews
        offboarded = rv[rv.outcome == "confirmed"].merchant_id.tolist()
    else:
        offboarded = d[d.level >= 3].merchant_id.tolist()
    if not offboarded:
        st.info("No merchants to share yet. Confirm some cases, or choose 'Review or Offboard'.")
        return
    shared = RPT.consortium_tokens(offboarded, p, key)
    a, b = st.columns(2)
    with a:
        st.markdown(f"**Provider A shares {len(shared)} tokens** from {len(offboarded)} merchants (no raw data):")
        st.dataframe(shared.head(8), hide_index=True, width="stretch")
        st.download_button("Download shared token list (CSV)", shared.to_csv(index=False), "consortium_tokens.csv")
    with b:
        st.markdown("##### Provider B's new applicants")
        up = st.file_uploader("Upload applicants (CSV with application_id, settlement_account, device_id)", type=["csv"])
        if up is not None:
            apps = pd.read_csv(up)
            for col in ["settlement_account", "device_id"]:
                if col not in apps:
                    apps[col] = ""
            if "application_id" not in apps:
                apps["application_id"] = [f"APP-{i}" for i in range(len(apps))]
        else:
            apps = RPT.simulate_applicants(p, offboarded)
            st.caption(f"Using {len(apps)} simulated applicants (a few are operators re-applying with reused accounts or phones)")
    res = RPT.check_applicants(apps, shared, key)
    hits = res[res.flag]
    st.markdown(f"### {len(hits)} of {len(res)} applicants match an offboarded merchant")
    show = ["application_id", "business_name", "category", "match_account", "match_device"] + \
        (["truth"] if "truth" in res and st.session_state.reveal else [])
    st.dataframe(hits[[c for c in show if c in hits]], hide_index=True, width="stretch")
    st.caption("A match doesn't mean automatic rejection: it triggers enhanced due diligence at onboarding. "
               "Neither provider ever saw the other's raw bank accounts or phone IDs.")


def reports_page():
    st.title("Regulator reports")
    st.markdown("Under PMLA, payment providers must file a **Suspicious Transaction Report (STR)** with FIU-IND within "
                "7 days of forming a suspicion. The implementation plan also feeds confirmed identifiers to the "
                "**I4C Suspect Registry**. These are drafts for the Principal Officer to check, not the official "
                "electronic formats.")
    r = state.results()
    d = r.decisions
    p = state.prepared()
    basis = st.radio("Report on", ["Analyst-confirmed merchants", "All merchants at Review or above"], horizontal=True)
    if basis.startswith("Analyst"):
        mids = d[d.level == 4].merchant_id.tolist()
        if not mids:
            st.info("No analyst-confirmed merchants in this session yet. Confirm cases on the Case management or "
                    "Merchant drill-down pages, or switch to 'All merchants at Review or above'.")
            return
    else:
        mids = d[d.level >= 3].merchant_id.tolist()
    st.caption(f"{len(mids)} merchants in scope")
    c, e = state.cases()
    case_of = c.drop_duplicates("merchant_id", keep="last").set_index("merchant_id").case_id if len(c) else pd.Series(dtype=str)
    entity = st.text_input("Reporting entity name", "[Payment Aggregator name]")

    one = st.selectbox("Preview one STR", mids, format_func=lambda x: state.merchant_label(d, x))
    cid = case_of.get(one, "")
    md = RPT.str_draft(one, r, p, case_id=cid, events=e[e.case_id == cid] if cid else None, entity=entity)
    with st.expander("Preview", expanded=True):
        st.markdown(md)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for mid in mids:
            cid = case_of.get(mid, "")
            z.writestr(f"STR_draft_{mid}.md", RPT.str_draft(mid, r, p, case_id=cid,
                                                            events=e[e.case_id == cid] if cid else None, entity=entity))
    i4c = RPT.i4c_submission(mids, p, d)
    a, b, cc = st.columns(3)
    a.download_button(f"All {len(mids)} STR drafts (zip)", buf.getvalue(), "STR_drafts.zip", type="primary")
    b.download_button("I4C Suspect Registry file (CSV)", i4c.to_csv(index=False), "i4c_suspect_registry.csv",
                      help="Identifiers in clear: confidential, for the regulator only")
    cc.download_button("Consortium tokens (CSV)", RPT.consortium_tokens(mids, p).to_csv(index=False), "consortium_tokens.csv",
                       help="Hashed identifiers, safe to share with other payment providers")
    st.markdown(f"##### I4C file preview · {len(i4c)} identifiers")
    st.dataframe(i4c.head(20), hide_index=True, width="stretch")
