# TrustLoop: Build Conversation Notes

A record of the build session that turned the Merchant Legitimacy Challenge notes into a working prototype,
dashboard, deployment setup, pitch deck and design pass. It follows the order of the conversation.
Repository: https://github.com/guransh111/merchantfiling

**Contents**
1. Starting point
2. Version 1: the first working prototype
3. "Explain what you have made"
4. Version 2: your own data and more sophisticated analysis
5. "Explain all it does"
6. What data, what method, and real data
7. Putting it online (Vercel and Streamlit Cloud)
8. Reviewing the implementation plan PDF
9. Version 3: the operational layer, deck and updated plan
10. Seeing the dashboard
11. unslop: what it is, and the design pass
12. Installing unslop and adding it to the repo
13. Running `/unslop`: audit and story video
14. "Why has it not updated on Streamlit"
15. Dark mode
16. Where everything is
17. Numbers to remember
18. Sources

---

## 1. Starting point

- **Input:** the earlier conversation notes (`merchant-legitimacy-chat.md`): the challenge, the
  "declared vs observed" idea, research, privacy law, existing solutions, the TrustLoop concept and an
  implementation plan.
- **Request:** "I am a finance student, help me build it… add a folder explaining everything."
- **Repository:** `guransh111/MerchantFiling` was empty.

---

## 2. Version 1: the first working prototype

**Built (Python):**

| Step | File | What it does |
|---|---|---|
| 1 | `src/generate.py` | Synthetic world: 1,000 merchants, 16 cities, 37 weeks (Mar–Nov 2026), ~3M UPI payments, IPL, a September series, Diwali |
| 2 | `src/features.py` | 10 weekly signals per merchant |
| 3 | `src/score.py` | Drift score: robust z-scores vs peers (category × city tier, same week), capped, squashed to 0–100 |
| 4 | `src/network.py` | Shared devices, bank accounts, customers, payout accounts; personalized PageRank from known-bad merchants |
| 5 | `src/actions.py` | Ladder Monitor → Ask → Friction → Review, with plain-English reasons |
| 6 | `src/evaluate.py` | Accuracy against the hidden truth, charts |
| – | `app/dashboard.py` | Streamlit dashboard |

**Hidden truth in the simulation:** 920 honest shops, 40 betting fronts, 10 rented accounts, and 30 honest
shops whose business genuinely changed (restaurant screening IPL, kirana turned wholesaler, late-night
delivery, online store, second branch). Deliberate evasion was built in: some fronts mimic shop hours, avoid
round amounts and hide payouts.

**The 10 signals:** match-hour share, night share (11pm–4am), round amounts, out-of-state payers, payments per
customer, amount variety, same-day pass-through, payout accounts, sales growth, takings vs declared turnover.

**Headline result:** 100% of bad merchants caught vs 20% for a typical "own history" detector; 0 of 920 honest
shops penalised; Diwali false alarms 62% → 1%.

**`explained/` folder:** plain-English guides 00–11 (problem, idea, code, signals, scoring, fairness and law,
results, how to run, pitch guide, limitations, glossary).

---

## 3. "Explain what you have made"

A plain-language walk-through: the fake world, the signals, peer comparison (like judging a P/E against its
sector), capped signals ("one odd thing is a story, several are a pattern"), the network, the ladder and the
results. Caveat: simulated data shows the method works as designed, not real-world accuracy.

---

## 4. Version 2: your own data and more sophisticated analysis

**Request:** "Make it so that the user can input data into it, make it much more sophisticated."

**Ways to put data in:**
- Upload CSV/Excel with any column names; automatic column mapping with plain-English checks (`src/schema.py`).
  Only 4 columns required (merchant ID, category, time, amount); missing columns switch signals off.
- Generate a custom world (size, % fronts, % rented, evasion).
- Check one merchant with sliders or by uploading its payments.
- Analyst Confirm / Clear buttons, merchant explanation form, live settings for every weight and threshold.

