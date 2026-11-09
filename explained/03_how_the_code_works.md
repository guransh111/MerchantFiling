# 3. How the code works (no coding knowledge needed)

Think of it as an assembly line with six stations. Each station is one Python file in `src/`. Each
reads the previous station's output from the `data/` folder and writes its own.

```
 generate.py      features.py       score.py          network.py        actions.py        evaluate.py
 ┌──────────┐    ┌──────────┐     ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
 │ fake     │───▶│ 10 weekly│────▶│ compare  │─────▶│ who is   │─────▶│ what to  │─────▶│ how good │
 │ merchants│    │ signals  │     │ with     │      │ linked to│      │ do + why │      │ was it?  │
 │ + 3M     │    │ per shop │     │ peers    │      │ known bad│      │ (ladder) │      │ charts   │
 │ payments │    │          │     │ 0-100    │      │ 0-100    │      │          │      │          │
 └──────────┘    └──────────┘     └──────────┘      └──────────┘      └──────────┘      └──────────┘
                                                                            │
                                                                            ▼
                                                            app/dashboard.py (the demo website)
```

`run_all.py` runs all six in order. `src/config.py` holds every setting (dates, weights, thresholds)
in one place, with comments, so you can tweak numbers without touching the logic.

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

It writes the top 3 reasons in plain English, comparing the merchant with its peers, e.g. *"Share of
money received during cricket match hours: 61% vs 10% for similar kirana stores in tier-1 cities"*.
Output: `decisions.csv`.

## Station 6: `evaluate.py` grades the system

Only now do we open the hidden labels and compare. It writes `reports/results.md` and 4 charts.
File 07 explains them.

## The dashboard: `app/dashboard.py`

A small website built with Streamlit. It has five tabs: the risk queue, a merchant drill-down, what
the merchant sees (the "tell us what changed" form and trust tier), what the paying customer sees (the
declared business shown on the payment screen), and the results.

## Tests: `tests/test_pipeline.py`

There are 11 automated checks. Examples: fronts really do peak on match days; drifters score below
fronts; no merchant reaches Review without a network link; the hidden label is never used as an
input (this would be cheating, called "leakage"). Run them with `pytest -q`.
