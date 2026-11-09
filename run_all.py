"""Run the whole pipeline in one go.

    python run_all.py           # 1,000 merchants (takes a few minutes)
    python run_all.py --small   # 150 merchants (under a minute)

Then open the dashboard:   streamlit run app/dashboard.py
"""
import argparse
import time

from src import actions, evaluate, features, generate, network, score

STEPS = [
    ("1/6 Creating synthetic merchants and payments", lambda a: generate.main(a.small)),
    ("2/6 Calculating weekly signals", lambda a: features.main()),
    ("3/6 Scoring drift vs peers (and the own-history baseline)", lambda a: (score.main("peer"), score.main("own"))),
    ("4/6 Building the network of shared phones, accounts and customers", lambda a: network.main()),
    ("5/6 Deciding actions and writing reasons", lambda a: actions.main()),
    ("6/6 Evaluating against the hidden truth", lambda a: evaluate.main()),
]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--small", action="store_true", help="150 merchants instead of 1,000")
    args = ap.parse_args()
    for title, fn in STEPS:
        t = time.time()
        print(f"\n=== {title} ===")
        fn(args)
        print(f"({time.time() - t:.0f}s)")
    print("\nDone. Results: reports/results.md   Dashboard: streamlit run app/dashboard.py")
