# 5. How the score works

## Step 1: median and spread of the peers

For every week and every peer group (e.g. "kirana, tier-2 cities"), and for every signal:

- **Peer median:** the middle value. We use the median rather than the average because a few
  betting fronts *inside* the peer group would drag an average up. The median ignores extremes.
  Think of median household income vs mean income when a billionaire moves into town.
- **Peer spread (MAD):** the *median absolute deviation*, meaning how far a typical peer sits from the
  median. Multiplied by 1.4826, it's comparable to a standard deviation, but extremes can't distort it.
- **Floor:** if all peers are nearly identical (e.g. night share is 0% for every kirana), the spread is
  close to zero and any tiny deviation would look infinite. So each signal has a minimum spread (e.g. 3
  percentage points for night share). See `FLOOR` in `src/score.py`.

## Step 2: z-score for each signal

```
z = (merchant's value − peer median) ÷ peer spread
```

This is the familiar standardisation from statistics or a Sharpe-ratio intuition: how many "typical
moves" away from normal. z = 0 is perfectly typical; z = 3 is far out.

Example, kirana tier-1, IPL week: peer median match-hours share = 10%, spread = 5 points.
A front at 61% gives z = (61 − 10) ÷ 5 = 10.2.

## Step 3: keep only the risky direction, cap it, weight it

```
points = weight × min( max(z in the risky direction, 0), 4 )
```

- **Risky direction only.** A kirana with *fewer* night sales than peers is not suspicious.
- **Cap at 4.** The z of 10.2 above counts as 4. This is the key design choice. No single signal,
  however extreme, can condemn a merchant. You need corroboration.
- **Weights** (in `src/config.py`): 1.2 for match hours and pass-through (the most betting-specific),
  0.8 for repeat payments and ticket variety (noisier), 1.0 for the rest.

## Step 4: add up and squash to 0 to 100

```
raw = sum of points over the 10 signals        (max possible ≈ 40)
drift score = 100 × (1 − e^(−raw / 15))
```

The squash makes the score behave like a probability-ish scale with diminishing returns:

| Raw points | Roughly means | Drift score |
|---|---|---|
| 3 | normal noise | 18 |
| 14 | about 3 or 4 signals maxed out | 60 (Ask) |
| 21 | about 5 signals maxed out | 75 (Friction) |
| 35 | about 8 or 9 signals maxed out | 90 (Review zone) |

## Step 5: from weeks to a merchant score

A merchant's drift score is the **average of its 3 worst weeks**. One bad week (a one-off event)
is not enough, but a front that's active through the IPL scores high.

## Step 6: the network score (personalized PageRank)

Imagine a random walker on the network of merchants. At each step they either follow a line to a
connected merchant (more likely along heavier lines: same phone or bank account counts for more), or
with 15% probability they **jump back to a known-bad merchant**. After many steps, the share of time
spent at each merchant measures how closely it is tied to the known-bad ones.

- Known-bad merchants themselves: 100.
- Merchants with no links: about 0.
- Merchants that share a phone, bank account or many gamblers with known-bad ones: close to 100.

We scale it so that 10% of the average known-bad merchant's PageRank equals 100 (capped).
A network score of 50 or more counts as a **network link** (the corroboration needed for Review).

## Step 7: combine

```
risk score = min(100, drift + 0.25 × network)
if merchant's UPI ID is on the known-bad list: risk score = at least 95
```

Behaviour is the main driver. The network adds up to 25 points and supplies the corroboration needed
for the toughest action.

## Why not machine learning (XGBoost, neural nets)?

We deliberately used a **transparent, rule-based** score for version 1:

1. **No labels on day one.** Supervised ML needs thousands of confirmed fronts to learn from. A
   provider starting out doesn't have them. Peer comparison works without labels.
2. **Explainability.** Every flag must come with a reason a merchant (and a court) can understand.
   "61% vs 10% for similar kirana stores" is that reason.
3. **Regulators prefer it.** RBI found rule-only systems produce many false positives, but opaque
   models are hard to defend. Ours is statistical, not crude rules, and still explainable.

Once reviewers confirm cases, a supervised model (e.g. gradient boosting) can be trained on top,
with these same 10 signals as inputs. That's phase 2 in file 10.
