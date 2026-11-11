// Shared look for Trace's Word appendices: text, tables, notes, images, numbered headings, a page-numbered
// contents page, title page and footer. Content files (fin_content.js, appendix_content.js) use these blocks.
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, BorderStyle, ShadingType,
  AlignmentType, HeadingLevel, ImageRun, Footer, PageBreak, InternalHyperlink, Bookmark, PageNumber, LevelFormat,
  TableLayoutType, Tab, TabStopType,
} = require("docx");

const C = { INK: "1C1C1F", INK2: "4A4A52", MUTED: "6E6E76", LINE: "DCDDE2", HEAD: "F1F2F5", ACCENT: "1F5FAE", NOTE: "F3F6FB" };
const FONT = "Arial";
const W = 9026; // A4 width minus 1" margins, in DXA
const RIGHT = AlignmentType.RIGHT, CENTER = AlignmentType.CENTER;

// Indian number formats
const LAKH = 1e5, CRORE = 1e7;
const grp = (n, d = 0) => Number(n).toLocaleString("en-IN", { minimumFractionDigits: d, maximumFractionDigits: d });
const fmt = {
  grp, L: (v, d = 1) => grp(v / LAKH, d), cr: (v, d = 2) => `₹${grp(v / CRORE, d)} crore`,
  lakh: (v, d = 1) => `₹${grp(v / LAKH, d)} lakh`, rs: (v) => `₹${grp(v)}`, rs1: (v) => `₹${grp(v, 1)}`,
  pct: (v, d = 0) => `${(v * 100).toFixed(d)}%`, LAKH, CRORE,
};

