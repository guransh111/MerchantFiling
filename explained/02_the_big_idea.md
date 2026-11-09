# 2. The big idea: declared vs observed

## The question we ask

Most fraud systems ask: **"Is this behaviour unusual?"**
We ask: **"Does this behaviour match what the merchant told us it is?"**

At sign-up, every merchant **declares**: I'm a kirana store, in Lucknow, small, expecting about
₹80,000 a month. After that we **observe** what actually happens. The gap between the two is the
**drift**.

## Finance analogy: relative valuation

You don't judge whether a P/E of 40 is high in isolation. You compare it with **comparable
companies** in the same sector, at the same time. A P/E of 40 is expensive for a bank and normal for
a high-growth tech stock.

We do the same with merchants. "60% of money arrives during cricket match hours" is:
- normal-ish for a **restaurant** (dinner time overlaps evening matches), and
- very strange for a **kirana store** (peers: about 10%).

And just as you'd compare companies **in the same quarter** (everyone's earnings fell in COVID), we
compare merchants **in the same week**. When every sweet shop triples its sales in Diwali week,
the peer "normal" triples too, so no individual sweet shop looks odd.

**Peer group** = same declared category, same city tier (metro / large city / small city).
If a group has fewer than 10 merchants, we fall back to the same category across all tiers.

## Why not compare a merchant with its own past?

That's what a typical anomaly detector does, and it fails both ways:

| Case | Own-history detector | Peer comparison |
|---|---|---|
| Sweet shop at Diwali | Sales jumped, **false alarm** (62% of honest festive shops alerted) | Peers jumped too, no alarm (1%) |
| Front that bet from day one | Nothing *changed*, **missed** (caught 0 of 40) | Never looked like a kirana, caught |
| Rented account | Changed suddenly, caught | Caught |

## Three more ideas on top

**1. Corroboration: several signals must agree.** We measure 10 signals (file 04). Each one can push
the score up by a limited amount. A restaurant screening matches looks odd on *one or two* signals
(match-hour share, maybe late nights). A betting front looks odd on *six or seven* at once: match
hours, round amounts, out-of-state payers, repeat payers, low variety, money out same day, many
payout accounts. It's like a credit analyst: one late payment is noise; late payments, maxed cards
and a new job together are a pattern.

**2. The network: fronts come in families.** One operator runs many fronts. They share phones,
bank accounts, gamblers and payout accounts. Some fronts' UPI IDs are posted openly on betting
websites and Telegram channels; we treat those as **known bad**. Anything strongly connected to a
known-bad merchant inherits suspicion. In our test, 93% of the fronts *not* on the known-bad list
were found this way.

**3. Proportionate response: ask before you punish.** Instead of "flag = freeze", there's a ladder:

```
Monitor  ->  Ask ("what's changed?")  ->  Friction (lower limits, slower settlement)  ->  Review (20% reserve + human)
```

Honest merchants who changed their business mostly end up at "Ask", which costs them a two-minute
form. Freezing money needs network corroboration and a human. Merchants who tell us about changes
in advance (e.g. "we started late-night delivery") move down a level, unless they are linked to a
betting network, because the ED cases show operators coach mules with fake explanations.

## The name: TrustLoop

Trust is earned in a loop: honest behaviour leads to a higher trust tier, which brings faster
settlement, higher limits and fewer checks. Merchants have a reason to keep their profile honest,
and fronts never build up trust.
