"""Run the whole pipeline in one go.

    python run_all.py           # 1,000 merchants (takes a few minutes)
    python run_all.py --small   # 150 merchants (under a minute)

Then open the dashboard:   streamlit run app/dashboard.py
"""
import argparse
import time

from src import engine, evaluate, generate

STEPS = [
    ("1/3 Creating synthetic merchants and payments", lambda a: generate.main(a.small)),
    ("2/3 Running Trace: signals, peer scores, network, change points, learning loop, decisions",
     lambda a: engine.main()),
    ("3/3 Evaluating against the hidden truth (incl. stress test)", lambda a: evaluate.main(stress=not a.small)),
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
