"""Load data window (opened from Home): upload your own, generate a simulated world, templates."""
from __future__ import annotations

import io
import os
import zipfile

import pandas as pd
import streamlit as st

import state
from src import config as C
from src import engine, schema
from src.generate import simulate

OPTIONAL_TABLES = {
    "known_bad": "Known-bad list: merchants whose UPI ID was found on betting pages (seeds the network)",
    "declarations": "Merchant declarations: changes merchants told you about in advance",
    "account_events": "Account events: phone / settlement-account changes",
    "calendar": "Match calendar: cricket match times (otherwise the built-in IPL schedule is used)",
}


@st.cache_data(show_spinner=False)
def _read(data: bytes, name: str) -> pd.DataFrame:
    return schema.read_any(io.BytesIO(data), name)


@st.cache_data(show_spinner="Building example files...")
def _templates_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, df in schema.template_tables().items():
            z.writestr(f"{name}.csv", df.to_csv(index=False))
        z.writestr("README.txt", _dictionary().to_string(index=False))
    return buf.getvalue()


def _dictionary() -> pd.DataFrame:
    rows = []
    for t, cols in schema.SCHEMA.items():
        for c, (req, desc, syn) in cols.items():
            rows.append({"file": t, "column": c, "required": "yes" if req else "", "meaning": desc,
                         "also recognised as": ", ".join(syn[:5])})
    return pd.DataFrame(rows)


def _mapping_ui(table: str, df: pd.DataFrame) -> dict:
    guess = schema.guess_mapping(table, list(df.columns))
    opts = ["(not in my file)"] + list(df.columns)
    mapping = {}
    cols = st.columns(3)
    for i, (col, (req, desc, _)) in enumerate(schema.SCHEMA[table].items()):
        default = opts.index(guess[col]) if guess[col] in opts else 0
        pick = cols[i % 3].selectbox(f"{col}{' *' if req else ''}", opts, index=default, help=desc,
                                     key=f"map_{table}_{col}")
        mapping[col] = None if pick == opts[0] else pick
    return mapping


def _upload_tab():
    st.markdown("Upload your merchants and their payments as **CSV or Excel**. Column names don't need to match "
                "exactly: we guess the mapping and you can correct it. Columns marked * are required; everything else "
                "is optional and simply switches on more signals.")
    tables, mappings = {}, {}
    c1, c2 = st.columns(2)
    with c1:
        fm = st.file_uploader("Merchants file *", type=["csv", "xlsx", "xls", "gz"], key="up_merchants")
    with c2:
        ft = st.file_uploader("Transactions file *", type=["csv", "xlsx", "xls", "gz"], key="up_transactions")
    with st.expander("Optional files (known-bad list, declarations, account events, match calendar)"):
        opt_files = {t: st.file_uploader(desc, type=["csv", "xlsx", "xls"], key=f"up_{t}") for t, desc in OPTIONAL_TABLES.items()}

    files = {"merchants": fm, "transactions": ft} | opt_files
    for t, f in files.items():
        if f is None:
            continue
        df = _read(f.getvalue(), f.name)
        with st.expander(f"**{t}**: {f.name} ({len(df):,} rows). Check the column mapping", expanded=t in ("merchants", "transactions")):
            st.dataframe(df.head(5), width="stretch", hide_index=True)
            mappings[t] = _mapping_ui(t, df)
            tables[t] = df

    if fm is None or ft is None:
        st.info("Waiting for both a merchants file and a transactions file. No data? Download the example files in "
                "the **Templates** tab, or generate a simulated world.")
        return

    use_labels = False
    if mappings.get("merchants", {}).get("label"):
        use_labels = st.checkbox("My `label` column is real investigation outcomes: use it to simulate past analyst "
                                 "reviews so the learning loop can train", value=False)
    if st.button("Check data and run the analysis", type="primary"):
        mapped = {t: schema.apply_mapping(df, t, mappings[t]) for t, df in tables.items()}
        clean, rep = schema.clean(mapped)
        for e in rep.errors:
            st.error(e)
        for w in rep.warnings:
            st.warning(w)
        for i in rep.info:
            st.caption(i)
        if not rep.ok:
            return
        with st.status("Analysing your data...", expanded=True) as status:
            p = engine.prepare(clean, progress=status.write, name=f"Uploaded: {fm.name}")
            if use_labels:
                status.write("Simulating past reviews from your labels...")
                p.review_history = engine.demo_review_history(p)
            status.update(label="Done", state="complete")
        state.set_dataset(p, clean["transactions"], clean["calendar"])
        st.session_state._toast = f"Loaded {len(p.merchants):,} merchants from {fm.name}"
        st.rerun()  # closes the window; Home shows the new dataset


def _memory_gb() -> float:
    """Memory this app may use: the container limit if there is one (cloud hosts), else the machine's RAM."""
    for path in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        try:
            raw = open(path).read().strip()
            if raw.isdigit() and int(raw) < 1 << 60:
                return int(raw) / 1e9
        except OSError:
            pass
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1e9
    except (ValueError, OSError, AttributeError):
        return 4.0


