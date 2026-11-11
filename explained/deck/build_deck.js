// Trace pitch deck (PowerPoint). Every visual is drawn with native, editable shapes in the dashboard's colours.
// Usage: NODE_PATH=<dir with pptxgenjs, react-icons, react, react-dom, sharp> node build_deck.js <out.pptx>
// Figures: reports/results.md (simulated world, 1,000 merchants, 37 weeks), data/real/ (NPCI), and
// explained/financials/results.json (costs). Speaker notes carry what to say on each slide.
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const LU = require("react-icons/lu");

const OUT = process.argv[2] || path.join(__dirname, "..", "Trace_Deck.pptx");
const FIN = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "financials", "results.json"), "utf8"));
const BASE = FIN.scenarios["Mid-size PA (base case)"];

// ------------------------------------------------------------------ look
// dark graphite like the dashboard; ladder colours from the Home animation; one blue accent
const HEX = {
  BG: "111113", PANEL: "1A1A1D", RAISED: "222226", LINE: "2A2A2F", TRACK: "2C2C31",
  INK: "EDEDEF", INK2: "A1A1A8", MUTED: "85858D",
  GREY: "6B6B70", BLUE: "6490D8", GOLD: "C4904A", ORANGE: "D4784A", RED: "C4605E",
};
const THEME = {
  name: "Trace",
  headFontFace: "Arial",
  bodyFontFace: "Arial",
  colors: {
    dk1: HEX.INK, lt1: HEX.BG, dk2: HEX.INK2, lt2: HEX.PANEL,
    accent1: HEX.BLUE, accent2: HEX.GOLD, accent3: HEX.ORANGE, accent4: HEX.RED, accent5: HEX.GREY, accent6: HEX.MUTED,
    hlink: HEX.BLUE, folHlink: HEX.INK2,
  },
};
const MONO = "Consolas";
const LADDER = [HEX.GREY, HEX.BLUE, HEX.GOLD, HEX.ORANGE, HEX.RED];
const LADDER_NAME = ["Monitor", "Ask", "Friction", "Review", "Offboard"];

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
pres.title = "Trace";
pres.author = "Trace";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;
const SW = 13.333, M = 0.6, CW = SW - 2 * M;

// ------------------------------------------------------------------ layouts
// CARD: the Home panel's anatomy. Section number top-left, the drawing in the top two-thirds, a mono caption,
// a hairline, then a bold title and one line of text.
pres.defineSlideMaster({
  title: "CARD",
  background: { color: HEX.BG },
  objects: [
    { line: { x: M, y: 5.5, w: CW, h: 0, line: { color: HEX.LINE, width: 1 } } },
    { text: { text: "Trace", options: { x: M, y: 7.02, w: 3, h: 0.3, fontFace: MONO, fontSize: 10, color: HEX.MUTED, margin: 0 } } },
    { placeholder: { options: { name: "kicker", type: "body", x: M, y: 0.42, w: 9, h: 0.36, fontFace: MONO, fontSize: 13, color: HEX.MUTED, margin: 0, valign: "middle" }, text: "" } },
    { placeholder: { options: { name: "caption", type: "body", x: M, y: 4.98, w: CW, h: 0.42, fontFace: MONO, fontSize: 14, color: HEX.MUTED, margin: 0, valign: "middle" }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: M, y: 5.68, w: CW, h: 0.62, fontSize: 28, bold: true, color: HEX.INK, margin: 0, valign: "middle", align: "left" }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: M, y: 6.36, w: CW, h: 0.56, fontSize: 16, color: HEX.INK2, margin: 0, valign: "top" }, text: "" } },
  ],
  slideNumber: { x: SW - M - 0.6, y: 7.02, w: 0.6, h: 0.3, fontFace: MONO, fontSize: 10, color: HEX.MUTED, align: "right" },
});
// COVER: title and closing slides
pres.defineSlideMaster({
  title: "COVER",
  background: { color: HEX.BG },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 3.0, w: CW, h: 1.2, fontSize: 72, bold: true, color: HEX.INK, margin: 0, valign: "middle", align: "left" }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: M, y: 4.3, w: 9.2, h: 1.0, fontSize: 22, color: HEX.INK2, margin: 0, valign: "top" }, text: "" } },
  ],
});

