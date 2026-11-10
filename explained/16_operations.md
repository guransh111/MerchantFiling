# 16. Running it as an operation (version 3)

Versions 1 and 2 *detect*. Version 3 adds what a payment provider needs to actually *run* the system day
to day, and fills the remaining gaps in the implementation plan. Each part has a dashboard page.

---

## 1. How fast does it act? (time-to-detection replay)

**Question from the plan:** "days from first anomaly to action".

**How we measure it.** We re-run the whole system at the end of every week from March to November, using
**only what was known that week**: payments so far, network links so far, known-bad UPI IDs only from the
date they appeared on a betting page, and declarations and phone/bank changes only once they happened. No
peeking at the future. Then we note the first week each merchant was penalised (Friction or above).

| | Penalised | Median days | 90% within | Slowest |
|---|---|---|---|---|
| Betting fronts | 40 of 40 | **7** | 14 | 21 |
| Rented accounts (from the handover) | 10 of 10 | **7** | 8 | 14 |

The system acts once a week, so **7 days is the fastest possible**. Across all 37 weeks, only **1 of 950**
honest merchants was ever penalised in any week (an honest shop whose business changed), and 13 were ever
asked a question.

**Finance analogy:** a back-test of a trading rule using only data available at each date (no look-ahead bias).

Code: `src/replay.py`. Chart: `reports/8_time_to_detection.png`.

---

## 2. Case management (page: Case management)

Flags become **cases** with a lifecycle, deadlines and an audit trail:

```
Awaiting merchant ──reply──▶ Under review ──▶ Closed: confirmed ──appeal──▶ Appealed ──▶ Upheld / Overturned
        │ (72h deadline)            │
        └───────────────────────────┴──▶ Closed: cleared
```

- **72-hour deadline** for the merchant to reply; overdue cases are highlighted. Deadlines can be extended.
- **Appeals** are decided by a second analyst within 7 days.
- **Audit log:** every action with who, when and a note. A regulator or ombudsman can inspect it.
- Confirming or clearing a case **feeds back** into the analysis, exactly like the drill-down buttons.
- **Metrics from the plan:** open and overdue cases, median time to decision, % of merchants replying
  within 72h, % cleared as genuine, and the **appeal overturn rate** (high = over-flagging).

On the demo, a quarter of case handling is **simulated**, with occasional analyst mistakes and appeals:
- median 59 hours to a decision;
- 92% of merchants replied within 72h;
- 20% of decided cases were cleared as genuine;
- 6% of appeals were overturned.

Code: `src/cases.py`.

---

## 3. GST cross-check (independent outside evidence)

A GST-registered business files its turnover with the tax department. If a merchant's UPI takings run at
**3× or more** the turnover in its GST returns, the two official records contradict each other.

- Fronts often have **no GST registration**, or a forged/nil one with tiny turnover.
- A **rented account** keeps the original shop's GST turnover, which stops matching once betting money
  arrives.
- Honest registered shops report roughly what they take, so they don't trip it. In our data, **no honest
  merchant** was flagged.

A GST mismatch counts as **corroboration**, like a network link, so it can justify the Review level for a
front that hides its network. Takings above the compulsory-registration level (₹40 lakh a year for goods)
with no GST registration are noted, but don't count, because many small shops are informal.

*The GST figures are simulated. In real life this needs merchant consent and the GSTN or Account
Aggregator APIs (phase 2 of the plan).*

---

## 4. Betting-page scanner (page: Scan a betting page)

Paste the text of a **public** betting website or Telegram post (or the text decoded from its QR code).
The scanner finds every UPI ID:
- plain IDs, like `shop042@okaxis`;
- disguised ones, like `shop042 [at] okaxis`;
- payment links, like `upi://pay?pa=shop042@okaxis&am=500`.

It ignores e-mail addresses and Telegram handles, matches the IDs to your merchants, and lets you add the
matches to the known-bad list with the source recorded. The network search then re-runs from the new
starting points. The example post finds 4 fronts that weren't on the list.

**Privacy rule:** public pages only, with provenance recorded. Code: `src/scanner.py`.

---

## 5. Consortium check (page: Consortium check)

**Problem:** a merchant offboarded by one payment provider signs up with another.

**Fix without sharing raw data:** every member turns identifiers (bank account, phone/device, UPI ID) into
a **token** using a secret key held by the consortium (a keyed hash, HMAC-SHA256). The same input always
gives the same token, and without the key it can't be reversed.
1. Provider A shares tokens for merchants it offboarded.
2. Provider B tokenises its new applicants and checks for matches.

In the demo, 7 of 200 applicants are caught re-applying with a bank account or phone from an offboarded
front. A match triggers **enhanced due diligence**, not automatic rejection. In real life the key would be
held by IDPIC or NPCI (phase 3 of the plan).

---

## 6. Regulator reports (page: Regulator reports)

- **Draft STR (Suspicious Transaction Report)** for FIU-IND, one per merchant. It covers the reporting
  entity, subject, grounds for suspicion (the system's reasons), transaction summary, linked merchants,
  case history and action taken. PMLA requires filing within **7 days** of forming a suspicion. These are
  drafts for the Principal Officer, not FIU-IND's official electronic format.
- **I4C Suspect Registry file:** identifiers of confirmed merchants. They are in clear text, so the file
  is **confidential**.
- **Consortium tokens:** the hashed version, safe to share with other providers.

Download one STR from the drill-down or case page, or all of them as a zip.

---

## 7. Policy file and change log (page: Settings & what-if)

Thresholds are **policy**, not code. You can download the current settings as a policy file, have the
risk committee approve it, and load it back. Every change is logged with **who, when, why and exactly what
changed** (e.g. `ask: 60 → 55`). This answers "who decided to make it stricter, and when?"

---

## 8. Investigator metric: distinct payer states

The plan's "payer spread" signal is shown on the drill-down as the number of different states paying the
merchant that week vs a typical peer. It isn't scored, because out-of-state share already captures it.

---

## What's still not built (and why)

| Plan item | Why not | In the pitch, say |
|---|---|---|
| Kafka stream + feature store | Infrastructure, not logic | "The pilot plugs our engine into the provider's warehouse" |
| Real GSTN / Account Aggregator / I4C connections | Need legal agreements and API access | "Phase 2/3; the logic is ready and demonstrated" |
| Official FIU-IND electronic format | Needs FIU-IND's schema and registration | "Drafts map to the fields; the officer files" |
| "Hours money stays" signal | Undefined when shops keep part of their takings | "Replaced by same-day pass-through and payout accounts" |
