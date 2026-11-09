# 7. Results: what the numbers mean

The full auto-generated report is [`reports/results.md`](../reports/results.md). This file explains it.

Setup: 1,000 simulated merchants over 37 weeks: 920 honest, 30 honest-but-changed, 40 betting
fronts, 10 rented accounts.

## Two words you need

- **Precision:** of the merchants we acted on, what % were really bad? *Low precision = harassing
  honest people.*
- **Recall:** of the really bad merchants, what % did we act on? *Low recall = fraud continues.*

There's always a trade-off, like a loan approval cut-off: approve fewer applicants and you get fewer
defaults (precision up), but you turn away good borrowers.

## Headline table

| System | Bad merchants caught (recall) | Precision of penalties | Honest shops penalised | Honest-but-changed penalised |
|---|---|---|---|---|
| A. Own-history only | 20% | 100% | 0 of 920 | 0 of 30 |
| B. Peer drift score only | 100% | 93% | 0 of 920 | 4 of 30 |
| **C. Full TrustLoop** | **100%** | **98%** | **0 of 920** | **1 of 30** |

"Penalised" = Friction or above. With "Ask" counted as an action, TrustLoop's precision is 82%: the 11
honest-but-changed shops it acts on are mostly just *asked* to explain, which is the intended
behaviour.

**How to read it:**
- **A** catches only the 10 rented accounts (they *changed*). It misses all 40 fronts, because a
  front that bet from day one never changes relative to itself.
- **B** catches everyone but penalises 4 honest shops whose business changed.
- **C** adds the network and declarations. Declarations lower honest drifters by a level, and the
  network corroboration confirms the fronts. Penalties on honest-but-changed shops drop from 4 to 1.

## The charts (in `reports/`)

1. **`1_scores_by_label.png`**: each dot is a merchant. Left panel (own history): fronts sit with the
   honest shops. Right panel (peers): fronts jump to 85 to 93, clearly separated.
2. **`2_diwali_false_alarms.png`**: share of honest sweet and electronics shops triggering a simple
   "sales spiked" alert. With own history, 62% in Diwali week; with peers, about 1%. **This is the
   best single slide for "protecting legitimate businesses".**
3. **`3_actions_by_label.png`**: what happens to each group. All 920 honest shops: Monitor. Fronts
   and rented: almost all Review.
4. **`4_weekly_examples.png`**: a betting front stays above the line all year, peaking in IPL and
   the September series. An honest restaurant that screens matches only bumps up during the series.

Charts 5 to 7 are new in version 2 (explained in file 13):

5. **`5_learned_weights.png`**: hand-set vs learned weights. The learning loop discovered that
   match hours separate fronts from *cleared honest merchants* poorly, and out-of-state payers well.
6. **`6_cost_curve.png`**: expected cost in rupees at every threshold. Cheapest anywhere from 80 to 91.
7. **`7_stress_test.png`**: as fraudsters hide better, behaviour alone falls to 50%; the full
   system stays at 100%.

## Version 2 results in one table

| Layer | Result on demo data |
|---|---|
| Change points | Found the exact handover week for **10 of 10** rented accounts; no honest shop had a shift coinciding with an account change |
| Learning loop | Trained on 80 simulated past reviews (50 confirmed, 30 cleared); cross-validated AUC 1.00 |
| Anomaly detector | Median percentile: honest 46, honest-but-changed 94, fronts 97. Used for audits only |
| Cost-based threshold | Lowest cost (₹75,000) for any Friction threshold from 80 to 91 |
| Stress test (100% evasion) | Full system 100%, behaviour alone 50%, 0 honest merchants penalised |

## Network result

30 of the 50 bad merchants were **not** on the known-bad list. The network linked 93% of them to a
known-bad merchant through a shared phone, bank account or gamblers.

## The honest caveat (say this before a judge does)

- **The data is simulated by us.** We designed both the fronts and the detector, so the separation
  is cleaner than reality. The results show the method works *as designed*, not real-world accuracy.
- Real fraudsters adapt (mimic retail hours, use more accounts, avoid round numbers). We added some
  of that evasion deliberately (30% mimic shops, 30% avoid round amounts, 40% hide payouts), and it
  still works because no single signal is required.
- The one honest-but-changed shop that gets Friction is a restaurant screening matches that did *not*
  pre-declare. In reality it would get a 72-hour window to explain, and a reviewer would clear it.

## The numbers to memorise

- **100%** of bad merchants caught vs **20%** for a typical detector
- **0 of 920** honest shops penalised
- **62% → 1%** Diwali false alarms
- **93%** of fronts not on the known-bad list found through the network
- **10 of 10** rented accounts pinned to their exact handover week
- **50% vs 100%**: behaviour alone vs full system when fraudsters hide as hard as they can
