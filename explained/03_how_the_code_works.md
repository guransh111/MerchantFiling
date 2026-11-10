# 3. How the code works (no coding knowledge needed)

Think of it as an assembly line. Each station is one Python file in `src/`.

```
 generate.py     features.py      score.py        network.py      changepoint.py   learn.py         actions.py
 ┌─────────┐    ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐      ┌─────────┐      ┌─────────┐
 │ fake    │───▶│10 weekly│────▶│ compare │────▶│ who is  │────▶│ when did│─────▶│ learn   │─────▶│ what to │
 │ world   │    │ signals │     │ w/ peers│     │ linked? │     │ it flip?│      │ from    │      │ do + why│
 │ (or YOUR│    │         │     │ 0-100   │     │ 0-100   │     │         │      │ analysts│      │ (ladder)│
 │  data)  │    └─────────┘     └─────────┘     └─────────┘     └─────────┘      └─────────┘      └─────────┘
 └─────────┘
        schema.py cleans uploaded data · engine.py runs everything in one call · evaluate.py grades it
                         app/dashboard.py is the website on top of all of it
```

| File | Job |
|---|---|
| `config.py` | Every setting (weights, thresholds, switches) in one `Settings` object the dashboard can change live |
| `schema.py` | Bring-your-own-data: recognises column names, cleans messy files, explains what's missing (file 12) |
| `generate.py` | Builds the fake world; now with sliders for size, mix and how hard fraudsters hide |
| `features.py` | Payments → 10 weekly signals (switches signals off when a column is missing) |
| `score.py` | Peer drift score; can also score a single new merchant |
| `network.py` | Links, PageRank from known-bad merchants, clusters |
| `changepoint.py` | Finds the week behaviour changed (file 13) |
| `learn.py` | Learning loop, anomaly detector, simulated review history (file 13) |
| `actions.py` | Ladder + plain-English reasons, including analyst overrides and merchant explanations |
| `tuning.py` | Cheapest threshold in rupees (file 13) |
| `replay.py` | Week-by-week replay: days from start of fraud to action (file 16) |
| `cases.py` | Case lifecycle, 72h deadlines, appeals, audit log, metrics (file 16) |
| `scanner.py` | Finds UPI IDs on public betting pages and matches them to merchants (file 16) |
| `reporting.py` | Draft STRs, I4C file, consortium tokens for privacy-safe sharing (file 16) |
| `app/ui.py` | The look: chart theme, ladder colours, "ladder pips" (file 17) |
| `engine.py` | Runs it all: `prepare` (slow: payments → signals and links) then `analyse` (fast: seconds) |
| `evaluate.py` | Grades against the hidden truth, charts, stress test |

`run_all.py` runs: generate → engine → evaluate. The split in `engine.py` is what makes the dashboard
quick: signals are computed once, and moving a slider only re-runs the fast part.

---

## Station 1: `generate.py` builds the fake world

**Why fake?** Real payment data is confidential. Simulating lets us plant fronts whose identity we
know, which is the only way to measure accuracy.

**What it creates (1,000 merchants, 16 Indian cities, 37 weeks from March to November 2026):**

| Hidden type | How many | How they behave |
|---|---|---|
| Honest shop | 920 | Category-specific hours (kirana: morning and evening; restaurant: lunch and dinner), realistic ticket sizes, mostly local customers, pay a few suppliers weekly, Diwali boost (sweet shops 3x, electronics 2.5x) |
| Betting front | 40 | Registered as a small kirana or electronics shop. Bets arrive around cricket matches and late at night in round amounts (₹500, ₹1,000), from gamblers in many states who deposit repeatedly. Many pay winners straight back out the same day |
| Rented account | 10 | Honest for weeks 8 to 28, then the phone and bank account change and betting starts |
| Honest shop whose business changed | 30 | Restaurant screening IPL matches, kirana turning wholesaler, late-night delivery, online store, second branch. **These are the people we must not punish** |