def max_world_size() -> int:
    """Generating ~1,000 merchants needs ~2 GB of memory, 300 needs ~0.9 GB. Free cloud hosts have ~1 GB."""
    override = os.environ.get("TRUSTLOOP_MAX_MERCHANTS")
    if override and override.isdigit():
        return max(100, int(override))
    gb = _memory_gb()
    return 1000 if gb >= 3 else 600 if gb >= 2 else 300 if gb >= 1 else 150


def _generate_tab():
    st.markdown("Build a fresh synthetic world with your own assumptions, e.g. *what if 10% of merchants are fronts "
                "and operators hide much better?* Every merchant's hidden truth is known, so you can see how well the "
                "system copes.")
    with st.form("gen"):
        c1, c2, c3 = st.columns(3)
        cap = max_world_size()
        n = c1.slider("Merchants", 100, cap, min(300, cap), 50,
                      help=None if cap >= 1000 else f"Capped at {cap} to fit this server's memory. Run it on your own "
                                                     "computer for up to 1,000.")
        weeks = c2.slider("Weeks of data", 12, 37, 37)
        seed = c3.number_input("Random seed", 1, 9999, 42, help="Same seed + same settings = identical world")
        c1, c2, c3 = st.columns(3)
        fronts = c1.slider("% betting fronts", 0.0, 20.0, 4.0, 0.5)
        rented = c2.slider("% rented accounts", 0.0, 10.0, 1.0, 0.5)
        drifters = c3.slider("% honest shops whose business changes", 0.0, 15.0, 3.0, 0.5)
        c1, c2 = st.columns(2)
        evasion = c1.slider("How hard operators try to hide (evasion)", 0.0, 1.0, 0.3, 0.05,
                            help="0.3 = default. Higher: fronts mimic shop traffic, avoid round amounts, use their own "
                                 "phones and bank accounts, spread bets thinly, recruit local gamblers.")
        kb = c2.slider("% of fronts already on the known-bad list", 0.0, 100.0, 50.0, 5.0)
        go = st.form_submit_button("Generate and analyse", type="primary")
    if go:
        with st.status("Building your world...", expanded=True) as status:
            status.write(f"Simulating {n} merchants over {weeks} weeks...")
            m, tx, cal, kbl, ev, decl = simulate(
                n, seed=int(seed), n_weeks=weeks, evasion=evasion, known_bad_share=kb / 100,
                label_mix={"betting_front": fronts / 100, "rented": rented / 100, "genuine_drifter": drifters / 100})
            tables = {"merchants": m, "transactions": tx, "calendar": cal, "known_bad": kbl,
                      "declarations": decl, "account_events": ev}
            p = engine.prepare(tables, start=C.START_DATE, progress=status.write,
                               name=f"Generated: {n} merchants, evasion {evasion:.2f}, seed {seed}")
            status.write("Simulating last quarter's analyst reviews (training data for the learning loop)...")
            p.review_history = engine.demo_review_history(p)
            status.update(label="Done", state="complete")
        state.set_dataset(p, tx, cal)
        st.session_state.generated_tables = tables
        st.session_state._toast = f"Generated {len(m):,} merchants and {len(tx):,} payments"
        st.rerun()  # closes the window; Home shows the new world
    if st.session_state.get("generated_tables") and not state.is_demo():
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for name, df in st.session_state.generated_tables.items():
                z.writestr(f"{name}.csv", df.to_csv(index=False))
        st.download_button("Download this world as CSV files (zip)", buf.getvalue(), "trace_world.zip")


def body():
    """Contents of the Load data window."""
    p = state.prepared()
    st.caption(f"Loaded now: {p.name} · {len(p.merchants):,} merchants")
    if not state.is_demo() and st.button("Switch back to the demo dataset"):
        state.use_demo()
        st.session_state._toast = "Switched back to the demo dataset"
        st.rerun()
    t1, t2, t3 = st.tabs(["Upload your own data", "Generate a simulated world", "Templates & data guide"])
    with t1:
        _upload_tab()
    with t2:
        _generate_tab()
    with t3:
        st.markdown("Download example files in exactly the right format, open them in Excel, replace with your data, "
                    "and upload them in the first tab.")
        st.download_button("Download example files (zip of CSVs)", _templates_zip(), "trace_templates.zip", type="primary")
        st.markdown("##### What each column means")
        st.dataframe(_dictionary(), hide_index=True, width="stretch")
        st.markdown("##### Minimum viable upload")
        st.markdown("- **merchants**: `merchant_id`, `category`\n- **transactions**: `merchant_id`, `ts` (date & time), `amount`\n\n"
                    "With only these, the system uses round amounts, match hours, late night, variety and growth. "
                    "Add payer IDs, payer state, direction (in/out), declared turnover, device and bank account to "
                    "switch on the other signals and the network.")
