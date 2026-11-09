# TrustLoop prototype

Goal: detect UPI merchants whose activity drifts from their declared business (e.g. illegal
betting fronts, rented accounts) without flagging genuine seasonal or changing merchants.

The user is a finance student, not a programmer: explain changes in plain language and keep
`explained/` up to date when behaviour or results change.

Stack: Python 3.11+, pandas, numpy, scipy, networkx, matplotlib, streamlit, pytest.

Pipeline (`python run_all.py [--small]`):
src/generate.py -> src/features.py -> src/score.py -> src/network.py -> src/actions.py -> src/evaluate.py
Dashboard: `streamlit run app/dashboard.py`. Tests: `pytest -q`.

Rules:
- seed=42 everywhere (src/config.py); results must be reproducible.
- The hidden `label` column is ground truth for evaluation ONLY. Never use it in features,
  scoring, network or action logic (a test enforces this).
- Tunable numbers (features, weights, thresholds, ladder) live in src/config.py.
- After changing logic, re-run `python run_all.py` and commit the regenerated reports/ and
  the small files in data/ that the dashboard reads.
