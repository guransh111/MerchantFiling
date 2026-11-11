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
      "In the 1xBet case the Enforcement Directorate found more than six thousand mule accounts, and CUTS reports UPI is now the main deposit channel for illegal betting.");
  }

  // 4 ── 02 Problem: both ways to fail
  {
    const s = card("02 Problem", "02   Problem");
    const pw = (CW - 0.4) / 2;
    // left: too lax, money streams through
    panel(s, M, 1.1, pw, 3.6, "lax panel");
    mono(s, "Too lax", { x: M + 0.35, y: 1.35, w: 3, h: 0.3, fontSize: 12, color: HEX.RED });
    tx(s, "Fronts keep collecting bets", { x: M + 0.35, y: 1.7, w: pw - 0.7, h: 0.45, fontSize: 20, bold: true });
    line(s, M + 0.35, 3.05, M + pw - 0.35, 3.05, HEX.LINE, 2, "lax wire");
    for (let i = 0; i < 9; i++) dot(s, M + 0.6 + i * ((pw - 1.2) / 8), 3.05, 0.09, HEX.RED, `lax money ${i}`);
    tx(s, "Regulators fine the provider: FIU-IND fined Paytm Payments Bank ₹5.49 crore over gambling money (2024)",
      { x: M + 0.35, y: 3.5, w: pw - 0.7, h: 0.8, fontSize: 13, color: HEX.INK2 });
    // right: too strict, an honest Diwali spike frozen
    const rx = M + pw + 0.4;
    panel(s, rx, 1.1, pw, 3.6, "strict panel");
    mono(s, "Too strict", { x: rx + 0.35, y: 1.35, w: 3, h: 0.3, fontSize: 12, color: HEX.GOLD });
    tx(s, "Honest shops get frozen", { x: rx + 0.35, y: 1.7, w: pw - 0.7, h: 0.45, fontSize: 20, bold: true });
    const heights = [0.22, 0.25, 0.2, 0.27, 0.24, 0.3, 0.95, 0.28];
    heights.forEach((h, i) => rrect(s, rx + 0.45 + i * 0.42, 3.3 - h, 0.28, h, i === 6 ? HEX.GOLD : HEX.GREY, 0.04, { objectName: `sales ${i}` }));
    mono(s, "Diwali", { x: rx + 0.45 + 6 * 0.42 - 0.2, y: 3.38, w: 0.7, h: 0.25, fontSize: 10, color: HEX.MUTED, align: "center" });
    rrect(s, rx + pw - 1.35, 2.3, 0.8, 0.8, HEX.RAISED, 0.12, { objectName: "lock tile" });
    s.addImage({ data: ICON.lock, x: rx + pw - 1.17, y: 2.48, w: 0.44, h: 0.44, objectName: "lock" });
    tx(s, "A sweet shop's festival rush looks like a spike, and freezing its money can ruin it",
      { x: rx + 0.35, y: 3.75, w: pw - 0.7, h: 0.6, fontSize: 13, color: HEX.INK2 });
    fill(s, {
      caption: "₹500 to a kirana is not suspicious on its own, and Diwali triples honest sales",
      title: "Each payment looks normal, and honest shops change too",
      body: "A good system has to catch the fronts and protect honest merchants at the same time",
    });
    s.addNotes("Why is this hard? Each payment looks normal: 500 rupees to a kirana proves nothing. And honest shops change too: Diwali, a restaurant screening IPL matches, a shop that starts delivery. " +
      "Get it wrong one way and fronts keep collecting bets while regulators fine the provider; FIU-IND fined Paytm Payments Bank 5.49 crore over gambling money. " +
      "Get it wrong the other way and you freeze an honest sweet shop in its busiest week. The challenge asks for both goals at once.");
  }

  // grid shared by slides 5 and 6 (Morph shrinks it to make room for the numbers)
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

  // 5 ── 03 Current solutions
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

  // 6 ── 04 The gap
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
      "A sales-spike rule flags 62 percent of honest sweet and electronics shops in Diwali week. Trace fills exactly the empty columns, shown in blue.");
  }

  // 7 ── 05 Introducing Trace
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

  // 8 ── 06 What Trace does: ten signals
  pres.addSection({ title: "06 What Trace does" });
  const SIGNALS = ["Match hours", "Late night", "Round amounts", "Other states", "Repeat payers", "Fixed stakes", "Same-day out", "Many payouts", "Sales growth", "Size vs declared"];
  {
    const s = card("06 What Trace does", "06   What Trace does");
    const rows = [["Restaurant screening IPL matches", [0, 1], "Monitor or Ask", HEX.BLUE],
                  ["Betting front posing as a kirana", [0, 1, 2, 3, 4, 5, 6], "Review", HEX.ORANGE]];
    const sq = 0.58, gap = 0.15, gx = M + 3.45;
    rows.forEach(([name, lit, verdict, col], r) => {
      const y = 1.35 + r * 1.55;
      tx(s, name, { x: M, y, w: 3.3, h: sq, fontSize: 15, bold: true, valign: "middle" });
      SIGNALS.forEach((_, i) => rrect(s, gx + i * (sq + gap), y, sq, sq, lit.includes(i) ? HEX.ORANGE : HEX.TRACK, 0.08, { objectName: `signal ${r}-${i}` }));
      mono(s, `${lit.length} of 10`, { x: gx + 10 * (sq + gap) + 0.15, y, w: 1.2, h: 0.32, fontSize: 16, bold: true });
      tx(s, verdict, { x: gx + 10 * (sq + gap) + 0.15, y: y + 0.32, w: 1.6, h: 0.3, fontSize: 12, color: col });
    });
    SIGNALS.forEach((n, i) => tx(s, n, { x: gx + i * (sq + gap) - 0.06, y: 4.2, w: sq + 0.12, h: 0.55, fontSize: 10, color: HEX.MUTED, align: "center", valign: "top" }));
    fill(s, {
      caption: "Each signal adds at most 4 points, so no single one can condemn a shop",
      title: "One odd signal is a story; seven together are a pattern",
      body: "Ten weekly signals, each compared with similar shops in the same week",
    });
    s.addNotes("Trace measures ten weekly signals: match hours, late nights, round amounts, payers from other states, repeat payers, fixed stake sizes, money out the same day, many payout accounts, growth, and size versus what was declared. " +
      "A restaurant screening IPL matches trips two of them. A betting front trips six or seven. Each signal is capped, so no single one can condemn a shop; several have to agree, like a credit analyst who ignores one late payment but not a pattern.");
  }

  // 9 ── 06 What Trace does: follow the links
  {
    const s = card("06 What Trace does", "06   What Trace does");
    const c = [6.65, 2.85];
    const fronts = [[4.2, 1.55, "Same phone"], [3.7, 3.6, "Same bank account"], [8.9, 1.45, "Shared gamblers"], [9.9, 3.75, ""], [6.3, 4.05, ""], [5.0, 2.55, ""]];
    fronts.forEach(([x, y, l], i) => {
      line(s, c[0], c[1], x, y, HEX.TRACK, 2, `link ${i}`);
      if (l) tx(s, l, { x: (c[0] + x) / 2 - 0.9, y: (c[1] + y) / 2 - 0.32, w: 1.8, h: 0.25, fontSize: 10, color: HEX.MUTED, align: "center" });
    });
    line(s, 4.2, 1.55, 5.0, 2.55, HEX.TRACK, 1.5, "link family");
    fronts.forEach(([x, y], i) => dot(s, x, y, 0.17, HEX.ORANGE, `front ${i}`));
    ring(s, 4.2, 1.55, 0.28, HEX.ORANGE, "this kirana halo", 1.25);
    tx(s, "The Pune kirana", { x: 2.4, y: 1.0, w: 2.2, h: 0.3, fontSize: 12, color: HEX.INK2, align: "right" });
    dot(s, c[0], c[1], 0.36, HEX.RED, "known bad");
    [[1.4, 1.6], [1.9, 4.2], [11.2, 2.4], [11.8, 4.1], [2.6, 2.7], [11.0, 1.2]].forEach(([x, y], i) => ring(s, x, y, 0.15, HEX.GREY, `honest ${i}`, 1.5));
    // legend: same pattern as the results slide
    dot(s, M + 0.1, 4.63, 0.08, HEX.RED); tx(s, "Known betting account (UPI ID found on a betting page)", { x: M + 0.28, y: 4.5, w: 4.6, h: 0.26, fontSize: 11, color: HEX.INK2 });
    dot(s, M + 5.1, 4.63, 0.07, HEX.ORANGE); tx(s, "Linked front", { x: M + 5.28, y: 4.5, w: 1.6, h: 0.26, fontSize: 11, color: HEX.INK2 });
    ring(s, M + 7.1, 4.63, 0.07, HEX.GREY, "legend ring", 1.25); tx(s, "Honest shop: no links", { x: M + 7.28, y: 4.5, w: 2.4, h: 0.26, fontSize: 11, color: HEX.INK2 });
    fill(s, {
      caption: "93% of fronts not on any known list were found this way",
      title: "Fronts come in families, so Trace follows the links",
      body: "From one UPI ID posted on a betting page, suspicion spreads along shared phones, bank accounts and gamblers",
    });
    s.addNotes("Fronts come in families: one operator runs many of them, and they share phones, bank accounts and gamblers. " +
      "Some fronts' UPI IDs are posted openly on betting pages; Trace treats those as known bad and follows the links outward. Our Pune kirana shares a phone with one of them. " +
      "Honest shops have no such links. In the simulation, 93 percent of the fronts that were not on any known list were found through the network.");
  }

  // 10 ── 06 What Trace does: the ladder
  {
    const s = card("06 What Trace does", "06   What Trace does");
    const counts = [937, 12, 2, 49, 0];
    const cost = ["Nothing visible", "A 2-minute question", "Lower limits, T+2", "20% reserve and a human", "Only after a human confirms"];
    const bw = 2.12, g = 0.37, base = 3.55;
    LADDER.forEach((col, i) => {
      const h = 0.45 + i * 0.5, x = M + i * (bw + g);
      rrect(s, x, base - h, bw, h, col, 0.08, { objectName: `step ${i}` });
      mono(s, counts[i].toLocaleString("en-IN"), { x, y: base - h - 0.5, w: bw, h: 0.42, fontSize: 22, bold: true, align: "center" });
      tx(s, LADDER_NAME[i], { x, y: base + 0.15, w: bw, h: 0.36, fontSize: 16, bold: true, align: "center" });
      tx(s, cost[i], { x, y: base + 0.52, w: bw, h: 0.55, fontSize: 12, color: HEX.INK2, align: "center" });
    });
    fill(s, {
      caption: "937 of 1,000 merchants see no action at all",
      title: "Ask before you punish",
      body: "Money is held only with a second source of evidence, and only a human can close an account",
    });
    s.addNotes("And Trace never punishes first. There is a ladder. Most merchants see nothing. A shop that looks different gets a neutral question: 'what's changed?', which takes two minutes. " +
      "Next comes friction: lower limits and slower settlement, but payments keep working. Holding money needs a second, independent source of evidence and a human investigator, and only a human can close an account. " +
      "In the demo, 937 of 1,000 merchants see no action at all.");
  }

  // 11 ── 06 What Trace does: results
  {
    const s = card("06 What Trace does", "06   What Trace does");
    // 1,000 merchants as dots: 950 honest stay grey, the 50 fronts and rented accounts are caught
    let seed = 11; const rnd = () => ((seed = (seed * 9301 + 49297) % 233280) / 233280);
    const bad = new Set(); while (bad.size < 50) bad.add(Math.floor(rnd() * 1000));
    const cols = 50, step = 0.128, r = 0.044, gx = M + 0.05, gy = 1.1;
    for (let i = 0; i < 1000; i++) {
      const x = gx + (i % cols) * step, y = gy + Math.floor(i / cols) * step;
      dot(s, x + r, y + r, r, bad.has(i) ? HEX.RED : HEX.TRACK, `m${i}`);
    }
    dot(s, M + 0.1, 4.03, 0.06, HEX.RED); tx(s, "Front or rented account: caught", { x: M + 0.25, y: 3.9, w: 3.2, h: 0.28, fontSize: 11, color: HEX.INK2 });
    dot(s, M + 3.6, 4.03, 0.06, HEX.TRACK); tx(s, "Honest shop: untouched", { x: M + 3.75, y: 3.9, w: 3, h: 0.28, fontSize: 11, color: HEX.INK2 });
    const sx = 7.55;
    [["100%", "of bad merchants caught", "vs 20% for a typical detector"], ["0 of 920", "honest shops penalised", ""],
     ["62% → 1%", "Diwali false alarms", "honest sweet and electronics shops"], ["7 days", "median time to act", "replayed week by week, no hindsight"]].forEach(([n, a, b], i) => {
      const x = sx + (i % 2) * 2.7, y = 1.0 + Math.floor(i / 2) * 1.75;
      mono(s, n, { x, y, w: 2.6, h: 0.65, fontSize: 30, bold: true });
      tx(s, a, { x, y: y + 0.66, w: 2.55, h: 0.3, fontSize: 14 });
      if (b) tx(s, b, { x, y: y + 0.98, w: 2.55, h: 0.5, fontSize: 11, color: HEX.MUTED });
    });
    fill(s, {
      caption: "Simulated world of 1,000 merchants over 37 weeks, calibrated to real NPCI data",
      title: "Every front caught, no honest shop penalised",
      body: "Proof that the method works as designed; a pilot on a provider's own data measures real-world accuracy",
    });
    s.addNotes("Results. This is the simulated world: a thousand merchants over 37 weeks, calibrated to real NPCI data. The fifty red dots are the betting fronts and rented accounts: Trace caught all of them, against 20 percent for a typical detector. " +
      "None of the 920 ordinary honest shops was penalised. Diwali false alarms fall from 62 percent to 1. And replayed week by week with no hindsight, Trace acts in a median of 7 days. " +
      "Be upfront: the data is simulated, so this shows the method works as designed; a pilot on real data measures real accuracy.");
  }

  // 12 ── 07 Financial implementation and costs
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
      body: "People are most of the cost; Trace needs little computing and no paid model licences",
    });
    s.addNotes("What does it cost? For a mid-size payment provider with 20 lakh merchants: about 2.15 crore rupees to implement over nine months, including a three-month shadow pilot, and about 1.88 crore a year to run. " +
      "That's roughly 9 rupees per merchant per year. Most of it is people: the analyst desk and a small model team. Cloud is about 29 lakh a year. " +
      "It pays for itself if it prevents one penalty the size of FIU-IND's fine on Paytm Payments Bank every 2.4 years. Every assumption is in appendix M.");
  }

  // 13 ── Close
  pres.addSection({ title: "Close" });
  {
    const s = pres.addSlide({ masterName: "CARD", sectionTitle: "Close" });
    s.addText("Trace", { placeholder: "kicker" });
    const pw = (CW - 0.6) / 3;
    const cards = [["01", "Compare with peers", "57% vs 10% in match hours"], ["02", "Follow the links", "93% of unlisted fronts found"], ["03", "Ask before you punish", "0 of 920 honest shops penalised"]];
    cards.forEach(([n, t, f], i) => {
      const x = M + i * (pw + 0.3);
      panel(s, x, 1.0, pw, 3.6, `close card ${i}`);
      mono(s, n, { x: x + 0.3, y: 1.2, w: 1, h: 0.3, fontSize: 12, color: HEX.MUTED });
      if (i === 0) { bar(s, x + 0.3, 2.0, pw - 0.6, 0.18, 1, HEX.ORANGE, "c bar a"); bar(s, x + 0.3, 2.45, pw - 0.6, 0.18, 0.1 / 0.57, HEX.GREY, "c bar b"); }
      if (i === 1) { const cx = x + pw / 2, cy = 2.3; [[-1.0, -0.4], [-0.8, 0.45], [0.95, -0.35]].forEach(([dx, dy], k) => { line(s, cx, cy, cx + dx, cy + dy, HEX.TRACK, 1.5); dot(s, cx + dx, cy + dy, 0.11, HEX.ORANGE); }); dot(s, cx, cy, 0.2, HEX.RED); ring(s, cx + 1.3, cy + 0.4, 0.1, HEX.GREY); }
      if (i === 2) LADDER.forEach((col, k) => rrect(s, x + 0.3 + k * ((pw - 0.6) / 5), 2.8 - (0.15 + k * 0.17), (pw - 0.6) / 5 - 0.08, 0.15 + k * 0.17, col, 0.04));
      tx(s, t, { x: x + 0.3, y: 3.15, w: pw - 0.6, h: 0.45, fontSize: 18, bold: true });
      mono(s, f, { x: x + 0.3, y: 3.65, w: pw - 0.6, h: 0.6, fontSize: 12, color: HEX.INK2 });
    });
    fill(s, {
      caption: "Pilot (0 to 6 months)  →  Enrich (6 to 12)  →  Ecosystem (12 to 24)",
      title: "Catch the fronts. Protect the shops.",
      body: "Live dashboard, full method and costs in the appendix",
    });
    s.addNotes("To close: Trace compares every shop with similar shops, follows the links between fronts, and asks before it punishes. " +
      "The plan is a six-month pilot on a provider's own data, then richer checks such as GST, then sharing across providers. Catch the fronts. Protect the shops.");
  }

  await pres.writeFile({ fileName: OUT });
}

// Morph between slides (PowerPoint 2019 / 365), with a fade for older versions. Shapes that keep the same name on
// consecutive slides (the payment flow on 2 and 3, the comparison grid on 5 and 6) move into place instead of cutting.
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
