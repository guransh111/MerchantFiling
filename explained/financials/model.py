"""Trace: implementation and running-cost model for a payment aggregator (PA).

Every number in the financial appendix comes from this file. Change an assumption below and run
    python explained/financials/model.py
to print the results and write explained/financials/results.json (read by build_docx.js).

All money is in Indian rupees. 1 lakh = 100,000; 1 crore = 100 lakh = 10,000,000.
These are planning estimates from stated assumptions, not quotes. Costs are INCREMENTAL: what a PA would
spend on top of the KYC and compliance team it already has.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

LAKH, CRORE = 1e5, 1e7

# ---------------------------------------------------------------- general assumptions
FX = 90.0                 # rupees per US dollar (USD/INR was 88.6-89.7 in Nov 2025; rounded up for caution)
OVERHEAD = 0.20           # on top of salary (CTC): office, laptops, recruiting, software seats
ANALYST_HOURS = 1700      # productive hours per analyst per year (about 220 days x 7.7 hours)
PAYMENTS_PER_MERCHANT_DAY = 8   # average P2M payments per active merchant per day (sizing only)

SCENARIOS = {"Small PA": 5 * LAKH, "Mid-size PA (base case)": 20 * LAKH, "Large PA": 100 * LAKH}
BASE = "Mid-size PA (base case)"

# annual cost to company (CTC), rupees
SALARY = {
    "Product / project lead": 35 * LAKH,
    "Senior data scientist": 24 * LAKH,
    "Data scientist": 18 * LAKH,
    "ML / data engineer": 22 * LAKH,
    "Backend engineer": 18 * LAKH,
    "DevOps / QA engineer": 16 * LAKH,
    "Compliance and legal specialist": 30 * LAKH,
    "Risk analyst": 6.5 * LAKH,
    "Analyst team lead": 14 * LAKH,
}

# ---------------------------------------------------------------- implementation (one-time)
PHASES = [  # name, months, what happens
    ("Discovery and data access", 1, "Map the PA's payment, KYC and settlement data; agree the action ladder with compliance"),
    ("Build and integrate", 4, "Signals, peer scoring, network, change points, case management, GST check, reporting"),
    ("Shadow pilot", 3, "Trace scores every merchant but takes no action; analysts check its flags against their own"),
    ("Rollout", 1, "Ask and Friction switched on first; Review and holds only after sign-off"),
]
IMPL_MONTHS = sum(m for _, m, _ in PHASES)

IMPL_TEAM = [  # role, people, months on the project
    ("Product / project lead", 1, 9),
    ("Senior data scientist", 1, 9),
    ("Data scientist", 1, 8),
    ("ML / data engineer", 2, 8),
    ("Backend engineer", 2, 6),
    ("DevOps / QA engineer", 1, 6),
    ("Compliance and legal specialist", 0.5, 9),
    ("Risk analyst", 3, 4),          # label past cases to seed the learning loop; review pilot flags
]

IMPL_OTHER = [  # item, rupees, note
    ("GST verification API (GSP) set-up and testing", 6 * LAKH, "Connect to a GST Suvidha Provider to read declared turnover"),
    ("Security testing and DPDP impact assessment", 8 * LAKH, "External penetration test; Digital Personal Data Protection review"),
    ("Legal review of the ladder, notices and appeals", 6 * LAKH, "Merchant-facing wording, hold policy, appeal process"),
    ("Analyst training and playbooks", 3 * LAKH, "How to work a case, write an STR draft, decide an appeal"),
]
CONTINGENCY = 0.15
BUILD_CLOUD_SHARE = 0.40   # dev, staging and the pilot run at about 40% of the production cloud bill

# ---------------------------------------------------------------- running (annual)
HOURS_PER_YEAR = 24 * 365
# cloud: on-demand list prices, AWS Mumbai (ap-south-1). m6i.2xlarge is sourced; the others are approximate.
PRICE = {
    "m6i.2xlarge": 0.404,     # 8 vCPU, 32 GB: weekly signals and scoring
    "r6i.4xlarge": 1.00,      # 16 vCPU, 128 GB (approx.): network graph and learning loop
    "m6i.xlarge": 0.202,      # 4 vCPU, 16 GB: dashboard, case management, APIs
    "kafka.broker": 0.25,     # managed Kafka broker (approx.)
    "postgres.multiaz": 1.00, # managed PostgreSQL, two zones (approx.)
    "s3.gb_month": 0.025,     # object storage per GB-month
}
BYTES_PER_PAYMENT = 60        # compressed, columnar
RETENTION_YEARS = 5           # PMLA record keeping
CLOUD_EXTRAS = 0.20           # monitoring, logs, backups, data transfer

MODEL_TEAM = [("Senior data scientist", 1.0), ("ML / data engineer", 1.0), ("Backend engineer", 0.5),
              ("DevOps / QA engineer", 0.25)]

CASE_RATE = 0.010             # share of merchants that reach Ask or above in a year
CASE_MIX = [  # step, share of cases, analyst minutes per case
    ("Ask: neutral question, merchant replies", 0.60, 10),
    ("Friction: lower limits, slower settlement", 0.25, 25),
    ("Review: reserve, investigation, STR draft", 0.15, 90),
]
APPEAL_RATE = 0.05            # share of Friction and Review cases that appeal
APPEAL_MINUTES = 60           # a second analyst decides
AUDIT_RATE = 0.0025           # random audit sample, share of merchants per year
AUDIT_MINUTES = 20
ANALYSTS_PER_LEAD = 8
GST_LOOKUP = 3.0              # rupees per GST lookup (approx.)

OTHER_RUNNING = [  # item, rupees per year at base scale, scales with merchants?
    ("Annual security test and compliance audit", 6 * LAKH, False),
    ("Monitoring, ticketing and other software", 5 * LAKH, True),
    ("Policy reviews and analyst training", 3 * LAKH, False),
    ("Consortium token sharing (legal and hosting)", 2 * LAKH, False),
]

# ---------------------------------------------------------------- value and break-even
FIU_PENALTY = 5.49 * CRORE    # FIU-IND on Paytm Payments Bank, March 2024 (gambling proceeds, PMLA)
AMORTISE_YEARS = 5
PRECISION_TRACE = 0.79        # simulation: share of merchants Trace acts on (Ask+) that are really bad
PRECISION_BASELINE = 0.43     # simulation: same for a typical own-history detector
SALARY_GROWTH, MERCHANT_GROWTH = 0.08, 0.10   # for the five-year view


def cloud(merchants: float, scale: float = 1.0) -> dict:
    """Production cloud bill per year, itemised."""
    batch_nodes = max(2, math.ceil(merchants / 4e5))
    graph_nodes = max(1, math.ceil(merchants / 1e6))
    app_nodes = 3 if merchants <= 50 * LAKH else 6
    payments_year = merchants * PAYMENTS_PER_MERCHANT_DAY * 365
    stored_gb = payments_year * BYTES_PER_PAYMENT * RETENTION_YEARS / 1e9
    items = [
        ("Weekly signals and scoring", f"{batch_nodes} x m6i.2xlarge, 4 h a day",
         batch_nodes * PRICE["m6i.2xlarge"] * 4 * 365),
        ("Network graph and learning loop", f"{graph_nodes} x r6i.4xlarge, 3 h a day",
         graph_nodes * PRICE["r6i.4xlarge"] * 3 * 365),
        ("Dashboard, case management, APIs", f"{app_nodes} x m6i.xlarge, always on",
         app_nodes * PRICE["m6i.xlarge"] * HOURS_PER_YEAR),
        ("Streaming payment feed (Kafka)", "3 managed brokers, always on", 3 * PRICE["kafka.broker"] * HOURS_PER_YEAR),
        ("Cases and results database", "Managed PostgreSQL, two zones", PRICE["postgres.multiaz"] * HOURS_PER_YEAR
         * (1 if merchants <= 50 * LAKH else 2)),
        ("Payment history storage", f"{stored_gb:,.0f} GB kept {RETENTION_YEARS} years, plus a backup copy",
         stored_gb * 2 * PRICE["s3.gb_month"] * 12),
    ]
    sub = sum(usd for *_, usd in items)
    items.append(("Monitoring, logs, backups, data transfer", f"{CLOUD_EXTRAS:.0%} on top", sub * CLOUD_EXTRAS))
    rows = [{"item": a, "basis": b, "usd": usd * scale, "inr": usd * FX * scale} for a, b, usd in items]
    return {"rows": rows, "inr": sum(r["inr"] for r in rows), "usd": sum(r["usd"] for r in rows),
            "payments_year": payments_year, "stored_gb": stored_gb}


def people_cost(role: str, fte: float, months: float = 12, salary_scale: float = 1.0) -> float:
    return SALARY[role] * salary_scale * (1 + OVERHEAD) * fte * months / 12


def analysts(merchants: float, case_rate: float = CASE_RATE, minutes_scale: float = 1.0, salary_scale: float = 1.0) -> dict:
    cases = merchants * case_rate
    rows = []
    hours = 0.0
    for step, share, mins in CASE_MIX:
        h = cases * share * mins * minutes_scale / 60
        hours += h
        rows.append({"item": step, "count": cases * share, "minutes": mins * minutes_scale, "hours": h})
    penalised = cases * sum(s for _, s, _ in CASE_MIX[1:])
    appeals = penalised * APPEAL_RATE
    h = appeals * APPEAL_MINUTES * minutes_scale / 60
    hours += h
    rows.append({"item": "Appeals, decided by a second analyst", "count": appeals, "minutes": APPEAL_MINUTES * minutes_scale, "hours": h})
    audits = merchants * AUDIT_RATE
    h = audits * AUDIT_MINUTES * minutes_scale / 60
    hours += h
    rows.append({"item": "Random audits of unflagged merchants", "count": audits, "minutes": AUDIT_MINUTES * minutes_scale, "hours": h})
    n = max(1, math.ceil(hours / ANALYST_HOURS))
    leads = max(1, math.ceil(n / ANALYSTS_PER_LEAD))
    cost = people_cost("Risk analyst", n, salary_scale=salary_scale) + people_cost("Analyst team lead", leads, salary_scale=salary_scale)
    reviews = cases * CASE_MIX[2][1]
    gst = (cases + reviews) * GST_LOOKUP
    return {"cases": cases, "rows": rows, "hours": hours, "analysts": n, "leads": leads, "cost": cost, "gst": gst,
            "minutes_per_case": sum(s * m for _, s, m in CASE_MIX) * minutes_scale}


def running(merchants: float, case_rate=CASE_RATE, minutes_scale=1.0, salary_scale=1.0, cloud_scale=1.0) -> dict:
    c = cloud(merchants, cloud_scale)
    team_extra = [("ML / data engineer", 1.0)] if merchants > 50 * LAKH else []
    team = [{"role": r, "fte": f, "inr": people_cost(r, f, salary_scale=salary_scale)} for r, f in MODEL_TEAM + team_extra]
    a = analysts(merchants, case_rate, minutes_scale, salary_scale)
    scale = merchants / (20 * LAKH)
    other = [{"item": i, "inr": v * (scale if s else 1)} for i, v, s in OTHER_RUNNING]
    other.append({"item": "GST lookups for flagged merchants", "inr": a["gst"]})
    lines = {"Cloud and data": c["inr"], "Model and engineering team": sum(t["inr"] for t in team),
             "Analyst desk": a["cost"], "Audit, software and other": sum(o["inr"] for o in other)}
    total = sum(lines.values())
    return {"cloud": c, "team": team, "analysts": a, "other": other, "lines": lines, "total": total,
            "per_merchant": total / merchants, "per_case": total / a["cases"]}


def implementation(merchants: float) -> dict:
    team = [{"role": r, "people": p, "months": m, "inr": people_cost(r, p, m)} for r, p, m in IMPL_TEAM]
    build_cloud = cloud(merchants)["inr"] / 12 * BUILD_CLOUD_SHARE * IMPL_MONTHS
    other = [{"item": i, "inr": v, "note": n} for i, v, n in IMPL_OTHER]
    other.insert(0, {"item": "Cloud for development, staging and the pilot", "inr": build_cloud,
                     "note": f"{BUILD_CLOUD_SHARE:.0%} of the production bill for {IMPL_MONTHS} months"})
    sub = sum(t["inr"] for t in team) + sum(o["inr"] for o in other)
    cont = sub * CONTINGENCY
    return {"team": team, "other": other, "subtotal": sub, "contingency": cont, "total": sub + cont,
            "team_total": sum(t["inr"] for t in team), "other_total": sum(o["inr"] for o in other)}


def main() -> dict:
    out = {"assumptions": {"fx": FX, "overhead": OVERHEAD, "analyst_hours": ANALYST_HOURS, "case_rate": CASE_RATE,
                           "payments_per_day": PAYMENTS_PER_MERCHANT_DAY, "salary": SALARY, "price": PRICE,
                           "case_mix": CASE_MIX, "appeal_rate": APPEAL_RATE, "appeal_minutes": APPEAL_MINUTES,
                           "audit_rate": AUDIT_RATE, "audit_minutes": AUDIT_MINUTES, "contingency": CONTINGENCY,
                           "retention": RETENTION_YEARS, "bytes": BYTES_PER_PAYMENT, "cloud_extras": CLOUD_EXTRAS,
                           "build_cloud_share": BUILD_CLOUD_SHARE, "analysts_per_lead": ANALYSTS_PER_LEAD,
                           "salary_growth": SALARY_GROWTH, "merchant_growth": MERCHANT_GROWTH,
                           "amortise": AMORTISE_YEARS, "fiu_penalty": FIU_PENALTY, "gst_lookup": GST_LOOKUP,
                           "precision_trace": PRECISION_TRACE, "precision_baseline": PRECISION_BASELINE},
           "phases": PHASES, "impl_months": IMPL_MONTHS, "scenarios": {}}
    for name, m in SCENARIOS.items():
        imp, run = implementation(m), running(m)
        annual_all_in = run["total"] + imp["total"] / AMORTISE_YEARS
        out["scenarios"][name] = {"merchants": m, "implementation": imp, "running": run,
                                  "annual_all_in": annual_all_in,
                                  "penalties_to_break_even": annual_all_in / FIU_PENALTY}

    base_m = SCENARIOS[BASE]
    b = out["scenarios"][BASE]
    base_total = b["running"]["total"]
    sens = []
    for label, kw_lo, kw_hi, lo_txt, hi_txt in [
        ("Share of merchants reaching a case", {"case_rate": 0.005}, {"case_rate": 0.02}, "0.5%", "2%"),
        ("Analyst minutes per case", {"minutes_scale": 0.7}, {"minutes_scale": 1.3}, "-30%", "+30%"),
        ("Salaries", {"salary_scale": 0.8}, {"salary_scale": 1.2}, "-20%", "+20%"),
        ("Cloud prices", {"cloud_scale": 0.7}, {"cloud_scale": 1.3}, "-30% (reserved)", "+30%"),
    ]:
        lo, hi = running(base_m, **kw_lo)["total"], running(base_m, **kw_hi)["total"]
        sens.append({"driver": label, "low_case": lo_txt, "high_case": hi_txt, "low": lo, "high": hi,
                     "base": base_total})
    out["sensitivity"] = sens

    # five-year view for the base case: running costs grow with salaries and merchants
    years = [{"year": "Year 0 (build)", "implementation": b["implementation"]["total"], "running": 0.0}]
    for y in range(1, 6):
        m = base_m * (1 + MERCHANT_GROWTH) ** (y - 1)
        r = running(m, salary_scale=(1 + SALARY_GROWTH) ** (y - 1))
        years.append({"year": f"Year {y}", "implementation": 0.0, "running": r["total"], "merchants": m,
                      "analysts": r["analysts"]["analysts"]})
    out["five_year"] = years
    out["five_year_total"] = sum(y["implementation"] + y["running"] for y in years)

    # value: analyst time saved versus a typical own-history detector (from the simulation's precision)
    a = b["running"]["analysts"]
    true_cases = a["cases"] * PRECISION_TRACE
    baseline_alerts = true_cases / PRECISION_BASELINE
    fewer = baseline_alerts - a["cases"]
    hours_saved = fewer * a["minutes_per_case"] / 60
    analyst_cost_hour = SALARY["Risk analyst"] * (1 + OVERHEAD) / ANALYST_HOURS
    out["value"] = {"true_cases": true_cases, "baseline_alerts": baseline_alerts, "fewer_reviews": fewer,
                    "hours_saved": hours_saved, "analysts_saved": hours_saved / ANALYST_HOURS,
                    "inr_saved": hours_saved * analyst_cost_hour, "analyst_cost_hour": analyst_cost_hour,
                    "fewer_share": 1 - PRECISION_BASELINE / PRECISION_TRACE}
    return out


if __name__ == "__main__":
    res = main()
    Path(__file__).with_name("results.json").write_text(json.dumps(res, indent=1, default=float))
    for name, s in res["scenarios"].items():
        print(f"{name:26s} merchants {s['merchants']:>12,.0f}  build Rs {s['implementation']['total'] / CRORE:5.2f} cr  "
              f"run Rs {s['running']['total'] / CRORE:5.2f} cr/yr  Rs {s['running']['per_merchant']:5.1f}/merchant  "
              f"analysts {s['running']['analysts']['analysts']}  all-in Rs {s['annual_all_in'] / CRORE:4.2f} cr/yr  "
              f"break-even {s['penalties_to_break_even']:.2f} penalties/yr")
    b = res["scenarios"][BASE]["running"]
    print({k: round(v / LAKH, 1) for k, v in b["lines"].items()}, "lakh")
    print("cloud usd", round(b["cloud"]["usd"]), "five-year total cr", round(res["five_year_total"] / CRORE, 2))
    print("value", {k: round(v, 1) for k, v in res["value"].items()})
