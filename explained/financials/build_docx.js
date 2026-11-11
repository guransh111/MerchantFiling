// Builds the financial appendix (Word) from results.json and the two charts.
// Usage: node build_docx.js <out.docx> [pages.json]
// pages.json maps heading ids to page numbers for the table of contents (found by rendering a first pass).
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, BorderStyle, ShadingType,
  AlignmentType, HeadingLevel, ImageRun, Footer, PageBreak, PositionalTab, PositionalTabAlignment,
  PositionalTabRelativeTo, PositionalTabLeader, InternalHyperlink, Bookmark, PageNumber, LevelFormat,
  TableLayoutType, Tab, TabStopType, TabStopPosition,
} = require("docx");

const HERE = __dirname;
const R = JSON.parse(fs.readFileSync(path.join(HERE, "results.json"), "utf8"));
const OUT = process.argv[2] || path.join(HERE, "Trace_Appendix_Financials.docx");
const PAGES = process.argv[3] && fs.existsSync(process.argv[3]) ? JSON.parse(fs.readFileSync(process.argv[3], "utf8")) : {};

const INK = "1C1C1F", INK2 = "4A4A52", MUTED = "6E6E76", LINE = "DCDDE2", HEAD = "F1F2F5", ACCENT = "1F5FAE", NOTE = "F3F6FB";
const FONT = "Arial";
const W = 9026; // A4 width minus 1" margins, in DXA
const LAKH = 1e5, CRORE = 1e7;
const A = R.assumptions;
const BASE = "Mid-size PA (base case)";
const S = R.scenarios, B = S[BASE];
const run = B.running, imp = B.implementation;

// ------------------------------------------------------------ number formats (Indian grouping)
const grp = (n, d = 0) => Number(n).toLocaleString("en-IN", { minimumFractionDigits: d, maximumFractionDigits: d });
const L = (v, d = 1) => grp(v / LAKH, d);                // in lakh, no symbol (for table columns headed "₹ lakh")
const cr = (v, d = 2) => `₹${grp(v / CRORE, d)} crore`;
const lakh = (v, d = 1) => `₹${grp(v / LAKH, d)} lakh`;
const rs = (v) => `₹${grp(v)}`;
const rs1 = (v) => `₹${grp(v, 1)}`;
const pct = (v, d = 0) => `${(v * 100).toFixed(d)}%`;

// ------------------------------------------------------------ building blocks
const t = (text, o = {}) => new TextRun({ text, font: FONT, ...o });
const p = (children, o = {}) => new Paragraph({ children: typeof children === "string" ? [t(children)] : children,
  spacing: { after: 120, line: 288 }, ...o });
const body = (text) => p([t(text, { color: INK })]);
const small = (text) => p([t(text, { size: 17, color: MUTED })], { spacing: { before: 0, after: 200 } });
const bullet = (children) => new Paragraph({ children: typeof children === "string" ? [t(children)] : children,
  numbering: { reference: "bullets", level: 0 }, spacing: { after: 80, line: 276 } });
const strong = (text) => t(text, { bold: true });

let tocEntries = [];
const BREAK_BEFORE = new Set(["2", "3", "4", "5", "8", "9"]);
function heading(level, num, text, id) {
  tocEntries.push({ level, num, text, id });
  return new Paragraph({
    heading: level === 1 ? HeadingLevel.HEADING_1 : HeadingLevel.HEADING_2,
    children: [new Bookmark({ id, children: [t(`${num}  ${text}`)] })],
    pageBreakBefore: level === 1 && BREAK_BEFORE.has(num),
    spacing: level === 1 && !BREAK_BEFORE.has(num) && num !== "1" ? { before: 480, after: 200 } : undefined,
  });
}

