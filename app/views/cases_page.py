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
    sim = " Demo: the case history is simulated, a plausible quarter of analyst work with occasional mistakes and " \
          "appeals; what you do here is real for this session." if st.session_state.get("cases_simulated") else ""
    st.caption(f"Clock: {now:%d %b %Y %H:%M}, the end of the data. Merchants have {K.SLA_HOURS} hours to reply; "
               f"appeals are decided within {K.APPEAL_SLA_DAYS} days by a second analyst.{sim}")

    k = K.metrics(c, e, now)
    if len(c):
        lc = ui.LEVEL_COLOR
        n = len(c)
        st_ = c.status.value_counts()
        open_n = int(st_.reindex(["Awaiting merchant", "Under review"]).fillna(0).sum())
        appealed = int(st_.get("Appealed", 0))
        confirmed = int(st_.reindex(["Closed: confirmed", "Appeal upheld"]).fillna(0).sum())
        cleared = int(st_.reindex(["Closed: cleared", "Appeal overturned"]).fillna(0).sum())
        st.markdown(f"##### {n:,} cases: {open_n + appealed:,} open, {confirmed:,} confirmed, {cleared:,} cleared")
        st.markdown(ui.funnel([
            (n, "All cases", "Opened when a merchant reaches Ask or above", ui.NEUTRAL_BAR,
             [(open_n / n, lc[1]), (appealed / n, lc[2]), (confirmed / n, lc[4]), (cleared / n, ui.GOOD)]),
            (open_n, "Open", f"Waiting on the merchant or an analyst; {k['overdue']} overdue", lc[1], open_n / n),
            (appealed, "Appealed", "A second analyst decides within 7 days", lc[2], appealed / n),
            (confirmed, "Confirmed misuse", "Includes appeals that were upheld", lc[4], confirmed / n),
            (cleared, "Cleared as genuine", "Includes appeals that were overturned", ui.GOOD, cleared / n),
        ]), unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        left, right = st.columns([3, 2], gap="medium")
        with left, ui.panel("case_clock"):
            st.markdown(f"##### Open cases against the {K.SLA_HOURS}-hour clock")
            op = c[c.status.isin(K.OPEN)].copy()
            if len(op):
                op["opened_t"], op["due_t"] = pd.to_datetime(op.opened), pd.to_datetime(op.due)
                op = op.sort_values("due_t")
                rows = []
                for x in op.itertuples():
                    span = (x.due_t - x.opened_t).total_seconds() or 1
                    left_h = (x.due_t - now).total_seconds() / 3600
                    used = (now - x.opened_t).total_seconds() / span
                    rows.append((x.merchant_id, f"· {x.case_id} · {x.status}", used,
                                 f"overdue {-left_h:.0f}h" if left_h < 0 else f"{left_h:.0f}h left"))
                st.markdown(ui.clock_rows(rows), unsafe_allow_html=True)
                st.caption("The bar is the share of the allowed time already used; it turns orange in the last third")
            else:
                st.caption("No open cases")
        with right, ui.panel("case_health"):
            st.markdown("##### How the desk is doing")
            rates = [(lab, float(v)) for lab, v in [("Replies within 72h", k["within_sla"]),
                                                    ("Cleared as genuine", k["cleared_share"]),
                                                    ("Appeals overturned", k["overturn_rate"])] if pd.notna(v)]
            if rates:
                st.markdown(ui.bar_list(rates, fmt="{:.0%}", accent_first=False, max_value=1), unsafe_allow_html=True)
            if pd.notna(k["median_hours_to_decision"]):
                st.caption(f"Median time to a decision: {k['median_hours_to_decision']:.0f} hours. A high overturn rate "
                           "means the system or the analysts are over-flagging")

    flagged_no_case = d[d.level.between(1, 3) & ~d.merchant_id.isin(c.merchant_id if len(c) else [])]
    if len(flagged_no_case):
        if st.button(f"Open cases for {len(flagged_no_case)} newly flagged merchant(s)"):
            c, e = K.open_cases(d, c, e, now, actor="system")
            state.save_cases(c, e)
            st.rerun()

    if not len(c):
        st.info("No cases yet. Cases open automatically for merchants at Ask or above.")
        return
    st.markdown("##### All cases")
    show = st.segmented_control("Show", ["Open", "Closed", "All"], default="All", key="case_filter",
                                label_visibility="collapsed") or "All"
    keep = {"Open": K.OPEN, "Closed": [x for x in K.ACTIONS if x not in K.OPEN], "All": list(K.ACTIONS)}[show]
    v = c[c.status.isin(keep)].copy()
    v["overdue"] = v.status.isin(K.OPEN) & (pd.to_datetime(v.due) < now)
    v["category"] = v.merchant_id.map(d.set_index("merchant_id").category)
    v["system action"] = v.merchant_id.map(d.set_index("merchant_id").level).map(C.LEVEL_SHORT)
    if st.session_state.reveal and "label" in d:
        v["hidden truth"] = v.merchant_id.map(d.set_index("merchant_id").label).map(lambda x: state.LABEL_NAME.get(x, x))
    for col in ("opened", "due", "decided"):
        v[col] = pd.to_datetime(v[col], errors="coerce")
    st.dataframe(v.sort_values(["overdue", "opened"], ascending=[False, False]).drop(columns=["level_at_open"]),
                 hide_index=True, width="stretch", height=320, column_config={
                     "case_id": "Case", "merchant_id": "Merchant", "status": "Status", "assignee": "Analyst",
                     "outcome": "Outcome", "appeal_outcome": "Appeal", "category": "Declared as",
                     "system action": "System action",
                     "opened": st.column_config.DatetimeColumn("Opened", format="D MMM, HH:mm"),
                     "due": st.column_config.DatetimeColumn("Due", format="D MMM, HH:mm"),
                     "decided": st.column_config.DatetimeColumn("Decided", format="D MMM, HH:mm"),
                     "overdue": st.column_config.CheckboxColumn("Overdue")})

    with ui.panel("case_work"):
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
            reasons = [x for x in [row.reason_1, row.reason_2, row.reason_3] if isinstance(x, str) and x]
            if reasons:
                lvl = int(row.level)
                st.markdown("".join(ui.reason_compare(x, ui.LEVEL_COLOR[lvl] if lvl else ui.ACCENT) for x in reasons),
                            unsafe_allow_html=True)
            due = pd.Timestamp(case.due)
            if case.status in K.OPEN:
                hrs = (due - now).total_seconds() / 3600
                (st.error if hrs < 0 else st.warning if hrs < 24 else st.caption)(
                    f"Deadline {due:%d %b %H:%M}: " + (f"overdue by {-hrs:.0f}h" if hrs < 0 else f"{hrs:.0f}h left"))
            st.markdown("##### Audit log")
            log = e[e.case_id == cid].sort_values("ts")
            st.dataframe(log[["ts", "actor", "action", "note"]].assign(ts=pd.to_datetime(log.ts, errors="coerce")),
                         hide_index=True, width="stretch", column_config={
                             "ts": st.column_config.DatetimeColumn("When", format="D MMM, HH:mm"),
                             "actor": "Who", "action": "What", "note": "Note"})
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

    dl = st.container(horizontal=True, gap="small")
    dl.download_button("Download all cases (CSV)", c.to_csv(index=False), "cases.csv", icon=":material/download:")
    dl.download_button("Download audit log (CSV)", e.to_csv(index=False), "case_audit_log.csv", icon=":material/download:")