function makeLib() {
  const toc = [];
  const t = (text, o = {}) => new TextRun({ text, font: FONT, ...o });
  const runs = (c, o = {}) => (typeof c === "string" ? [t(c, o)] : c);
  const p = (children, o = {}) => new Paragraph({ children: runs(children), spacing: { after: 120, line: 288 }, ...o });
  const body = (text, o = {}) => p(runs(text, { color: C.INK }), o);
  const lead = (text) => body(text, { keepNext: true });      // a sentence that introduces the table below it
  const small = (text) => p([t(text, { size: 17, color: C.MUTED })], { spacing: { before: 0, after: 200 } });
  const bullet = (children) => new Paragraph({ children: runs(children), numbering: { reference: "bullets", level: 0 },
    spacing: { after: 80, line: 276 } });
  const strong = (text) => t(text, { bold: true });
  const label = (text) => p([strong(text)], { spacing: { before: 120, after: 60 }, keepNext: true });

  // level 1 = appendix (A, B, ...), level 2 = section (A.1), level 3 = sub-section (not in the contents)
  function heading(level, num, text, id, o = {}) {
    if (level <= 2) toc.push({ level, num, text, id });
    const hl = [HeadingLevel.HEADING_1, HeadingLevel.HEADING_2, HeadingLevel.HEADING_3][level - 1];
    const inner = [t(`${num}  ${text}`)];
    return new Paragraph({ heading: hl, children: level <= 2 ? [new Bookmark({ id, children: inner })] : inner,
      pageBreakBefore: !!o.pageBreak, spacing: o.spacing });
  }

  const border = { style: BorderStyle.SINGLE, size: 4, color: C.LINE };
  const borders = { top: border, bottom: border, left: border, right: border };
  function cell(text, width, o = {}) {
    const { bold = false, fill, align = AlignmentType.LEFT, color = C.INK, size = 18, topRule = false, keepNext = false } = o;
    return new TableCell({
      width: { size: width, type: WidthType.DXA },
      borders: topRule ? { ...borders, top: { style: BorderStyle.SINGLE, size: 10, color: C.INK2 } } : borders,
      shading: fill ? { fill, type: ShadingType.CLEAR, color: "auto" } : undefined,
      margins: { top: 70, bottom: 70, left: 110, right: 110 },
      children: [new Paragraph({ alignment: align, spacing: { after: 0, line: 264 }, keepNext,
        children: [t(String(text), { bold, color, size })] })],
    });
  }
  // cols: [{w, align}] widths in DXA summing to W; opts.totals: indexes of total rows (bold, rule above)
  function table(header, rows, cols, opts = {}) {
    const totals = new Set(opts.totals || []);
    const keep = rows.length <= 12;
    const hdr = new TableRow({ tableHeader: true, cantSplit: true, children: header.map((h, i) =>
      cell(h, cols[i].w, { bold: true, fill: C.HEAD, align: cols[i].align || AlignmentType.LEFT, color: C.INK2, size: 17, keepNext: true })) });
    const rws = rows.map((r, ri) => new TableRow({ cantSplit: true, children: r.map((c, i) =>
      cell(c, cols[i].w, { align: cols[i].align || AlignmentType.LEFT, bold: totals.has(ri), topRule: totals.has(ri),
        keepNext: keep && ri < rows.length - 1 })) }));
    return [new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: cols.map((c) => c.w),
      layout: TableLayoutType.FIXED, rows: [hdr, ...rws] }), new Paragraph({ children: [], spacing: { after: 100 } })];
  }
  // a two-column "term | meaning" table with even widths, a common shape in the appendix
  const pairs = (header, rows, w0 = 2800) => table(header, rows, [{ w: w0 }, { w: W - w0 }]);

  const note = (children) => new Paragraph({
    children: runs(children, { color: C.INK2, size: 19 }),
    shading: { fill: C.NOTE, type: ShadingType.CLEAR, color: "auto" },
    border: { left: { style: BorderStyle.SINGLE, size: 18, color: C.ACCENT, space: 8 } },
    indent: { left: 160, right: 160 }, spacing: { before: 120, after: 200, line: 288 },
  });
  const image = (file, wIn, hIn) => new Paragraph({ alignment: CENTER, spacing: { before: 120, after: 60 }, keepNext: true,
    children: [new ImageRun({ type: "png", data: fs.readFileSync(file), transformation: { width: wIn * 96, height: hIn * 96 } })] });
  const caption = (text) => p([t(text, { size: 17, color: C.MUTED })], { alignment: CENTER, spacing: { after: 200 } });
  const code = (text) => new Paragraph({ children: [t(text, { font: "Courier New", size: 18, color: C.INK2 })],
    shading: { fill: C.HEAD, type: ShadingType.CLEAR, color: "auto" }, indent: { left: 160, right: 160 },
    spacing: { before: 60, after: 160, line: 276 }, keepNext: true });

  function tocLine(e, pages) {
    const page = pages[e.id] != null ? String(pages[e.id]) : "00";
    const l1 = e.level === 1;
    return new Paragraph({
      spacing: { before: l1 ? 140 : 30, after: 30 }, indent: { left: l1 ? 0 : 440 },
      tabStops: [{ type: TabStopType.RIGHT, position: W, leader: "dot" }],
      children: [new InternalHyperlink({ anchor: e.id, children: [
        t(`${e.num}  ${e.text}`, { bold: l1, color: l1 ? C.INK : C.INK2, size: l1 ? 21 : 19 }),
        new TextRun({ font: FONT, bold: l1, color: l1 ? C.INK : C.INK2, size: l1 ? 21 : 19, children: [new Tab(), page] }),
      ] })],
    });
  }

  // title: {kicker, title, subtitle, meta: [lines], note}
  async function build({ title, content, pages = {}, out, footerText }) {
    const tp = [
      new Paragraph({ spacing: { before: 2400, after: 120 }, children: [t(title.kicker, { size: 20, color: C.ACCENT, bold: true, characterSpacing: 40 })] }),
      new Paragraph({ spacing: { after: 200 }, children: [t(title.title, { size: 52, bold: true, color: C.INK })] }),
      new Paragraph({ spacing: { after: 600 }, children: [t(title.subtitle, { size: 26, color: C.INK2 })] }),
      new Paragraph({ border: { top: { style: BorderStyle.SINGLE, size: 6, color: C.LINE, space: 12 } }, spacing: { after: 80 },
        children: [t(title.meta[0], { size: 20, color: C.INK2 })] }),
      new Paragraph({ spacing: { after: 800 }, children: [t(title.meta[1], { size: 20, color: C.MUTED })] }),
      note(title.note),
      new Paragraph({ children: [new PageBreak()] }),
    ];
    const contents = [new Paragraph({ spacing: { after: 240 }, children: [t("Contents", { size: 36, bold: true, color: C.INK })] }),
      ...toc.map((e) => tocLine(e, pages))];
    const footer = new Footer({ children: [new Paragraph({ border: { top: { style: BorderStyle.SINGLE, size: 4, color: C.LINE, space: 6 } },
      tabStops: [{ type: TabStopType.RIGHT, position: W }],
      children: [t(footerText, { size: 16, color: C.MUTED }),
        new TextRun({ font: FONT, size: 16, color: C.MUTED, children: [new Tab(), PageNumber.CURRENT] })] })] });
    const doc = new Document({
      creator: "Trace", title: title.title,
      styles: {
        default: { document: { run: { font: FONT, size: 21, color: C.INK } } },
        paragraphStyles: [
          { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
            run: { font: FONT, size: 34, bold: true, color: C.INK }, paragraph: { spacing: { before: 0, after: 200 }, keepNext: true, outlineLevel: 0 } },
          { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
            run: { font: FONT, size: 24, bold: true, color: C.ACCENT }, paragraph: { spacing: { before: 320, after: 120 }, keepNext: true, outlineLevel: 1 } },
          { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
            run: { font: FONT, size: 21, bold: true, color: C.INK }, paragraph: { spacing: { before: 240, after: 100 }, keepNext: true, outlineLevel: 2 } },
        ],
      },
      numbering: { config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
        alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 440, hanging: 260 } } } }] }] },
      sections: [{
        properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1300, bottom: 1300, left: 1440, right: 1440 } }, titlePage: true },
        footers: { default: footer, first: new Footer({ children: [new Paragraph({ children: [] })] }) },
        children: [...tp, ...contents, new Paragraph({ children: [new PageBreak()] }), ...content],
      }],
    });
    const buf = await Packer.toBuffer(doc);
    fs.writeFileSync(out, buf);
    fs.writeFileSync(out.replace(/\.docx$/, ".toc.json"), JSON.stringify(toc));
    console.log("wrote", out);
  }

  return { t, p, body, lead, small, bullet, strong, label, heading, table, pairs, note, image, caption, code, build, W, RIGHT, CENTER, C };
}

module.exports = { makeLib, fmt };