const border = { style: BorderStyle.SINGLE, size: 4, color: LINE };
const borders = { top: border, bottom: border, left: border, right: border };
function cell(text, width, o = {}) {
  const { bold = false, fill, align = AlignmentType.LEFT, color = INK, size = 18, topRule = false, keepNext = false } = o;
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    borders: topRule ? { ...borders, top: { style: BorderStyle.SINGLE, size: 10, color: INK2 } } : borders,
    shading: fill ? { fill, type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 70, bottom: 70, left: 110, right: 110 },
    children: [new Paragraph({ alignment: align, spacing: { after: 0, line: 264 }, keepNext,
      children: [t(String(text), { bold, color, size })] })],
  });
}
// cols: [{w, align}] ; rows: array of arrays ; opts.total = index of total rows
function table(header, rows, cols, opts = {}) {
  const totals = new Set(opts.totals || []);
  const hdr = new TableRow({ tableHeader: true, cantSplit: true, children: header.map((h, i) =>
    cell(h, cols[i].w, { bold: true, fill: HEAD, align: cols[i].align || AlignmentType.LEFT, color: INK2, size: 17, keepNext: true })) });
  const keep = rows.length <= 12;
  const body = rows.map((r, ri) => new TableRow({ cantSplit: true, children: r.map((c, i) =>
    cell(c, cols[i].w, { align: cols[i].align || AlignmentType.LEFT, bold: totals.has(ri), topRule: totals.has(ri),
      keepNext: keep && ri < rows.length - 1 })) }));
  return [new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: cols.map((c) => c.w),
    layout: TableLayoutType.FIXED, rows: [hdr, ...body] }), new Paragraph({ children: [], spacing: { after: 100 } })];
}
const RIGHT = AlignmentType.RIGHT;
const gap = () => new Paragraph({ children: [], spacing: { after: 60 } });

function note(children) {
  return new Paragraph({
    children: typeof children === "string" ? [t(children, { color: INK2, size: 19 })] : children,
    shading: { fill: NOTE, type: ShadingType.CLEAR, color: "auto" },
    border: { left: { style: BorderStyle.SINGLE, size: 18, color: ACCENT, space: 8 } },
    indent: { left: 160, right: 160 }, spacing: { before: 120, after: 200, line: 288 },
  });
}
function image(file, wIn, hIn) {
  return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 60 },
    children: [new ImageRun({ type: "png", data: fs.readFileSync(path.join(HERE, file)),
      transformation: { width: wIn * 96, height: hIn * 96 } })] });
}
const caption = (text) => p([t(text, { size: 17, color: MUTED })], { alignment: AlignmentType.CENTER, spacing: { after: 200 } });

// ------------------------------------------------------------ derived figures
const lines = run.lines;
const linesTotal = run.total;
const people = lines["Analyst desk"] + lines["Model and engineering team"];
const an = run.analysts;
const val = R.value;
const yearsToBreakEven = 1 / B.penalties_to_break_even;
const scen = Object.entries(S);

// ------------------------------------------------------------ content
const content = [];

// 1 Summary
content.push(heading(1, "1", "Summary", "s1"));
content.push(body(`For a mid-size payment aggregator (PA) with 20 lakh active merchants, Trace costs about ${cr(imp.total)} ` +
  `to implement over ${R.impl_months} months and about ${cr(run.total)} a year to run. That is roughly ` +
  `${rs1(run.per_merchant)} per merchant per year, or ${rs(run.per_case)} for every case an analyst handles.`));
content.push(...table(["Measure (mid-size PA, base case)", "Value"], [
  [`One-time implementation (${R.impl_months} months)`, cr(imp.total)],
  ["Annual running cost", cr(run.total)],
  ["Running cost per active merchant", `${rs1(run.per_merchant)} a year`],
  ["Running cost per case handled", rs(run.per_case)],
  ["Analysts needed", `${an.analysts} analysts and ${an.leads} team lead`],
  ["Annual cost with the build spread over 5 years", cr(B.annual_all_in)],
  ["Five-year cost of ownership (build plus five years)", cr(R.five_year_total)],
  ["Break-even", `One FIU-IND-scale penalty (${cr(A.fiu_penalty)}) avoided every ${yearsToBreakEven.toFixed(1)} years`],
], [{ w: 5226 }, { w: 3800, align: RIGHT }]));
content.push(gap());
content.push(p([strong("What the numbers say")], { spacing: { before: 120, after: 80 } }));
content.push(bullet(`People are most of the cost. The analyst desk and the model team are ${pct(people / linesTotal)} of the ` +
  `running cost; cloud and data are ${pct(lines["Cloud and data"] / linesTotal)}.`));
content.push(bullet(`The cost per merchant falls with scale: ${rs1(S["Small PA"].running.per_merchant)} a year for a small PA, ` +
  `${rs1(run.per_merchant)} for a mid-size one and ${rs1(S["Large PA"].running.per_merchant)} for a large one.`));
content.push(bullet("The biggest unknown is how many merchants reach a case each year. Halving or doubling it moves the " +
  "running cost more than any other assumption (section 7)."));
content.push(bullet(`Trace pays for itself if it prevents one penalty of the size FIU-IND imposed on Paytm Payments Bank ` +
  `every ${yearsToBreakEven.toFixed(1)} years, before counting about ${lakh(val.inr_saved)} a year of analyst time saved ` +
  `or the honest merchants it keeps out of trouble (section 9).`));

