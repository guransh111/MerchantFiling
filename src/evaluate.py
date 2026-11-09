"""Step 6: how good is it? Compare the system's actions with the hidden truth.

Questions answered (results go to reports/results.md + charts in reports/):
  1. Of the merchants we act on, how many are really bad?        (precision)
  2. Of the really bad merchants, how many do we act on?         (recall)
  3. How many honest merchants do we bother?                     (false-positive rate)
     - especially 'genuine drifters', the honest shops whose business changed
  4. Does the peer comparison matter? (vs comparing a shop only with its own past)
  5. Are honest sweet / electronics shops flagged during the Diwali rush?
  6. Does the network catch fronts that were NOT on the known-bad list?
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import config as C
from .actions import decide

LABEL_ORDER = ["legit", "genuine_drifter", "betting_front", "rented"]
LABEL_NAME = {"legit": "Honest shop", "genuine_drifter": "Honest shop, business changed",
              "betting_front": "Betting front", "rented": "Rented account"}
COLORS = {"legit": "#2a78d6", "betting_front": "#eb6834", "genuine_drifter": "#1baf7a", "rented": "#eda100"}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
BAD = {"betting_front", "rented"}


def _style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(GRID)
    ax.tick_params(colors=MUTED)
    ax.yaxis.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)


def metrics(d: pd.DataFrame, level_col="level") -> dict:
    bad = d.label.isin(BAD)
    out = {}
    for name, lvl in [("any action (Ask or above)", 1), ("penalty (Friction or above)", 2)]:
        hit = d[level_col] >= lvl
        tp = (hit & bad).sum()
        out[name] = {
            "precision": tp / max(hit.sum(), 1),
            "recall": tp / max(bad.sum(), 1),
            "honest shops hit": f"{(hit & (d.label == 'legit')).sum()} of {(d.label == 'legit').sum()}",
            "honest drifters hit": f"{(hit & (d.label == 'genuine_drifter')).sum()} of {(d.label == 'genuine_drifter').sum()}",
        }
    return out


def score_only_levels(s: pd.Series) -> pd.Series:
    return np.select([s >= 75, s >= 60], [2, 1], 0)


def main():
    m = pd.read_csv(C.DATA / "merchants.csv")
    weekly = pd.read_csv(C.DATA / "scores_weekly.csv", parse_dates=["week_start"])
    weekly_own = pd.read_csv(C.DATA / "scores_weekly_nopeer.csv", parse_dates=["week_start"])
    scores = pd.read_csv(C.DATA / "scores.csv")
    scores_own = pd.read_csv(C.DATA / "scores_nopeer.csv")
    net = pd.read_csv(C.DATA / "network.csv")
    decl = pd.read_csv(C.DATA / "declarations.csv")
    ev = pd.read_csv(C.DATA / "account_events.csv")
    full = pd.read_csv(C.DATA / "decisions.csv")
    C.REPORTS.mkdir(exist_ok=True)

    # --- the three systems we compare
    peer_only = m.merge(scores, on="merchant_id")
    peer_only["level"] = score_only_levels(peer_only.drift_score)
    own_only = m.merge(scores_own, on="merchant_id")
    own_only["level"] = score_only_levels(own_only.drift_score)
    systems = {
        "A. Own-history only (typical anomaly detector)": own_only,
        "B. Peer drift score only": peer_only,
        "C. Full TrustLoop (peer + network + declarations + ladder)": full,
    }
    rows = []
    for name, d in systems.items():
        for kind, v in metrics(d).items():
            rows.append({"system": name, "counts as flagged": kind, "precision": f"{v['precision']:.0%}",
                         "recall": f"{v['recall']:.0%}", "honest shops hit": v["honest shops hit"],
                         "honest drifters hit": v["honest drifters hit"]})
    comp = pd.DataFrame(rows)

    # --- network: recall on fronts NOT on the known-bad list
    unseeded = full[full.label.isin(BAD) & ~full.known_bad]
    caught_unseeded = (unseeded.level >= 2).mean() if len(unseeded) else np.nan
    caught_by_net = (unseeded.network_link).mean() if len(unseeded) else np.nan

    # --- Diwali: honest sweet / electronics shops flagged in Diwali week
    dw = pd.Timestamp(C.DIWALI_DAY) - pd.Timedelta(days=pd.Timestamp(C.DIWALI_DAY).dayofweek)
    festive_shops = m[(m.label == "legit") & m.category.isin(["sweet_shop", "electronics"])].merchant_id
    def flag_rate(w):
        # a typical rule: "sales jumped far more than usual" (z-score of growth above 3)
        x = w[w.merchant_id.isin(festive_shops)]
        return x.groupby("week_start")["volume_growth__z"].apply(lambda s: (s >= 3).mean())
    fr_peer, fr_own = flag_rate(weekly), flag_rate(weekly_own)

    # --- ladder outcome table
    ladder = pd.crosstab(full.label.map(LABEL_NAME).rename("Hidden truth"), full.action).reindex([LABEL_NAME[l] for l in LABEL_ORDER])

    # ================================================================ charts
    # 1. score by label, own-history vs peer
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for ax, (title, d) in zip(axes, [("Compared with its own past", own_only), ("Compared with peers (TrustLoop)", peer_only)]):
        rng = np.random.default_rng(0)
        for i, lab in enumerate(LABEL_ORDER):
            y = d[d.label == lab].drift_score
            ax.scatter(i + rng.uniform(-0.25, 0.25, len(y)), y, s=14, color=COLORS[lab], alpha=0.75, edgecolor="white", lw=0.4)
        ax.axhline(60, color=MUTED, lw=1, ls="--")
        ax.text(3.45, 61, "Ask threshold (60)", ha="right", va="bottom", fontsize=8, color=MUTED)
        ax.set_xticks(range(4), [LABEL_NAME[l].replace(", ", ",\n") for l in LABEL_ORDER], fontsize=8.5)
        ax.set_title(title, fontsize=11, color=INK, loc="left")
        _style(ax)
    axes[0].set_ylabel("Drift score (0-100)", color=MUTED)
    fig.suptitle("Peer comparison separates betting fronts from honest shops", x=0.01, ha="left", fontsize=13, color=INK)
    fig.tight_layout()
    fig.savefig(C.REPORTS / "1_scores_by_label.png", dpi=150)
    plt.close(fig)

    # 2. Diwali chart
    fig, ax = plt.subplots(figsize=(11, 3.8))
    ax.plot(fr_own.index, fr_own.values * 100, color=COLORS["betting_front"], lw=2, label="Own-history only")
    ax.plot(fr_peer.index, fr_peer.values * 100, color=COLORS["legit"], lw=2, label="Peer comparison (TrustLoop)")
    ax.axvspan(dw, dw + pd.Timedelta(days=7), color=GRID, alpha=0.8)
    ax.text(dw - pd.Timedelta(days=1), ax.get_ylim()[1] * 0.92, "Diwali week", ha="right", fontsize=9, color=MUTED)
    ax.set_ylabel("% of honest sweet & electronics\nshops with a 'sales spike' alert", color=MUTED, fontsize=9)
    ax.set_title("The Diwali rush triggers sales-spike alerts, unless shops are compared with their peers", loc="left", fontsize=12, color=INK)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    _style(ax)
    fig.tight_layout()
    fig.savefig(C.REPORTS / "2_diwali_false_alarms.png", dpi=150)
    plt.close(fig)

    # 3. ladder outcome, stacked horizontal bars
    acts = [a for _, _, a in C.LADDER]
    short = ["Monitor", "Ask", "Friction", "Review"]
    lad = pd.crosstab(full.label, full.level).reindex(index=LABEL_ORDER, columns=range(4), fill_value=0)
    pct = lad.div(lad.sum(axis=1), axis=0) * 100
    fig, ax = plt.subplots(figsize=(11, 3.4))
    lad_colors = ["#c3c2b7", "#2a78d6", "#eda100", "#eb6834"]
    left = np.zeros(len(pct))
    for j in range(4):
        ax.barh(range(len(pct)), pct[j], left=left, color=lad_colors[j], edgecolor="white", lw=2, label=short[j], height=0.6)
        for i, (v, n) in enumerate(zip(pct[j], lad[j])):
            if v >= 7:
                ax.text(left[i] + v / 2, i, f"{n}", ha="center", va="center", fontsize=8.5, color=INK)
        left += pct[j].to_numpy()
    ax.set_yticks(range(len(pct)), [LABEL_NAME[l] for l in LABEL_ORDER], fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("% of merchants in each group (numbers = merchant counts)", color=MUTED, fontsize=9)
    ax.set_title("What the system does to each kind of merchant", loc="left", fontsize=12, color=INK)
    ax.legend(ncol=4, frameon=False, fontsize=9, loc="lower right", bbox_to_anchor=(1, 1.0))
    _style(ax)
    ax.yaxis.grid(False)
    fig.tight_layout()
    fig.savefig(C.REPORTS / "3_actions_by_label.png", dpi=150)
    plt.close(fig)

    # 4. one betting front's weekly score next to an honest drifter's
    ex = []
    for lab in ["betting_front", "genuine_drifter"]:
        cand = full[full.label == lab]
        if len(cand):
            ex.append(cand.iloc[0].merchant_id)
    fig, ax = plt.subplots(figsize=(11, 3.6))
    for mid, lab in zip(ex, ["betting_front", "genuine_drifter"]):
        w = weekly[weekly.merchant_id == mid]
        ax.plot(w.week_start, w.drift_score, color=COLORS[lab], lw=2, label=f"{mid}: {LABEL_NAME[lab]}")
    ipl = (pd.Timestamp(C.IPL[0]), pd.Timestamp(C.IPL[1]))
    ax.axvspan(*ipl, color=GRID, alpha=0.6)
    ax.text(ipl[0] + pd.Timedelta(days=2), 3, "IPL season", fontsize=9, color=MUTED)
    ser = (pd.Timestamp(C.SEPT_SERIES[0]), pd.Timestamp(C.SEPT_SERIES[1]))
    ax.axvspan(*ser, color=GRID, alpha=0.6)
    ax.text(ser[0] + pd.Timedelta(days=1), 3, "Sept series", fontsize=9, color=MUTED)
    ax.axhline(60, color=MUTED, lw=1, ls="--")
    ax.set_ylim(0, 115)
    ax.set_yticks(range(0, 101, 20))
    ax.set_ylabel("Weekly drift score", color=MUTED)
    ax.set_title("Week by week: a betting front stays high all year; an honest change is a shorter bump", loc="left", fontsize=12, color=INK)
    ax.legend(frameon=False, fontsize=9, loc="upper right", ncol=2)
    _style(ax)
    fig.tight_layout()
    fig.savefig(C.REPORTS / "4_weekly_examples.png", dpi=150)
    plt.close(fig)

    # ================================================================ write-up
    n_lab = m.label.value_counts()
    peak_own = fr_own.max()
    peak_peer = fr_peer.max()
    md = [
        "# Results (auto-generated by `python -m src.evaluate`)",
        "",
        f"Synthetic world: **{len(m):,} merchants**, {C.N_WEEKS} weeks "
        f"({C.START_DATE} to {(pd.Timestamp(C.START_DATE) + pd.Timedelta(weeks=C.N_WEEKS) - pd.Timedelta(days=1)).date()}), "
        f"covering IPL, a September cricket series and Diwali.",
        "",
        "| Hidden truth | Merchants |", "|---|---|",
        *[f"| {LABEL_NAME[l]} | {n_lab.get(l, 0)} |" for l in LABEL_ORDER],
        "",
        "## 1. Headline comparison",
        "",
        "*Precision* = of the merchants we acted on, the share that were really bad.  ",
        "*Recall* = of the really bad merchants, the share we acted on.",
        "",
        comp.to_markdown(index=False),
        "",
        "## 2. Diwali false alarms",
        "",
        "A common rule is 'alert when sales jump far more than usual' (growth z-score of 3 or more). "
        f"Share of **honest** sweet and electronics shops triggering it in the worst week: "
        f"**{peak_own:.0%} with own-history comparison** vs **{peak_peer:.0%} with peer comparison**.",
        "",
        "![Diwali](2_diwali_false_alarms.png)",
        "",
        "## 3. The network layer",
        "",
        f"Bad merchants **not** on the known-bad list: {len(unseeded)}. "
        f"Linked to a known-bad merchant through the network: **{caught_by_net:.0%}**. "
        f"Ending at Friction or Review: **{caught_unseeded:.0%}**.",
        "",
        "## 4. What happens to each kind of merchant",
        "",
        ladder.to_markdown(),
        "",
        "![Actions](3_actions_by_label.png)",
        "",
        "![Scores](1_scores_by_label.png)",
        "",
        "![Weekly](4_weekly_examples.png)",
        "",
        "## Caveat",
        "",
        "These numbers come from *synthetic* data that we designed, so they show the method works "
        "as intended, not how it would perform on a real payment provider's data. Real fraudsters adapt; "
        "the plan for that is in `explained/10_limitations_and_next_steps.md`.",
    ]
    (C.REPORTS / "results.md").write_text("\n".join(md))
    print(comp.to_string(index=False))
    print(f"\nDiwali peak sales-spike alert rate: own-history {peak_own:.0%} vs peer {peak_peer:.0%}")
    print(f"Unseeded bad merchants: {len(unseeded)}, network-linked {caught_by_net:.0%}, Friction+ {caught_unseeded:.0%}")
    print(ladder.to_string())


if __name__ == "__main__":
    main()
