// node export.js <html> <out.mp4> [fps]  -- steps the film's timeline frame by frame (no screen recording)
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
(async () => {
  const [html, out, fpsArg] = process.argv.slice(2);
  const fps = +(fpsArg || 60);
  const b = await chromium.launch();
  const pg = await b.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  pg.on('pageerror', e => console.log('PAGE ERROR', e.message));
  await pg.goto('file://' + path.resolve(html) + '?manual');
  await pg.waitForFunction(() => window.__ready === true, null, { timeout: 30000 });
  const total = await pg.evaluate(() => window.__TOTAL);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-i', '-',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '15', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });
  const n = Math.round(total * fps);
  for (let i = 0; i < n; i++) {
    const b64 = await pg.evaluate((t) => { window.__renderAt(t); return document.getElementById('c').toDataURL('image/png').split(',')[1]; }, i / fps);
    if (!ff.stdin.write(Buffer.from(b64, 'base64'))) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 600 === 0) console.log(`frame ${i}/${n}`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  await b.close();
  console.log('wrote', out);
})();
