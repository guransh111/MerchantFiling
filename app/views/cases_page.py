"""Case management: deadlines, decisions, appeals and the audit log."""
from __future__ import annotations

import pandas as pd
import streamlit as st

import state
import ui
from src import cases as K
from src import config as C
from src import reporting as RPT

# a small status dot carries the state; colours only where they mean something
def status_color(status: str) -> str:
    lv = ui.LEVEL_COLOR
    return {"Awaiting merchant": lv[1], "Under review": lv[1], "Appealed": lv[2],
            "Closed: confirmed": lv[4], "Appeal upheld": lv[4],
            "Closed: cleared": ui.GOOD, "Appeal overturned": ui.GOOD}.get(status, lv[0])


def status_dot(status: str) -> str:
    return (f"<span style='display:inline-block;width:8px;height:8px;border-radius:4px;margin-right:8px;"
            f"background:{status_color(status)}'></span>{status}")


def page():
    st.title("Case management")
    r = state.results()
    d = r.decisions
    c, e = state.cases()
    now = state.clock()
    st.caption(f"Clock: {now:%d %b %Y %H:%M} (end of the data). Merchants have {K.SLA_HOURS} hours to reply; "
               f"appeals are decided within {K.APPEAL_SLA_DAYS} days by a second analyst.")
    if st.session_state.get("cases_simulated"):
        st.info("Demo: the case history below is **simulated** (a plausible quarter of analyst work, with occasional "
                "analyst mistakes and appeals). Actions you take here are real for this session and change the results.")

    k = K.metrics(c, e, now)
    m = st.columns(6)
    m[0].metric("Open cases", k["open"])
    m[1].metric("Overdue", k["overdue"], help="Open cases past their deadline")
    m[2].metric("Median time to decision", f"{k['median_hours_to_decision']:.0f} h" if pd.notna(k["median_hours_to_decision"]) else "n/a")
    m[3].metric("Replies within 72h", f"{k['within_sla']:.0%}" if pd.notna(k["within_sla"]) else "n/a")
    m[4].metric("Cleared as genuine", f"{k['cleared_share']:.0%}" if pd.notna(k["cleared_share"]) else "n/a",
                help="Share of decided cases where the merchant turned out to be genuine")
    m[5].metric("Appeal overturn rate", f"{k['overturn_rate']:.0%}" if pd.notna(k["overturn_rate"]) else "n/a",
                help="High = the system or analysts are over-flagging (a metric from the implementation plan)")

    flagged_no_case = d[d.level.between(1, 3) & ~d.merchant_id.isin(c.merchant_id if len(c) else [])]
    if len(flagged_no_case):
        if st.button(f"Open cases for {len(flagged_no_case)} newly flagged merchant(s)"):
            c, e = K.open_cases(d, c, e, now, actor="system")
            state.save_cases(c, e)
            st.rerun()

    if not len(c):
        st.info("No cases yet. Cases open automatically for merchants at Ask or above.")
        return
    show = st.segmented_control("Show", ["Open", "Closed", "All"], default="All", key="case_filter") or "All"
    keep = {"Open": K.OPEN, "Closed": [x for x in K.ACTIONS if x not in K.OPEN], "All": list(K.ACTIONS)}[show]
    v = c[c.status.isin(keep)].copy()
    v["overdue"] = v.status.isin(K.OPEN) & (pd.to_datetime(v.due) < now)
    v["category"] = v.merchant_id.map(d.set_index("merchant_id").category)
    v["system action"] = v.merchant_id.map(d.set_index("merchant_id").level).map(C.LEVEL_SHORT)
    if st.session_state.reveal and "label" in d:
        v["hidden truth"] = v.merchant_id.map(d.set_index("merchant_id").label).map(lambda x: state.LABEL_NAME.get(x, x))
    st.dataframe(v.sort_values(["overdue", "opened"], ascending=[False, False]).drop(columns=["level_at_open"]),
                 hide_index=True, width="stretch", height=320)

    st.markdown("##### Work a case")
    order = v.sort_values("opened", ascending=False).case_id.tolist()
    if not order:
        return
    cid = st.selectbox("Case", order, format_func=lambda x: f"{x} · {c.set_index('case_id').loc[x, 'merchant_id']} · "
                                                         f"{c.set_index('case_id').loc[x, 'status']}")
    case = c.set_index("case_id").loc[cid]
    mid = case.merchant_id
    row = d.set_index("merchant_id").loc[mid]
    left, right = st.columns([3, 2])
    with left:
        st.markdown(f"**{mid}** · {str(row.category).replace('_', ' ')} · {row.city} · system action "
                    f"{state.level_badge(int(row.level))} · risk {row.risk_score:.0f}", unsafe_allow_html=True)
        for x in [row.reason_1, row.reason_2, row.reason_3]:
            if isinstance(x, str) and x:
                st.markdown(f"- {x}")
        due = pd.Timestamp(case.due)
        if case.status in K.OPEN:
            hrs = (due - now).total_seconds() / 3600
            (st.error if hrs < 0 else st.warning if hrs < 24 else st.caption)(
                f"Deadline {due:%d %b %H:%M}: " + (f"overdue by {-hrs:.0f}h" if hrs < 0 else f"{hrs:.0f}h left"))
        st.markdown("##### Audit log")
        log = e[e.case_id == cid].sort_values("ts")
        st.dataframe(log[["ts", "actor", "action", "note"]], hide_index=True, width="stretch")
    with right:
        st.markdown(f"Status: {status_dot(case.status)}", unsafe_allow_html=True)
        allowed = K.ACTIONS.get(case.status, [])
        if not allowed:
            st.caption("This case is closed. No further actions.")
        else:
            actor = st.text_input("Your name", value=st.session_state.get("analyst_name", "Analyst"), key="actor")
            st.session_state.analyst_name = actor
            note = st.text_area("Note / evidence", key=f"cnote_{cid}")
            for a in allowed:
                if st.button(K.ACTION_LABEL[a], key=f"{cid}_{a}", type="primary" if a in ("confirm", "uphold") else "secondary"):
                    who = "merchant" if a in ("merchant_responded", "appeal") else actor
                    c2, e2 = K.act(c.copy(), e.copy(), cid, a, now, who, note)
                    state.save_cases(c2, e2)
                    if a in ("confirm", "uphold"):
                        state.add_review(mid, "confirmed", f"{cid}: {note}", source="case management")
                    elif a in ("clear", "overturn"):
                        state.add_review(mid, "cleared", f"{cid}: {note}", source="case management")
                    st.rerun()
        if case.outcome == "confirmed":
            st.markdown("##### Regulatory reporting")
            st.download_button("Draft STR for FIU-IND (Markdown)", RPT.str_draft(mid, r, state.prepared(), case_id=cid,
                               events=e[e.case_id == cid]), f"STR_draft_{mid}.md", key=f"str_{cid}")

    a, b = st.columns(2)
    a.download_button("Download all cases (CSV)", c.to_csv(index=False), "cases.csv")
    b.download_button("Download audit log (CSV)", e.to_csv(index=False), "case_audit_log.csv")
