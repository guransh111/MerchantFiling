# 12. Using your own data

The dashboard can analyse **any** merchant data you give it, not just the demo. There are three
ways to put data in.

## Way 1: Upload files (Load data → Upload your own data)

You need two files, as **CSV or Excel**:

| File | Required columns | Nice-to-have columns (switch on more signals) |
|---|---|---|
| **merchants** | `merchant_id`, `category` | `city`, `state`, `tier` (1/2/3), `declared_monthly_turnover`, `settlement_account`, `label` |
| **transactions** | `merchant_id`, `ts` (date and time), `amount` | `direction` (in/out), `counterparty_id` (payer), `counterparty_state`, `device_id` |

Optional extra files: a **known-bad list** (merchants found on betting pages), **declarations**
(changes merchants told you about), **account events** (phone or bank-account changes) and a
**match calendar**. Without a calendar, the built-in IPL schedule (28 Mar to 31 May each year) is used.

### Your column names don't have to match

The system recognises common alternatives. For example, `Amount (Rs)`, `amt` or `txn_amount` all
become `amount`, and `Txn Time`, `timestamp` or `created_at` all become `ts`. After you upload, a
**column-mapping** panel shows its guess for every field, and you can fix it with drop-downs.
Direction values such as `CR`/`DR`, `credit`/`debit` or negative amounts are understood too.

### What happens if columns are missing

Nothing breaks: the signals that need the missing data are **switched off**, and the report tells
you which. Examples:

| Missing | Effect |
|---|---|
| `counterparty_state` or merchant `state` | No out-of-state signal |
| `counterparty_id` | No repeat-payment signal, no shared-customer links |
| `direction` | Everything treated as money in; no pass-through or payout signals |
| `declared_monthly_turnover` | No size-vs-declared signal |
| `tier` | Peers grouped by category only |
| `device_id`, `settlement_account` | Fewer network links |

The bare minimum (merchant ID, category, time, amount) still gives you round amounts, match hours,
late night, amount variety and growth.

### Checks you'll see

The upload runs a data check before analysing:
- **Errors** (red) stop the run, e.g. "transactions is missing required column(s): amount".
- **Warnings** (orange): rows with unreadable dates or amounts are dropped; categories with fewer
  than 10 merchants (peer comparison unreliable); less than 4 weeks of data.
- **Info**: which signals are switched off and why.

### The `label` column

If your merchants file has a `label` column (e.g. real investigation outcomes), it is used **only**
to grade the results on the Performance page, never to score. You can optionally let it simulate
"past analyst reviews" so the learning loop can train.

## Way 2: Generate a simulated world (Load data → Generate)

Use sliders to set: number of merchants (100 to 1,000), weeks of data, % betting fronts, % rented
accounts, % honest shops whose business changes, **how hard operators try to hide** (evasion 0 to 1),
and what share of fronts are already on the known-bad list. Every merchant's hidden truth is known,
so you can see how the system copes. You can also download the world as CSV files.

Good experiments to show judges:
- Evasion 0.9: behaviour alone weakens, and the network carries the load.
- Known-bad 0%: no starting points for the network, so it's behaviour only.
- 15% drifters: lots of honest change. Do honest merchants get penalised? (Mostly asked, not penalised.)

## Way 3: Type a merchant in (Check a merchant)

To score **one** merchant without a whole dataset:
- **Sliders:** set its 10 signals by hand, or start from an example ("Betting front (classic)",
  "Restaurant screening IPL", "Sweet shop in Diwali week"…). You see the score, the action and how
  many points each signal adds. Tick boxes add other evidence (network link, known-bad, account
  change, pre-declared change).
- **Upload its payments:** a file with at least date-time and amount. It's scored week by week
  against the loaded dataset's peers.

## Your own inputs while using the dashboard

These also feed back into the analysis:

| Where | What you do | What it changes |
|---|---|---|
| Merchant drill-down | **Confirm** or **Clear** a case | Overrides the action (Offboard / Monitor), adds a label for the learning loop, and a confirmed merchant becomes a new network starting point |
| Merchant's view | Submit an explanation | Recorded as a declaration; lowers the merchant one level unless network-linked |
| Settings & what-if | Change weights, thresholds, switches | Everything recalculates; an impact table shows who moved |
| Learning loop | Apply suggested weights | Uses what was learned from reviewer decisions |
| Performance | Enter the ₹ cost of each mistake | Finds the cheapest threshold and lets you apply it |

Decisions last for your browser session. Use **Download your decisions** on the Learning loop page
to save them, and load them again later.

## Example files

`templates/` in the repo (or **Load data → Templates** in the dashboard) holds small example
files in exactly the right format. Open them in Excel, replace them with your data, and upload.
