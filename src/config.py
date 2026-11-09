"""Shared settings for the whole prototype.

Everything that a non-programmer might want to tweak lives here:
dates, merchant mix, feature list, weights and action thresholds.

The `Settings` class bundles every tunable number so the dashboard can change
them live ("what if we lower the Ask threshold to 50?") without editing code.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REPORTS = ROOT / "reports"
TEMPLATES = ROOT / "templates"

SEED = 42

# ---------------------------------------------------------------- calendar
START_DATE = "2026-03-16"  # a Monday
N_WEEKS = 37               # runs to 2026-11-29, covers IPL, a September series and Diwali

IPL = ("2026-03-28", "2026-05-31")          # daily evening matches
SEPT_SERIES = ("2026-09-09", "2026-09-28")  # every other day
DIWALI_DAY = "2026-11-08"
DIWALI_DAYS = {2024: "2024-11-01", 2025: "2025-10-20", 2026: "2026-11-08", 2027: "2027-10-29", 2028: "2028-10-17"}

# ---------------------------------------------------------------- merchant mix (synthetic data)
N_MERCHANTS_FULL = 1000
N_MERCHANTS_SMALL = 150
LABEL_MIX = {               # share of merchants with each hidden label
    "betting_front": 0.04,  # registered as a shop, really collects bets
    "rented": 0.01,         # genuine shop whose account gets handed to a betting operator
    "genuine_drifter": 0.03,  # honest shop whose business really changed
}
CATEGORIES = ["kirana", "restaurant", "sweet_shop", "pharmacy", "electronics"]

# ---------------------------------------------------------------- features
# name -> (direction that looks risky, default weight, plain-English description)
FEATURES = {
    "volume_growth":     (+1, 1.0, "growth in weekly takings vs the merchant's own recent weeks"),
    "size_mismatch":     (+1, 1.0, "takings compared with the business size declared at sign-up"),
    "round_share":       (+1, 1.0, "share of payments in round amounts (multiples of Rs 100)"),
    "match_hours_share": (+1, 1.2, "share of money received during cricket match hours"),
    "night_share":       (+1, 1.0, "share of money received between 11pm and 4am"),
    "out_of_state_share": (+1, 1.0, "share of payers from outside the merchant's state"),
    "payments_per_payer": (+1, 0.8, "average number of payments by each customer in a week"),
    "ticket_variety":    (-1, 0.8, "variety of payment amounts (low variety looks like fixed bet sizes)"),
    "pass_through":      (+1, 1.2, "share of incoming money sent straight out the same day"),
    "payout_fanout":     (+1, 1.0, "number of different accounts the merchant pays out to"),
}
SHORT_NAME = {
    "volume_growth": "Sales growth", "size_mismatch": "Size vs declared", "round_share": "Round amounts",
    "match_hours_share": "Match hours", "night_share": "Late night", "out_of_state_share": "Out-of-state payers",
    "payments_per_payer": "Repeat payments", "ticket_variety": "Amount variety", "pass_through": "Same-day pass-through",
    "payout_fanout": "Payout accounts",
}

# Backwards-compatible constants (defaults of Settings below)
Z_CAP = 4.0
MIN_PEER_GROUP = 10
NETWORK_LINK_THRESHOLD = 50

LEVELS = {
    0: "Monitor",
    1: "Ask: neutral prompt to explain the change",
    2: "Friction: lower limits, T+2 settlement",
    3: "Review: 20% rolling reserve + human review",
    4: "Offboard & report (confirmed by analyst)",
}
LEVEL_SHORT = {0: "Monitor", 1: "Ask", 2: "Friction", 3: "Review", 4: "Offboard"}
LADDER = [(0, 0, LEVELS[0]), (60, 1, LEVELS[1]), (75, 2, LEVELS[2]), (90, 3, LEVELS[3])]


@dataclass
class Settings:
    """Every tunable number in one place. Defaults reproduce the published results."""

    # --- drift score
    weights: dict = field(default_factory=lambda: {f: w for f, (_, w, _) in FEATURES.items()})
    z_cap: float = Z_CAP              # max 'spreads' one signal can contribute
    squash_k: float = 15.0            # raw points -> 0..100 (higher = stricter scale)
    min_peer_group: int = MIN_PEER_GROUP
    worst_weeks: int = 3              # merchant score = average of its N worst weeks

    # --- action ladder
    ask: float = 60.0
    friction: float = 75.0
    review: float = 90.0
    require_corroboration: bool = True  # Review needs a network link / known-bad match

    # --- network
    use_network: bool = True
    network_weight: float = 0.25      # risk points added per network point
    network_link_threshold: float = NETWORK_LINK_THRESHOLD
    # importance multipliers per link type (x1 = default; 0 switches a link type off)
    edge_weights: dict = field(default_factory=lambda: {"device": 1.0, "account": 1.0, "payers": 1.0, "payouts": 1.0})

    # --- other inputs
    use_declarations: bool = True     # pre-declared changes lower the level by one
    use_takeover: bool = True         # phone + bank account change = possible rental
    use_changepoint: bool = True      # behaviour shift right after an account change = escalate
    use_learning: bool = True         # model trained on reviewer decisions can escalate Monitor -> Ask
    learning_escalate_at: float = 0.8  # model probability needed to escalate

    def thresholds(self) -> list[tuple[float, int]]:
        return [(0, 0), (self.ask, 1), (self.friction, 2), (self.review, 3)]

    def to_dict(self) -> dict:
        return asdict(self)
