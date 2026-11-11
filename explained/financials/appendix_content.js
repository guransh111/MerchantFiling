// The full Trace appendix: the reasoning, method, results, operations, costs and limits behind Trace.
// Written for judges and a payment provider's risk team. Figures come from reports/results.md (synthetic world of
// 1,000 merchants over 37 weeks), data/real/ (NPCI) and explained/financials/results.json (costs).
const path = require("path");
const { finContent } = require("./fin_content");

const REPORTS = path.join(__dirname, "..", "..", "reports");

function appendixContent(lib) {
  const { body, lead, small, bullet, strong, t, label, table, pairs, note, image, caption, code, RIGHT, W } = lib;
  const c = [];
  const push = (...x) => x.forEach((y) => (Array.isArray(y) ? c.push(...y) : c.push(y)));
  // a new page only before the main parts; shorter appendices follow on with space above
  const NEW_PAGE = new Set(["E", "G", "K", "M", "N", "P"]);
  const A = (letter, text) => lib.heading(1, letter, text, `ap${letter}`,
    NEW_PAGE.has(letter) ? { pageBreak: true } : letter === "A" ? {} : { spacing: { before: 560, after: 200 } });
  const S = (num, text) => lib.heading(2, num, text, `ap${num.replace(".", "_")}`);
  const fig = (file, h, cap) => [image(path.join(REPORTS, file), 6.2, h), caption(cap)];
  const bullets = (xs) => xs.map((x) => (Array.isArray(x) ? bullet([strong(x[0]), t(x[1])]) : bullet(x)));

  // ------------------------------------------------------------------ A. Context
  push(A("A", "Current context: UPI and payment aggregators"));
  push(S("A.1", "How a shop gets paid by UPI"));
  push(body("When a customer scans a shop's QR code and pays by UPI, the money often passes through a payment aggregator " +
    "(PA) such as Razorpay, Cashfree or PhonePe's merchant business. The PA does three things:"));
  push(...bullets([
    ["Onboards ", "the merchant: checks documents such as PAN, GST registration, bank account and a shop photo (KYC)."],
    ["Collects ", "payments from customers on the merchant's behalf."],
    ["Settles ", "the money into the merchant's bank account, usually the next day (T+1)."],
  ]));
  push(body("The PA earns a small fee per payment and is legally responsible for knowing who its merchants really are and " +
    "what they really do, under the RBI's Payment Aggregator Directions and the Prevention of Money Laundering Act (PMLA)."));
  push(S("A.2", "The scale of everyday UPI commerce"));
  push(body("Small, frequent payments to neighbourhood shops are the backbone of UPI. In July 2025, the first month NPCI " +
    "published figures by merchant category, grocery stores alone received 3,033 million UPI payments worth ₹64,882 crore."));
  push(lead("Real average payment sizes by category (NPCI, July 2025), which Trace's simulation is calibrated to:"));
  push(table(["Merchant category", "Average payment", "Confidence"], [
    ["Grocery stores and supermarkets (kirana)", "₹214", "High"],
    ["Fast food and other restaurants", "₹113 to ₹158", "High / medium"],
    ["Drug stores and pharmacies", "₹398", "High"],
    ["Electronics shops", "₹1,093", "High"],
    ["Bakeries (proxy for sweet shops)", "₹262", "Low"],
  ], [{ w: 4626 }, { w: 2200, align: RIGHT }, { w: 2200 }]));
  push(small("Collected from Business Standard, SBI Research, OfficeChai and The Head and Tale, which reproduce NPCI's release (data/real/)."));
  push(S("A.3", "What a payment aggregator can and cannot see"));
  push(lead("Trace is built for what a PA actually has, and is explicit about what it does not cover."));
  push(table(["A PA sees (person-to-merchant payments)", "A PA does not see"], [
    ["Amount and time of every payment to its merchants", "Person-to-person UPI transfers that never touch the PA"],
    ["Payer's UPI ID and bank, and so the payer's state", "What happens in other banks or wallets"],
    ["Devices and phones the merchant uses", "Private betting groups and chats"],
    ["Payouts the merchant makes, and its settlement account", "The merchant's real premises, unless it checks"],
  ], [{ w: 4513 }, { w: 4513 }]));
  push(body("Much betting money also moves person to person. That side belongs to the banks and NPCI (for example, the RBI's " +
    "MuleHunter.AI). Trace covers the merchant side and is designed to share its flags with those systems."));

  // ------------------------------------------------------------------ B. Problem
  push(A("B", "The problem: betting money hiding in merchant accounts"));
  push(S("B.1", "How betting money hides"));
  push(body("Online betting on cricket is illegal in most of India, and real-money gaming was banned in 2025. Betting operators " +
    "still need a way to collect deposits from gamblers. The common method:"));
  push(...bullets([
    "Recruit people, often poor and paid a few thousand rupees, to open merchant accounts as ordinary businesses such as \"Sharma General Store, Lucknow\". The documents are genuine or well forged, so onboarding checks pass.",
    "Post that merchant's UPI ID or QR code on a betting website or Telegram channel.",
    "Gamblers \"pay the kirana store\". The PA settles to the bank account, and the operator moves the money on quickly, often into crypto.",
    "When an account is blocked, move to the next one. New UPI IDs appear every day.",
  ]));
  push(S("B.2", "Rented accounts"));
  push(body("A variant is the rented account: a genuine shop owner hands their merchant account to an operator for a monthly fee. " +
    "The account has months of honest history, which makes it look safe, until its behaviour changes almost overnight."));
  push(S("B.3", "Real cases"));
  push(lead("The pattern is documented in enforcement actions and research:"));
  push(pairs(["Case", "What happened"], [
    ["1xBet (Enforcement Directorate, 2025 to 2026)", "Over 6,000 mule accounts; merchants onboarded on payment gateways whose declared business did not match their transactions"],
    ["Parimatch (Enforcement Directorate)", "UPI collections disguised as e-commerce refunds, chargebacks or vendor payments"],
    ["CUTS International report (2025)", "UPI is now the main deposit channel for illegal gambling sites"],
    ["Paytm Payments Bank (FIU-IND, March 2024)", "₹5.49 crore penalty under the PMLA after proceeds of online gambling were routed through accounts at the bank"],
  ], 3000));
  push(S("B.4", "Why it is hard"));
  push(lead("A good solution has to meet two goals at once: catch the fronts and protect honest merchants."));
  push(pairs(["Challenge", "Why it matters"], [
    ["Documents are fine", "It cannot be caught at onboarding; behaviour after onboarding has to be watched"],
    ["Each payment looks normal", "₹500 to a kirana store is not suspicious on its own"],
    ["Honest businesses change too", "Diwali rush, a restaurant screening IPL matches, a shop that starts delivery"],
    ["Too strict hurts real people", "Freezing a small shop's money can ruin it; India has millions of them"],
    ["Too lax lets fraud continue", "Plus regulatory penalties, as FIU-IND's fine on Paytm Payments Bank shows"],
    ["Fraudsters adapt", "They avoid round amounts, spread across many small accounts and rotate quickly"],
  ], 3000));
  push(note("Most existing systems focus on catching fraud and treat honest merchants as collateral damage. Trace treats both as goals."));

  // ------------------------------------------------------------------ C. Current solutions
  push(A("C", "Current solutions"));
  push(lead("Several tools already exist. Each covers part of the problem."));
  push(table(["Approach", "Who uses it", "What it does well", "Where it falls short"], [
    ["KYC at onboarding", "Every PA", "Checks identity and documents", "Fronts pass with genuine or forged documents; nothing is checked after day one"],
    ["\"Sales spike\" rules", "Many PAs and banks", "Simple and cheap", "Flagged 62% of honest sweet and electronics shops in Diwali week in our test"],
    ["Own-history anomaly detectors", "Common in fraud teams", "Spot sudden changes, so they catch rented accounts", "Miss fronts that bet from day one, because nothing changes (caught 20% of bad merchants)"],
    ["RBI MuleHunter.AI", "Banks", "Finds mule bank accounts", "Works on bank accounts, not PA merchants"],
    ["I4C Suspect Registry, DoT Financial Fraud Risk Indicator", "Banks, PAs, telecoms", "Shared lists of reported suspects", "Reactive: driven by complaints after the money has moved"],
    ["Website scanning (e.g. LegitScript)", "Card networks, global PAs", "Checks merchants' websites", "Built for card merchants with websites, not UPI kiranas"],
  ], [{ w: 1900 }, { w: 1700 }, { w: 2300 }, { w: 3126 }]));
  push(small("The 62% and 20% figures come from Trace's simulation (appendix L)."));

  // ------------------------------------------------------------------ D. Gap
  push(A("D", "The gap"));
  push(body("No current tool asks the question that matters for this problem: does this merchant's money match the business it " +
    "declared? The tools above either look only at documents, or compare a merchant only with its own past, or react after " +
    "complaints. Three things are missing:"));
  push(...bullets([
    ["Declared versus observed, against peers. ", "Nobody compares a merchant's behaviour with similar shops in the same week, adjusted for Indian seasons such as IPL and Diwali."],
    ["A graduated response. ", "Existing systems are mostly \"flag = freeze\". There is no middle ground between doing nothing and blocking a shop's money."],
    ["Links between fronts. ", "Fronts come in families that share phones, bank accounts and gamblers, but merchant-side tools rarely follow those links."],
  ]));
  push(lead("The cost of the gap shows up in both directions:"));
  push(table(["Failure", "Example from the simulation"], [
    ["Missed fronts", "An own-history detector catches 20% of bad merchants: it misses every front that bet from day one"],
    ["Honest shops disrupted", "A sales-spike rule alerts on 62% of honest sweet and electronics shops in Diwali week"],
  ], [{ w: 2800 }, { w: 6226 }]));
  push(note("Trace is designed to fill exactly these three gaps, and to feed existing systems such as FIU-IND, the I4C Suspect " +
    "Registry and MuleHunter rather than replace them."));

  // ------------------------------------------------------------------ E. Trace idea
  push(A("E", "Introducing Trace: the core idea"));
  push(S("E.1", "Declared versus observed"));
  push(body("Most fraud systems ask: \"Is this behaviour unusual?\" Trace asks: \"Does this behaviour match what the merchant " +
    "told us it is?\" At sign-up every merchant declares: a kirana store in Lucknow, small, expecting about ₹80,000 a month. " +
    "Trace then observes what actually happens. The gap between the two is the drift."));
  push(S("E.2", "Compare with peers, in the same week"));
  push(body("A finance analogy: a P/E of 40 is not high or low on its own; it is expensive for a bank and normal for a fast-growing " +
    "tech stock. Trace judges merchants the same way. \"60% of money arrives during cricket match hours\" is close to normal for " +
    "a restaurant, whose dinner trade overlaps evening matches, and very strange for a kirana, whose peers sit at about 10%."));
  push(body("Just as companies are compared in the same quarter, merchants are compared in the same week. When every sweet shop " +
    "triples its sales in Diwali week, the peer \"normal\" triples too, so no individual sweet shop looks odd. A peer group is the " +
    "same declared category and the same city tier; groups under 10 merchants fall back to the category across all tiers."));
  push(lead("Why not compare a merchant with its own past?"));
  push(table(["Case", "Own-history detector", "Peer comparison (Trace)"], [
    ["Sweet shop at Diwali", "Sales jumped: false alarm (62% of honest festive shops alerted)", "Peers jumped too: no alarm (1%)"],
    ["Front that bet from day one", "Nothing changed: missed", "Never looked like a kirana: caught"],
    ["Rented account", "Changed suddenly: caught", "Caught"],
  ], [{ w: 2400 }, { w: 3313 }, { w: 3313 }]));
  push(S("E.3", "Three ideas on top"));
  push(...bullets([
    ["Several signals must agree. ", "Trace measures ten signals, and each can push the score up by only a limited amount. A restaurant screening matches looks odd on one or two; a betting front looks odd on six or seven at once. One late payment is noise; late payments, maxed cards and a new job together are a pattern."],
    ["Fronts come in families. ", "One operator runs many fronts that share phones, bank accounts, gamblers and payout accounts. Fronts whose UPI IDs are posted on public betting pages are known bad, and merchants strongly linked to them inherit suspicion."],
    ["Ask before you punish. ", "Instead of flag = freeze, a ladder: Monitor, Ask (\"what's changed?\"), Friction (lower limits, slower settlement), Review (a 20% reserve and a human). Money is held only with a second, independent source of evidence."],
  ]));
  push(S("E.4", "The name"));
  push(body("Trace traces three things: the money back to the business the merchant declared, each front back to the known " +
    "betting accounts it is linked to, and every action back to a reason the merchant can read and answer."));

  // ------------------------------------------------------------------ F. Signals
  push(A("F", "The ten signals"));
  push(lead("Each signal is computed per merchant, per week. Only the risky direction counts: a kirana with fewer night sales than its peers is not suspicious. Typical values are medians from the simulation."));
  push(table(["#", "Signal", "How it is calculated", "Risky when", "Honest shop", "Betting front"], [
    ["1", "Match-hours share", "₹ received in live cricket match windows ÷ all ₹ (match weeks only)", "High", "~10% (kirana)", "~70%"],
    ["2", "Night share", "₹ received 11pm to 4am ÷ all ₹", "High", "~0%", "~45%"],
    ["3", "Round amounts", "% of payments that are exact multiples of ₹100", "High", "~5%", "~95%"],
    ["4", "Out-of-state payers", "% of payments from payers in another state", "High", "~3%", "~90%"],
    ["5", "Payments per customer", "Payments ÷ unique payers in the week", "High", "~1.5", "~2.3"],
    ["6", "Amount variety", "Spread of payment amounts (entropy, 0 to ~5)", "Low", "~4.3", "~2.8"],
    ["7", "Same-day pass-through", "Each day min(money in, money out), summed ÷ money in", "High", "~24%", "~78%"],
    ["8", "Payout accounts", "Different accounts the merchant pays out to", "High", "2 to 3", "~27"],
    ["9", "Sales growth", "This week vs median of its previous 8 weeks", "High", "~0%", "Varies"],
    ["10", "Size vs declared", "Monthly takings ÷ turnover declared at sign-up", "High", "~1x", "10x or more"],
  ], [{ w: 520 }, { w: 1700 }, { w: 3006 }, { w: 1000 }, { w: 1400 }, { w: 1400 }]));
  push(S("F.1", "Why each one"));
  push(...bullets([
    ["Match hours: ", "betting volume follows the cricket schedule; groceries do not."],
    ["Night: ", "kiranas close; online betting does not."],
    ["Round amounts: ", "bets are ₹500 or ₹1,000; groceries cost ₹137 or ₹284."],
    ["Out of state: ", "a Lucknow kirana serves Lucknow; a betting site's customers are all over India."],
    ["Repeat payments: ", "gamblers deposit again and again; shoppers buy once or twice a week."],
    ["Variety: ", "real baskets produce many different amounts; betting uses a menu of fixed stakes."],
    ["Pass-through: ", "betting pays winners almost immediately, so money does not rest. Like a cash conversion cycle near zero."],
    ["Payout accounts: ", "a shop pays a handful of suppliers; a front pays dozens of winners."],
    ["Growth: ", "sudden growth matters only relative to peers in the same week, which is how Diwali is excused."],
    ["Size vs declared: ", "a \"small kirana expecting ₹60,000 a month\" taking ₹6 lakh a week contradicts its own declaration."],
  ]));
  push(S("F.2", "Where honest businesses look similar"));
  push(lead("Honest merchants trip one or two signals; fronts trip many. That is why each signal is capped."));
  push(table(["Honest situation", "Signals it trips", "Why it usually stays at Monitor or Ask"], [
    ["Restaurant screening IPL matches", "Match hours, night, round set-menu prices", "Local customers, normal variety, no pass-through, no payout fan-out, no network links"],
    ["Kirana becoming a wholesaler", "Size, growth, round bulk orders, pass-through", "Local customers, few suppliers, normal hours"],
    ["Late-night delivery", "Night share", "Only one or two signals"],
    ["Online store shipping across India", "Out-of-state payers, growth", "Normal hours, normal amounts"],
    ["Diwali rush", "Growth", "Peers grow too, so the deviation is close to zero"],
  ], [{ w: 2600 }, { w: 2600 }, { w: 3826 }]));
  push(S("F.3", "Signals deliberately left out"));
  push(...bullets([
    ["Payment notes ", "(\"id\", \"bet\", \"deposit\"): powerful, but reading free text raises privacy issues. If added, keyword flags only, never stored text."],
    ["Refund and chargeback patterns: ", "the Parimatch case disguised payouts as refunds."],
    ["Website, maps presence and geotagged shop photos: ", "LegitScript-style checks for a later phase."],
  ]));

  // ------------------------------------------------------------------ G. Scoring
  push(A("G", "How the score works"));
  push(S("G.1", "Step 1: the peers' median and spread"));
  push(body("For every week, every peer group (for example, kiranas in tier-2 cities) and every signal, Trace takes the peers' " +
    "median, not the average, because a few fronts inside the group would drag an average up. Spread is the median absolute " +
    "deviation (MAD) × 1.4826, comparable to a standard deviation but immune to extremes. Each signal has a minimum spread, so " +
    "that a group where everyone is at 0% does not turn a tiny deviation into an infinite one."));
  push(S("G.2", "Step 2: a z-score for each signal"));
  push(code("z = (merchant's value − peer median) ÷ peer spread"));
  push(body("Example: kiranas in tier-1 cities in an IPL week have a median match-hours share of 10% and a spread of 5 points. " +
    "A front at 61% scores z = (61 − 10) ÷ 5 = 10.2."));
  push(S("G.3", "Step 3: risky direction only, capped, weighted"));
  push(code("points = weight × min( max(z in the risky direction, 0), 4 )"));
  push(body("The cap at 4 is the key design choice: the z of 10.2 above counts as 4. No single signal, however extreme, can condemn a " +
    "merchant; several have to agree. Weights are 1.2 for match hours and pass-through (the most betting-specific), 0.8 for " +
    "repeat payments and amount variety (noisier) and 1.0 for the rest."));
  push(S("G.4", "Step 4: add up and squash to 0 to 100"));
  push(code("drift score = 100 × (1 − e^(−raw points ÷ 15))"));
  push(table(["Raw points", "Roughly means", "Drift score"], [
    ["3", "Normal noise", "18"], ["14", "About 3 or 4 signals maxed out", "60 (Ask)"],
    ["21", "About 5 signals maxed out", "75 (Friction)"], ["35", "About 8 or 9 signals maxed out", "90 (Review zone)"],
  ], [{ w: 2000 }, { w: 4626 }, { w: 2400, align: RIGHT }]));
  push(body("A merchant's drift score is the average of its 3 worst weeks: one odd week is not enough, but a front active through " +
    "the IPL scores high."));
  push(S("G.5", "Step 5: the network score"));
  push(body("Merchants are joined by shared phones, bank accounts, customers and payout accounts. Trace runs a personalized " +
    "PageRank: a random walker follows these links (heavier ones more often) and, 15% of the time, jumps back to a known-bad " +
    "merchant. The share of time spent at each merchant measures how tightly it is tied to known betting accounts. A network " +
    "score of 50 or more counts as a network link, the corroboration needed for Review."));
  push(S("G.6", "Step 6: combine"));
  push(code("risk score = min(100, drift + 0.25 × network)"));
  push(body("A UPI ID on the known-bad list sets the risk score to at least 95. Behaviour is the main driver; the network adds up to 25 points and supplies the corroboration for the toughest action."));
  push(S("G.7", "Why not a big machine-learning model"));
  push(...bullets([
    ["No labels on day one. ", "Supervised models need thousands of confirmed fronts; a provider starting out has none. Peer comparison works without labels."],
    ["Explainability. ", "Every flag must come with a reason a merchant, a regulator and a court can understand: \"61% vs 10% for similar kirana stores\"."],
    ["Defensibility. ", "Rule-only systems produce many false positives, but opaque models are hard to defend. Trace is statistical and still explainable."],
  ]));
  push(body("Learning is layered on top once analysts' decisions provide labels (appendix H.2), without giving up explainability."));

  // ------------------------------------------------------------------ H. Advanced layers
  push(A("H", "The advanced layers"));
  push(S("H.1", "Change points: when did it change?"));
  push(body("For every merchant, Trace finds the single week that best splits its weekly score into a \"before\" and an \"after\" " +
    "(least squared error), like a structural-break test on a company's margins after a new CEO arrives. A rented account looks " +
    "honest for months and then flips; a shift in the same week as a phone and bank-account change is far stronger evidence " +
    "than either alone. Result: for all 10 rented accounts the detected week matched the real handover week exactly, and no " +
    "honest shop had a shift that coincided with an account change."));
  push(S("H.2", "Learning loop: learn from the analysts"));
  push(body("Every analyst decision to confirm or clear a case is a label. Once there are at least 5 of each, a logistic regression " +
    "learns which signals really separate confirmed fronts from cleared merchants, like a credit scorecard re-fitted on which " +
    "loans actually defaulted. Predictions are out-of-fold, so a merchant is never scored by a model that saw its own label. " +
    "It is a second opinion only: it can move a merchant from Monitor to Ask, never further on its own."));
  push(...fig("5_learned_weights.png", 2.48, "Hand-set weights vs weights learned from 82 simulated past reviews (50 confirmed, 32 cleared)"));
  push(note("The system corrected our own assumption. Match hours had the joint-highest hand-set weight, but honest restaurants " +
    "screening IPL matches have high match-hour shares too, so the learning loop gave it almost none. Out-of-state payers and " +
    "low amount variety matter most."));
  push(S("H.3", "Anomaly detector: what is odd that no rule covers?"));
  push(body("An Isolation Forest scores how easily each merchant's whole profile can be separated from everyone else's, with no " +
    "labels. Median anomaly percentile: honest shops 46, honest shops that changed 94, fronts 97, rented accounts 99. Unusual is " +
    "not the same as bad, so it is used only to choose which unflagged merchants to audit, never to penalise."));
  push(S("H.4", "Thresholds chosen in rupees"));
  push(body("A risk team enters what each mistake costs (a missed front ₹5 lakh, an honest merchant wrongly penalised ₹20,000, " +
    "analyst time ₹1,500 a case) and Trace finds the Friction threshold with the lowest expected cost, like setting a credit " +
    "cut-off from expected losses. On the demo data the cost is lowest (₹75,000, all of it review time) anywhere from 85 to 91."));
  push(S("H.5", "Stress test: what if fraudsters get smarter?"));
  push(body("Five fresh worlds of 400 merchants in which operators hide harder: genuine-looking cover traffic, amounts such as " +
    "₹499, separate phones and accounts, winners paid from other accounts, local gamblers and deposits during shop hours."));
  push(table(["Evasion", "Caught by full Trace", "Caught by behaviour alone", "Honest merchants penalised"], [
    ["0%", "100%", "100%", "0"], ["30% (default)", "100%", "100%", "0"], ["60%", "100%", "100%", "0"],
    ["80%", "100%", "90%", "0"], ["100%", "100%", "55%", "0"],
  ], [{ w: 2026 }, { w: 2300, align: RIGHT }, { w: 2400, align: RIGHT }, { w: 2300, align: RIGHT }]));
  push(...fig("7_stress_test.png", 2.14, "As operators hide better, behaviour alone degrades; the network and corroboration layers carry the load"));
  push(small("Caveat: even at 100% evasion the simulated fronts still share gamblers with known-bad fronts. A truly isolated operator would be much harder to catch."));
  push(S("H.6", "Network clusters"));
  push(body("Besides spreading suspicion from known-bad merchants, Trace finds communities of merchants densely linked to each " +
    "other (the Louvain method). Eight \"unrelated\" kiranas sharing gamblers and a bank account are a red flag even before any " +
    "of them appears on a known-bad list."));

  // ------------------------------------------------------------------ I. Actions, fairness, law
  push(A("I", "Actions, fairness and the law"));
  push(S("I.1", "The action ladder"));
  push(table(["Level", "Risk score", "What happens", "Cost to an honest merchant"], [
    ["0 Monitor", "Under 60", "Nothing visible", "None"],
    ["1 Ask", "60 to 75", "Neutral message: \"Your sales pattern has changed. Tell us what's new\", with a short form and an evidence upload", "Two minutes"],
    ["2 Friction", "75 to 90", "Lower limits; settlement slows from T+1 to T+2; payments keep working", "A one-day cash-flow delay"],
    ["3 Review", "90+ and a second source of evidence", "20% rolling reserve and a human investigator", "Real, so corroboration is required"],
    ["Offboard", "After human confirmation", "Account closed; STR filed with FIU-IND; identifiers shared with the I4C Suspect Registry", ""],
  ], [{ w: 1400 }, { w: 1800 }, { w: 3626 }, { w: 2200 }]));
  push(S("I.2", "Adjustments"));
  push(...bullets([
    ["No Review without corroboration. ", "A high behaviour score alone stops at Friction. Holding money needs a known-bad match, a network link or a GST mismatch."],
    ["Possible rental. ", "If both the phone and the settlement bank account change within 14 days, the merchant goes to at least Ask, and one level higher if network-linked."],
    ["Pre-declared changes. ", "A merchant who told Trace in advance (\"we started late-night delivery\") drops one level and is asked for evidence, unless network-linked, because ED cases show operators coach mules with scripted explanations."],
  ]));
  push(S("I.3", "Why a ladder rather than flag = freeze"));
  push(...bullets([
    ["Errors are inevitable. ", "A ladder makes a mistake cheap: an honest merchant gets a question, not a frozen account."],
    ["Legal proportionality. ", "The Supreme Court's Puttaswamy test expects the least intrusive measure that works."],
    ["Business sense. ", "Small merchants are the PA's customers; freezing them causes churn and bad press."],
    ["Better data. ", "Merchants' explanations and analysts' decisions become labels that improve the system."],
  ]));
  push(S("I.4", "Fair process and trust tiers"));
  push(...bullets([
    "Every flag has a reason in plain English, with peer numbers.",
    "72 hours to respond for Friction and above, and an appeal decided by a second analyst.",
    "A human reviews before any money is held.",
    "Random audits of unflagged merchants check what the system misses.",
  ]));
  push(body("Trust tiers reward honest merchants: a long record of matching their profile earns same-day settlement, higher " +
    "limits and lower fees (Gold). Loss aversion gives merchants a reason to keep their profile current, and fronts never reach " +
    "Gold because they are rotated before they build a history."));
  push(S("I.5", "Is monitoring legal?"));
  push(lead("Yes, and it is required. Privacy law limits how it is done, not whether."));
  push(pairs(["Law or rule", "What it means for Trace"], [
    ["RBI Payment Aggregator Directions (2025)", "PAs must monitor merchant transactions after onboarding and move merchants into higher due-diligence tiers based on patterns"],
    ["Prevention of Money Laundering Act", "Payment system operators are reporting entities: they must file suspicious transaction reports with FIU-IND, within 7 days of forming a suspicion"],
    ["Digital Personal Data Protection Act, 2023", "No general \"fraud prevention\" ground as in the GDPR; the basis is processing required by law (RBI, PMLA) plus the merchant agreement. Main provisions in force from 13 May 2027"],
  ], 3000));
  push(S("I.6", "Privacy by design"));
  push(...bullets([
    "Score the merchant, not the payer: payer data is used only in aggregate.",
    "Pseudonymised payer IDs and metadata only (amount, time, state); no payment-note text.",
    "Purpose limitation: never reused for marketing or credit.",
    "Proportionate escalation, human review and appeal before any hold.",
    "Audit logs of who accessed what.",
    "Known-bad list from public pages only, with provenance recorded.",
  ]));
  push(small("Not legal advice; the DPDP Act and the PA Directions should be checked by counsel before deployment."));

  // ------------------------------------------------------------------ J. Operations
  push(A("J", "Running Trace as an operation"));
  push(S("J.1", "Time to detection"));
  push(body("The whole year was replayed week by week using only what was known at each point: payments so far, network links " +
    "so far, known-bad IDs only once posted, and declarations and account changes only once they happened. It is a back-test " +
    "with no look-ahead."));
  push(table(["", "Penalised", "Median days", "90% within", "Slowest"], [
    ["Betting fronts", "40 of 40", "7", "14", "21"], ["Rented accounts (from the handover)", "10 of 10", "7", "8", "14"],
  ], [{ w: 3426 }, { w: 1400, align: RIGHT }, { w: 1400, align: RIGHT }, { w: 1400, align: RIGHT }, { w: 1400, align: RIGHT }]));
  push(body("Trace acts once a week, so 7 days is the fastest possible. Across all 37 weeks only 1 of 950 honest merchants was ever penalised in any week."));
  push(...fig("8_time_to_detection.png", 2.14, "Share of fronts and rented accounts penalised, by days since the betting started or the account changed hands"));
  push(S("J.2", "Case management"));
  push(body("Flags become cases with a lifecycle: Awaiting merchant (72-hour deadline), Under review, then Closed as confirmed or " +
    "cleared; a confirmed merchant can appeal to a second analyst, who decides within 7 days. Every step is in an audit log a " +
    "regulator can inspect, and every decision feeds the learning loop."));
  push(table(["Metric (simulated quarter)", "Value"], [
    ["Median time to a decision", "59 hours"], ["Merchants replying within 72 hours", "92%"],
    ["Decided cases cleared as genuine", "20%"], ["Appeals overturned (high = over-flagging)", "6%"],
  ], [{ w: 6226 }, { w: 2800, align: RIGHT }]));
  push(S("J.3", "Outside evidence and intelligence"));
  push(...bullets([
    ["GST cross-check. ", "UPI takings of 3× or more the turnover in GST returns contradict two official records. Fronts often have no GST registration; a rented account keeps the original shop's turnover. No honest merchant was flagged, and with it all 40 fronts reach Review."],
    ["Betting-page scanner. ", "Paste the text of a public betting page or Telegram post and Trace finds every UPI ID, including disguised ones (\"shop042 [at] okaxis\") and payment links. The example post revealed 4 fronts not yet on the known-bad list."],
    ["Consortium check. ", "Providers share keyed hashes (HMAC-SHA256) of offboarded merchants' bank accounts and phones, so a front cannot simply sign up elsewhere. In the demo 7 of 200 applicants at another provider were caught; a match triggers enhanced due diligence, not rejection. No raw data changes hands."],
  ]));
  push(S("J.4", "Reports and governance"));
  push(...bullets([
    ["Draft STRs ", "for FIU-IND, one per confirmed merchant: grounds for suspicion (the system's reasons), transactions, linked merchants, case history and action taken. Drafts for the Principal Officer, not FIU-IND's official electronic format."],
    ["I4C Suspect Registry file ", "with confirmed merchants' identifiers (confidential)."],
    ["Policy file and change log: ", "thresholds are policy, approved by the risk committee; every change records who, when, why and what changed."],
  ]));

  // ------------------------------------------------------------------ K. Data and method
  push(A("K", "Data and method"));
  push(S("K.1", "Why the main dataset is simulated"));
  push(...bullets([
    ["Real transaction-level UPI data is not public. ", "Individual payments are personal data, protected by bank secrecy and the DPDP Act."],
    ["Real data has no answer key. ", "Even a PA does not know which of its merchants are fronts it has not caught. In a simulation the fronts are planted, so detection can be measured exactly."],
  ]));
  push(body("The demo world has 1,000 merchants in 16 cities over 37 weeks (16 March to 29 November 2026), about 3 million UPI " +
    "payments, the IPL, a September cricket series and Diwali (8 November 2026). Hidden truth: 920 honest shops, 30 honest shops " +
    "whose business genuinely changed, 40 betting fronts and 10 rented accounts."));
  push(S("K.2", "What is real inside the simulation"));
  push(pairs(["Part", "Real source"], [
    ["Average payment size per category", "NPCI UPI statistics, July 2025; simulated averages match within 1%"],
    ["How fronts behave", "Enforcement Directorate cases (1xBet, Parimatch), the CUTS International report, press investigations: round deposits, match-time spikes, payers across India, quick payouts, rented accounts, shared devices"],
    ["Cricket calendar", "IPL dates and match times (7:30pm, weekend 3:30pm double-headers)"],
    ["Diwali", "The actual date and the category-specific rush (sweets, electronics)"],
    ["Cities, states, tiers", "Real Indian cities in tiers 1 to 3"],
  ], 3000));
  push(S("K.3", "Assumptions to defend"));
  push(table(["Assumption", "Value", "Why it is reasonable"], [
    ["Share of fronts / rented / honest drifters", "4% / 1% / 3%", "Illustrative; the Generate page changes it"],
    ["Bet sizes", "₹100 to ₹10,000, mostly ₹500 and ₹1,000", "Typical deposit menus on betting sites"],
    ["How hard fraudsters hide", "30% evasion by default", "Stress-tested from 0% to 100%"],
  ], [{ w: 3200 }, { w: 2626 }, { w: 3200 }]));
  push(S("K.4", "The reality check"));
  push(body("Before calibration, simulated restaurants averaged ₹503 per payment against a real ₹113 to ₹158, and electronics " +
    "₹3,750 against ₹1,093. After fixing this with the NPCI figures and re-running everything, the headline results did not " +
    "change: the method does not depend on guesses about payment sizes."));
  push(S("K.5", "Using a provider's real data"));
  push(body("The dashboard accepts CSV or Excel uploads with any column names and maps them automatically. The minimum is four " +
    "columns (merchant ID, category, time, amount); more columns switch on more signals. A provider can run Trace on its own data " +
    "in the first month of a pilot and measure precision through human review."));

  // ------------------------------------------------------------------ L. Results
  push(A("L", "Results"));
  push(S("L.1", "Headline comparison"));
  push(lead("Precision: of the merchants acted on, the share that were really bad. Recall: of the bad merchants, the share acted on. \"Penalised\" means Friction or above."));
  push(table(["System", "Bad merchants caught", "Precision of penalties", "Honest shops penalised", "Honest drifters penalised"], [
    ["A. Own-history only", "20%", "91%", "0 of 920", "1 of 30"],
    ["B. Peer drift score only", "100%", "89%", "0 of 920", "6 of 30"],
    ["C. Full Trace", "100%", "98%", "0 of 920", "1 of 30"],
  ], [{ w: 2426 }, { w: 1600, align: RIGHT }, { w: 1700, align: RIGHT }, { w: 1600, align: RIGHT }, { w: 1700, align: RIGHT }], { totals: [2] }));
  push(body("A catches only the 10 rented accounts, because they changed; it misses all 40 fronts. B catches everyone but penalises " +
    "6 honest shops whose business changed. C adds the network, declarations and corroboration, which drops penalties on honest " +
    "drifters from 6 to 1. Counting Ask as an action, Trace's precision is 79%: the honest drifters it acts on are mostly just asked to explain."));
  push(...fig("1_scores_by_label.png", 2.37, "Each dot is a merchant. Against its own past, fronts sit with honest shops; against peers, they separate clearly"));
  push(S("L.2", "Protecting honest merchants"));
  push(...fig("2_diwali_false_alarms.png", 2.14, "Share of honest sweet and electronics shops with a 'sales spike' alert: 62% in Diwali week with own-history comparison, about 1% with peers"));
  push(...fig("3_actions_by_label.png", 1.92, "What happens to each kind of merchant: all 920 honest shops stay at Monitor; fronts and rented accounts reach Review"));
  push(S("L.3", "Results in one table"));
  push(pairs(["Result", "Value"], [
    ["Bad merchants penalised", "100% (typical own-history detector: 20%)"],
    ["Honest shops penalised", "0 of 920"],
    ["Honest shops whose business changed, penalised", "1 of 30 (12 more only asked a question)"],
    ["Diwali false alarms (sales-spike rule)", "62% → 1%"],
    ["Fronts not on the known-bad list, linked by the network", "93%"],
    ["Rented accounts pinned to the exact handover week", "10 of 10"],
    ["Median days from the start of betting to a penalty", "7 (the fastest possible)"],
    ["Honest merchants ever penalised in any week", "1 of 950"],
    ["Behaviour alone at maximum evasion", "55% (full system: 100%)"],
    ["Appeal overturn rate (simulated quarter)", "6%"],
  ], 5000));
  push(note("These results come from a simulation calibrated to real NPCI category data and real enforcement cases. They show " +
    "that the method works as designed, not its real-world accuracy, which a pilot on a provider's own data would measure."));

  // ------------------------------------------------------------------ M. Costs (the financial appendix)
  push(A("M", "Implementation and running costs"));
  push(body("What it costs a payment aggregator to deploy and operate Trace. All figures are planning estimates in Indian rupees " +
    "(1 lakh = ₹1,00,000; 1 crore = ₹1,00,00,000), built from the assumptions in M.3. They are not vendor quotes; the model that " +
    "produces every table is explained/financials/model.py."));
  push(...finContent(lib, { prefix: "M.", base: 2, idp: "apM" }));

  // ------------------------------------------------------------------ N. Limitations and roadmap
  push(A("N", "Limitations and roadmap"));
  push(S("N.1", "Known limitations"));
  push(table(["Limitation", "Why it matters", "Mitigation"], [
    ["Synthetic data", "Results are cleaner than reality", "Pilot on real data; measure precision through human review"],
    ["Fronts and detector designed together", "Risk of finding only what was planted", "Evasion built in; random audits in real use"],
    ["Biased labels", "Analysts only see what the system flags", "Random audits and the anomaly-driven audit queue"],
    ["Very careful operators", "Behaviour alone catches 55% at maximum evasion", "Network, change points, consortium sharing"],
    ["Polluted peer groups", "If many shops in a city are fronts, \"normal\" shifts", "Median is robust; remove confirmed fronts from baselines"],
    ["Person-to-person payments", "Much betting money moves P2P", "Share flags with banks (MuleHunter) and NPCI"],
    ["Fake declarations", "Operators coach mules", "Declarations need evidence and are ignored when network-linked"],
    ["Legitimate pass-through businesses", "Wholesalers and aggregators pass money through", "Their own declared category and peer group"],
  ], [{ w: 2600 }, { w: 3013 }, { w: 3413 }]));
  push(S("N.2", "Rollout"));
  push(table(["Phase", "Timeline", "Build", "Depends on"], [
    ["1. Pilot", "0 to 6 months", "Data pipeline, drift score, ladder, review queue, appeals", "Provider's own data"],
    ["2. Enrich", "6 to 12 months", "Merchant portal, GST and Account Aggregator checks, takeover detection, public-page scanning, supervised model", "Merchant consent, GSTN API"],
    ["3. Ecosystem", "12 to 24 months", "Cross-provider sharing with hashed identifiers, I4C feeds, declared category shown to payers", "IDPIC or NPCI governance, RBI sandbox"],
  ], [{ w: 1500 }, { w: 1600 }, { w: 3726 }, { w: 2200 }]));
  push(S("N.3", "Metrics to track"));
  push(...bullets([
    "Flag precision, from human review",
    "False-positive rate on genuine merchants, and the appeal overturn rate",
    "Days from first anomaly to action",
    "Share of total payment volume under friction (the business cost)",
    "STRs filed and Suspect Registry submissions",
    "Churn among merchants who were flagged and then cleared",
  ]));

  // ------------------------------------------------------------------ O. Questions
  push(A("O", "Questions a judge or regulator may ask"));
  const qa = [
    ["Your data is simulated. How do you know it works?", "Real transaction data is confidential and has no answer key. A simulation lets us plant fronts and measure exactly, with deliberate evasion built in. The method needs no labels, so a provider can run it on its own data in the first pilot month and measure precision through human review."],
    ["Won't fraudsters adapt?", "Some will. No single signal is required, so dodging one is not enough. The signals that matter most are economic, not cosmetic: collecting bets means receiving money from many people across India around matches, and paying winners creates outflows. Analysts' decisions retrain the model, and random audits look for new patterns."],
    ["What about a genuine sports bar that is busy during the IPL?", "That is the restaurant-screening-matches case. It trips two or three signals, not six: local customers, normal amounts, no network links. Most stay at Monitor or Ask, and a declaration keeps them at Monitor."],
    ["How is this different from MuleHunter or the Suspect Registry?", "MuleHunter works on bank accounts, not PA merchants. The Suspect Registry is reactive, driven by complaints. Nobody compares declared with actual behaviour for UPI merchants with Indian seasonality, and nobody offers a graduated response. Trace feeds those systems rather than replacing them."],
    ["What does a false positive cost a merchant?", "At Ask, two minutes. At Friction, a one-day settlement delay. Holding money needs a second source of evidence and a human. The appeal overturn rate is tracked as a key metric."],
    ["Is this legal under the DPDP Act?", "Monitoring is required by the RBI's PA Directions and the PMLA, which is the legal basis. Trace scores merchants, not payers, pseudonymises payer IDs, uses metadata only and keeps audit logs."],
    ["How quickly does it act?", "Replayed week by week with no hindsight, fronts were penalised in a median of 7 days, the fastest possible for a weekly system, and all within 21 days."],
    ["What stops an offboarded merchant signing up elsewhere?", "Consortium tokens: providers share keyed hashes of offboarded merchants' bank accounts and phones, so a re-applicant is flagged at onboarding without any raw data changing hands."],
    ["What does it cost?", "For a mid-size PA with 20 lakh merchants, about ₹2.15 crore to implement and ₹1.88 crore a year to run, roughly ₹9 per merchant per year (appendix M)."],
  ];
  qa.forEach(([q, a], i) => { push(lib.heading(3, `O.${i + 1}`, q, `apO${i}`)); push(body(a)); });

  // ------------------------------------------------------------------ P. Glossary
  push(A("P", "Glossary"));
  push(pairs(["Term", "Meaning"], [
    ["UPI", "Unified Payments Interface: India's instant bank-to-bank payment system"],
    ["NPCI", "National Payments Corporation of India, which runs UPI"],
    ["Payment aggregator (PA)", "Company that collects payments for merchants and settles to them; regulated by the RBI"],
    ["P2M / P2P", "Person-to-merchant / person-to-person payments; a PA sees P2M"],
    ["Settlement, T+1, T+2", "Paying collected money to the merchant's bank the next day / two days later"],
    ["Rolling reserve", "Holding back a share of each settlement for a period as a safety buffer"],
    ["KYC", "Know Your Customer: identity and document checks"],
    ["Kirana", "Neighbourhood grocery store"],
    ["Mule account", "Account used to receive or move criminal money, often rented from a real person"],
    ["Front", "A merchant account pretending to be one business while processing payments for another"],
    ["FIU-IND", "Financial Intelligence Unit-India, which receives suspicious transaction reports"],
    ["STR", "Suspicious Transaction Report, filed with FIU-IND under the PMLA within 7 days of a suspicion"],
    ["ED", "Enforcement Directorate, which investigates money laundering"],
    ["I4C", "Indian Cyber Crime Coordination Centre, which runs the Suspect Registry"],
    ["DPDP Act", "Digital Personal Data Protection Act, 2023: India's privacy law"],
    ["Peer group", "Merchants with the same declared category and city tier"],
    ["Median, MAD", "Middle value; median absolute deviation, a spread measure that extremes cannot distort"],
    ["z-score", "How many typical spreads a value is from normal"],
    ["Drift", "The gap between declared and observed behaviour"],
    ["Precision / recall", "Share of flags that are right / share of bad cases flagged"],
    ["Personalized PageRank", "Spreads suspicion from known-bad merchants along shared phones, accounts and customers"],
    ["Logistic regression", "A simple, explainable model giving a probability from weighted inputs"],
    ["Out-of-fold", "Scoring each case with a model that never saw it, for honest accuracy"],
    ["Isolation Forest", "An anomaly detector: how easily can this case be separated from the rest?"],
    ["Change point", "The week a time series switches to a new level"],
    ["HMAC token", "A fingerprint of an identifier made with a secret key: matchable, not reversible without the key"],
  ], 2600));

  // ------------------------------------------------------------------ Q. Sources
  push(A("Q", "Sources"));
  push(...bullets([
    ["Enforcement Directorate ", "press releases on 1xBet (2025, 2026) and Parimatch"],
    ["CUTS International ", "report on UPI mule accounts and illegal gambling (2025), via MediaNama"],
    ["FIU-IND penalty on Paytm Payments Bank: ", "Tribune India and Moneylife (1 March 2024); PIB release via TaxGuru"],
    ["NPCI UPI ecosystem statistics: ", "npci.org.in/what-we-do/upi/upi-ecosystem-statistics; July 2025 figures via Business Standard (10 August 2025), SBI Research \"New Insights from UPI Data\" (18 August 2025), OfficeChai and The Head and Tale"],
    ["Reserve Bank of India: ", "Payment Aggregator Directions; press releases on monetary penalties on payment system operators"],
    ["Law: ", "Prevention of Money Laundering Act, 2002; Digital Personal Data Protection Act, 2023; K.S. Puttaswamy v. Union of India (2017)"],
    ["Cost inputs: ", "see appendix M.12"],
    ["Trace results: ", "reports/results.md and explained/ in the Trace repository"],
  ]));
  return c;
}

module.exports = { appendixContent };
