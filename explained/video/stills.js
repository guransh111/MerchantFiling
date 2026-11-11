// node stills.js <html> <outdir> t1 t2 ...  -> PNG frames rendered exactly at those times
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const [html, out, ...ts] = process.argv.slice(2);
  const b = await chromium.launch();
  const pg = await b.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  pg.on('pageerror', e => console.log('PAGE ERROR', e.message));
  await pg.goto('file://' + path.resolve(html) + '?manual');
  await pg.waitForFunction(() => window.__ready === true, null, { timeout: 30000 });
  for (const t of ts) {
    await pg.evaluate((t) => window.__renderAt(+t), t);
    await pg.locator('canvas').screenshot({ path: `${out}/f_${String(t).padStart(5, '0')}.png` });
  }
  await b.close();
})();