**New analysis layers:**
- **Change points:** the week behaviour flipped, and whether a phone/bank change came with it.
- **Learning loop:** logistic regression on reviewer decisions, out-of-fold, with suggested weights.
- **Anomaly detector:** Isolation Forest for the audit queue only.
- **Cost-based thresholds:** cheapest cut-off in rupees.
- **Stress test:** five worlds with increasingly evasive fraudsters.
- **Network clusters:** Louvain communities.

**Engineering:** `src/engine.py` splits slow preparation from fast analysis, so sliders update in seconds;
`src/config.Settings` holds every tunable number. Bugs found in browser testing and fixed: a session-state key
clashing with Streamlit, a mis-renamed variable, and stress-test evasion that was too easy (made realistic).

**Notable finding:** the learning loop showed that "match hours" barely separates fronts from honest
restaurants that screen matches, while out-of-state payers and fixed bet sizes do.

Docs added: `12_using_your_own_data.md`, `13_advanced_layers.md`.

---

## 5. "Explain all it does"

A full end-to-end explanation: data in → 10 signals → peer drift score → network → change points → learning
loop → decision ladder → grading and stress test, plus every dashboard page.

---

## 6. What data, what method, and real data

- **Dataset:** simulated, because real transaction-level UPI data is not public and has no answer key.
- **Real data found:** NPCI's official July 2025 UPI person-to-merchant statistics by merchant category.
  NPCI's website blocks automated access from cloud servers (it returned "Access Denied"), even after a
  personal cloud environment named **merchantfiling** was created to allow npci.org.in. The figures were taken
  from reputable reports reproducing NPCI's release (Business Standard, SBI Research, OfficeChai, The Head and Tale).
- **What it revealed:** simulated payment sizes were wrong for some categories.

| Category | Real average (NPCI, Jul 2025) | Before | After calibration |
|---|---|---|---|
| Kirana / grocery | ₹214 | ₹206 | ₹213 |
| Pharmacy | ₹398 | ₹386 | ₹398 |
| Restaurant | ₹113–158 | ₹503 | ₹158 |
| Electronics | ₹1,093 | ₹3,750 | ₹1,096 |
| Sweet shop (bakery proxy, low confidence) | ~₹262 | ₹447 | ₹262 |

- **After recalibrating and re-running, the headline results did not change.** Saved in `data/real/`.
- Docs: `14_data_and_method.md`.

---

## 7. Putting it online (Vercel and Streamlit Cloud)

- **Vercel cannot run the Streamlit dashboard.** It runs short-lived functions; the dashboard needs a
  persistent Python server (300 MB to 2 GB of memory).
- **Setup:** live dashboard on **Streamlit Community Cloud** (free; main file `app/dashboard.py`, Python 3.12)
  plus a **Vercel landing page** (`site/index.html`, `vercel.json`, `site/build.sh`; set the `DASHBOARD_URL`
  environment variable to the Streamlit address).
- The "Generate a world" page caps its size automatically to fit free-tier memory.
- Option offered but not built: a read-only static version of the dashboard on Vercel.
- Docs: `15_putting_it_online.md`.

---

## 8. Reviewing the implementation plan PDF

Compared page by page with the build. Differences: categories (salon / online services vs sweet shop /
electronics), level vs change-based scoring, isolation forest role, logistic regression vs XGBoost, two
missing features, 1% vs 2% audits. Missing items: days-to-action metric, case management with appeals,
regulator reports, GST check, betting-site scraping, cross-provider sharing, saved policy config.

---

## 9. Version 3: the operational layer, deck and updated plan

**Request:** "Do whatever more you can do."

