# 10. Limitations and next steps

## Known limitations

| Limitation | Why it matters | Mitigation |
|---|---|---|
| Synthetic data | Results are cleaner than reality | Pilot on real data; measure precision through human review |
| We designed fronts and detector together | Risk of building a detector that only finds what we planted | Evasion built in; random audits in real use |
| Biased labels later | Reviewers only see what the system flags, so the model learns its own blind spots | Randomly audit ~1% of unflagged merchants every quarter |
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

## Ideas to extend the prototype (if you have time)

1. **Supervised model.** Train gradient boosting on the 10 signals using the labels, with
   cross-validation. Compare with the rule score.
2. **Payment-note keywords.** Add a `note` column with occasional "id"/"bet" text for fronts.
3. **Threshold slider in the dashboard** showing precision/recall live.
4. **Federated sharing demo.** Two simulated PAs sharing hashed device and account IDs.
