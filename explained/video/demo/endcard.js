// Dumps the logo ending (from intro.html, with the tagline) as PNG frames. Usage: node endcard.js <intro.html> <out dir> [fps] [seconds]
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
(async () => {
  const [html, out, fpsArg, secArg] = process.argv.slice(2);
  const fps = +(fpsArg || 60), secs = +(secArg || 5.2);
  fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch();
  const pg = await b.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  await pg.goto('file://' + path.resolve(html) + '?manual');
  await pg.waitForFunction(() => window.__ready === true);
  await pg.evaluate(() => { window.__TAGLINE = true; });
  // the logo starts drawing at 43.45 s of the intro timeline
  const n = Math.round(secs * fps);
  for (let i = 0; i <= n; i++) {
    const b64 = await pg.evaluate((t) => { window.__renderAt(t); return document.getElementById("c").toDataURL("image/png").split(",")[1]; }, 43.3 + i / fps);
    fs.writeFileSync(`${out}/${String(i).padStart(4, '0')}.png`, Buffer.from(b64, 'base64'));
  }
  console.log('endcard frames', n + 1);
  await b.close();
})();
