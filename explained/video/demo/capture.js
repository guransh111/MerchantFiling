// Captures the dashboard for the demo film: for each page a full-length screenshot (main area made scrollable as one
// page), the sidebar, and the boxes of the elements the camera and cursor go to. Usage:
//   node capture.js <app url> <out dir>
const { chromium } = require('playwright');
const fs = require('fs');
const DSF = 1.5;
(async () => {
  const [url, out] = process.argv.slice(2);
  fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch();
  const pg = await b.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: DSF, colorScheme: 'dark' });
  pg.on('pageerror', e => console.log('PAGE ERROR', e.message));
  for (let i = 0; i < 30; i++) { try { await pg.goto(url); break; } catch { await new Promise(r => setTimeout(r, 2000)); } }
  await pg.waitForSelector('text=Open the risk queue', { timeout: 300000 });
  await pg.waitForTimeout(6000); // let the opening intro finish
  const meta = {};
  const box = async (sel) => { const l = pg.locator(sel).first(); if (!(await l.count())) return null; const bb = await l.boundingBox(); return bb && [bb.x, bb.y, bb.width, bb.height]; };
  const nav = async (label) => {
    await pg.locator(`[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:has-text("${label}")`).first().click();
  };
  // make the main area one long page so a full-page screenshot holds everything
  const unscroll = async () => {
    await pg.addStyleTag({ content: `html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] { height: auto !important; overflow: visible !important; }` });
    await pg.waitForTimeout(800);
  };
  const shoot = async (name, waitText, boxes = {}, before) => {
    await pg.waitForSelector(`text=${waitText}`, { timeout: 180000 });
    await pg.waitForTimeout(3000);
    if (before) await before();
    await pg.evaluate(() => window.scrollTo(0, 0));
    const side = await box('[data-testid="stSidebar"]');
    await pg.screenshot({ path: `${out}/${name}_view.png` });
    await unscroll();
    await pg.screenshot({ path: `${out}/${name}_full.png`, fullPage: true });
    const m = { side, height: await pg.evaluate(() => document.documentElement.scrollHeight), nav: {}, boxes: {} };
    for (const label of ['Home', 'Overview', 'Risk queue', 'Merchant drill-down', 'Network', 'Case management', 'Scan a betting page', "Customer's payment screen"])
      m.nav[label] = await box(`[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:has-text("${label}")`);
    for (const [k, sel] of Object.entries(boxes)) m.boxes[k] = await box(sel);
    meta[name] = m;
    // put scrolling back for the next page
    await pg.reload(); await pg.waitForSelector('[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]', { timeout: 120000 }); await pg.waitForTimeout(6000);
  };

  await nav('Home');
  await shoot('home', 'Open the risk queue', { panel: 'iframe' });
  await nav('Overview');
  await shoot('overview', 'From 1,000 merchants', { funnel: '[data-testid="stMarkdownContainer"]:has-text("Every merchant, every week")', head: 'h5:has-text("From 1,000 merchants")' });
  await nav('Risk queue');
  await shoot('queue', 'Download all decisions', { table: '[data-testid="stDataFrame"]' });
  await nav('Merchant drill-down');
  await shoot('merchant', 'Analyst decision', { head: '.st-key-panel_mx_head', why: '.st-key-panel_mx_why',
    r1: 'div:text-is("Share of money received during cricket match hours")', r2: 'div:text-is("Share of incoming money sent straight out the same day")' });
  await nav('Network');
  await shoot('network', 'Centre the picture on', { centre: 'text=Centre the picture on', table: '[data-testid="stDataFrame"]' });
  await nav('Scan a betting page');
  await shoot('scan0', 'Load an example post', { button: 'button:has-text("Load an example post")' });
  await nav('Scan a betting page');
  await shoot('scan1', 'Load an example post', { found: 'text=UPI IDs found', table: '[data-testid="stDataFrame"]' }, async () => {
    await pg.locator('button:has-text("Load an example post")').first().click(); await pg.waitForSelector('text=UPI IDs found', { timeout: 60000 }); await pg.waitForTimeout(2500);
  });
  await nav('Case management');
  await shoot('cases', 'Work a case', { clock: '.st-key-panel_case_clock', health: '.st-key-panel_case_health', work: 'text=Work a case' });
  await nav("Customer's payment screen");
  await shoot('payer', 'Paying', { paying: 'text=Paying', warn: 'text=This merchant is registered as' });
  fs.writeFileSync(`${out}/meta.json`, JSON.stringify(meta, null, 1));

  // the Home animation, stepped frame by frame (its own playback has finished by now)
  await nav('Home'); await pg.waitForSelector('text=Open the risk queue', { timeout: 120000 }); await pg.waitForTimeout(6000);
  const frame = pg.frames().find(f => f !== pg.mainFrame());
  const total = await frame.evaluate(() => window.__TOTAL);
  fs.mkdirSync(`${out}/home_anim`, { recursive: true });
  const fps = 60, n = Math.ceil(total * fps);
  for (let i = 0; i <= n; i++) {
    await frame.evaluate((t) => window.__renderAt(t), i / fps);
    await pg.screenshot({ path: `${out}/home_anim/${String(i).padStart(4, '0')}.png` });
  }
  console.log('home animation frames', n + 1, 'total', total);
  await b.close();
})();