**Realism tricks (so it isn't too easy):**
- 30% of fronts keep some genuine-looking daytime shop traffic as cover.
- 30% of operators avoid perfectly round amounts (₹499, ₹1,007).
- 40% of operators pay winners from other accounts, so their fronts show no payouts.
- 30% of fronts run on their own phone rather than the operator's; half use their own bank account.
- 25% of fronts submit fake "we're having a festival sale" declarations.
- Honest shops sometimes change phone (5%) or bank account (2%) for innocent reasons.
- 10% of honest shops price in round numbers too.
- Neighbouring shops in the same city share customers.

It also creates `known_bad.csv`: half of the fronts, whose UPI IDs were "found on a public betting
website or Telegram channel". This simulates scraping public betting pages, as mFilterIt does in real life.

**Output files:** `merchants.csv`, `transactions.csv` (~3 million rows), `calendar.csv` (IPL, the
September series, Diwali), `known_bad.csv`, `declarations.csv`, `account_events.csv`.

## Station 2: `features.py` computes weekly signals

It turns 3 million payments into one row per merchant per week, with 10 numbers (file 04 explains
each). Weeks with fewer than 5 payments are skipped as too little information. Output: `features.csv`.

## Station 3: `score.py` computes the drift score

For each merchant, week and signal: how far is this merchant from the median of its peers that week,
measured in "typical spreads"? It adds up the risky-direction deviations, with each signal capped,
and squashes the total into 0 to 100. A merchant's overall drift score is the average of its 3 worst
weeks, so a single odd week doesn't count. File 05 explains this properly.

It also runs the **no-peer baseline** (`--no-peer`), which compares each merchant only with its own
past. We use it to show why peers matter. Outputs: `scores.csv`, `scores_weekly.csv`, `*_nopeer.csv`.

## Station 4: `network.py` follows the links

It draws a line between two merchants when they share:

| Shared thing | Weight | Why it matters |
|---|---|---|
| Same phone/device | 3 | One person running several "different" shops |
| Same settlement bank account | 3 | Money from several shops ending up in one place |
| Many of the same customers (≥10 and ≥5% overlap) | up to 5 | Gamblers deposit wherever the operator says |
| Many of the same payout accounts (≥3) | 2 | Paying the same winners |

Then **personalized PageRank** (the idea behind Google's original ranking) spreads suspicion from
known-bad merchants along these lines. Output: `network.csv` (score 0 to 100 plus "linked to M0070:
same device, 166 shared customers").

## Station 5: `actions.py` decides and explains

```
risk score = drift score + 0.25 × network score     (known-bad match → at least 95)
```

Then the ladder (file 06): Monitor < 60 ≤ Ask < 75 ≤ Friction < 90 ≤ Review. Adjustments:
- Review requires a network link; otherwise the merchant stays at Friction.
- Phone **and** bank account changed within 14 days means a possible rental: at least Ask, plus
  one level if network-linked.
- A pre-declared change moves the merchant down one level, unless it is network-linked.
- **New in v2:** a behaviour shift right after an account change (change point) escalates; the
  learning loop can move Monitor → Ask when it's 80%+ sure; an **analyst's decision overrides
  everything** (confirmed → Offboard & report, level 4; cleared → Monitor).

It writes the top 3 reasons in plain English, comparing the merchant with its peers, e.g. *"Share of
money received during cricket match hours: 61% vs 10% for similar kirana stores in tier-1 cities"*.
Output: `decisions.csv`.

## Station 6: `evaluate.py` grades the system

Only now do we open the hidden labels and compare. It writes `reports/results.md` and 7 charts,
including the learned weights, the cost curve and the **stress test** (five fresh worlds with
increasingly evasive fraudsters). Files 07 and 13 explain them.

## The dashboard: `app/dashboard.py` (+ `app/views/`)

A website built with Streamlit, with a menu on the left:

| Page | What it's for |
|---|---|
| Start here | What it is and how to use it |
| Load data | Upload your own files, generate a world, download templates (file 12) |
| Overview | Counts per action, share of payment volume under friction, most common reasons, which signals your data supports |
| Risk queue | Sortable, filterable list; download all decisions as CSV |
| Merchant drill-down | Full case file: reasons, weekly score with the change-point marker, peer table, hour-of-day chart, network links, latest payments, **Confirm / Clear buttons** |
| Network | Clusters of linked merchants and an interactive picture |
| Check a merchant | Score one merchant from sliders or its payments file |
| Settings & what-if | Every weight and threshold; shows who moved after a change |
| Learning loop | What it learned, suggested weights, audit queue |
| Performance & thresholds | Precision/recall, cost-based threshold, stress test |
| Case management | Cases with 72h deadlines, decisions, appeals, audit log, metrics |
| Scan a betting page | Paste a public page, find UPI IDs, add matches to the known-bad list |
| Consortium check | Share offboarded merchants with other providers as hashed tokens |
| Regulator reports | Draft STRs (zip), I4C Suspect Registry file, consortium tokens |
| Merchant's view / Customer's payment screen | The human side; merchant explanations feed back in |

## Tests: `tests/test_pipeline.py`

There are 31 automated checks (22 in `test_pipeline.py`, 9 in `test_operations.py`). Examples: fronts peak on match days; drifters score below fronts; no
Review without a network link; change points find every rented handover; the learning loop trains
out-of-fold; an analyst's decision overrides the system; messy uploads are mapped correctly; a
3-column upload still works; the hidden label is never used as an input (that would be cheating,
called "leakage"). Run them with `pytest -q`.