// 2 Scope
content.push(heading(1, "2", "Scope and approach", "s2"));
content.push(heading(2, "2.1", "Who implements Trace", "s21"));
content.push(body("The buyer is a payment aggregator authorised by the Reserve Bank of India: the company that onboards " +
  "merchants, collects their UPI payments and settles the money to their bank accounts. Under the RBI's Payment " +
  "Aggregator directions and the Prevention of Money Laundering Act, it must know what its merchants really do, so " +
  "monitoring is an obligation, not an option."));
content.push(body("A PA already runs KYC at onboarding and has a compliance team. Every cost in this appendix is " +
  "incremental: what Trace adds on top of what the PA already spends."));
content.push(heading(2, "2.2", "What is included", "s22"));
content.push(p([strong("Included")], { spacing: { after: 60 } }));
[
  "Building Trace into the PA's systems: data pipelines, the ten weekly signals, peer scoring, the network, change points, the learning loop, case management, the GST check and regulator reports",
  "A three-month shadow pilot in which Trace scores merchants without acting, so its flags can be checked first",
  "Running it: cloud, the team that maintains the models, and the analysts who work the cases Trace opens",
  "Security testing, a data-protection impact assessment, legal review of merchant notices and appeals, and training",
].forEach((x) => content.push(bullet(x)));
content.push(p([strong("Not included")], { spacing: { before: 120, after: 60 } }));
[
  "The PA's existing KYC, onboarding and compliance staff, which it pays for today with or without Trace",
  "Person-to-person UPI transfers, which never reach a PA; those are watched by banks and NPCI (for example, RBI's MuleHunter.AI)",
  "Revenue effects of offboarding merchants. Most small UPI merchants pay no merchant discount rate, so losing a front costs a PA little revenue",
  "Litigation, if a merchant takes a decision to court",
].forEach((x) => content.push(bullet(x)));
content.push(heading(2, "2.3", "Three sizes of payment aggregator", "s23"));
content.push(body("Costs are worked out for three sizes. The mid-size PA is the base case used throughout."));
content.push(...table(["Scenario", "Active merchants", "Payments a year", "History kept (5 years)"],
  scen.map(([n, s]) => [n, grp(s.merchants), `${grp(s.running.cloud.payments_year / 1e9, 1)} billion`,
    `${grp(s.running.cloud.stored_gb / 1000, 1)} TB`]),
  [{ w: 2826 }, { w: 2000, align: RIGHT }, { w: 2100, align: RIGHT }, { w: 2100, align: RIGHT }]));
content.push(small(`Payments a year assume ${A.payments_per_day} payments per merchant per day. History is stored compressed ` +
  `(about ${A.bytes} bytes per payment) for ${A.retention} years, the PMLA record-keeping period.`));

// 3 Assumptions
content.push(heading(1, "3", "Key assumptions", "s3"));
content.push(body("Every figure in this appendix follows from the assumptions below. Changing one and re-running the model " +
  "(explained/financials/model.py) regenerates every table."));
content.push(heading(2, "3.1", "General", "s31"));
content.push(...table(["Assumption", "Value", "Basis"], [
  ["Exchange rate", `₹${A.fx} per US$`, "USD/INR ranged from 88.6 to 89.7 in November 2025; rounded up for caution"],
  ["Overhead on salaries", pct(A.overhead), "Office, laptops, recruiting and software seats on top of cost to company"],
  ["Productive hours per analyst", `${grp(A.analyst_hours)} a year`, "About 220 working days of 7.7 hours"],
  ["Contingency on implementation", pct(A.contingency), "Standard allowance for integration surprises"],
  ["Build spread over", `${A.amortise} years`, "Used only for the all-in annual cost and break-even"],
  ["Growth in the five-year view", `${pct(A.merchant_growth)} merchants, ${pct(A.salary_growth)} salaries a year`, "Planning assumption"],
], [{ w: 2600 }, { w: 2226 }, { w: 4200 }]));
content.push(heading(2, "3.2", "Salaries", "s32"));
content.push(body("Annual cost to company in India. Market surveys put the average data scientist at roughly ₹7 to ₹14 lakh " +
  "and mid-level at ₹8 to ₹20 lakh; fintech and senior roles pay more, so the figures below sit at the upper end. " +
  "Anti-money-laundering analysts have a median of about ₹5 to ₹6 lakh."));
content.push(...table(["Role", "₹ lakh a year"], Object.entries(A.salary).map(([r, v]) => [r, L(v)]),
  [{ w: 6226 }, { w: 2800, align: RIGHT }]));
