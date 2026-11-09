# 1. The problem

## What a payment provider (payment aggregator) does

When you scan a shop's QR code and pay by UPI, the money often goes through a **payment aggregator
(PA)** such as Razorpay, Cashfree or PhonePe's merchant business. The PA:

1. **Onboards** the merchant: checks documents (PAN, GST, bank account, shop photo). This is KYC.
2. **Collects** payments from customers on the merchant's behalf.
3. **Settles**: pays the money into the merchant's bank account, usually the next day (T+1).

The PA earns a small fee per payment. It is also legally responsible for knowing who its merchants
really are and what they really do (RBI Payment Aggregator Directions and PMLA; see file 06).

## How betting money hides

Online betting on cricket is illegal in most of India, and real-money gaming was banned in 2025.
Betting operators still need a way to collect deposits from gamblers. Their trick:

1. Recruit people (often poor, often paid a few thousand rupees) to open merchant accounts as
   ordinary businesses, such as "Sharma General Store, Lucknow". The documents are genuine (or
   well forged), so onboarding checks pass.
2. Show gamblers that merchant's UPI ID or QR code on a betting website or Telegram channel.
3. Gamblers "pay the kirana store". The PA settles to the bank account, and the operator moves the
   money on quickly (often into crypto).
4. When an account gets blocked, move on to the next one. Thousands of new UPI IDs appear every day.

Real cases:
- **1xBet (Enforcement Directorate, 2025 to 2026):** over 6,000 mule accounts; merchants onboarded on
  payment gateways whose declared business didn't match their transactions.
- **Parimatch:** UPI collections disguised as e-commerce refunds, chargebacks or vendor payments.
- **CUTS International report (2025):** UPI is now the main deposit channel for illegal gambling sites.

A variant is the **rented account**. A genuine shop owner hands over their merchant account to an
operator for a monthly fee. The account has months of honest history, which makes it look safe.

## Why it's hard

| Challenge | Why it matters |
|---|---|
| Documents are fine | You can't catch it at onboarding; you have to watch behaviour afterwards |
| Each payment looks normal | ₹500 to a kirana store is not suspicious on its own |
| Honest businesses change too | Diwali rush, a restaurant screening IPL matches, a shop that starts delivery |
| Too strict hurts real people | Freezing a small shop's money can ruin it; India has millions of them |
| Too lax lets fraud continue | Plus regulatory penalties (FIU-IND fined Paytm Payments Bank) |
| Fraudsters adapt | Avoid round amounts, spread across many small accounts, rotate quickly |

So the challenge asks for two things at once: **catch** the fronts, and **protect** honest merchants.
Most existing systems focus on the first and treat the second as collateral damage. We treat both as goals.

## What a PA can and can't see

A PA sees payments **to its merchants** (person-to-merchant, P2M): amount, time, payer's UPI ID and
bank/state, device used by the merchant, payouts the merchant makes, settlement account.

A PA **doesn't** see personal-UPI transfers (person-to-person, P2P) that never touch it. Much betting
money moves that way. That's the banks' and NPCI's job (RBI's MuleHunter.AI). We are explicit that we
cover the merchant side and would **share** our flags with those systems.
