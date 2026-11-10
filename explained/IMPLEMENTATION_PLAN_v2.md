# Trace: Implementation Plan (v2, as built)

This updates the original 4-page implementation plan to match what the prototype actually does.
Items marked ✅ are built and demonstrable in the dashboard; ⏳ means planned for a real rollout.

## Track A: competition prototype

| # | Plan item | Status | What was built (and any deliberate change) |
|---|---|---|---|
| 1 | Synthetic data: ~1,000 merchants, 5 categories, 3 city tiers, 6–12 months, daily/weekend cycles, Diwali, IPL | ✅ | 1,000 merchants, 37 weeks (Mar–Nov 2026), IPL + a September series + Diwali. Categories: kirana, restaurant, sweet shop, pharmacy, electronics (instead of salon / online services, for sharper Diwali contrast). **Payment sizes calibrated to real NPCI July 2025 category averages** |
| 1a | ~4% betting fronts, ~3% genuine drifters, a few rented accounts | ✅ | 40 fronts, 30 honest drifters (5 kinds of genuine change), 10 rented accounts; adjustable evasion 0–100% |
| 2 | Weekly features | ✅ | 10 scored signals. "Hours money stays" was replaced by **same-day pass-through** and **payout accounts** (hold time is undefined when shops keep part of revenue). "Distinct payer states" is shown as an investigator metric |
| 3 | Seasonality-adjusted drift score vs peers | ✅ (changed) | Peers = category × city tier, **same week**. We compare **levels**, not week-on-week changes: a change-based score would miss fronts that bet from day one. Size is handled by the "takings vs declared turnover" signal rather than by splitting peer groups |
| 3a | Isolation forest in the score | ✅ (changed) | Used for the **audit queue** only: honest drifters are also anomalous (94th percentile), so anomaly alone must not drive penalties |
| 3b | Supervised XGBoost once labels exist | ✅ (changed) | **Logistic regression learning loop** on analyst decisions (out-of-fold), with suggested weights. XGBoost would overfit ~80 labels; revisit at hundreds |
| 4 | Network analysis + personalized PageRank from seeded known-bad | ✅ | Shared devices, settlement accounts, customers, payout accounts; PageRank; **Louvain clusters**; analyst-confirmed merchants become new seeds |
| 5 | Actions with top-3 reason codes (SHAP) | ✅ | Ladder Monitor → Ask → Friction → Review → Offboard. Reasons are each signal's exact contribution (equivalent to SHAP for an additive score), in plain English with peer numbers |
| 6 | Streamlit dashboard, drill-down, appeal and payer-screen mock-ups | ✅ | 16 pages incl. bring-your-own-data upload, check-a-merchant, settings what-if |
| 7 | Evaluation: precision/recall, drifter FPR, no-peer baseline on Diwali | ✅ | Plus stress test, cost-based threshold, change-point accuracy, **time-to-detection replay** |

### Score → action (unchanged, now editable as policy)

| Risk score | Action |
|---|---|
| < 60 | Monitor |
| 60–75 | Ask: neutral prompt to explain |
| 75–90 | Friction: lower limits, T+2 settlement |
| ≥ 90 **and corroboration** | Review: 20% rolling reserve + human review |
| Analyst confirms | Offboard; STR to FIU-IND; I4C Suspect Registry |

Corroboration = a network link **or** a GST mismatch (UPI takings ≥ 3× GST-declared turnover).

## Track B: real-world rollout

| Phase | Plan | Prototype status |
|---|---|---|
| **1. Pilot (0–6 months)**: data pipeline, drift score, ladder, review queue, appeals | Provider's own data only | ✅ Drift score, ladder, **case management with 72h SLA, appeals and audit log**, bring-your-own-data upload. ⏳ Production pipeline (Kafka → warehouse) |
| **2. Enrich (6–12 months)**: profile portal, GST/AA checks, takeover detection, betting-site scraping, network | Merchant consent, GSTN API | ✅ **GST cross-check** (on simulated GST turnover), **account-takeover detection** (change points + phone/bank change), **betting-page UPI ID scanner** (public pages, provenance recorded), network model, merchant explanation form. ⏳ Real GSTN / Account Aggregator integration |
| **3. Ecosystem (12–24 months)**: hashed cross-provider sharing, I4C feeds, NPCI category at payment | IDPIC / NPCI governance, sandbox | ✅ **Consortium check** (HMAC-tokenised identifiers, demo of re-application detection), **I4C Suspect Registry file**, **draft STRs**, payer-screen mock-up. ⏳ Governance, real key management |

## System components

| # | Component | Prototype |
|---|---|---|
| 1 | Ingest | CSV/Excel upload with column mapping and data checks (`src/schema.py`) |
| 2 | Features | Weekly signals (`src/features.py`) |
| 3 | Models | Drift, network, change points, anomaly, learning loop |
| 4 | Decision engine | Ladder as **editable policy**: save/load JSON, change log with who/why |
| 5 | Case management | Statuses, 72h deadlines, evidence notes, appeals, audit log, metrics |
| 6 | Merchant portal | Explanation form (feeds back into decisions), trust tier, payer screen |
| 7 | Feedback loop | Analyst decisions → learning loop; 2% random audits + anomaly audit queue |

## Metrics (from the plan) and where they are measured

| Metric | Where |
|---|---|
| Precision of flags | Performance page; `reports/results.md` §1 |
| False-positive rate on genuine merchants | Performance page; §1, §11 (ever penalised in any week) |
| **Days from first anomaly to action** | Time-to-detection replay, §11 |
| **Appeal overturn rate** | Case management page |
| Share of volume under friction | Overview page |
| Reports filed to I4C / FIU | Regulator reports page (STR drafts, I4C file) |

## Risks

| Risk | Mitigation (built) |
|---|---|
| Biased labels | 2% random audits + anomaly-driven audit queue feed the learning loop |
| Small peer groups | Fall back from category × tier to category (minimum 10 merchants) |
| Fraudsters adapt | Stress test up to 100% evasion; several independent layers; quarterly re-learning of weights |
| Merchant pushback | Published, versioned policy file; 72h response window; appeals decided by a second analyst; overturn rate tracked |
| Provider-hopping | Consortium tokens flag re-applications at onboarding |
