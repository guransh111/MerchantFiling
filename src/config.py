"""Shared settings for the whole prototype.

Everything that a non-programmer might want to tweak lives here:
dates, merchant mix, feature list, weights and action thresholds.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REPORTS = ROOT / "reports"

SEED = 42

# ---------------------------------------------------------------- calendar
START_DATE = "2026-03-16"  # a Monday
N_WEEKS = 37               # runs to 2026-11-29, covers IPL, a September series and Diwali

IPL = ("2026-03-28", "2026-05-31")          # daily evening matches
SEPT_SERIES = ("2026-09-09", "2026-09-28")  # every other day
DIWALI_DAY = "2026-11-08"

# ---------------------------------------------------------------- merchant mix
N_MERCHANTS_FULL = 1000
N_MERCHANTS_SMALL = 150
LABEL_MIX = {               # share of merchants with each hidden label
    "betting_front": 0.04,  # registered as a shop, really collects bets
    "rented": 0.01,         # genuine shop whose account gets handed to a betting operator
    "genuine_drifter": 0.03,  # honest shop whose business really changed
}
CATEGORIES = ["kirana", "restaurant", "sweet_shop", "pharmacy", "electronics"]

# ---------------------------------------------------------------- features
# name -> (direction that looks risky, weight, plain-English description)
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

# A single feature can add at most this many 'standard deviations' to the score.
# This is what makes the score reward *several* odd signals instead of one extreme one.
Z_CAP = 4.0
MIN_PEER_GROUP = 10

# ---------------------------------------------------------------- action ladder
LADDER = [  # (minimum score, level, action shown to the risk team)
    (0,  0, "Monitor"),
    (60, 1, "Ask: neutral prompt to explain the change"),
    (75, 2, "Friction: lower limits, T+2 settlement"),
    (90, 3, "Review: 20% rolling reserve + human review"),
]
# Level 3 additionally needs a network link or a known-bad match;
# otherwise the merchant stays at level 2 (no reserve without corroboration).
NETWORK_LINK_THRESHOLD = 50
