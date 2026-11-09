# 6. Actions and fairness

## The response ladder

| Level | Risk score | What happens | Cost to an honest merchant |
|---|---|---|---|
| 0 Monitor | under 60 | Nothing visible | None |
| 1 Ask | 60 to 75 | Neutral message: *"Your sales pattern has changed. Tell us what's new."* with a short form and an evidence upload | 2 minutes |
| 2 Friction | 75 to 90 | Lower transaction limits, settlement slows from T+1 to T+2. **Payments keep working** | A one-day cash-flow delay |
| 3 Review | 90+ **and** a network link | 20% rolling reserve (a fifth of settlements held back for a period) plus a human investigator | Real, so it requires corroboration |
| Confirmed | after human review | Offboard; file a suspicious transaction report with FIU-IND; share with the I4C Suspect Registry | |

**Adjustments:**
- **No Review without corroboration.** A high behaviour score alone caps at Friction. Holding money
  needs a second, independent source: a known-bad match or a network link.
- **Possible rental.** If the merchant's phone *and* settlement bank account both changed within 14
  days, the merchant goes to at least Ask, and one level higher if also network-linked.
- **Pre-declared changes.** If the merchant told us in advance ("we started late-night delivery"),
  they drop one level and are asked for evidence (Swiggy partner page, GST return). **Exception:** if
  they're network-linked, the declaration doesn't help, because ED cases show operators give mules
  scripted explanations.

## Why a ladder rather than "flag = freeze"

1. **Errors are inevitable.** Any detector makes mistakes. A ladder makes a mistake cheap: an honest
   merchant gets a question, not a frozen account.
2. **Legal proportionality.** The Supreme Court's Puttaswamy test (legality, legitimate aim,
   proportionality) and general fairness principles expect the least intrusive effective measure.
3. **Business sense.** Small merchants are the PA's customers. Freezing them causes churn and bad press.
4. **Better data.** Merchants' explanations and reviewers' decisions become labels that improve the
   model over time.

## Fair process built in

- **Every flag has a reason**, written in plain English with peer numbers.
- **72-hour response window** for Friction and above, plus an appeal to a grievance officer.
- **Human review** before any money is held.
- **Published criteria** for trust tiers, so merchants know how to move up.
- **Random audits** of about 1% of unflagged merchants, to check what the system misses (file 10).

## Trust tiers: the carrot

| Tier | Who | Benefit |
|---|---|---|
| Gold | Long record of matching their profile | Same-day settlement, higher limits, lower fees |
| Silver | Normal | Next-day settlement |
| Bronze | New, or at Friction | T+2, lower limits |

Honest merchants have a reason to keep their profile current (*loss aversion*: nobody wants to lose
Gold). Fronts and rented accounts never reach Gold, because they get rotated before building history.

## Is monitoring legal? (India)

Short answer: **yes, and it's required.** Privacy law limits *how* it's done, not *whether*.

- **RBI Payment Aggregator Directions (2025):** PAs must monitor merchant transactions after onboarding
  and move merchants into higher due-diligence tiers based on transaction patterns.
- **PMLA (Prevention of Money Laundering Act):** payment system operators are reporting entities. They
  must file suspicious transaction reports with FIU-IND and are protected from civil liability when
  reporting in good faith.
- **DPDP Act 2023 (Digital Personal Data Protection):** there is no general "fraud prevention" ground
  as in Europe's GDPR. The legal basis is *processing required by law* (RBI, PMLA) plus the merchant
  agreement. The main provisions come into force on 13 May 2027.

## Privacy by design (what we did)

1. **Score the merchant, not the payer.** Payer data is only used in aggregate (shares, counts).
2. **Pseudonymised payer IDs.** In our data, payers are just numbers.
3. **Data minimisation.** Metadata only: amount, time, state. No payment notes text.
4. **Purpose limitation.** Data used only for this, never reused for marketing or credit.
5. **Proportionate escalation.** The ladder.
6. **Human review and appeal** before any hold.
7. **Audit logs** of who accessed what.
8. **Known-bad list from public pages only**, with provenance recorded. No infiltrating private groups.

*This is not legal advice; check the DPDP Act Section 7 and the PA Directions text before a final.*