| Built | File | Result on demo data |
|---|---|---|
| Time-to-detection replay (week by week, no hindsight) | `src/replay.py` | Fronts penalised in a median of **7 days** (fastest possible), all within 21; rented accounts median 7 days from handover; **1 of 950** honest merchants ever penalised in any week |
| Case management (72h deadline, appeals, audit log) | `src/cases.py` | Simulated quarter: 59h median to decision, 92% replies within 72h, 20% cleared, 6% of appeals overturned |
| GST cross-check (UPI takings ≥ 3× GST turnover) | `src/actions.py` | Flags fronts and rented accounts only; all 40 fronts now reach Review |
| Betting-page UPI ID scanner | `src/scanner.py` | Example post exposes 4 unlisted fronts, including disguised "[at]" IDs and QR links |
| Draft STRs for FIU-IND, I4C file, consortium tokens (HMAC) | `src/reporting.py` | 7 of 200 re-applicants at another provider caught, no raw data shared |
| Versioned policy file with change log | Settings page | Who / when / why / what changed |
| Distinct payer states (investigator metric) | Merchant page | From the plan's "payer spread" |

- Dashboard grew to 16 pages; tests to 31.
- **Pitch deck:** 16 slides with speaker notes and real charts: https://claude.ai/artifact/LiTyTSGFHaf2adhkgyjsWM
  (private until shared from its Share menu; downloads as PowerPoint or PDF).
- **Updated plan:** `explained/IMPLEMENTATION_PLAN_v2.md`. Docs: `16_operations.md`.
- Still not built: Kafka streaming, real GSTN / Account Aggregator / I4C connections, FIU-IND's official
  electronic format, the "hours money stays" signal.

---

## 10. Seeing the dashboard

- Started in the cloud session and shown in the app's preview pane (temporary).
- On a laptop: install Python 3.11+, download the repo, `pip install -r requirements.txt`, then
  `streamlit run app/dashboard.py`, then open `http://localhost:8501`.
- Permanent link: deploy on share.streamlit.io (section 7).

---

## 11. unslop: what it is, and the design pass

