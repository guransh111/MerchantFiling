# Real data used for calibration

`npci_upi_mcc_july2025.csv`: official NPCI UPI person-to-merchant statistics by merchant
category (MCC) for **July 2025**, the first month NPCI published category-wise figures.
These are **real, aggregate** numbers (monthly totals per category), not individual payments.

They were collected from reputable reports that reproduce NPCI's release, because NPCI's own
website blocks automated access from cloud servers:

- Business Standard, "UPI's top checkout by volume in July: The grocery aisle dominates" (10 Aug 2025)
  https://www.business-standard.com/finance/news/upi-s-top-checkout-in-july-the-grocery-aisle-125081000433_1.html
- SBI Research, "New Insights from UPI Data", Issue 20, FY26 (18 Aug 2025)
  https://sbi.bank.in/documents/13958/14472/New+Insights+from+UPI+Data_SBI+Research.pdf
- OfficeChai, "Here's How India Spends Money On UPI, As Per NPCI Data"
  https://officechai.com/stories/heres-how-india-spends-money-on-upi-as-per-npci-data/
- The Head and Tale, "UPI's July leaders: 3 billion grocery payments, Rs 93,857 crore in debt collections"
  https://theheadandtale.com/explainer/upi-s-july-leaders-3-billion-grocery-payments-rs-93857-crore-in-debt-collections/

Notes
- avg_ticket_rs = value / volume (as also reported by SBI Research), rounded.
- A later Head and Tale article reports slightly different July numbers for pharmacies (311.94M, Rs 13,157 cr)
  and electronics (82.80M, Rs 11,322 cr), likely a revision. Average tickets are similar (Rs 422 / Rs 1,367).
- The bakery figure is low confidence (period not confirmed) and is only a proxy for sweet shops.
- Official source to check against: https://www.npci.org.in/what-we-do/upi/upi-ecosystem-statistics

How it is used: `src/generate.py` sets each category's typical payment size so that the synthetic
average matches these real averages, and `src/evaluate.py` prints a reality check (synthetic vs real).