// ------------------------------------------------------------------ drawing helpers
const tx = (s, text, o) => s.addText(text, { isTextBox: true, margin: 0, fontFace: "Arial", color: HEX.INK, ...o });
const mono = (s, text, o) => tx(s, text, { fontFace: MONO, ...o });
const rect = (s, x, y, w, h, fill, o = {}) => s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: fill }, line: { type: "none" }, ...o });
const rrect = (s, x, y, w, h, fill, r, o = {}) => s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: r, fill: { color: fill }, line: { type: "none" }, ...o });
const panel = (s, x, y, w, h, name) => rrect(s, x, y, w, h, HEX.PANEL, 0.12, { line: { color: HEX.LINE, width: 1 }, objectName: name });
const dot = (s, cx, cy, r, fill, name) => s.addShape(pres.shapes.OVAL, { x: cx - r, y: cy - r, w: 2 * r, h: 2 * r, fill: { color: fill }, line: { type: "none" }, objectName: name });
const ring = (s, cx, cy, r, color, name, width = 1.75) => s.addShape(pres.shapes.OVAL, { x: cx - r, y: cy - r, w: 2 * r, h: 2 * r, fill: { type: "none" }, line: { color, width }, objectName: name });
function line(s, x1, y1, x2, y2, color, width = 1.5, name, o = {}) {
  s.addShape(pres.shapes.LINE, { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.max(Math.abs(x2 - x1), 0.001), h: Math.max(Math.abs(y2 - y1), 0.001),
    flipV: (x2 - x1) * (y2 - y1) < 0, line: { color, width, ...o }, objectName: name });
}
// a labelled bar on a track, like the dashboard's thin bars
function bar(s, x, y, w, h, frac, color, name) {
  rrect(s, x, y, w, h, HEX.TRACK, h / 2, { objectName: name + " track" });
  rrect(s, x, y, Math.max(h, w * frac), h, color, h / 2, { objectName: name });
}
async function icon(name, color, px = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(LU[name], { color: "#" + color, size: px, strokeWidth: 1.5 }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}
function card(sectionTitle, kicker) {
  const s = pres.addSlide({ masterName: "CARD", sectionTitle });
  s.addText(kicker, { placeholder: "kicker" });
  return s;
}
const fill = (s, { caption, title, body }) => {
  if (caption) s.addText(caption, { placeholder: "caption" });
  s.addText(title, { placeholder: "title" });
  if (body) s.addText(body, { placeholder: "body" });
};

// The Trace mark: a big merchant and a small one tied to it ("follow the links")
function mark(s, x, y, size, color, name = "Trace mark") {
  const k = size / 159; // drawn in the intro's 159-unit box
  const P = (u, v) => [x + (u - 74) * k, y + (v - 41) * k];
  const [bx, by] = P(122, 148), [sx, sy] = P(200, 74);
  line(s, bx, by, sx, sy, color, 14 * k * 72, name + " stem");
  dot(s, bx, by, 44 * k, color, name + " big");
  dot(s, sx, sy, 29 * k, color, name + " small");
}

// ------------------------------------------------------------------ slides
async function build() {
  const ICON = {
    phone: await icon("LuSmartphone", HEX.INK2), bank: await icon("LuLandmark", HEX.INK2), store: await icon("LuStore", HEX.INK2),
    lock: await icon("LuLock", HEX.INK), storeRed: await icon("LuStore", HEX.RED), check: await icon("LuCheck", HEX.INK2),
  };

  // 1 ── Title
  pres.addSection({ title: "Trace" });
  {
    const s = pres.addSlide({ masterName: "COVER", sectionTitle: "Trace" });
    mark(s, M, 1.35, 1.35, HEX.INK);
    s.addText("Trace", { placeholder: "title" });
    s.addText("Finds UPI merchants whose money doesn't match the business they declared, without punishing honest shops",
      { placeholder: "body" });
    mono(s, "Merchant Legitimacy Challenge  ·  November 2026", { x: M, y: 6.7, w: 8, h: 0.35, fontSize: 12, color: HEX.MUTED });
    s.addNotes("Trace. One sentence: it finds UPI merchants whose money doesn't match the business they declared, without punishing honest shops. " +
      "Everything that follows is that sentence, unpacked.");
  }

  // flow geometry shared by slides 2 and 3, so Morph carries the picture across
  const F = { y: 2.95, cust: 4.6, pa: 7.75, bank: 11.4 };

  // 2 ── 01 Current context
  pres.addSection({ title: "01 Current context" });
  {
    const s = card("01 Current context", "01   Current context");
    mono(s, "3,033", { x: M, y: 1.6, w: 3.6, h: 1.0, fontSize: 66, bold: true, color: HEX.INK, objectName: "big figure" });
    tx(s, "million UPI payments to grocery stores in a single month", { x: M, y: 2.65, w: 3.3, h: 0.7, fontSize: 15, color: HEX.INK2, objectName: "big figure label" });
    mono(s, "₹64,882 crore", { x: M, y: 3.5, w: 3.3, h: 0.4, fontSize: 18, color: HEX.BLUE, objectName: "value" });
    // flow: customer -> payment provider -> shop's bank, with money dots on the wires
    line(s, F.cust + 0.45, F.y, F.pa - 1.15, F.y, HEX.LINE, 2, "wire 1");
    line(s, F.pa + 1.15, F.y, F.bank - 0.45, F.y, HEX.LINE, 2, "wire 2");
    [0.25, 0.5, 0.75].forEach((f, i) => dot(s, F.cust + 0.45 + (F.pa - 1.6 - F.cust) * f, F.y, 0.07, HEX.BLUE, `money a${i}`));
    [0.3, 0.65].forEach((f, i) => dot(s, F.pa + 1.15 + (F.bank - 1.6 - F.pa) * f, F.y, 0.07, HEX.BLUE, `money b${i}`));
    ring(s, F.cust, F.y, 0.45, HEX.LINE, "customer node", 1.5);
    s.addImage({ data: ICON.phone, x: F.cust - 0.22, y: F.y - 0.22, w: 0.44, h: 0.44, objectName: "customer icon" });
    tx(s, "Customer scans a QR", { x: F.cust - 1.0, y: F.y + 0.6, w: 2.0, h: 0.35, fontSize: 13, color: HEX.INK2, align: "center" });
    panel(s, F.pa - 1.15, F.y - 0.95, 2.3, 1.9, "provider node");
    tx(s, "Payment provider", { x: F.pa - 1.0, y: F.y - 0.8, w: 2.0, h: 0.35, fontSize: 14, bold: true, align: "center" });
    ["Onboards the shop", "Collects payments", "Settles next day"].forEach((t, i) =>
      tx(s, t, { x: F.pa - 1.0, y: F.y - 0.32 + i * 0.36, w: 2.0, h: 0.3, fontSize: 12, color: HEX.INK2, align: "center" }));
    ring(s, F.bank, F.y, 0.45, HEX.LINE, "shop node", 1.5);
    s.addImage({ data: ICON.store, x: F.bank - 0.22, y: F.y - 0.22, w: 0.44, h: 0.44, objectName: "shop icon" });
    tx(s, "Kirana's bank account", { x: F.bank - 1.0, y: F.y + 0.6, w: 2.0, h: 0.35, fontSize: 13, color: HEX.INK2, align: "center", objectName: "shop label" });
    fill(s, {
      caption: "NPCI, July 2025: grocery stores, the biggest UPI merchant category",
      title: "India pays its kiranas by UPI, through a payment provider",
      body: "The provider onboards the shop, collects its payments and settles them, and must know what the shop really does",
    });
    s.addNotes("Start with how normal this is. In July 2025 grocery stores alone received 3,033 million UPI payments worth about 65 thousand crore rupees. " +
      "Most of that money passes through a payment provider: it onboards the shop, collects the payments and settles the money the next day. " +
      "Under the RBI's payment aggregator rules and the anti-money-laundering law, that provider is responsible for knowing what its merchants really do.");
  }

  // 3 ── 02 Problem: some shops aren't shops
  pres.addSection({ title: "02 Problem" });
  {
    const s = card("02 Problem", "02   Problem");
    // gamblers from all over India converge on one "shop", and the money fans straight out again
    const shopX = 6.3, shopY = 2.75;
    let seed = 7; const rnd = () => ((seed = (seed * 9301 + 49297) % 233280) / 233280);
    for (let i = 0; i < 22; i++) {
      const gx = M + 0.2 + rnd() * 4.6, gy = 1.25 + rnd() * 2.9;
      line(s, gx, gy, shopX, shopY, HEX.LINE, 1, `bet line ${i}`);
      dot(s, gx, gy, 0.075, HEX.RED, `gambler ${i}`);
    }
    for (let i = 0; i < 7; i++) {
      const ox = shopX + 2.2 + (i % 2) * 0.45, oy = 1.4 + i * 0.45;
      line(s, shopX, shopY, ox, oy, HEX.LINE, 1, `payout line ${i}`);
      dot(s, ox, oy, 0.06, HEX.GOLD, `payout ${i}`);
    }
    dot(s, shopX, shopY, 0.52, HEX.BG, "shop mask");
    ring(s, shopX, shopY, 0.52, HEX.RED, "shop node", 2);
    s.addImage({ data: ICON.storeRed, x: shopX - 0.24, y: shopY - 0.24, w: 0.48, h: 0.48, objectName: "shop icon" });
    tx(s, "“Kirana”", { x: shopX - 1.0, y: shopY + 0.62, w: 2.0, h: 0.35, fontSize: 14, bold: true, color: HEX.INK, align: "center", objectName: "shop label" });
    tx(s, "Gamblers across India", { x: M + 0.2, y: 4.35, w: 3.5, h: 0.3, fontSize: 12, color: HEX.MUTED });
    tx(s, "Paid out the same night", { x: shopX + 1.7, y: 4.35, w: 3.0, h: 0.3, fontSize: 12, color: HEX.MUTED });
    // proof, quietly on the right
    const px = 10.5;
    [["6,000+", "mule accounts in the 1xBet case (ED)"], ["#1", "UPI is the main deposit channel for illegal betting (CUTS, 2025)"]].forEach(([a, b], i) => {
      mono(s, a, { x: px, y: 1.35 + i * 1.45, w: 2.3, h: 0.6, fontSize: 32, bold: true, color: HEX.INK });
      tx(s, b, { x: px, y: 1.95 + i * 1.45, w: 2.3, h: 0.7, fontSize: 12, color: HEX.INK2 });
    });
    fill(s, {
      caption: "Real documents pass onboarding; the QR code is posted on betting sites and Telegram",
      title: "Some of these shops aren't shops",
      body: "Betting operators open merchant accounts as ordinary kiranas, or rent real ones, and move the money on overnight",
    });
    s.addNotes("Now the problem. Online betting is illegal in most of India, but operators still need to collect deposits. " +
      "They open merchant accounts as ordinary shops with genuine documents, post the QR code on betting sites and Telegram, and gamblers from all over India pay 'the kirana'. " +
      "The money goes straight out again to winners and the operator. Some operators rent real shops' accounts instead. " +
      "In the 1xBet case the Enforcement Directorate found more than six thousand mule accounts, and CUTS reports UPI is now the main deposit channel for illegal betting. " +
      "Getting this wrong is costly both ways: FIU-IND fined Paytm Payments Bank 5.49 crore over gambling money, but freezing an honest shop in Diwali week can ruin it.");
  }

  // grid shared by slides 4 and 5 (Morph shrinks it to make room for the numbers)
  const TOOLS = ["KYC at onboarding", "Sales-spike rules", "Own-history detectors", "MuleHunter (banks)", "Suspect Registry"];
  const NEEDS = ["Checks documents", "Watches behaviour", "Compares with similar shops", "Follows links", "Responds in steps"];
  const COVER = [[1, 0, 0, 0, 0], [0, 1, 0, 0, 0], [0, 1, 0, 0, 0], [0, 1, 0, 1, 0], [0, 0, 0, 1, 0]];
  function grid(s, gx, gy, gw, rowH, labelW, withTrace) {
    const colW = (gw - labelW) / NEEDS.length;
    if (withTrace) [2, 4].forEach((c) => rrect(s, gx + labelW + c * colW + 0.04, gy - 0.05, colW - 0.08, rowH * (TOOLS.length + 2) + 0.1, "1B2433", 0.08, { objectName: `gap column ${c}` }));
    NEEDS.forEach((n, c) => tx(s, n, { x: gx + labelW + c * colW, y: gy, w: colW, h: rowH, fontSize: withTrace ? 11 : 13, color: HEX.INK2, align: "center", valign: "middle", objectName: `need ${c}` }));
    const rows = withTrace ? [...TOOLS, "Trace"] : TOOLS;
    rows.forEach((t, r) => {
      const y = gy + rowH * (r + 1), isT = t === "Trace";
      line(s, gx, y, gx + gw, y, HEX.LINE, 0.75, `row rule ${r}`);
      tx(s, t, { x: gx, y, w: labelW, h: rowH, fontSize: withTrace ? 12 : 15, bold: isT, color: isT ? HEX.INK : HEX.INK, valign: "middle", objectName: `tool ${r}` });
      NEEDS.forEach((_, c) => {
        const cx = gx + labelW + c * colW + colW / 2, cy = y + rowH / 2, on = isT || COVER[r][c];
        if (on) dot(s, cx, cy, 0.11, isT ? HEX.BLUE : HEX.INK2, `cell ${r}-${c}`);
        else ring(s, cx, cy, 0.11, HEX.GREY, `cell ${r}-${c}`, 1.25);
      });
    });
  }

  // 4 ── 03 Current solutions
  pres.addSection({ title: "03 Current solutions" });
  {
    const s = card("03 Current solutions", "03   Current solutions");
    grid(s, M, 1.0, CW, 0.62, 3.4, false);
    fill(s, {
      caption: "● covers it    ○ doesn't",
      title: "Today's tools each see part of the picture",
      body: "None compares a shop with similar shops, and none responds in steps between doing nothing and freezing",
    });
    s.addNotes("These are the tools providers and banks use today. KYC checks documents at onboarding, but fronts pass with real documents. " +
      "Sales-spike rules and own-history detectors watch behaviour, but only against the shop's own past. MuleHunter, the RBI's tool, works on bank accounts, not merchants, and the Suspect Registry lists accounts after people complain. " +
      "Look at the two empty columns: nobody compares a shop with similar shops, and nobody responds in steps.");
  }

  // 5 ── 04 The gap
  pres.addSection({ title: "04 The gap" });
  {
    const s = card("04 The gap", "04   The gap");
    grid(s, M, 1.0, 7.3, 0.5, 2.15, true);
    const sx = 8.55;
    [["20%", "of bad merchants caught by a typical detector: it misses every front that bet from day one", HEX.RED],
     ["62%", "of honest sweet and electronics shops flagged by a sales-spike rule in Diwali week", HEX.GOLD]].forEach(([n, l, col], i) => {
      panel(s, sx, 1.0 + i * 1.9, SW - M - sx, 1.7, `gap stat ${i}`);
      mono(s, n, { x: sx + 0.3, y: 1.15 + i * 1.9, w: 2.2, h: 0.8, fontSize: 44, bold: true, color: col });
      tx(s, l, { x: sx + 0.3, y: 1.95 + i * 1.9, w: SW - M - sx - 0.6, h: 0.65, fontSize: 12, color: HEX.INK2 });
    });
    fill(s, {
      caption: "Simulated world of 1,000 merchants, calibrated to real NPCI data",
      title: "They miss the fronts or punish the honest",
      body: "The missing pieces: compare each shop with similar shops, follow the links, and respond in steps",
    });
    s.addNotes("That gap has a cost in both directions. A typical detector that compares a shop with its own past catches only 20 percent of bad merchants, because a front that bet from day one never changes. " +
      "A sales-spike rule flags 62 percent of honest sweet and electronics shops in Diwali week. Those two numbers are the two ways to fail: too lax and too strict. Trace fills exactly the empty columns, shown in blue.");
  }

  // 6 ── 05 Introducing Trace
  pres.addSection({ title: "05 Introducing Trace" });
  {
    const s = card("05 Introducing Trace", "05   Introducing Trace");
    panel(s, M, 1.0, 3.5, 3.7, "declared card");
    mono(s, "Declared", { x: M + 0.3, y: 1.25, w: 3, h: 0.3, fontSize: 12, color: HEX.MUTED });
    s.addImage({ data: ICON.store, x: M + 0.3, y: 1.7, w: 0.5, h: 0.5 });
    tx(s, "Kirana store", { x: M + 0.95, y: 1.72, w: 2.4, h: 0.45, fontSize: 20, bold: true, valign: "middle" });
    [["City", "Pune, tier 2"], ["Expects", "₹48,000 a month"], ["Peers", "Kiranas in tier-2 cities"]].forEach(([a, b], i) => {
      tx(s, a, { x: M + 0.3, y: 2.55 + i * 0.6, w: 1.0, h: 0.3, fontSize: 12, color: HEX.MUTED });
      tx(s, b, { x: M + 1.25, y: 2.55 + i * 0.6, w: 2.1, h: 0.3, fontSize: 13, color: HEX.INK2 });
    });
    const ox = M + 3.9, ow = SW - M - ox;
    mono(s, "Observed: share of money received during cricket match hours", { x: ox, y: 1.25, w: ow, h: 0.3, fontSize: 12, color: HEX.MUTED });
    tx(s, "This kirana", { x: ox, y: 1.85, w: 4, h: 0.4, fontSize: 18 });
    mono(s, "57%", { x: ox + ow - 1.6, y: 1.8, w: 1.6, h: 0.5, fontSize: 28, bold: true, align: "right" });
    bar(s, ox, 2.42, ow, 0.26, 0.57 / 0.57, HEX.ORANGE, "this shop bar");
    tx(s, "Similar kiranas, same week", { x: ox, y: 3.05, w: 4.5, h: 0.4, fontSize: 18 });
    mono(s, "10%", { x: ox + ow - 1.6, y: 3.0, w: 1.6, h: 0.5, fontSize: 28, bold: true, align: "right", color: HEX.INK2 });
    bar(s, ox, 3.62, ow, 0.26, 0.10 / 0.57, HEX.GREY, "peers bar");
    fill(s, {
      caption: "Like judging a P/E against its sector: 40 is expensive for a bank and normal for a tech stock",
      title: "Does this shop's money match the business it declared?",
      body: "Every merchant is compared with similar shops in the same week, so a Diwali rush looks normal and a front doesn't",
    });
    s.addNotes("This is Trace. Instead of asking 'is this unusual?', it asks 'does this match what the merchant told us it is?'. " +
      "This kirana in Pune declared itself a small grocery expecting 48 thousand rupees a month. 57 percent of its money arrives during cricket match hours; similar kiranas in the same week sit at 10. " +
      "It's like judging a P/E ratio against its sector. And because the comparison is with similar shops in the same week, a Diwali rush lifts everyone together and nobody looks strange.");
  }

  // 7 ── 06 What Trace does: the Home panel's three ideas, with the results underneath
  pres.addSection({ title: "06 What Trace does" });
  {
    const s = card("06 What Trace does", "06   What Trace does");
    const pw = (CW - 0.6) / 3, top = 1.0, ch = 2.8;
    const cards = [
      ["01", "Compare with peers", "A front trips 7 of 10 signals"],
      ["02", "Follow the links", "93% of unlisted fronts found"],
      ["03", "Ask before you punish", "937 of 1,000 see no action"],
    ];
    cards.forEach(([n, title, fig], i) => {
      const x = M + i * (pw + 0.3), ix = x + 0.3, iw = pw - 0.6;
      panel(s, x, top, pw, ch, `idea card ${i}`);
      mono(s, n, { x: ix, y: top + 0.15, w: 0.6, h: 0.28, fontSize: 12, color: HEX.MUTED });
      if (i === 0) {
        // ten signals: a restaurant screening matches lights 2, a betting front lights 7
        const sq = 0.24, g = (iw - 10 * sq) / 9;
        [["Restaurant screening matches", 2, "2 of 10"], ["Betting front", 7, "7 of 10"]].forEach(([lab, k, cnt], r) => {
          const y = top + 0.5 + r * 0.62;
          tx(s, lab, { x: ix, y, w: iw - 0.8, h: 0.24, fontSize: 11, color: HEX.INK2 });
          mono(s, cnt, { x: ix + iw - 0.8, y, w: 0.8, h: 0.24, fontSize: 11, bold: true, align: "right" });
          for (let q = 0; q < 10; q++) rrect(s, ix + q * (sq + g), y + 0.27, sq, sq, q < k ? HEX.ORANGE : HEX.TRACK, 0.04, { objectName: `signal ${r}-${q}` });
        });
      }
      if (i === 1) {
        // a small network around one known betting account
        const cx = x + pw / 2, cy = top + 1.05;
        [[-1.15, -0.4], [-0.95, 0.4], [0.75, -0.48], [1.05, 0.3], [-0.1, 0.55]].forEach(([dx, dy], k) => {
          line(s, cx, cy, cx + dx, cy + dy, HEX.TRACK, 1.5, `net link ${k}`); dot(s, cx + dx, cy + dy, 0.1, HEX.ORANGE, `net front ${k}`);
        });
        dot(s, cx, cy, 0.2, HEX.RED, "net known bad");
        ring(s, x + pw - 0.45, top + 0.45, 0.09, HEX.GREY, "net honest a", 1.25);
        ring(s, ix + 0.1, top + 1.55, 0.09, HEX.GREY, "net honest b", 1.25);
      }
      if (i === 2) {
        // the ladder, with how many merchants sit on each step
        const counts = [937, 12, 2, 49, 0], bw = iw / 5, base = top + 1.75;
        LADDER.forEach((col, k) => {
          const h = 0.18 + k * 0.17;
          rrect(s, ix + k * bw + 0.03, base - h, bw - 0.06, h, col, 0.04, { objectName: `ladder ${k}` });
          mono(s, counts[k].toLocaleString("en-IN"), { x: ix + k * bw, y: base - h - 0.27, w: bw, h: 0.24, fontSize: 11, bold: true, align: "center" });
          tx(s, LADDER_NAME[k], { x: ix + k * bw - 0.05, y: base + 0.05, w: bw + 0.1, h: 0.22, fontSize: 9, color: HEX.MUTED, align: "center" });
        });
      }
      line(s, ix, top + 2.05, ix + iw, top + 2.05, HEX.LINE, 0.75, `idea rule ${i}`);
      tx(s, title, { x: ix, y: top + 2.13, w: iw, h: 0.32, fontSize: 16, bold: true });
      mono(s, fig, { x: ix, y: top + 2.45, w: iw, h: 0.28, fontSize: 10, color: HEX.INK2 });
    });
    // results strip
    const rw = CW / 4;
    [["100%", "of bad merchants caught (vs 20%)"], ["0 of 920", "honest shops penalised"], ["62% → 1%", "Diwali false alarms"], ["7 days", "median time to act"]].forEach(([n, l], k) => {
      mono(s, n, { x: M + k * rw, y: 3.98, w: rw - 0.2, h: 0.45, fontSize: 24, bold: true });
      tx(s, l, { x: M + k * rw, y: 4.43, w: rw - 0.2, h: 0.3, fontSize: 12, color: HEX.INK2 });
    });
    fill(s, {
      caption: "Results from a simulated world of 1,000 merchants over 37 weeks, calibrated to real NPCI data",
      title: "Compare with peers, follow the links, ask before punishing",
      body: "Every flag comes with a reason in plain English; money is held only with a second source of evidence and a human",
    });
    s.addNotes("This is what Trace does, in three ideas. First, compare with peers: ten weekly signals such as match hours, late nights, round amounts and payers from other states, each compared with similar shops in the same week. " +
      "A restaurant screening IPL matches trips two; a betting front trips seven. Each signal is capped, so several have to agree. " +
      "Second, follow the links: fronts come in families that share phones, bank accounts and gamblers. Starting from UPI IDs posted on betting pages, Trace found 93 percent of the fronts that were on no list. " +
      "Third, ask before you punish: most merchants see nothing, a changed shop gets a two-minute question, and money is held only with a second source of evidence and a human decision. " +
      "The results, from a simulated world calibrated to real NPCI data: every front and rented account caught, against 20 percent for a typical detector; none of 920 honest shops penalised; Diwali false alarms down from 62 percent to 1; and action in a median of 7 days.");
  }

  // 8 ── 07 Financial implementation and costs
  pres.addSection({ title: "07 Financial implementation and costs" });
  {
    const s = card("07 Financial implementation and costs", "07   Financial implementation and costs");
    const run = BASE.running, per = run.per_merchant;
    mono(s, `₹${per.toFixed(1)}`, { x: M, y: 1.0, w: 4.2, h: 1.25, fontSize: 80, bold: true, color: HEX.INK, objectName: "per merchant" });
    tx(s, "per merchant per year to run", { x: M, y: 2.3, w: 4.2, h: 0.4, fontSize: 16, color: HEX.INK2 });
    [[`₹${(BASE.implementation.total / 1e7).toFixed(2)} crore`, "to implement, over 9 months"], [`₹${(run.total / 1e7).toFixed(2)} crore`, "a year to run"]].forEach(([a, b], i) => {
      mono(s, a, { x: M + i * 2.15, y: 3.2, w: 2.1, h: 0.45, fontSize: 20, bold: true });
      tx(s, b, { x: M + i * 2.15, y: 3.65, w: 2.0, h: 0.5, fontSize: 12, color: HEX.MUTED });
    });
    // where the money goes: one bar split by component
    const bx = 5.35, bw = SW - M - bx;
    mono(s, "Where the running cost goes", { x: bx, y: 1.1, w: bw, h: 0.3, fontSize: 12, color: HEX.MUTED });
    const parts = [["Analyst desk", run.lines["Analyst desk"], HEX.BLUE], ["Model team", run.lines["Model and engineering team"], "4A6FA8"],
      ["Cloud", run.lines["Cloud and data"], HEX.GREY], ["Other", run.lines["Audit, software and other"], "4A4A51"]];
    let x = bx;
    parts.forEach(([n, v, col], i) => {
      const w = bw * v / run.total;
      rect(s, x, 1.6, w - 0.04, 0.55, col, { objectName: `cost ${i}` });
      const last = i === parts.length - 1, lx = last ? SW - M - 1.0 : x, lw = last ? 1.0 : w - 0.1, al = last ? "right" : "left";
      tx(s, n, { x: lx, y: 2.25, w: lw, h: 0.3, fontSize: 12, color: HEX.INK2, align: al });
      mono(s, `₹${(v / 1e5).toFixed(0)} L`, { x: lx, y: 2.55, w: lw, h: 0.3, fontSize: 13, bold: true, align: al });
      x += w;
    });
    panel(s, bx, 3.2, bw, 1.3, "break-even");
    tx(s, [{ text: "Pays for itself ", options: { bold: true } },
      { text: `if it prevents one FIU-IND-scale penalty (₹5.49 crore) every ${(1 / BASE.penalties_to_break_even).toFixed(1)} years, before counting analyst time saved or honest shops protected` }],
      { x: bx + 0.3, y: 3.38, w: bw - 0.6, h: 0.95, fontSize: 14, color: HEX.INK2, valign: "middle" });
    fill(s, {
      caption: "A payment provider with 20 lakh merchants; planning estimates, every assumption in appendix M",
      title: "About ₹9 per merchant per year",
      body: [{ text: "Catch the fronts. Protect the shops.", options: { bold: true, color: HEX.INK } },
        { text: "   A six-month pilot on a provider's own data comes first" }],
    });
    s.addNotes("What does it cost? For a mid-size payment provider with 20 lakh merchants: about 2.15 crore rupees to implement over nine months, including a three-month shadow pilot, and about 1.88 crore a year to run. " +
      "That's roughly 9 rupees per merchant per year. Most of it is people: the analyst desk and a small model team. Cloud is about 29 lakh a year. " +
      "It pays for itself if it prevents one penalty the size of FIU-IND's fine on Paytm Payments Bank every 2.4 years. Every assumption is in appendix M. " +
      "To close: the plan is a six-month pilot on a provider's own data, then richer checks such as GST, then sharing across providers. Catch the fronts. Protect the shops.");
  }

  await pres.writeFile({ fileName: OUT });
}

// Morph between slides (PowerPoint 2019 / 365), with a fade for older versions. Shapes that keep the same name on
// consecutive slides (the comparison grid on 4 and 5) move into place instead of cutting.
async function addMorph(file) {
  const JSZip = require("jszip");
  const zip = await JSZip.loadAsync(fs.readFileSync(file));
  const names = Object.keys(zip.files).filter((n) => /^ppt\/slides\/slide\d+\.xml$/.test(n));
  const tr = '<mc:AlternateContent xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006">' +
    '<mc:Choice xmlns:p159="http://schemas.microsoft.com/office/powerpoint/2015/09/main" Requires="p159">' +
    '<p:transition spd="slow" xmlns:p14="http://schemas.microsoft.com/office/powerpoint/2010/main" p14:dur="1000"><p159:morph option="byObject"/></p:transition>' +
    '</mc:Choice><mc:Fallback><p:transition spd="slow"><p:fade/></p:transition></mc:Fallback></mc:AlternateContent>';
  for (const n of names) {
    let xml = await zip.file(n).async("string");
    if (xml.includes("<p:transition")) continue;
    if (xml.includes("</p:clrMapOvr>")) xml = xml.replace("</p:clrMapOvr>", "</p:clrMapOvr>" + tr);
    else xml = xml.replace("</p:cSld>", "</p:cSld>" + tr);
    zip.file(n, xml);
  }
  // drop bare folder entries (cloud viewers dislike them); zip.remove() would delete the folder's contents too
  Object.keys(zip.files).filter((n) => zip.files[n].dir).forEach((n) => delete zip.files[n]);
  fs.writeFileSync(file, await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
}

module.exports = { build, THEME, OUT };
if (require.main === module) {
  build().then(async () => {
    const { applyTheme } = require(process.env.PPTX_SKILL + "/scripts/apply_theme.js");
    await applyTheme(OUT, THEME);
    await addMorph(OUT);
    console.log("wrote", OUT);
  });
}
