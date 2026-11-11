"""Two charts for the financial appendix, drawn from results.json (run model.py first)."""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).parent
R = json.loads((HERE / "results.json").read_text())
INK, INK2, MUTED, GRID, ACCENT, SOFT = "#1c1c1f", "#56565e", "#6e6e76", "#e2e2e6", "#1f5fae", "#9db6d8"
plt.rcParams.update({"font.family": ["Liberation Sans", "DejaVu Sans"], "font.size": 10, "axes.edgecolor": GRID,
                     "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": INK, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.spines.left": False})
LAKH, CRORE = 1e5, 1e7
base = R["scenarios"]["Mid-size PA (base case)"]

# 1. annual running cost by component, base case
lines = sorted(base["running"]["lines"].items(), key=lambda kv: kv[1])
fig, ax = plt.subplots(figsize=(6.4, 2.4), dpi=200)
labels, vals = [k for k, _ in lines], [v / LAKH for _, v in lines]
bars = ax.barh(labels, vals, height=0.56, color=ACCENT)
for b, v in zip(bars, vals):
    ax.text(b.get_width() + 1.2, b.get_y() + b.get_height() / 2, f"₹{v:,.1f} L", va="center", color=INK, fontsize=9.5)
ax.set_xlim(0, max(vals) * 1.22)
ax.xaxis.grid(True, color=GRID, linewidth=0.8)
ax.set_axisbelow(True)
ax.tick_params(axis="y", length=0)
ax.tick_params(axis="x", length=0, labelsize=8.5)
ax.set_xlabel("₹ lakh per year", fontsize=8.5, color=MUTED)
fig.tight_layout()
fig.savefig(HERE / "chart_running.png")

# 2. five-year cost of ownership, base case
yrs = R["five_year"]
fig, ax = plt.subplots(figsize=(6.4, 2.6), dpi=200)
names = [y["year"].replace(" (build)", "\n(build)") for y in yrs]
vals = [(y["implementation"] + y["running"]) / CRORE for y in yrs]
colors = [SOFT] + [ACCENT] * (len(yrs) - 1)
bars = ax.bar(names, vals, width=0.56, color=colors)
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.05, f"₹{v:.2f} cr", ha="center", va="bottom",
            color=INK, fontsize=9)
ax.set_ylim(0, max(vals) * 1.2)
ax.yaxis.grid(True, color=GRID, linewidth=0.8)
ax.set_axisbelow(True)
ax.tick_params(length=0, labelsize=8.5)
ax.set_ylabel("₹ crore", fontsize=8.5, color=MUTED)
fig.tight_layout()
fig.savefig(HERE / "chart_five_year.png")
print("charts written")
