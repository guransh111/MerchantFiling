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
| A. Own-history only | 20% | 91% | 0 of 920 | 1 of 30 |
| B. Peer drift score only | 100% | 89% | 0 of 920 | 6 of 30 |
| **C. Full Trace** | **100%** | **98%** | **0 of 920** | **1 of 30** |

"Penalised" = Friction or above. With "Ask" counted as an action, Trace's precision is 79%: the 13
honest-but-changed shops it acts on are mostly just *asked* to explain, which is the intended
behaviour.

**How to read it:**
- **A** catches only the 10 rented accounts (they *changed*). It misses all 40 fronts, because a
  front that bet from day one never changes relative to itself.
- **B** catches everyone but penalises 6 honest shops whose business changed.
- **C** adds the network and declarations. Declarations lower honest drifters by a level, and the
  network corroboration confirms the fronts. Penalties on honest-but-changed shops drop from 6 to 1.

## The charts (in `reports/`)

1. **`1_scores_by_label.png`**: each dot is a merchant. Left panel (own history): fronts sit with the
   honest shops. Right panel (peers): fronts jump to 83 to 93, clearly separated.
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
6. **`6_cost_curve.png`**: expected cost in rupees at every threshold. Cheapest anywhere from 85 to 91.
7. **`7_stress_test.png`**: as fraudsters hide better, behaviour alone falls to 55%; the full
   system stays at 100%.

## Version 2 results in one table

| Layer | Result on demo data |
|---|---|
| Change points | Found the exact handover week for **10 of 10** rented accounts; no honest shop had a shift coinciding with an account change |
| Learning loop | Trained on 82 simulated past reviews (50 confirmed, 32 cleared); cross-validated AUC 1.00 |
| Anomaly detector | Median percentile: honest 46, honest-but-changed 94, fronts 97, rented 99. Used for audits only |
| Cost-based threshold | Lowest cost (₹75,000) for any Friction threshold from 85 to 91 |
| Stress test (100% evasion) | Full system 100%, behaviour alone 55%, 0 honest merchants penalised |

## Version 3 results

| Layer | Result on demo data |
|---|---|
| Time-to-detection replay | Fronts: 40 of 40 penalised, median **7 days** (fastest possible), all within 21. Rented: 10 of 10, median 7 days from handover, all within 14. Honest merchants ever penalised in any week: **1 of 950** |
| GST cross-check | Flags fronts and rented accounts only; **no honest merchant**. With it, all 40 fronts reach Review (one previously stopped at Friction for lack of corroboration) |
| Case management (simulated quarter) | Median 59h to decision, 92% of replies within 72h, 20% cleared as genuine, 6% of appeals overturned |
| Betting-page scanner | The example post reveals 4 fronts not yet on the known-bad list |
| Consortium check | 7 of 200 new applicants at another provider caught reusing an offboarded front's bank account or phone |

Chart 8: **`8_time_to_detection.png`**: share of fronts and rented accounts penalised vs days since they started.

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
- **55% vs 100%**: behaviour alone vs full system when fraudsters hide as hard as they can
- **7 days** median from the start of betting to a penalty (the system acts weekly, so that's the fastest possible)
- **1 of 950** honest merchants ever penalised in any week of the year