content.push(heading(2, "3.3", "Workload", "s33"));
content.push(...table(["Assumption", "Value", "Basis"], [
  ["Merchants reaching a case each year", pct(A.case_rate, 1), "Share that reach Ask or above; the real rate is unknown, so section 7 tests 0.5% to 2%"],
  ...A.case_mix.map(([step, share, mins]) => [step, `${pct(share)} of cases, ${mins} min`, step.startsWith("Review") ?
    "Includes the investigation and drafting the STR" : step.startsWith("Ask") ? "Reading the merchant's reply and closing" : "Checking evidence and setting limits"]),
  ["Appeals", `${pct(A.appeal_rate)} of Friction and Review cases, ${A.appeal_minutes} min`, "Decided by a second analyst"],
  ["Random audits", `${pct(A.audit_rate, 2)} of merchants, ${A.audit_minutes} min`, "Unflagged merchants, to find new patterns"],
  ["Analysts per team lead", String(A.analysts_per_lead), "Span of control"],
], [{ w: 3200 }, { w: 2626 }, { w: 3200 }]));
content.push(heading(2, "3.4", "Cloud prices", "s34"));
content.push(body("On-demand list prices in AWS Mumbai (ap-south-1). Only the m6i.2xlarge price is taken from a published " +
  "price list; the others are approximate and should be checked in the AWS pricing calculator before a budget is approved."));
content.push(...table(["Resource", "US$ per hour", "Used for"], [
  ["m6i.2xlarge (8 vCPU, 32 GB)", A.price["m6i.2xlarge"].toFixed(3), "Weekly signals and scoring"],
  ["r6i.4xlarge (16 vCPU, 128 GB), approx.", A.price["r6i.4xlarge"].toFixed(3), "Network graph and learning loop"],
  ["m6i.xlarge (4 vCPU, 16 GB)", A.price["m6i.xlarge"].toFixed(3), "Dashboard, case management, APIs"],
  ["Managed Kafka broker, approx.", A.price["kafka.broker"].toFixed(3), "Streaming payment feed"],
  ["Managed PostgreSQL, two zones, approx.", A.price["postgres.multiaz"].toFixed(3), "Cases and results"],
  ["Object storage", `${A.price["s3.gb_month"]} per GB-month`, "Payment history"],
], [{ w: 3826 }, { w: 1800, align: RIGHT }, { w: 3400 }]));

// 4 Implementation
content.push(heading(1, "4", "Implementation cost (one-time)", "s4"));
content.push(body(`Implementation takes ${R.impl_months} months and costs about ${cr(imp.total)} for the base case. ` +
  `People are ${pct(imp.team_total / imp.subtotal)} of it.`));
content.push(heading(2, "4.1", "Timeline", "s41"));
content.push(...table(["Phase", "Months", "What happens"],
  [...R.phases.map(([n, m, w]) => [n, String(m), w]), ["Total", String(R.impl_months), ""]],
  [{ w: 2500 }, { w: 1000, align: RIGHT }, { w: 5526 }], { totals: [R.phases.length] }));
content.push(small("Merchants are only acted on after the shadow pilot, and money is held only after compliance signs off."));
content.push(heading(2, "4.2", "Team", "s42"));
content.push(...table(["Role", "People", "Months", "₹ lakh"],
  [...imp.team.map((x) => [x.role, grp(x.people, x.people % 1 ? 1 : 0), String(x.months), L(x.inr)]),
    ["Team total", "", "", L(imp.team_total)]],
  [{ w: 4626 }, { w: 1300, align: RIGHT }, { w: 1300, align: RIGHT }, { w: 1800, align: RIGHT }], { totals: [imp.team.length] }));
content.push(small(`Includes ${pct(A.overhead)} overhead. The three risk analysts label past cases to seed the learning loop and check the pilot's flags.`));
content.push(heading(2, "4.3", "Other one-time costs", "s43"));
content.push(...table(["Item", "₹ lakh", "Note"],
  [...imp.other.map((o) => [o.item, L(o.inr), o.note]), ["Other total", L(imp.other_total), ""]],
  [{ w: 3826 }, { w: 1300, align: RIGHT }, { w: 3900 }], { totals: [imp.other.length] }));
content.push(heading(2, "4.4", "Total implementation cost", "s44"));
content.push(...table(["Component", "₹ lakh"], [
  ["Team", L(imp.team_total)], ["Other one-time costs", L(imp.other_total)], ["Subtotal", L(imp.subtotal)],
  [`Contingency (${pct(A.contingency)})`, L(imp.contingency)], ["Total implementation cost", L(imp.total)],
], [{ w: 6226 }, { w: 2800, align: RIGHT }], { totals: [2, 4] }));
content.push(small(`About ${cr(imp.total)}. A small PA pays almost the same (${cr(S["Small PA"].implementation.total)}) because ` +
  `the build work does not shrink with the number of merchants; section 10 covers cheaper routes for smaller PAs.`));

