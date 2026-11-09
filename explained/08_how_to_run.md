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

Full version (1,000 merchants, 2 to 3 minutes; this is what the results in this folder use):

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

## A 3-minute demo script for the dashboard

1. **Risk queue tab.** "Out of 1,000 merchants, 939 are never touched. 10 are asked a question.
   Only 48 reach Review, and every one has both behaviour evidence and a network link."
2. Turn on **Show hidden truth** in the sidebar. "This column only exists because the data is
   simulated. Every Review case is a real front or rented account."
3. **Merchant drill-down**: pick the top merchant. Read the three reasons aloud ("39% of money during
   match hours vs 4% for similar electronics shops"). Point at the weekly chart peaking in IPL.
   Notes say its UPI ID was found on a public betting page. Scroll to **Network links**: "these
   other merchants share its phone, bank account or customers, so suspicion spreads to them too."
4. In the drop-down, find a merchant at **Ask** (filter Action = Ask in the sidebar). With hidden
   truth on, it's an honest restaurant screening matches. "The system noticed, but it asks rather
   than punishes."
5. **Merchant's view** tab: "This is what that restaurant sees: a neutral question, a form, an
   evidence upload, and their trust tier."
6. **Customer's payment screen** tab: pick a Review merchant. "The paying customer sees 'Verified:
   Electronics, Gaya'. If they're placing a bet, that's a red flag to them too, and 'Report' gives
   us free labels."

## Run the tests (optional)

```bash
pytest -q
```

You should see `11 passed`.

## Changing things

All the tunable numbers are in `src/config.py`: feature weights, the cap, the ladder thresholds,
the merchant mix. Change one, re-run `python run_all.py`, and see how the results move. For example,
set the Ask threshold to 50 and see more honest drifters get asked. This is a good way to show
judges you understand the precision/recall trade-off.

## Troubleshooting

| Problem | Fix |
|---|---|
| `python: command not found` | Use `python3`, or reinstall Python with "Add to PATH" ticked |
| `ModuleNotFoundError: No module named ...` | Run the `pip install -r requirements.txt` step again |
| Dashboard says "No results yet" | Run `python run_all.py --small` first |
| Dashboard looks stale after re-running | Press `C` then refresh the page in the browser (clears the cache) |
