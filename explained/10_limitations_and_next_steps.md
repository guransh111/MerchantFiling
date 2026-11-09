# 10. Limitations and next steps

## Known limitations

| Limitation | Why it matters | Mitigation |
|---|---|---|
| Synthetic data | Results are cleaner than reality | Pilot on real data; measure precision through human review |
| We designed fronts and detector together | Risk of building a detector that only finds what we planted | Evasion built in; random audits in real use |
| Biased labels | Reviewers only see what the system flags, so the learning loop learns its own blind spots | Random audits (2% in the demo) plus the anomaly-driven audit queue |
| Learning loop on small samples | With few reviews the learned weights are noisy | Needs 5+ of each outcome before it trains; it only suggests weights; a human applies them |
| Very careful operators | At maximum evasion behaviour alone catches 50% (stress test) | Network, change points and cross-provider sharing |
| Small peer groups | Unstable medians | Fall back to category across all tiers when fewer than 10 merchants |
| Polluted peers | If many kiranas in a city are fronts, "normal" shifts | Median is robust; remove confirmed fronts from baselines |
| P2P out of scope | Much betting money moves person-to-person | Share flags with banks (MuleHunter) and NPCI |
| Fake declarations | Operators coach mules | Declarations need third-party evidence; ignored when network-linked |
| Legitimate pass-through businesses (e.g. wholesalers, aggregators) | High pass-through is normal for them | Give them their own declared category and peer group |
| Hard thresholds | A score of 74.9 vs 75.1 | Thresholds are tunable; add a human review band |

## Real-world rollout

| Phase | Timeline | Build | Depends on |
|---|---|---|---|
| 1. Pilot | 0 to 6 months | Data pipeline, drift score, ladder, review queue, appeals | Provider's own data only |
| 2. Enrich | 6 to 12 months | Merchant profile portal, GST/Account Aggregator checks, takeover detection, public-page scraping, supervised model on confirmed cases | Merchant consent, GSTN API |
| 3. Ecosystem | 12 to 24 months | Cross-provider sharing with hashed identifiers, I4C feeds, NPCI declared-category display | IDPIC/NPCI governance, RBI sandbox |

**System components:** ingestion (Kafka to warehouse), weekly feature store, models, decision engine
(ladder as editable rules), case management, merchant portal, feedback loop.

**Team:** 2 data engineers, 2 data scientists, 1 product manager, 3 to 5 risk analysts, plus legal and
compliance sign-off.

## Metrics to track

- Flag precision (from human review)
- False-positive rate on genuine merchants, and **appeal overturn rate**
- Days from first anomaly to action
- Share of total volume under friction (business cost)
- Suspicious transaction reports filed and Suspect Registry submissions
- Merchant churn among flagged-then-cleared merchants

## Already built in version 2

- ✅ Supervised learning on reviewer decisions (logistic regression with learned weights) → file 13
- ✅ Threshold tuning in the dashboard (Settings page, cost-based tool) → file 13
- ✅ Random-audit queue driven by an anomaly detector → file 13
- ✅ Bring-your-own-data upload → file 12

## Ideas to extend further (if you have time)

1. **Payment-note keywords.** Add a `note` column with occasional "id"/"bet" text for fronts; use
   keyword flags only (privacy).
2. **Federated sharing demo.** Two simulated payment providers sharing hashed device and account IDs.
3. **Saving decisions permanently.** Analyst decisions currently last for a session (with download
   and upload); a real system would store them in a database with an audit log.
4. **Gradient boosting** next to the logistic regression, once there are hundreds of labelled cases.
5. **Separate peer group for legitimate pass-through businesses** (wholesalers, aggregators).