// 5 Running
content.push(heading(1, "5", "Running cost (annual)", "s5"));
content.push(heading(2, "5.1", "Overview", "s51"));
content.push(body(`Running Trace costs about ${cr(run.total)} a year for the base case.`));
content.push(image("chart_running.png", 6.2, 2.33));
content.push(caption("Annual running cost by component, mid-size PA"));
content.push(...table(["Component", "₹ lakh a year", "Share"],
  [...Object.entries(lines).map(([k, v]) => [k, L(v), pct(v / linesTotal)]), ["Total running cost", L(linesTotal), "100%"]],
  [{ w: 5226 }, { w: 2200, align: RIGHT }, { w: 1600, align: RIGHT }], { totals: [Object.keys(lines).length] }));
content.push(heading(2, "5.2", "Cloud and data", "s52"));
content.push(...table(["Item", "Basis", "US$ a year", "₹ lakh"],
  [...run.cloud.rows.map((r) => [r.item, r.basis, grp(r.usd), L(r.inr)]),
    ["Cloud total", "", grp(run.cloud.usd), L(run.cloud.inr)]],
  [{ w: 2900 }, { w: 3326 }, { w: 1500, align: RIGHT }, { w: 1300, align: RIGHT }], { totals: [run.cloud.rows.length] }));
content.push(small("On-demand prices. Committing to one-year reserved capacity typically cuts compute cost by about 30% (section 10). " +
  "Trace needs no GPUs: its models are statistics, graph algorithms and a logistic regression."));
content.push(heading(2, "5.3", "Model and engineering team", "s53"));
content.push(body("A small permanent team keeps the data flowing, retrains the learning loop, tunes thresholds with " +
  "compliance and maintains the dashboard."));
content.push(...table(["Role", "Full-time equivalent", "₹ lakh a year"],
  [...run.team.map((x) => [x.role, grp(x.fte, 2), L(x.inr)]), ["Team total", "", L(lines["Model and engineering team"])]],
  [{ w: 4826 }, { w: 2200, align: RIGHT }, { w: 2000, align: RIGHT }], { totals: [run.team.length] }));
content.push(heading(2, "5.4", "Analyst desk", "s54"));
content.push(body(`With ${pct(A.case_rate, 1)} of ${grp(B.merchants)} merchants reaching a case, analysts handle about ` +
  `${grp(an.cases)} cases a year, at an average of ${an.minutes_per_case.toFixed(1)} minutes each.`));
content.push(...table(["Work", "A year", "Minutes each", "Hours"],
  [...an.rows.map((r) => [r.item, grp(r.count), grp(r.minutes), grp(r.hours)]), ["Total", "", "", grp(an.hours)]],
  [{ w: 4626 }, { w: 1500, align: RIGHT }, { w: 1500, align: RIGHT }, { w: 1400, align: RIGHT }], { totals: [an.rows.length] }));
content.push(body(`${grp(an.hours)} hours ÷ ${grp(A.analyst_hours)} productive hours = ${an.analysts} analysts, plus ` +
  `${an.leads} team lead, costing ${lakh(an.cost)} a year with overhead.`));
content.push(note("Most cases are light. Six in ten are a neutral question that the merchant answers; only the 15% that " +
  "reach Review need a full investigation. That is the action ladder working as a cost control as well as a fairness one."));
content.push(heading(2, "5.5", "Audit, software and other", "s55"));
content.push(p([t(`Fixed yearly items, plus GST lookups at about ${rs(A.gst_lookup)} each for every flagged merchant and again for Review cases.`)], { keepNext: true }));
content.push(...table(["Item", "₹ lakh a year"],
  [...run.other.map((o) => [o.item, L(o.inr)]), ["Total", L(lines["Audit, software and other"])]],
  [{ w: 6226 }, { w: 2800, align: RIGHT }], { totals: [run.other.length] }));

// 6 Scale
content.push(heading(1, "6", "Costs at different scales", "s6"));
content.push(body("Fixed costs (the team, the always-on systems, the build) are spread over more merchants as a PA grows, " +
  "so the cost per merchant falls sharply. Analyst cost grows roughly in line with merchants."));
