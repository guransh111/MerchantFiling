// The full Trace appendix (Word). Usage: node build_appendix.js <out.docx> [pages.json]
const fs = require("fs");
const path = require("path");
const { makeLib } = require("./lib");
const { appendixContent } = require("./appendix_content");

const OUT = process.argv[2] || path.join(__dirname, "..", "Trace_Appendix.docx");
const PAGES = process.argv[3] && fs.existsSync(process.argv[3]) ? JSON.parse(fs.readFileSync(process.argv[3], "utf8")) : {};
const lib = makeLib();
const content = appendixContent(lib);

lib.build({
  out: OUT, pages: PAGES, content, footerText: "Trace · Appendix",
  title: {
    kicker: "TRACE", title: "Appendix",
    subtitle: "The reasoning, method, results, operations and costs behind Trace: finding UPI merchants whose money doesn't " +
      "match the business they declared, without punishing honest shops",
    meta: ["Merchant Legitimacy Challenge", "November 2026"],
    note: "Results in this appendix come from a simulated world of 1,000 merchants over 37 weeks, calibrated to real NPCI " +
      "category data and real enforcement cases. They show the method working as designed, not real-world accuracy. Costs are " +
      "planning estimates in Indian rupees from stated assumptions (appendix M).",
  },
});
