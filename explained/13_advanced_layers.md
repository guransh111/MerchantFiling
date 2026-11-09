# 13. The advanced layers (version 2)

Version 1 was peer drift score + network + ladder. Version 2 adds six layers that make it smarter
and harder to fool. Each is explained here with a finance analogy and what it showed on the demo data.

---

## 1. Change-point detection: "when did it change?"

**What it does.** For every merchant, it looks at the weekly drift score as a time series and finds
the single week that best splits it into a "before" and an "after". Technically, it's the split that
makes each half as flat as possible (least squared error).

**Finance analogy.** It's a structural-break test, like spotting the quarter a company's margins
permanently shifted after a new CEO arrived.

**Why it matters.** A **rented account** looks honest for months, then flips. Knowing *"behaviour
shifted in the week of 15 June, the same day as a phone and bank-account change"* is far stronger
evidence than either fact alone. It also tells an investigator where to start looking.

**Result.** For all 10 rented accounts, the detected week matched the real handover week exactly
(100%). Only rented accounts had a shift that coincided with an account change; no honest shop did.

**Effect on decisions.** A big shift (20+ points) within 3 weeks of an account change escalates the
merchant: at least Ask, or Friction if there is other evidence. It's also written into the notes.

Code: `src/changepoint.py`.

---

## 2. Learning loop: "learn from the analysts"

**What it does.** Every time an analyst **confirms** ("yes, betting") or **clears** ("genuine
business") a case, that's a label. Once there are at least 5 of each, the system fits a **logistic
regression**: which signals actually separated confirmed fronts from cleared merchants?

It produces:
1. A **probability** for every merchant: "looks like past confirmed cases".
2. **Learned weights**, shown next to the hand-set ones, with an **Apply suggested weights** button.

**Finance analogy.** Like a credit scorecard that is re-fitted every quarter on which loans actually
defaulted, instead of trusting the analyst's original weights forever.

**Honest evaluation.** Predictions for reviewed merchants are *out-of-fold*: a merchant is never scored
by a model that saw its own label. Cross-validated AUC on the demo is 1.00 (82 past reviews: 50 confirmed, 32 cleared) (1.0 = perfect separation,
0.5 = coin flip). That is high because the synthetic data is clean; expect lower on real data.

**What it discovered.** Our hand-set weights gave *match hours* the joint-highest weight. The learning
loop gave it the **lowest** (effectively zero), because honest restaurants screening IPL matches also have high
match-hour share, so it doesn't separate fronts from *cleared* merchants. It learned that
**out-of-state payers** and **low amount variety** matter most. That's a good slide: *the system
corrected our own assumption.* (Chart: `reports/5_learned_weights.png`.)

**Effect on decisions.** It is a second opinion only. It can move a merchant from Monitor to **Ask**
(probability 80%+), and never further on its own.

**Bias warning (built in).** Analysts mostly review what the system already flags, so the model can
only learn what the system already sees. That's why random audits are part of the training data.

Code: `src/learn.py` (`learn`, `suggested_weights`).

---

## 3. Anomaly detector: "what's weird that we don't have a rule for?"

**What it does.** An **Isolation Forest** looks at each merchant's whole profile of 10 peer-relative
signals and asks how easy it is to separate this merchant from everyone else. It needs **no labels**.
Output: an anomaly percentile from 0 to 100.

**Finance analogy.** Outlier screening in an audit sample: you don't know what fraud looks like yet,
but you look at the transactions that don't resemble the rest.

**Result.** Median percentile: honest shops 46, honest shops that changed 94, fronts 97, rented 99.
So "unusual" isn't the same as "bad": honest drifters are unusual too. That's exactly why we use it
**only to choose which unflagged merchants to audit** (the *Audit queue* on the Learning loop page),
never to penalise.

---

## 4. Choosing thresholds with money

**What it does.** You enter what each mistake costs:
- a **missed** betting front (default ₹5 lakh: regulatory penalty, reputation, unreported funds),
- an honest merchant **wrongly penalised** (default ₹20,000: lost fees, churn, complaints),
- **analyst time** per flagged case (default ₹1,500).

It sweeps the Friction threshold from 0 to 100, computes the expected total cost at each, and marks
the cheapest. One click applies it.

**Finance analogy.** Setting a credit-score cut-off from the expected loss of a default versus the
profit of a good loan. It's a business decision, so it's expressed in rupees.

**Result.** On the demo data, the cost is lowest (₹75,000, all of it review time) for any threshold
from **85 to 91**: everything bad is caught and no honest merchant is penalised. Below 85, honest
merchants start getting penalised (1 at 80, 6 at 75, 15 at 60). Above 91, fronts start slipping through,
and each miss costs ₹5 lakh. The tool reports 91 because ties go to the higher threshold (fewer
merchants bothered). Our default of 75 costs ₹2.0 lakh. That's cheap, but the tool shows you could
safely go stricter on honesty. (Chart: `reports/6_cost_curve.png`.)

Note: this sweep uses the raw risk score. The real ladder also lowers merchants who pre-declared a
change, so at 75 only 1 honest merchant is actually penalised, not 6.

Code: `src/tuning.py`.

---

## 5. Stress test: "what if fraudsters get smarter?"

**What it does.** It builds five fresh worlds of 400 merchants where operators try harder and harder
to hide, and re-runs everything. At high evasion, operators:
- keep genuine-looking shop traffic as cover,
- avoid round amounts (₹499, ₹1,007),
- run each front on its own phone and bank account (fewer network links),
- pay winners from other accounts (no pass-through),
- spread bets thinly over many fronts (less volume each),
- recruit local gamblers (fewer out-of-state payers),
- take deposits during normal shop hours.

**Result.**

| Evasion | Caught by full TrustLoop | Caught by behaviour score alone | Honest merchants penalised |
|---|---|---|---|
| 0% | 100% | 100% | 0 |
| 30% (default) | 100% | 100% | 0 |
| 60% | 100% | 100% | 0 |
| 80% | 100% | 90% | 0 |
| 100% | 100% | **55%** | 0 |

**The story.** As fraudsters hide better, behaviour alone degrades, but the **layers** (network,
corroboration, change points) keep catching them. No single defence is enough, and that's why
the design has several. (Chart: `reports/7_stress_test.png`.)

**Honest caveat.** Even at 100% evasion the network still works, because fronts in our simulation
share gamblers with known-bad fronts. A truly careful operator who also used completely separate
gambler pools would be much harder to catch. Say so if asked.

---

## 6. Network clusters

**What it does.** Besides spreading suspicion from known-bad merchants (PageRank), it now finds
**communities** of merchants densely linked to each other (the Louvain method). A cluster of eight
"unrelated" kirana stores that share gamblers and a bank account is a red flag in itself, even before
any of them is on a known-bad list. The Network page lists clusters and draws an interactive picture.

---

## How they fit together

```
                 ┌─────────────── behaviour ───────────────┐
payments ──▶ 10 signals ──▶ peer drift score ──▶ change point ─┐
                                                               ├─▶ risk score ─▶ ladder ─▶ action + reasons
known-bad + shared phones/accounts/gamblers ──▶ network ───────┤                   ▲
                                                               │                   │
analyst confirm/clear ──▶ learning loop (2nd opinion) ─────────┘     merchant explanations,
anomaly detector ──▶ audit queue ──▶ more analyst labels             analyst overrides
```

The behaviour score is still the **main** driver, and every decision can still be explained in one
sentence. The new layers add corroboration, timing, learning and economics around it.
