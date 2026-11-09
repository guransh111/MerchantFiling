# 4. The ten signals

Each signal is computed **per merchant, per week**. The "Risky when" column says which direction
pushes the score up; moves in the other direction never count against a merchant.

Typical values below come from our simulated data (medians across all weeks).

| # | Signal | How it's calculated | Risky when | Honest shop | Betting front |
|---|---|---|---|---|---|
| 1 | **Match-hours share** | ₹ received during live cricket match windows ÷ all ₹ received (match weeks only) | High | ~10% for a kirana (restaurants ~27%, since dinner overlaps) | ~70% |
| 2 | **Night share** | ₹ received 11pm to 4am ÷ all ₹ | High | ~0% | ~45% |
| 3 | **Round-amount share** | % of payments that are exact multiples of ₹100 | High | ~5% | ~95% |
| 4 | **Out-of-state payers** | % of payments from payers whose bank/state differs from the shop's state | High | ~3% | ~90% |
| 5 | **Payments per customer** | payments ÷ unique payers in the week | High | ~1.5 | ~2.3 (gamblers top up repeatedly) |
| 6 | **Ticket variety** | how spread out the payment amounts are (an entropy measure, 0 to ~5) | **Low** | ~4.3 | ~2.8 (just ₹100/500/1,000/…) |
| 7 | **Pass-through** | each day: min(money in, money out); summed ÷ money in | High | ~24% (suppliers paid twice a week) | ~78% (winners paid same night) |
| 8 | **Payout fan-out** | number of different accounts the merchant pays out to | High | 2 to 3 suppliers | ~27 |
| 9 | **Volume growth** | this week's takings vs median of its previous 8 weeks | High | ~0% | varies |
| 10 | **Size mismatch** | takings (scaled to a month) ÷ monthly turnover declared at sign-up | High | ~1x | ~10x+ |

## Why each one, in one line

1. **Match hours.** Betting volume follows the cricket schedule; groceries don't.
2. **Night.** Kiranas close; online betting (and "casino" games between matches) doesn't.
3. **Round amounts.** Bets are placed as ₹500 or ₹1,000. Groceries cost ₹137 or ₹284.
4. **Out of state.** A Lucknow kirana serves Lucknow. A betting site's customers are all over India.
5. **Repeat payments.** Gamblers deposit again and again. Shoppers buy once or twice a week.
6. **Variety.** Real baskets produce many different amounts; betting uses a menu of fixed stakes.
7. **Pass-through.** Betting pays winners almost immediately, so money doesn't "rest". A shop pays
   suppliers on a schedule. (It's like the cash conversion cycle: a betting front's is near zero.)
8. **Fan-out.** A shop pays a handful of suppliers. A betting front pays dozens of winners.
9. **Growth.** Sudden growth matters, but only *relative to peers in the same week*. That's how
   Diwali is excused.
10. **Size mismatch.** "Small kirana expecting ₹60,000/month" taking ₹6 lakh a week contradicts the
    declaration directly.

## Where honest businesses can look similar (and why it's OK)

| Honest situation | Signals it trips | Why it usually stays at Monitor or Ask |
|---|---|---|
| Restaurant screening IPL matches | Match hours, night, round set-menu prices | Local customers, normal variety, no pass-through, no fan-out, no network links |
| Kirana becoming a wholesaler | Size mismatch, growth, round bulk orders, pass-through | Local customers, few suppliers, normal hours |
| Late-night delivery | Night share | Only one or two signals |
| Online store shipping across India | Out-of-state payers, growth | Normal hours, normal amounts |
| Diwali rush | Growth | Peers grow too, so the deviation is close to zero |

This is the reason for **capping**: each signal adds at most 4 "spreads" (× its weight) to the score.
To reach Friction (75) a merchant needs roughly five or six signals clearly abnormal at the same time.

## Signals we deliberately left out (and could add later)

- **Payment notes**, e.g. "id", "bet", "deposit". These are powerful, but reading free text raises
  privacy issues. If added, use keyword flags only and never store the text.
- **Refund/chargeback patterns.** The Parimatch case disguised payouts as refunds.
- **Website and Google Maps presence, geotagged shop photo.** These are LegitScript-style checks.
- **GST turnover vs UPI volume**, with merchant consent via GSTN or the Account Aggregator.