const sc = scen.map(([, s]) => s);
content.push(...table(["Measure", ...scen.map(([n]) => n.replace(" (base case)", ""))], [
  ["Active merchants", ...sc.map((s) => grp(s.merchants))],
  ["Implementation (₹ crore)", ...sc.map((s) => grp(s.implementation.total / CRORE, 2))],
  ["Running cost (₹ crore a year)", ...sc.map((s) => grp(s.running.total / CRORE, 2))],
  ["Running cost per merchant (₹ a year)", ...sc.map((s) => grp(s.running.per_merchant, 1))],
  ["Cases a year", ...sc.map((s) => grp(s.running.analysts.cases))],
  ["Analysts and leads", ...sc.map((s) => `${s.running.analysts.analysts} + ${s.running.analysts.leads}`)],
  ["All-in annual cost, build over 5 years (₹ crore)", ...sc.map((s) => grp(s.annual_all_in / CRORE, 2))],
  ["Years between avoided FIU-scale penalties to break even", ...sc.map((s) => grp(1 / s.penalties_to_break_even, 1))],
], [{ w: 3626 }, { w: 1800, align: RIGHT }, { w: 1800, align: RIGHT }, { w: 1800, align: RIGHT }]));
content.push(small("The mid-size column is the base case. A large PA also gets a second database, more app servers and one more engineer."));

// 7 Sensitivity
content.push(heading(1, "7", "Sensitivity", "s7"));
content.push(p([t(`How the base case's annual running cost (${cr(run.total)}) changes when one assumption moves and the rest stay put.`)], { keepNext: true }));
content.push(...table(["Driver", "Low case", "₹ crore a year", "High case", "₹ crore a year"],
  R.sensitivity.map((x) => [x.driver, x.low_case, grp(x.low / CRORE, 2), x.high_case, grp(x.high / CRORE, 2)]),
  [{ w: 2926 }, { w: 1600 }, { w: 1300, align: RIGHT }, { w: 1900 }, { w: 1300, align: RIGHT }]));
const caseS = R.sensitivity[0];
content.push(body(`The share of merchants reaching a case matters most: at 2% the running cost rises to ${cr(caseS.high)}, ` +
  `at 0.5% it falls to ${cr(caseS.low)}. This is why the shadow pilot comes first: it measures the real rate before ` +
  `analysts are hired. Cloud prices matter least, because Trace needs little computing.`));

// 8 Five-year
content.push(heading(1, "8", "Five-year cost of ownership", "s8"));
content.push(body(`Building Trace and running it for five years costs about ${cr(R.five_year_total)} for the base case, assuming ` +
  `merchants grow ${pct(A.merchant_growth)} and salaries ${pct(A.salary_growth)} a year.`));
content.push(image("chart_five_year.png", 6.2, 2.52));
content.push(caption("Cost per year, mid-size PA. Year 0 is the build; years 1 to 5 are running costs"));
content.push(...table(["Year", "Merchants", "Analysts", "Implementation (₹ lakh)", "Running (₹ lakh)", "Total (₹ lakh)"],
  [...R.five_year.map((y) => [y.year, y.merchants ? grp(y.merchants) : "", y.analysts ? String(y.analysts) : "",
    y.implementation ? L(y.implementation) : "", y.running ? L(y.running) : "", L(y.implementation + y.running)]),
    ["Five-year total", "", "", "", "", L(R.five_year_total)]],
  [{ w: 1626 }, { w: 1500, align: RIGHT }, { w: 1100, align: RIGHT }, { w: 1700, align: RIGHT }, { w: 1500, align: RIGHT },
    { w: 1600, align: RIGHT }], { totals: [R.five_year.length] }));
content.push(small("Steps in the curve come from hiring whole people: a ninth analyst also brings a second team lead."));

// 9 Value
content.push(heading(1, "9", "Value and break-even", "s9"));
content.push(body("Trace's value to a PA is mostly risk avoided, which is hard to price exactly. The three parts below are " +
  "shown separately so that each can be judged on its own."));
content.push(heading(2, "9.1", "Regulatory exposure", "s91"));
content.push(body(`In March 2024, FIU-IND fined Paytm Payments Bank ${cr(A.fiu_penalty)} under the PMLA after law enforcement ` +
  "found that proceeds of online gambling had been routed through accounts at the bank. The RBI can also fine payment " +
  "system operators up to ₹10 lakh or twice the amount involved, whichever is higher, and can restrict or withdraw a " +
  "PA's authorisation, a far larger cost that is not priced here."));
