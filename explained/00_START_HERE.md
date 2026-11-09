# Start here

This folder explains the whole project in plain English. You don't need to know how to code.
Read the files in order. Each takes 5 to 10 minutes.

| # | File | What you'll understand after reading it |
|---|---|---|
| 01 | [The problem](01_the_problem.md) | Why betting money hides inside "kirana stores", and why this is hard |
| 02 | [The big idea](02_the_big_idea.md) | "Declared vs observed" and why we compare with peers |
| 03 | [How the code works](03_how_the_code_works.md) | The 6 steps of the pipeline, one file each, no code knowledge needed |
| 04 | [The ten signals](04_the_ten_signals.md) | Exactly what we measure about each merchant, and why |
| 05 | [How the score works](05_scoring_explained.md) | z-scores, medians and PageRank, explained with finance analogies |
| 06 | [Actions and fairness](06_actions_and_fairness.md) | The response ladder, appeals, privacy and Indian law |
| 07 | [Results](07_results.md) | What the numbers and charts mean, and what to say about them |
| 08 | [How to run it](08_how_to_run.md) | Step-by-step install and demo, for a complete beginner |
| 09 | [Pitch guide](09_pitch_guide.md) | Slide-by-slide storyline, demo script, likely judge questions |
| 10 | [Limitations and next steps](10_limitations_and_next_steps.md) | What's weak, and how a real provider would roll it out |
| 11 | [Glossary](11_glossary.md) | Every acronym and technical term in one place |
| 12 | [Using your own data](12_using_your_own_data.md) | Uploading your own CSV/Excel, generating test worlds, typing in one merchant |
| 13 | [The advanced layers](13_advanced_layers.md) | Change points, learning loop, anomaly detector, cost-based thresholds, stress test, clusters |
| 14 | [Data and method](14_data_and_method.md) | Exactly which data is used (simulated, calibrated to real NPCI figures), how decisions are made, and what real data exists |

## The 2-minute version

**The problem.** Illegal betting operators open payment accounts that claim to be ordinary shops,
such as a kirana store in Patna. Their documents look real. Gamblers pay these "shops" by UPI. A
payment provider has to find them without harassing the millions of honest shops.

**Why simple rules fail.** "Alert if sales jump" also catches every sweet shop at Diwali.
"Alert if a merchant changes" misses fronts that were betting from day one, because they never change.

**Our idea: TrustLoop.**
1. **Compare each merchant with its peers in the same week.** These are shops of the same declared
   type in the same kind of city. If every sweet shop triples at Diwali, that's normal. If one
   "kirana" takes 60% of its money during IPL match hours while other kiranas take 10%, that's not.
2. **Require several signals to agree.** Each signal can add only a limited amount to the score.
   One odd thing is a story. Five odd things together are a pattern.
3. **Follow the network.** Fronts share phones, bank accounts and gamblers. Start from accounts already
   found on public betting websites and follow those links.
4. **Respond proportionately.** Monitor, then ask, then add friction, then review. Money is held only
   when a network link backs up the behaviour. Every flag comes with a plain-English reason, and the
   merchant can explain or appeal.

**Version 2 adds (file 13):** detecting *the week* behaviour changed, so rented accounts are caught
the day the phone and bank account switch; a **learning loop** that learns from analysts' confirm/clear
decisions (it found our own assumption about match hours was wrong); an anomaly detector to choose
what to audit; thresholds set in **rupees**; and a **stress test** against smarter fraudsters.

**You can now put your own data in (file 12):** upload CSV/Excel with any column names, generate a
custom world, or type one merchant in with sliders. Analysts can confirm or clear cases, and merchants
can submit explanations, in the dashboard; both change the results.

**Results on our simulated data (1,000 merchants):** we caught all 50 bad merchants and penalised
none of the 920 honest shops. Only 1 of 30 honest shops whose business changed was penalised.
A typical "own history" detector caught only 20% of the bad merchants.

## What's real and what's simulated

- **Simulated:** all merchants and payments. No real payment data is publicly available, so we built
  a realistic fake world (`src/generate.py`), calibrated so average payment sizes match **real NPCI
  UPI statistics** for each merchant category (file 14, `data/real/`). Because we built it, we know who is really a front,
  which lets us measure accuracy. The numbers show the *method* works; they are **not** proof of
  real-world performance. Say this openly when you present; judges respect it.
- **Real:** the problem (Enforcement Directorate cases on 1xBet and Parimatch, the CUTS report on UPI
  mule accounts), the regulations (RBI Payment Aggregator Directions, PMLA, DPDP Act), and the
  techniques (peer comparison, robust statistics, PageRank).