- **unslop** (https://github.com/heydamir/unslop) by Damir Sokolovsky (@heydamir), CC BY 4.0: a Claude Code
  skill that turns "vibecoded", AI-looking interfaces into designed ones. It audits for tell-tale signs, sets a
  direction from the product, and fixes nine layers in order (spacing, colour, icons, copy, type, layout,
  details, visuals, motion).
- **Audit of the dashboard:** emoji icons (16 menu items and statuses), heavy bold headings, default font,
  bright pill badges, nine equal stat boxes (one duplicate, one filler), a rainbow log-scale chart, mixed
  number formats, the developer toolbar. Landing page: uppercase tracked label, weight-700 headline, no
  product visual.
- **Direction:** product = a risk console for compliance teams; character = exact, fair, unhurried;
  world = a bank's compliance desk (ink-grey neutrals, one cobalt accent `#1f5fae`, IBM Plex);
  moment = "how far this merchant is from similar shops" chart; signature = **ladder pips**.
- **Changes:** theme in `.streamlit/config.toml`, shared look in `app/ui.py`, line icons, pips, rebuilt
  Overview (four stats, weekly trend, ladder list, thin-bar lists), distance-from-peers chart, quiet
  three-way filters, landing page with a real product preview built from M0002's actual figures.
- The push initially clashed with your `.devcontainer` commit; changes were placed on top of yours.
- Docs: `17_design_pass.md`.

---

## 12. Installing unslop and adding it to the repo

- Installed to `~/.claude/skills/unslop` in the cloud session (temporary).
- **Option 2 chosen:** copied unchanged into the repo at `.claude/skills/unslop`, with its LICENSE and a
  `SOURCE.md` credit, so `/unslop` works in any Claude Code session that opens the repo.

---

## 13. Running `/unslop`: audit and story video

The README's three example commands were run:
1. **"This dashboard":** re-audit found no slop (no emoji, exclamation marks, uppercase labels, heavy bold,
   gradients or glows). Three optional refinements were suggested, not applied: friendly table column
   names, keep the sidebar menu expanded, blank instead of "None" for undecided dates.
2. **"The hero of example.com":** skipped; it's a placeholder address.
3. **"My landing page and the story video":** a 9-second square video (2160×2160, 60 fps) of the landing page
   redesigning itself in four steps, with redline measurements and the required "unslop by @heydamir"
   credit. Saved in `unslop-story/trustloop-unslop.mp4` with its story file and bundled IBM Plex fonts.

---

## 14. "Why has it not updated on Streamlit"

GitHub was up to date, so the cause was on Streamlit Cloud. Most likely: theme settings in
`.streamlit/config.toml` are only read at start-up, so the app needs **⋮ → Reboot app** on share.streamlit.io.
Other checks: hard refresh the browser, confirm branch `main` and file `app/dashboard.py`, read the logs
under **Manage app**.

---

## 15. Dark mode

- Light and dark palettes in `.streamlit/config.toml`; follows the viewer's system setting, switchable via
  **⋮ → Settings → Theme**; a hint is in the sidebar.
- `app/ui.py` resolves colours per viewer, so pips, lists, charts and the network picture match the active
  theme without one viewer affecting another.
- Fixed while testing: comparison labels, the "IPL" chart label and the known-bad rings were invisible on dark.
- Reboot the Streamlit Cloud app after this update.

---

## 16. Where everything is

| What | Where |
|---|---|
| Code | `src/` (engine, schema, generate, features, score, network, changepoint, learn, actions, tuning, replay, cases, scanner, reporting, evaluate) |
| Dashboard | `app/dashboard.py`, pages in `app/views/`, look in `app/ui.py` and `.streamlit/config.toml` |
| Plain-English guides | `explained/00_START_HERE.md` to `17_design_pass.md`, `IMPLEMENTATION_PLAN_v2.md`, this file |
| Results and charts | `reports/results.md`, `reports/1_…png` to `8_…png` |
| Real NPCI figures | `data/real/` |
| Example input files | `templates/` |
| Landing page (Vercel) | `site/index.html`, `vercel.json` |
| Story video | `unslop-story/trustloop-unslop.mp4` |
| unslop skill | `.claude/skills/unslop/` |
| Tests | `tests/` (31 checks, `pytest -q`) |
| Pitch deck | https://claude.ai/artifact/LiTyTSGFHaf2adhkgyjsWM |

Commands:

```bash
pip install -r requirements.txt
```

```bash
streamlit run app/dashboard.py
```

```bash
python run_all.py
```

---

## 17. Numbers to remember

| Result (simulated world, 1,000 merchants, 37 weeks) | Value |
|---|---|
| Bad merchants penalised (Friction or above) | **100%** (typical own-history detector: 20%) |
| Honest shops penalised | **0 of 920** |
| Honest shops whose business changed, penalised | **1 of 30** (12 more only asked a question) |
| Diwali false alarms (sales-spike rule) | **62% → 1%** |
| Unlisted fronts linked by the network | **93%** |
| Rented accounts pinned to the exact handover week | **10 of 10** |
| Median days from first bet to a penalty | **7** |
| Honest merchants ever penalised in any week | **1 of 950** |
| Behaviour alone at maximum evasion | 55% (full system: 100%) |
| Appeal overturn rate (simulated quarter) | 6% |

**Always say:** results come from a simulation calibrated to real NPCI category data and real enforcement
cases. They show the method works as designed, not real-world accuracy.

---

## 18. Sources

- Enforcement Directorate press releases on 1xBet (Nov 2025, 2026)
- CUTS International report on UPI mules, via MediaNama (2025)
- NPCI UPI Ecosystem Statistics: https://www.npci.org.in/what-we-do/upi/upi-ecosystem-statistics
- Business Standard, "UPI's top checkout by volume in July: The grocery aisle dominates" (Aug 2025)
- SBI Research, "New Insights from UPI Data", Issue 20, FY26 (Aug 2025)
- OfficeChai, "Here's How India Spends Money On UPI, As Per NPCI Data"
- The Head and Tale, "UPI's July leaders" (Aug 2025)
- unslop by Damir Sokolovsky: https://github.com/heydamir/unslop (CC BY 4.0)
- Earlier research sources are listed in the original notes file (`merchant-legitimacy-chat.md`)
