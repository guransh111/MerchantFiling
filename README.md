# TrustLoop: does this merchant's money match its business?

A working prototype for the **Merchant Legitimacy Challenge**:

> How might a payment provider identify merchants whose actual activity (e.g. illegal betting)
> differs from their declared business, while protecting legitimate businesses from unnecessary
> scrutiny, disruption or penalties?

**New here? Read [`explained/00_START_HERE.md`](explained/00_START_HERE.md) first.** It explains
everything in plain English. No coding or statistics background needed.

## The idea in one line

Don't ask *"is this behaviour unusual?"* Ask *"does this behaviour match what the merchant declared,
compared with similar shops in the same week?"* Then respond **proportionately**: ask first, add
friction second, hold money only with independent corroboration, and offboard only when a human confirms.

## What's inside

| Layer | What it does |
|---|---|
| 10 weekly signals | Match hours, late night, round amounts, out-of-state payers, repeat payments, amount variety, same-day pass-through, payout accounts, growth, size vs declared |
| Peer drift score | Each merchant vs its peers in the same week, so Diwali is normal; capped signals, so several must agree |
| Network | Shared phones, bank accounts, gamblers; PageRank from known-bad merchants; cluster detection |
| Change points | The week behaviour flipped, and whether a phone/bank change came with it (catches rented accounts) |
| Learning loop | Learns from analysts' confirm/clear decisions; suggests better weights; out-of-fold evaluation |
| Anomaly detector | Isolation Forest to choose which unflagged merchants to audit |
| Cost-based thresholds | Picks the cut-off with the lowest expected cost in rupees |
| Proportionate ladder | Monitor → Ask → Friction → Review → Offboard, with a plain-English reason for every flag |
| GST cross-check | UPI takings far above GST-declared turnover = independent corroboration |
| Operations | Case management (72h deadlines, appeals, audit log), betting-page UPI ID scanner, consortium sharing via hashed tokens, draft STRs for FIU-IND, I4C file, versioned policy with change log |
| Time-to-detection replay | Re-runs the year week by week with no hindsight to measure days to action |

## Put your own data in

The dashboard (`streamlit run app/dashboard.py`) lets you:
- **Upload** merchants and transactions as CSV or Excel, with **any column names** (automatic
  mapping you can correct). The minimum is 4 columns; more columns switch on more signals.
- **Generate** a simulated world with your own assumptions (size, % fronts, how hard fraudsters hide).
- **Check a merchant**: type one in with sliders, or upload its payments.
- **Confirm or clear** cases as an analyst, and submit **merchant explanations**; both feed back in.
- Change **every weight and threshold** live and see who moves.

Guide: [`explained/12_using_your_own_data.md`](explained/12_using_your_own_data.md). Example files: [`templates/`](templates/).

## Data

The demo uses a **simulated** world (real transaction-level UPI data isn't public), calibrated so
average payment sizes per merchant category match **real NPCI UPI statistics for July 2025**
([`data/real/`](data/real/)). Betting behaviour follows Enforcement Directorate cases and the CUTS
report. Full explanation: [`explained/14_data_and_method.md`](explained/14_data_and_method.md).

## Headline results (synthetic data, 1,000 merchants, 37 weeks)

| | Typical "own-history" detector | TrustLoop |
|---|---|---|
| Betting fronts & rented accounts caught | **20%** | **100%** |
| Honest shops penalised | 0 of 920 | **0 of 920** |
| Honest shops whose business changed, penalised | 1 of 30 | **1 of 30** (12 more simply asked to explain) |
| Honest sweet/electronics shops with a "sales spike" alert in Diwali week | **62%** | **1%** |
| Rented accounts pinned to their exact handover week | | **10 of 10** |
| Caught when fraudsters hide as hard as possible (stress test) | | **100%** (behaviour alone: 55%) |
| Days from start of betting to a penalty (week-by-week replay, no hindsight) | | **7** median (fastest possible) |
| Honest merchants ever penalised in any week of the year | | **1 of 950** |

Full results and charts: [`reports/results.md`](reports/results.md).

![What the system does to each kind of merchant](reports/3_actions_by_label.png)

## Run it

```bash
pip install -r requirements.txt
```

```bash
streamlit run app/dashboard.py
```

The demo results are already in the repo. To regenerate everything (about 4 minutes):

```bash
python run_all.py
```

Step-by-step instructions for beginners: [`explained/08_how_to_run.md`](explained/08_how_to_run.md).

## Put it online

- **Live dashboard → Streamlit Community Cloud** (free): main file `app/dashboard.py`.
- **Landing page → Vercel** (free): import the repo; `vercel.json` builds `site/`. Set the `DASHBOARD_URL`
  environment variable to your Streamlit app URL.

Vercel can't host the Streamlit dashboard itself (it needs a server that stays running).
Step-by-step guide: [`explained/15_putting_it_online.md`](explained/15_putting_it_online.md).

## What's in the repo

| Path | What it is |
|---|---|
| `explained/` | **Plain-English guide**: problem, idea, signals, scoring, results, pitch, your own data, advanced layers, glossary |
| `src/engine.py` | Runs the whole pipeline on any dataset (`prepare` = slow part, `analyse` = fast part) |
| `src/schema.py` | Bring-your-own-data: column recognition, cleaning, validation |
| `src/generate.py` | Synthetic world: ~3 million UPI payments, IPL, Diwali, fronts, rented accounts, honest drifters |
| `src/features.py`, `score.py` | 10 weekly signals; peer drift score |
| `src/network.py`, `changepoint.py`, `learn.py` | Network and clusters; change points; learning loop and anomaly detector |
| `src/actions.py`, `tuning.py` | Response ladder with reasons; cost-based thresholds |
| `src/evaluate.py` | Accuracy vs hidden truth, charts, stress test → `reports/` |
| `src/config.py` | Every setting in one `Settings` object |
| `src/replay.py`, `cases.py`, `scanner.py`, `reporting.py` | Replay; case management; betting-page scanner; STRs, I4C file, consortium tokens |
| `app/` | Streamlit dashboard (16 pages) |
| `site/`, `vercel.json` | Landing page for Vercel |
| `templates/` | Example input files in the right format |
| `tests/` | 31 automated checks (`pytest -q`) |
| `explained/IMPLEMENTATION_PLAN_v2.md` | The implementation plan updated to what is built |
