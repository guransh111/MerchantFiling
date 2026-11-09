"""Step 1: create a realistic *synthetic* (made-up) world of UPI merchants.

We cannot get real payment data, so we simulate it. The trick is that we
*know* the truth about every fake merchant (its hidden `label`), which lets
us measure later how well the detector works.

Hidden labels
-------------
legit            honest shop behaving normally (incl. Diwali rush for sweet shops)
betting_front    registered as a shop, actually collects cricket bets
rented           honest shop whose account is handed to a betting operator mid-way
genuine_drifter  honest shop whose business really changed (the people we must NOT punish)

Run:  python -m src.generate            (1,000 merchants)
      python -m src.generate --small    (150 merchants, fast)
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from . import config as C

CITIES = [  # city, state, tier
    ("Mumbai", "MH", 1), ("Delhi", "DL", 1), ("Bengaluru", "KA", 1), ("Chennai", "TN", 1),
    ("Hyderabad", "TG", 1), ("Pune", "MH", 2), ("Jaipur", "RJ", 2), ("Lucknow", "UP", 2),
    ("Indore", "MP", 2), ("Surat", "GJ", 2), ("Patna", "BR", 2), ("Nashik", "MH", 3),
    ("Varanasi", "UP", 3), ("Udaipur", "RJ", 3), ("Mysuru", "KA", 3), ("Gaya", "BR", 3),
]
STATES = sorted({s for _, s, _ in CITIES} | {"WB", "OR", "AS", "HR", "PB", "KL", "AP", "CG", "JH"})

SIZE_RATE = {"small": 5, "medium": 12, "large": 24}  # average payments per day

# share of the day's payments in each hour 0..23
def _profile(peaks: dict[int, float]) -> np.ndarray:
    p = np.full(24, 0.002)
    for h, w in peaks.items():
        p[h] += w
    return p / p.sum()

HOURS = {
    "kirana":      _profile({7: 4, 8: 6, 9: 6, 10: 4, 11: 3, 12: 3, 13: 2, 14: 2, 15: 2, 16: 3, 17: 5, 18: 7, 19: 7, 20: 6, 21: 3}),
    "restaurant":  _profile({12: 5, 13: 7, 14: 5, 15: 2, 16: 1, 17: 1, 18: 2, 19: 5, 20: 8, 21: 8, 22: 5, 23: 1}),
    "sweet_shop":  _profile({9: 2, 10: 3, 11: 4, 12: 4, 13: 3, 14: 3, 15: 3, 16: 4, 17: 6, 18: 7, 19: 7, 20: 5, 21: 2}),
    "pharmacy":    _profile({8: 3, 9: 4, 10: 5, 11: 5, 12: 4, 13: 3, 14: 3, 15: 3, 16: 4, 17: 5, 18: 6, 19: 6, 20: 5, 21: 4, 22: 2, 23: 1}),
    "electronics": _profile({11: 4, 12: 5, 13: 5, 14: 5, 15: 5, 16: 6, 17: 7, 18: 7, 19: 6, 20: 4}),
}
TICKET = {  # (median rupees, spread) for a lognormal distribution
    "kirana": (150, 0.8), "restaurant": (420, 0.6), "sweet_shop": (350, 0.7),
    "pharmacy": (280, 0.8), "electronics": (2500, 0.9),
}
DIWALI_BOOST = {"sweet_shop": 3.0, "electronics": 2.5, "kirana": 1.6, "restaurant": 1.3, "pharmacy": 1.0}
WEEKEND_BOOST = {"kirana": 1.0, "restaurant": 1.3, "sweet_shop": 1.2, "pharmacy": 0.9, "electronics": 1.3}

BET_SIZES = np.array([100, 200, 300, 500, 1000, 2000, 5000, 10000])
BET_P = np.array([.15, .15, .05, .25, .20, .10, .08, .02])

DRIFT_TYPES = {  # type -> categories it can happen to, and the honest declaration text
    "late_night_delivery": (["restaurant", "sweet_shop"], "Started late-night home delivery via Swiggy/Zomato"),
    "online_store":        (["electronics", "sweet_shop"], "Launched an online store shipping across India"),
    "match_screening":     (["restaurant"], "Screening cricket matches with set-menu deals"),
    "wholesale":           (["kirana"], "Started wholesale supply to nearby shops"),
    "expansion":           (C.CATEGORIES, "Opened a second branch"),
}

SUPPLIER_BASE = 10_000_000
GAMBLER_BASE = 20_000_000
COLLECTION_BASE = 30_000_000


# --------------------------------------------------------------------------- calendar
def build_calendar(n_weeks: int = C.N_WEEKS) -> pd.DataFrame:
    days = pd.date_range(C.START_DATE, periods=n_weeks * 7, freq="D")
    cal = pd.DataFrame({"date": days})
    ipl = (days >= C.IPL[0]) & (days <= C.IPL[1])
    sept = (days >= C.SEPT_SERIES[0]) & (days <= C.SEPT_SERIES[1]) & ((days.day % 2) == 1)
    weekend = days.dayofweek >= 5
    cal["is_match_day"] = ipl | sept
    # evening match 19:30-23:30; IPL weekend double-headers start 15:30
    cal["match_start"] = np.where(cal.is_match_day, np.where(ipl & weekend, 15.5, 19.5), np.nan)
    cal["match_end"] = np.where(cal.is_match_day, 23.5, np.nan)
    d = (days - pd.Timestamp(C.DIWALI_DAY)).days
    cal["is_diwali_week"] = (d >= -6) & (d <= 1)
    # festive multiplier ramps up over 3 weeks before Diwali and falls after
    ramp = np.clip(1 - np.abs(np.clip(d, -21, 7) + 3) / 18, 0, 1)
    cal["festive_level"] = np.where((d >= -21) & (d <= 7), ramp, 0.0)
    return cal


# --------------------------------------------------------------------------- merchants
def build_merchants(n: int, rng: np.random.Generator, label_mix: dict | None = None,
                    n_weeks: int = C.N_WEEKS) -> pd.DataFrame:
    labels = np.array(["legit"] * n, dtype=object)
    idx = rng.permutation(n)
    pos = 0
    for lab, share in (label_mix or C.LABEL_MIX).items():
        k = max(2 if share > 0 else 0, int(round(share * n)))
        labels[idx[pos:pos + k]] = lab
        pos += k
    city_idx = rng.integers(0, len(CITIES), n)
    m = pd.DataFrame({
        "merchant_id": [f"M{i:04d}" for i in range(n)],
        "category": rng.choice(C.CATEGORIES, n, p=[.35, .2, .15, .15, .15]),
        "city": [CITIES[i][0] for i in city_idx],
        "state": [CITIES[i][1] for i in city_idx],
        "tier": [CITIES[i][2] for i in city_idx],
        "declared_size": rng.choice(list(SIZE_RATE), n, p=[.6, .3, .1]),
        "label": labels,
    })
    # betting fronts mostly claim to be small kirana / electronics shops
    fronts = m.label == "betting_front"
    m.loc[fronts, "category"] = rng.choice(["kirana", "electronics", "sweet_shop", "pharmacy"], fronts.sum(), p=[.5, .3, .1, .1])
    m.loc[fronts, "declared_size"] = rng.choice(["small", "medium"], fronts.sum(), p=[.8, .2])
    # drifters get a drift type consistent with their category
    m["drift_type"] = ""
    m["drift_week"] = -1
    for i in m.index[m.label == "genuine_drifter"]:
        t = rng.choice(list(DRIFT_TYPES))
        m.loc[i, "drift_type"] = t
        m.loc[i, "category"] = rng.choice(DRIFT_TYPES[t][0])
        lo = min(6, n_weeks // 3)
        m.loc[i, "drift_week"] = int(rng.integers(lo, max(lo + 1, n_weeks - 6)))
    lo = min(8, n_weeks // 3)
    m.loc[m.label == "rented", "drift_week"] = rng.integers(lo, max(lo + 1, min(29, n_weeks - 2)), (m.label == "rented").sum())
    m["settlement_account"] = [f"SA{i:05d}" for i in range(n)]
    # what the merchant wrote on the sign-up form ("expected monthly turnover")
    typical = m.declared_size.map(SIZE_RATE) * 30 * m.category.map(lambda c: TICKET[c][0] * 1.3)
    m["declared_monthly_turnover"] = (typical * rng.uniform(0.6, 1.5, n)).round(-3).astype(int)
    return m


# --------------------------------------------------------------------------- transactions
class Builder:
    """Collects transaction columns as numpy arrays, then makes one DataFrame."""

    def __init__(self):
        self.parts = []

    def add(self, mid, days, hours, amounts, cp, cp_state, device, direction):
        n = len(days)
        if n == 0:
            return
        self.parts.append(pd.DataFrame({
            "merchant_id": mid, "day": days, "hour": hours, "amount": amounts,
            "counterparty_id": cp, "counterparty_state": cp_state,
            "device_id": device, "direction": direction,
        }))

    def frame(self, rng, cal) -> pd.DataFrame:
        t = pd.concat(self.parts, ignore_index=True)
        minutes = rng.integers(0, 60, len(t))
        t["ts"] = cal.date.values[t.day.values] + pd.to_timedelta(t.hour * 60 + minutes, unit="m")
        t = t.sort_values(["ts", "merchant_id"]).reset_index(drop=True)
        t.insert(0, "txn_id", np.arange(len(t)))
        return t[["txn_id", "merchant_id", "ts", "amount", "direction",
                  "counterparty_id", "counterparty_state", "device_id"]]


def _legit_amounts(cat, n, rng, round_pref):
    med, sd = TICKET[cat]
    a = np.round(np.exp(np.log(med) + sd * rng.standard_normal(n))).clip(10)
    r = rng.random(n) < round_pref  # some shops price in round numbers
    a[r] = np.maximum(50, np.round(a[r] / 50) * 50)
    return a


def _sample_hours(p, n, rng):
    return rng.choice(24, n, p=p)


def simulate(n_merchants: int, seed: int = C.SEED, n_weeks: int = C.N_WEEKS,
             label_mix: dict | None = None, evasion: float = 0.3, known_bad_share: float = 0.5):
    """Build the synthetic world.

    evasion (0-1): how hard the betting operators try to hide. 0.3 = default.
      Controls the share of fronts that keep genuine-looking shop traffic, avoid round
      amounts, run on their own phone / bank account, and pay winners from elsewhere.
      Above 0.3, operators also spread bets thinly over more accounts, recruit local
      gamblers and take deposits during normal shop hours.
    known_bad_share: share of fronts whose UPI ID is found on public betting pages.
    """
    rng = np.random.default_rng(seed)
    # tactics beyond the default level (0.3) only kick in as evasion rises towards 1
    hard = max(0.0, (evasion - 0.3) / 0.7)
    cal = build_calendar(n_weeks)
    m = build_merchants(n_merchants, rng, label_mix, n_weeks)
    n_days = len(cal)
    dow = cal.date.dt.dayofweek.values
    festive = cal.festive_level.values
    match_day = cal.is_match_day.values
    weekend_ipl = match_day & (cal.match_start.values < 19)

    # --- city customer pools: neighbours share some customers, as in real life
    city_pool = {c: np.arange(i * 5000, (i + 1) * 5000) for i, (c, _, _) in enumerate(CITIES)}
    city_state = {c: s for c, s, _ in CITIES}
    n_local = len(CITIES) * 5000

    # --- betting operators: each runs several fronts with shared gamblers, devices, accounts
    bad = m.index[m.label.isin(["betting_front", "rented"])]
    n_ops = max(2, len(bad) // 6)
    ops = []
    for k in range(n_ops):
        pool = GAMBLER_BASE + k * 1000 + np.arange(600)
        ops.append({
            "pool": pool,
            "pool_state": rng.choice(STATES, len(pool)),
            "weights": (w := rng.pareto(1.2, len(pool)) + 0.2) / w.sum(),
            "devices": [f"D-X{k}{j}" for j in range(2)],
            "settlement": f"SA-X{k:02d}",
            "collection": COLLECTION_BASE + k,
        })
    m["operator"] = -1
    m.loc[bad, "operator"] = rng.integers(0, n_ops, len(bad))

    b = Builder()
    events, declarations = [], []
    week_of_day = np.arange(n_days) // 7

    for i, row in m.iterrows():
        mid, cat, lab = row.merchant_id, row.category, row.label
        own_device = f"D{i:05d}"
        base = SIZE_RATE[row.declared_size] * rng.uniform(0.7, 1.3)
        growth = 1 + rng.uniform(-0.1, 0.3) * np.arange(n_days) / 365
        rate = base * growth * np.where(dow >= 5, WEEKEND_BOOST[cat], 1.0)
        rate = rate * (1 + (DIWALI_BOOST[cat] - 1) * festive)
        rate = rate * rng.lognormal(0, 0.15, n_days)  # day-to-day noise
        round_pref = rng.choice([0.05, 0.15, 0.4], p=[.6, .3, .1])
        pool = rng.choice(city_pool[row.city], int(base * 25), replace=False)
        pw = rng.pareto(1.5, len(pool)) + 0.3
        pw /= pw.sum()
        hours_p = HOURS[cat]
        oos_share = 0.03  # tourists / visitors from other states
        dweek = row.drift_week

        if lab == "rented":       # shop slows down after the handover
            rate = np.where(week_of_day >= dweek, rate * 0.2, rate)
        if lab == "betting_front":  # fronts keep only a trickle of genuine-looking activity
            rate = rate * (rng.uniform(0.15 + 0.6 * hard, 0.4 + 0.6 * hard) if rng.random() < evasion else 0.02)

        # ---- honest shop payments (in)
        counts = rng.poisson(rate)
        days = np.repeat(np.arange(n_days), counts)
        n = len(days)
        hrs = _sample_hours(hours_p, n, rng)
        amt = _legit_amounts(cat, n, rng, round_pref)
        payer = rng.choice(pool, n, p=pw)
        pstate = np.full(n, row.state, dtype=object)
        visitor = rng.random(n) < oos_share
        payer[visitor] = rng.integers(0, n_local, visitor.sum())
        pstate[visitor] = rng.choice(STATES, visitor.sum())

        # ---- genuine drift: the business really changes from `dweek`
        if lab == "genuine_drifter":
            after = week_of_day[days] >= dweek
            t = row.drift_type
            extra_days = np.array([], int)
            if t == "late_night_delivery":
                extra = rng.poisson(rate * 0.6 * (week_of_day >= dweek))
                extra_days = np.repeat(np.arange(n_days), extra)
                ex_hrs = rng.choice([22, 23, 0, 1], len(extra_days), p=[.35, .35, .2, .1])
                ex_amt = _legit_amounts(cat, len(extra_days), rng, round_pref)
            elif t == "match_screening":
                extra = rng.poisson(rate * 2.0 * (week_of_day >= dweek) * match_day)
                extra_days = np.repeat(np.arange(n_days), extra)
                ex_hrs = rng.choice([19, 20, 21, 22, 23], len(extra_days))
                ex_amt = rng.choice([499, 500, 799, 1000, 1500], len(extra_days)).astype(float)
            elif t == "online_store":
                extra = rng.poisson(rate * 0.8 * (week_of_day >= dweek))
                extra_days = np.repeat(np.arange(n_days), extra)
                ex_hrs = _sample_hours(_profile({h: 1 for h in range(9, 23)}), len(extra_days), rng)
                ex_amt = _legit_amounts(cat, len(extra_days), rng, round_pref)
            elif t == "wholesale":
                extra = rng.poisson(rate * 0.3 * (week_of_day >= dweek))
                extra_days = np.repeat(np.arange(n_days), extra)
                ex_hrs = rng.choice(np.arange(9, 19), len(extra_days))
                ex_amt = np.round(rng.lognormal(np.log(2500), 0.6, len(extra_days)) / 100) * 100
            elif t == "expansion":
                extra = rng.poisson(rate * 1.3 * (week_of_day >= dweek))
                extra_days = np.repeat(np.arange(n_days), extra)
                ex_hrs = _sample_hours(hours_p, len(extra_days), rng)
                ex_amt = _legit_amounts(cat, len(extra_days), rng, round_pref)
            k = len(extra_days)
            if k:
                if t == "online_store":
                    ex_payer = rng.integers(0, n_local, k)
                    ex_state = rng.choice(STATES, k)
                else:
                    ex_pool = rng.choice(city_pool[row.city], int(base * 30), replace=False)
                    ex_payer = rng.choice(ex_pool, k)
                    ex_state = np.full(k, row.state, dtype=object)
                days = np.concatenate([days, extra_days])
                hrs = np.concatenate([hrs, ex_hrs])
                amt = np.concatenate([amt, ex_amt])
                payer = np.concatenate([payer, ex_payer])
                pstate = np.concatenate([pstate, ex_state])
            if rng.random() < 0.6:  # most honest drifters tell us in advance
                declarations.append((mid, str(cal.date[dweek * 7].date()), DRIFT_TYPES[t][1]))

        device = np.full(len(days), own_device, dtype=object)
        b.add(mid, days, hrs, amt, payer, pstate, device, "in")
        shop_in = pd.Series(amt).groupby(week_of_day[days]).sum()

        # ---- betting collections (fronts from day 1, rented after handover)
        bet_days = bet_amt = None
        if lab in ("betting_front", "rented"):
            op = ops[row.operator]
            start = 0 if lab == "betting_front" else dweek * 7
            uses_op_device = rng.random() < 1 - evasion
            bet_device = rng.choice(op["devices"]) if uses_op_device or lab == "rented" else own_device
            # hard evasion: spread bets thinly over many more accounts -> less volume per front
            fstrength = rng.uniform(25, 70) * (1 - 0.75 * hard)
            active = np.arange(n_days) >= start
            lam = np.where(match_day, fstrength, fstrength * 0.25) * active * rng.lognormal(0, 0.2, n_days)
            cnt = rng.poisson(lam)
            bet_days = np.repeat(np.arange(n_days), cnt)
            nb = len(bet_days)
            on_match = match_day[bet_days]
            hrs_match = rng.choice([18, 19, 20, 21, 22, 23, 0, 1], nb, p=[.08, .2, .22, .2, .14, .08, .05, .03])
            hrs_dbl = rng.choice([15, 16, 17, 18, 19, 20, 21, 22, 23], nb)
            hrs_casino = rng.choice([20, 21, 22, 23, 0, 1, 2], nb, p=[.1, .15, .2, .2, .15, .12, .08])
            bh = np.where(on_match, np.where(weekend_ipl[bet_days], hrs_dbl, hrs_match), hrs_casino)
            bet_amt = rng.choice(BET_SIZES, nb, p=BET_P).astype(float)
            if rng.random() < evasion:  # evasive operators avoid perfectly round amounts
                odd = rng.random(nb) < 0.5
                bet_amt[odd] += rng.choice([-1, 1, 7, -3, 9], odd.sum())
            sub = rng.choice(op["pool"], 350, replace=False)
            sw = op["weights"][np.searchsorted(op["pool"], sub)]
            g = rng.choice(sub, nb, p=sw / sw.sum())
            gstate = op["pool_state"][g - op["pool"][0]]
            if hard > 0:
                # hard evasion: recruit gamblers locally, and take deposits during shop hours too
                local = rng.random(nb) < 0.7 * hard
                gstate = np.where(local, row.state, gstate)
                daytime = rng.random(nb) < 0.5 * hard
                bh = np.where(daytime, _sample_hours(hours_p, nb, rng), bh)
            b.add(mid, bet_days, bh, bet_amt, g, gstate, np.full(nb, bet_device, dtype=object), "in")

            if lab == "rented":
                ts = str(cal.date[start].date())
                events += [(mid, ts, "device_change", bet_device), (mid, ts, "settlement_account_change", op["settlement"])]
            elif rng.random() < max(0.0, 0.8 - evasion):
                m.loc[i, "settlement_account"] = op["settlement"]
            if rng.random() < 0.25:  # scripted fake explanation, as seen in ED cases
                declarations.append((mid, str(cal.date[int(rng.integers(2, max(3, min(20, n_weeks)))) * 7].date()),
                                     rng.choice(["Festival sale", "Started home delivery", "Bulk order from a client"])))

            # payouts: most of each day's bets go straight back out to winners and the operator.
            # ~40% of operators are more careful: they pay winners from other accounts, so this
            # merchant shows no payouts at all (pass-through signals stay silent for them).
            day_in = pd.Series(bet_amt).groupby(bet_days).sum()
            if rng.random() < min(1.0, evasion + 0.1):
                day_in = day_in.iloc[:0]
            for d, v in day_in.items():
                out_total = v * rng.uniform(0.7, 0.92)
                k = 1 + rng.poisson(len(bet_days[bet_days == d]) * 0.25) if v > 0 else 0
                winners = rng.choice(sub, k)
                shares = rng.dirichlet(np.ones(k + 1))
                cps = np.concatenate([winners, [op["collection"]]])
                cstates = np.concatenate([op["pool_state"][winners - op["pool"][0]], ["XX"]])
                b.add(mid, np.full(k + 1, d), rng.choice([23, 0, 1, 2], k + 1),
                      np.round(out_total * shares), cps, cstates,
                      np.full(k + 1, bet_device, dtype=object), "out")

        # ---- honest supplier payments (out): weekly, a few known suppliers
        n_sup = 3
        sup_share = rng.uniform(0.5, 0.75)
        pays_per_week = 2
        for w, v in shop_in.items():
            nsup, share, ppw = n_sup, sup_share, pays_per_week
            if lab == "genuine_drifter" and row.drift_type == "wholesale" and w >= dweek:
                nsup, share, ppw = 8, 0.88, 5  # distributor: buys and resells quickly
            sup = SUPPLIER_BASE + i * 10 + np.arange(nsup)
            dd = w * 7 + rng.choice(6, ppw, replace=False)
            amts = np.round(v * share * rng.dirichlet(np.ones(ppw)))
            b.add(mid, dd, rng.integers(10, 18, ppw), amts, rng.choice(sup, ppw),
                  np.full(ppw, row.state, dtype=object), np.full(ppw, own_device, dtype=object), "out")

        # ---- innocent account changes (new phone, new bank) add realistic noise
        if lab == "legit" and rng.random() < 0.05:
            events.append((mid, str(cal.date[int(rng.integers(0, n_days))].date()), "device_change", f"D{i:05d}b"))
        if lab == "legit" and rng.random() < 0.02:
            events.append((mid, str(cal.date[int(rng.integers(0, n_days))].date()), "settlement_account_change", f"SA{i:05d}b"))

    tx = b.frame(rng, cal)

    # ---- known-bad list: half the fronts are found on public betting pages / Telegram channels
    fronts = m.merchant_id[m.label == "betting_front"].to_numpy()
    seeds = rng.choice(fronts, int(len(fronts) * known_bad_share), replace=False)
    known_bad = pd.DataFrame({
        "merchant_id": seeds,
        "source": rng.choice(["public betting website", "public Telegram channel"], len(seeds)),
        "found_date": [str(cal.date[int(rng.integers(min(14, len(cal) - 2), min(120, len(cal) - 1)))].date()) for _ in seeds],
    })
    ev = pd.DataFrame(events, columns=["merchant_id", "date", "event", "new_value"])
    decl = pd.DataFrame(declarations, columns=["merchant_id", "week_start", "declared_change"])
    return m, tx, cal, known_bad, ev, decl


def main(small: bool = False):
    n = C.N_MERCHANTS_SMALL if small else C.N_MERCHANTS_FULL
    m, tx, cal, kb, ev, decl = simulate(n)
    C.DATA.mkdir(exist_ok=True)
    m.to_csv(C.DATA / "merchants.csv", index=False)
    tx.to_csv(C.DATA / "transactions.csv", index=False)
    cal.to_csv(C.DATA / "calendar.csv", index=False)
    kb.to_csv(C.DATA / "known_bad.csv", index=False)
    ev.to_csv(C.DATA / "account_events.csv", index=False)
    decl.to_csv(C.DATA / "declarations.csv", index=False)
    print(f"{len(m)} merchants, {len(tx):,} transactions")
    print(m.label.value_counts().to_string())
    return m, tx


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--small", action="store_true")
    main(ap.parse_args().small)
