# 9. Pitch guide

## The storyline (10 slides)

| # | Slide title (the title *is* the message) | Content |
|---|---|---|
| 1 | Betting money is hiding in plain sight inside "kirana stores" | 1xBet: 6,000+ mule accounts, mismatched declared business (ED, 2025). UPI is now the main deposit channel (CUTS 2025) |
| 2 | Today's tools either miss fronts or punish honest shops | "Sales spike" rules flag 62% of honest sweet shops at Diwali; own-history detectors miss 100% of day-one fronts |
| 3 | Our question: does the money match the declared business? | Declared vs observed; compare with peers in the same week (P/E vs sector analogy) |
| 4 | Ten signals separate betting from commerce | Table from file 04; "61% in match hours vs 10% for kiranas" |
| 5 | One odd signal is a story; six together are a pattern | Capped z-scores; restaurant-screening example vs front |
| 6 | Fronts come in families; follow the links | Network diagram: shared phone, bank account, gamblers; 93% of unlisted fronts found |
| 7 | Ask before you punish | The ladder; no money held without corroboration plus a human; 72-hour appeal; trust tiers |
| 8 | Results: 100% of bad merchants caught, 0 honest shops penalised | Chart 3 plus headline numbers; honest caveat on synthetic data |
| 9 | Legal by design: required by RBI and PMLA, minimal under DPDP | Privacy-by-design list |
| 10 | Rollout: pilot in 6 months on the provider's own data | Phases from file 10; metrics; ask |

**Optional extra slides for version 2** (put them after slide 8):

| # | Slide title | Content |
|---|---|---|
| 8a | We catch rented accounts the week they change hands | Weekly score chart with change-point marker; 10 of 10 handover weeks found exactly |
| 8b | The system corrected our own assumption | Learned vs hand-set weights chart: match hours down, out-of-state payers up |
| 8c | Smarter fraudsters? The layers carry the load | Stress test chart: behaviour alone 55% vs full system 100% at maximum evasion |
| 8d | We set thresholds in rupees | Cost curve: cheapest between 85 and 91 |

Then do a live dashboard demo (script in file 08) or show screenshots as a backup.

## One-liners worth memorising

- *"We don't ask whether a merchant is unusual. We ask whether it matches what it declared."*
- *"Every sweet shop triples at Diwali, so none of them looks odd. That's the point of peers."*
- *"One odd signal is a story; six together are a pattern."*
- *"The regulator requires us to monitor. Our design makes that monitoring minimal, proportionate
  and contestable."*
- *"Honest merchants earn faster settlement; fronts never live long enough to earn trust."*
- *"Every analyst decision makes the system smarter, and it shows you what it learned."*
- *"We don't pick thresholds by gut feel; we pick the one that costs least in rupees."*

## How it covers all four solution types the challenge asked for

| Type | Our element |
|---|---|
| Technical | Peer drift score, network PageRank, explainable reasons |
| Business | Trust tiers (settlement speed, limits, fees), rolling reserve instead of freeze |
| Policy | Ladder with human review, 72-hour appeal, reporting to FIU-IND and the I4C Suspect Registry, NPCI category display |
| Behavioural | Neutral "what's new?" prompts, pre-declaration, loss aversion via tiers, customer sees declared category |

## Likely judge questions and answers

**"Your data is fake. How do you know it works?"**
Correct, and we say so. Real data is confidential. Simulation lets us plant fronts we know about and
measure. We added deliberate evasion (30% mimic shops, 30% avoid round amounts, 40% hide payouts). The
method needs no labels, so a provider could run it on its own data in the first pilot month and
measure precision via human review.

**"Won't fraudsters just adapt?"**
Some will. Three defences: (1) no single signal is required, so dodging one isn't enough; (2) the
signals that matter most are economic, not cosmetic. To collect bets you *must* receive money from
many people across India around matches, and paying winners creates outflows. (3) Quarterly
retraining on confirmed cases, plus 1% random audits to find new patterns.

**"What about a genuine sports bar that gets busy during IPL?"**
That's exactly our "restaurant screening matches" case. It trips 2 or 3 signals, not 6. It has local
customers, normal amounts, and no network links. Most end up at Monitor or Ask. With a declaration,
they stay at Monitor.

**"Why not use machine learning?"**
No labels on day one, and every action must be explainable to the merchant. We'll layer gradient
boosting on top once human reviews generate labels. The same 10 signals become its inputs.

**"How is this different from what Razorpay or MuleHunter already do?"**
MuleHunter (RBI) works on bank accounts, not PA merchants. The Suspect Registry and DoT's Financial
Fraud Risk Indicator are reactive, driven by complaints. Global vendors like LegitScript scan websites
for card merchants. Nobody does declared-vs-actual for UPI merchants with Indian seasonality, and
nobody offers the graduated response. We'd *feed* those systems rather than replace them.

**"What's the cost of a false positive?"**
At Ask, two minutes of a merchant's time. At Friction, a one-day settlement delay. Holding money
needs corroboration plus a human. We track the appeal-overturn rate as a key metric.

**"Is this legal under the DPDP Act?"**
Monitoring is required by RBI PA Directions and PMLA, which is the legal basis. We score merchants,
not payers, pseudonymise payer IDs, use metadata only, and keep audit logs.

**"How big is the peer group? What if there are only 3 sweet shops in tier-3 cities?"**
Groups under 10 fall back to the same category across all tiers. At a real PA with millions of
merchants, groups would be large.

**"What's the threshold and why?"**
60/75/90 on a 0 to 100 scale. A 60 needs about 3 to 4 strongly abnormal signals. These are settings
a risk team tunes against its appetite for false positives. We can show the trade-off live by
changing `config.py`.

**"Can you run it on our data?"**
Yes. The dashboard takes CSV or Excel uploads with any column names (it maps them and lets you fix
the mapping). The minimum is merchant ID, category, time and amount; more columns switch on more
signals. See file 12.

**"How does it improve over time?"**
Analysts confirm or clear cases in the dashboard. Those labels train a logistic regression that shows
which signals really matter and suggests new weights. It's evaluated out-of-fold, so it can't mark
its own homework. Random audits stop it learning only what it already sees.

**"What if fraudsters copy normal shop behaviour?"**
We tested exactly that. At maximum evasion, behaviour alone catches only about half the fronts (55%). The network
(shared gamblers, phones, accounts), change points and corroboration still catch them all in our
simulation, with zero honest merchants penalised. A truly isolated operator would be harder to catch,
which is why cross-provider data sharing is in phase 3.

**"How do you pick thresholds?"**
In rupees. Enter the cost of a missed front, of a wrongly penalised honest merchant and of review
time, and the tool shows the cheapest threshold. On our data, anything from 85 to 91 is optimal.
