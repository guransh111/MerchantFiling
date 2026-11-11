// Standalone financial appendix (Word). Usage: node build_docx.js <out.docx> [pages.json]
const fs = require("fs");
const path = require("path");
const { makeLib } = require("./lib");
const { finContent } = require("./fin_content");

const OUT = process.argv[2] || path.join(__dirname, "..", "Trace_Appendix_Financials.docx");
const PAGES = process.argv[3] && fs.existsSync(process.argv[3]) ? JSON.parse(fs.readFileSync(process.argv[3], "utf8")) : {};
const lib = makeLib();
const content = finContent(lib, { prefix: "", base: 1, idp: "s" });

lib.build({
  out: OUT, pages: PAGES, content, footerText: "Trace · Appendix: Implementation and running costs",
  title: {
    kicker: "TRACE", title: "Appendix: Implementation and Running Costs",
    subtitle: "What it costs a payment aggregator to deploy and operate Trace, with every assumption stated",
    meta: ["Merchant Legitimacy Challenge", "November 2026"],
    note: "All figures are planning estimates in Indian rupees (1 lakh = ₹1,00,000; 1 crore = ₹1,00,00,000), built from the " +
      "assumptions in section 3. They are not vendor quotes. The model that produces every table is " +
      "explained/financials/model.py in the Trace repository.",
  },
});