content.push(heading(2, "9.2", "Analyst time", "s92"));
content.push(body(`In the simulation, ${pct(A.precision_trace)} of the merchants Trace acts on are really fronts or rented ` +
  `accounts, against ${pct(A.precision_baseline)} for a typical detector that compares a merchant only with its own history. ` +
  `Finding the same ${grp(val.true_cases)} bad merchants with the typical detector would mean reviewing about ` +
  `${grp(val.baseline_alerts)} alerts instead of ${grp(an.cases)}: ${grp(val.fewer_reviews)} fewer reviews, ` +
  `${grp(val.hours_saved)} hours, or about ${grp(val.analysts_saved, 1)} analysts (${lakh(val.inr_saved)} a year).`));
content.push(note("This saving is generous to the typical detector: in the simulation it found only 20% of the bad merchants, " +
  "so in practice it could not find the same number at any price. The figures come from synthetic data and show the " +
  "method working as designed, not real-world accuracy."));
content.push(heading(2, "9.3", "Honest merchants protected", "s93"));
content.push(body("A common 'sales spike' rule flagged 62% of honest sweet and electronics shops in Diwali week; comparing " +
  "each shop with similar shops in the same week cut that to 1%. No ordinary honest shop of 920 was penalised. Each " +
  "wrongly frozen shop is a complaint, a lost customer and a story in the press; this value is real but not priced here."));
content.push(heading(2, "9.4", "Break-even", "s94"));
content.push(...table(["Measure", ...scen.map(([n]) => n.replace(" (base case)", ""))], [
  ["All-in annual cost (₹ crore)", ...sc.map((s) => grp(s.annual_all_in / CRORE, 2))],
  ["FIU-scale penalties to avoid per year", ...sc.map((s) => grp(s.penalties_to_break_even, 2))],
  ["Break-even: one avoided penalty every", ...sc.map((s) => `${grp(1 / s.penalties_to_break_even, 1)} years`)],
], [{ w: 3626 }, { w: 1800, align: RIGHT }, { w: 1800, align: RIGHT }, { w: 1800, align: RIGHT }]));
content.push(body(`For the base case, Trace breaks even if it prevents one penalty the size of FIU-IND's ${cr(A.fiu_penalty)} ` +
  `every ${yearsToBreakEven.toFixed(1)} years, before counting analyst time saved or honest merchants protected.`));

// 10 Lower cost
content.push(heading(1, "10", "Ways to lower the cost", "s10"));
[
  [`Reserved cloud capacity. `, `A one-year commitment cuts compute by about 30%, around ${lakh(run.cloud.inr * 0.3)} a year for the base case.`],
  ["Measure before hiring. ", "Use the shadow pilot's real case rate to size the analyst desk instead of hiring for the base-case estimate."],
  ["Automate the Ask step. ", "Most cases are a neutral question; sending it and reading simple replies automatically shrinks the largest group of cases."],
  ["Start with the riskiest categories. ", "Roll out first to categories and cities where fronts cluster, then widen."],
  ["Share the build. ", "Several smaller PAs could share one Trace service, with consortium tokens keeping their merchant data separate. A small PA would then pay a share of the build instead of the full cost."],
  ["Keep the stack open-source. ", "Trace runs on Python, pandas, scikit-learn and networkx, so there are no model licence fees."],
].forEach(([a, b]) => content.push(bullet([strong(a), t(b)])));

// 11 Limitations
content.push(heading(1, "11", "Limitations", "s11"));
[
  "These are planning estimates, not quotes. Salaries vary by city and seniority, and cloud prices change; most cloud prices here are approximate.",
  "The real share of merchants that reach a case is unknown until the pilot runs. Section 7 shows its effect.",
  "Value figures from the simulation (precision, Diwali false alarms) come from synthetic data calibrated to real NPCI category statistics. They show the method working as designed, not real-world accuracy.",
  "UPI pricing is changing. Reports in 2026 describe a 0.4% merchant discount rate on payments above ₹2,000; this appendix does not depend on it.",
  "Regulatory penalties are uncertain events. The break-even figure is a yardstick, not a forecast.",
].forEach((x) => content.push(bullet(x)));

