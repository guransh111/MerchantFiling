# Trace prototype

Goal: detect UPI merchants whose activity drifts from their declared business (e.g. illegal
betting fronts, rented accounts) without flagging genuine seasonal or changing merchants.

The user is a finance student, not a programmer: explain changes in plain language and keep
`explained/` up to date when behaviour or results change.

Stack: Python 3.11+, pandas, numpy, scipy, scikit-learn, networkx, matplotlib, streamlit, altair, pytest.

Pipeline (`python run_all.py [--small]`): src/generate.py -> src/engine.py -> src/evaluate.py
engine.prepare() = features.py + network.build_edges (slow); engine.analyse() = score, network,
changepoint, learn, actions (fast; what the dashboard re-runs on every settings/review change).
Uploads go through src/schema.py (column mapping + clean) before engine.prepare().
Dashboard: `streamlit run app/dashboard.py` (pages in app/views/, shared state in app/state.py;
store values in session_state under names that don't clash with widget keys, e.g. `tl_settings`).
Operational layer: src/replay.py (week-by-week, no look-ahead), src/cases.py (case lifecycle),
src/scanner.py (UPI IDs from public pages), src/reporting.py (STR drafts, I4C file, HMAC consortium tokens).
evaluate.main(stress=True) also runs the stress test and the replay (~8 min on 1,000 merchants).
Tests: `pytest -q`.

Rules:
- seed=42 everywhere (src/config.py); results must be reproducible.
- The hidden `label` column is ground truth for evaluation ONLY. Never use it in features,
  scoring, network, change-point or action logic (a test enforces this). The one sanctioned use is
  learn.simulate_review_history(), which stands in for past analyst investigations in the demo.
- Tunable numbers live in config.Settings; the dashboard edits them live.
- After changing logic, re-run `python run_all.py` and commit the regenerated reports/ and
  the small files in data/ that the dashboard reads (features.csv.gz, network_edges.csv, etc.).
