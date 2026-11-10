# 8. How to run it (complete beginner version)

## One-time setup (about 15 minutes)

**1. Install Python.** Go to https://www.python.org/downloads/ and install Python 3.11 or newer.
On Windows, **tick "Add Python to PATH"** on the first installer screen.

**2. Get the code.** On the GitHub page of this repo, click the green **Code** button, then
**Download ZIP**. Unzip it somewhere easy, e.g. your Desktop. (If you know git: `git clone` it.)

**3. Open a terminal in that folder.**
- **Windows:** open the unzipped folder in File Explorer, click the address bar, type `cmd`, press Enter.
- **Mac:** open Terminal, type `cd ` (with a space), drag the folder into the window, press Enter.

**4. Install the libraries** (the add-ons the code uses):

```bash
pip install -r requirements.txt
```

If `pip` isn't found, try `python -m pip install -r requirements.txt`. On Mac, try `pip3` and `python3`
instead of `pip` and `python` throughout.

## Run the analysis

Quick version (150 merchants, under a minute):

```bash
python run_all.py --small
```

Full version (1,000 merchants, about 4 minutes including the stress test; this is what the results in this folder use):

```bash
python run_all.py
```

You'll see six steps print out, ending in a results table. Charts appear in the `reports/` folder.

**You don't actually need to run this to see the dashboard**: the repo already includes the results
from the full run.

## Open the dashboard

```bash
streamlit run app/dashboard.py
```

A browser tab opens at `http://localhost:8501`. To stop it, press `Ctrl + C` in the terminal.

It follows your computer's light/dark setting. To switch by hand: the ⋮ menu (top right) → **Settings** → **Theme**.

## The dashboard pages

The menu on the left has 16 pages. File 03 lists what each is for, and file 12 explains how to put
your own data in. The ones you'll use most: **Risk queue**, **Merchant drill-down**,
**Check a merchant** and **Settings & what-if**.

The first page you open takes about 5 to 10 seconds while it analyses the demo data; after that,
pages are quick.

## A 5-minute demo script

1. **Overview.** "Out of 1,000 merchants, 937 are never touched. 12 are asked a question. 49 reach
   Review, and every one has both behaviour evidence and a network link."
2. Turn on **Show hidden truth** in the sidebar. "This only exists because the data is simulated.
   Every Review case is a real front or rented account."
3. **Merchant drill-down** (top merchant). Read the three reasons aloud. Show the weekly chart and
   the hour-of-day chart (its money arrives at night; a real kirana's doesn't). Scroll to **Network
   links**. Then click **Confirm: betting / misuse**: "the analyst's decision overrides the system,
   becomes a label for the learning loop, and turns this merchant into a new starting point for the
   network search."
4. Pick a **rented account** (with hidden truth on, the label says so). Point to the red line on the
   weekly chart: "the system found the exact week it changed hands, the same day the phone and bank
   account changed."
5. **Check a merchant.** Choose the example "Restaurant screening IPL": it's asked, not punished.
   Switch to "Betting front (classic)": the score jumps. Tick "pre-declared change" to show it lowers
   the level only when there's no network link.
6. **Settings & what-if.** Lower the Ask threshold to 40 and press Apply. The impact table shows who
   moved, and how many more honest merchants get asked. "This is the trade-off, and it's a business
   choice."
7. **Performance & thresholds.** Change the cost of a missed front, and the cheapest threshold moves.
   "We set thresholds in rupees, not by gut feel."
8. **Learning loop.** "It learned that match hours matter less than we thought, because honest
   restaurants screen matches too." Optionally press **Apply suggested weights**.
9. **Load data → Generate.** Set evasion to 1.0 and generate 300 merchants. Show the result on
   Performance: still caught, thanks to the network.
10. **Case management.** "Every flag becomes a case with a 72-hour clock, an audit log and an appeal
    path. Our appeal overturn rate is 6%: that's the metric that tells us if we're over-flagging."
    Pick the open case at the top and press **Record merchant's reply**, then **Clear: genuine business**.
11. **Scan a betting page.** Press **Load an example post**: it finds 4 hidden UPI IDs, including one written
    as "[at]" and one inside a QR link. Add them to the known-bad list.
12. **Regulator reports.** Choose "All merchants at Review or above" and show the draft STR. "Under PMLA we
    must file within 7 days; this drafts it in seconds."
13. **Customer's payment screen.** "The paying customer sees 'Verified: Kirana, Lucknow'. If they
    think they're placing a bet, that's a red flag to them too."

## Run the tests (optional)

```bash
pytest -q
```

You should see `22 passed`.

## Changing things

Easiest: the **Settings & what-if** page in the dashboard (no code). To change the defaults
permanently, edit `src/config.py` (the `Settings` class) and re-run `python run_all.py`.

## Using your own data

See file 12. Short version: dashboard → **Load data** → upload a merchants file and a transactions
file (CSV or Excel), check the column mapping, press the button.

## Troubleshooting

| Problem | Fix |
|---|---|
| `python: command not found` | Use `python3`, or reinstall Python with "Add to PATH" ticked |
| `ModuleNotFoundError: No module named ...` | Run the `pip install -r requirements.txt` step again |
| Dashboard says "No results yet" | Run `python run_all.py --small` first |
| Dashboard looks stale after re-running | Press `C` then refresh the page in the browser (clears the cache) |
| Excel upload fails | Run `pip install openpyxl`, or save the sheet as CSV |
| Upload says a required column is missing | Use the column-mapping drop-downs to point it at the right column |
| "Need at least 5 confirmed and 5 cleared cases" | The learning loop needs more analyst decisions; confirm/clear a few more cases |