// 12 Sources
content.push(heading(1, "12", "Sources", "s12"));
[
  ["Salaries: ", "Scaler, Data Scientist Salary in India 2025 (scaler.com/blog/data-scientist-salary-in-india); Hero Vired (herovired.com/learning-hub/blogs/data-scientist-salary); Payscale, Anti-Money Laundering Analyst salary in India (payscale.com); Salary.com, KYC AML Analyst salary in India; AmbitionBox, AML Compliance Analyst salary"],
  ["Cloud: ", "DoIT, AWS EC2 m6i.2xlarge pricing in ap-south-1 (doit.com/compute/spot/ap-south-1/m6i.2xlarge)"],
  ["Exchange rate: ", "ValutaFX daily USD/INR history, November 2025; VT Markets, USD/INR near 88.85 (14 November 2025)"],
  ["FIU-IND penalty: ", "Tribune India and Moneylife, Financial Intelligence Unit imposes ₹5.49 crore fine on Paytm Payments Bank (1 March 2024); PIB release via TaxGuru"],
  ["RBI penalty framework: ", "RBI press releases on monetary penalties on payment system operators; Upstox, RBI tightens rules: ₹10 lakh fine and daily penalties for payment system violations"],
  ["UPI pricing: ", "Inc42, MDR on UPI is here, but who foots the bill? (2026); PIB, incentive scheme for low-value BHIM-UPI transactions (2025)"],
  ["Trace results: ", "reports/results.md in this repository (synthetic world of 1,000 merchants, 37 weeks)"],
].forEach(([a, b]) => content.push(bullet([strong(a), t(b, { color: INK2 })])));

// ------------------------------------------------------------ title page and table of contents
const title = [
  new Paragraph({ spacing: { before: 2400, after: 120 }, children: [t("TRACE", { size: 20, color: ACCENT, bold: true, characterSpacing: 40 })] }),
  new Paragraph({ spacing: { after: 200 }, children: [t("Appendix: Implementation and Running Costs", { size: 52, bold: true, color: INK })] }),
  new Paragraph({ spacing: { after: 600 }, children: [t("What it costs a payment aggregator to deploy and operate Trace, with every assumption stated",
    { size: 26, color: INK2 })] }),
  new Paragraph({ border: { top: { style: BorderStyle.SINGLE, size: 6, color: LINE, space: 12 } }, spacing: { after: 80 },
    children: [t("Merchant Legitimacy Challenge", { size: 20, color: INK2 })] }),
  new Paragraph({ spacing: { after: 800 }, children: [t("November 2026", { size: 20, color: MUTED })] }),
  note([t("All figures are planning estimates in Indian rupees (1 lakh = ₹1,00,000; 1 crore = ₹1,00,00,000), built from the " +
    "assumptions in section 3. They are not vendor quotes. The model that produces every table is " +
    "explained/financials/model.py in the Trace repository.", { color: INK2, size: 19 })]),
  new Paragraph({ children: [new PageBreak()] }),
];

function tocLine(e) {
  const page = PAGES[e.id] != null ? String(PAGES[e.id]) : "00";
  const lvl1 = e.level === 1;
  return new Paragraph({
    spacing: { before: lvl1 ? 140 : 40, after: 40 },
    tabStops: [{ type: TabStopType.RIGHT, position: W, leader: "dot" }],
    indent: { left: lvl1 ? 0 : 440 },
    children: [new InternalHyperlink({ anchor: e.id, children: [
      t(`${e.num}  ${e.text}`, { bold: lvl1, color: lvl1 ? INK : INK2, size: lvl1 ? 21 : 19 }),
      new TextRun({ font: FONT, bold: lvl1, color: lvl1 ? INK : INK2, size: lvl1 ? 21 : 19, children: [new Tab(), page] }),
    ] })],
  });
}
const toc = [
  new Paragraph({ spacing: { after: 240 }, children: [t("Contents", { size: 36, bold: true, color: INK })] }),
  ...tocEntries.map(tocLine),
];

// ------------------------------------------------------------ document
const footer = new Footer({ children: [new Paragraph({ border: { top: { style: BorderStyle.SINGLE, size: 4, color: LINE, space: 6 } },
  children: [t("Trace · Appendix: Implementation and running costs", { size: 16, color: MUTED }),
    new TextRun({ font: FONT, size: 16, color: MUTED, children: [new Tab(), PageNumber.CURRENT] })],
  tabStops: [{ type: TabStopType.RIGHT, position: W }] })] });

const doc = new Document({
  creator: "Trace", title: "Trace: Appendix, Implementation and Running Costs",
  styles: {
    default: { document: { run: { font: FONT, size: 21, color: INK } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 34, bold: true, color: INK },
        paragraph: { spacing: { before: 0, after: 200 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 24, bold: true, color: ACCENT },
        paragraph: { spacing: { before: 320, after: 120 }, keepNext: true, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
    alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 440, hanging: 260 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1300, bottom: 1300, left: 1440, right: 1440 } },
      titlePage: true },
    footers: { default: footer, first: new Footer({ children: [new Paragraph({ children: [] })] }) },
    children: [...title, ...toc, new Paragraph({ children: [new PageBreak()] }), ...content],
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(OUT, buf);
  fs.writeFileSync(OUT.replace(/\.docx$/, ".toc.json"), JSON.stringify(tocEntries));
  console.log("wrote", OUT);
});
